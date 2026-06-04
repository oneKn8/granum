"""Unit tests for atomic payload writes (live-grow: pollers never see a half file)."""
import json

from granum.web.payload_io import write_payload_atomic


def test_writes_valid_json(tmp_path):
    p = tmp_path / "aetna_cardiac.json"
    write_payload_atomic(p, {"meta": {"id": "x"}, "strategies": []})
    assert json.loads(p.read_text()) == {"meta": {"id": "x"}, "strategies": []}


def test_overwrites_existing_file(tmp_path):
    p = tmp_path / "c.json"
    write_payload_atomic(p, {"v": 1})
    write_payload_atomic(p, {"v": 2})
    assert json.loads(p.read_text()) == {"v": 2}


def test_leaves_no_temp_litter(tmp_path):
    p = tmp_path / "c.json"
    write_payload_atomic(p, {"v": 1})
    write_payload_atomic(p, {"v": 2})
    # Only the target remains — temp files are renamed away on success.
    assert sorted(f.name for f in tmp_path.iterdir()) == ["c.json"]


def test_creates_parent_dirs(tmp_path):
    p = tmp_path / "nested" / "dir" / "c.json"
    write_payload_atomic(p, {"v": 1})
    assert json.loads(p.read_text()) == {"v": 1}


def test_accepts_str_path(tmp_path):
    p = tmp_path / "c.json"
    write_payload_atomic(str(p), {"v": 1})
    assert json.loads(p.read_text()) == {"v": 1}
