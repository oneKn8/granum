"""Tests for the Granum FastAPI — serves CellPayload artifacts to the frontend."""
import json

import pytest
from fastapi.testclient import TestClient

from granum.web.api import app


def _payload() -> dict:
    return {
        "meta": {
            "id": "aetna_cardiac", "payer": "aetna", "diagnosis": "cardiac",
            "baselineOverturn": 0.9, "currentOverturn": 0.96,
            "generations": 8, "populationSize": 2, "apoptosisTotal": 10,
        },
        "strategies": [
            {
                "id": "aetna_cardiac__bcell_1", "cell": "aetna_cardiac", "generation": 0,
                "parentId": None, "label": "G0 — seed", "promptBody": "x",
                "mutationNote": None, "fitness": 0.96, "tag": "production",
                "status": "champion", "citations": ["CPB 0119"],
            }
        ],
        "rounds": [
            {
                "id": "tr_aetna_cardiac_g0", "cell": "aetna_cardiac", "generation": 0,
                "denialId": "d1", "candidateIds": ["aetna_cardiac__bcell_1"],
                "winnerId": "aetna_cardiac__bcell_1", "loserIds": [],
                "judgeRationale": "fb", "winnerAppeal": "letter",
            }
        ],
        "fitness": [
            {"generation": 0, "meanFitness": 0.9, "maxFitness": 0.9,
             "survivingCount": 1, "apoptosisCount": 0}
        ],
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "aetna_cardiac.json").write_text(json.dumps(_payload()))
    monkeypatch.setenv("GRANUM_DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_list_cells(client):
    r = client.get("/api/cells")
    assert r.status_code == 200
    cells = r.json()["cells"]
    assert len(cells) == 1
    assert cells[0]["id"] == "aetna_cardiac"
    assert cells[0]["currentOverturn"] == 0.96


def test_get_cell_payload(client):
    r = client.get("/api/cells/aetna_cardiac")
    assert r.status_code == 200
    p = r.json()
    assert p["meta"]["currentOverturn"] == 0.96
    assert p["strategies"][0]["status"] == "champion"
    assert {"id", "fitness", "status", "citations", "parentId"} <= set(p["strategies"][0])
    assert len(p["fitness"]) == 1


def test_get_unknown_cell_404(client):
    assert client.get("/api/cells/nope_nope").status_code == 404


def test_coevolution_empty_when_no_data(client):
    """Missing co-evolution data returns an empty-but-valid state, not 404.

    The frontend cell page fetches this unconditionally and treats non-200 as
    fatal, so an empty population must come back 200.
    """
    r = client.get("/api/cells/aetna_cardiac/coevolution")
    assert r.status_code == 200
    body = r.json()
    assert body == {"cell": "aetna_cardiac", "writers": [], "payers": []}


def _bcell_strategy(strategy_id: str, cell: str) -> dict:
    return {
        "id": strategy_id,
        "cell": cell,
        "status": "candidate",
        "fitness": 0.72,
        "generation": 1,
        "label": "G1 — red-queen seed",
        "promptBody": "appeal body text",
        "mutationNote": None,
        "parentId": None,
        "tag": "red_queen",
        "citations": ["CPB 0119"],
    }


@pytest.fixture
def coevolution_client(tmp_path, monkeypatch):
    """Fixture with ONLY a _coevolution.json file — no matching cell payload."""
    artifact = {
        "cell": "aetna_cardiac",
        "writers": [_bcell_strategy("aetna_cardiac__rq_writer_1", "aetna_cardiac")],
        "payers": [_bcell_strategy("aetna_cardiac__rq_payer_1", "aetna_cardiac")],
    }
    (tmp_path / "aetna_cardiac_coevolution.json").write_text(json.dumps(artifact))
    monkeypatch.setenv("GRANUM_DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_coevolution_endpoint_serves_artifact_when_present(coevolution_client):
    """Co-evolution endpoint returns the stored artifact when the file exists.

    Also verifies that /api/cells does not surface the _coevolution.json file
    as a cell entry (since no matching aetna_cardiac.json was written).
    """
    # Endpoint must return 200 with the stored artifact.
    r = coevolution_client.get("/api/cells/aetna_cardiac/coevolution")
    assert r.status_code == 200
    body = r.json()
    assert body["cell"] == "aetna_cardiac"
    assert len(body["writers"]) > 0
    assert len(body["payers"]) > 0

    # The coevolution file must not be listed as a cell.
    r_cells = coevolution_client.get("/api/cells")
    assert r_cells.status_code == 200
    cell_ids = [c["id"] for c in r_cells.json()["cells"]]
    assert "aetna_cardiac" not in cell_ids
