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


def test_coevolution_404_without_data(client):
    assert client.get("/api/cells/aetna_cardiac/coevolution").status_code == 404
