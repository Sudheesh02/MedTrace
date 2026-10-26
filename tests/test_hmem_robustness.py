"""H-MEM persistence robustness: atomic saves and loud (logged, preserved) handling of a corrupt store."""
import json
import logging
import os

import pytest

from app.engines.hmem import HMemEngine


def _engine(path):
    return HMemEngine(persistence_file=str(path))


def test_save_roundtrip_leaves_no_temp_files(tmp_path):
    path = tmp_path / "mem" / "hmem_store.json"
    eng = _engine(path)
    eng.record_officer_decision("FAC-CHC-01", "MED-001", "PEER_TRANSFER", "REJECTED", "road closed")
    assert json.loads(path.read_text(encoding="utf-8"))["episodic_memory"][0]["decision"] == "REJECTED"
    assert [p.name for p in path.parent.iterdir()] == ["hmem_store.json"]
    # a fresh engine sees the stored decision
    again = _engine(path)
    assert again.long_term_beliefs["officer_action_preferences"]["FAC-CHC-01_PEER_TRANSFER"]["rejected"] == 1


def test_failed_save_keeps_previous_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "hmem_store.json"
    eng = _engine(path)
    eng.record_officer_decision("FAC-CHC-01", "MED-001", "PEER_TRANSFER", "APPROVED", "ok")
    before = path.read_text(encoding="utf-8")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("app.engines.hmem.json.dump", boom)
    with pytest.raises(OSError):
        eng.record_officer_decision("FAC-CHC-01", "MED-001", "PEER_TRANSFER", "REJECTED", "later")
    assert path.read_text(encoding="utf-8") == before  # not truncated / half-written
    assert [p.name for p in tmp_path.iterdir()] == ["hmem_store.json"]  # temp file cleaned up


def test_corrupt_store_is_logged_and_preserved_not_silently_dropped(tmp_path, caplog):
    path = tmp_path / "hmem_store.json"
    path.write_text("{ not valid json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="app.engines.hmem"):
        eng = _engine(path)
    assert eng.episodic_memory == []
    assert any("corrupt" in r.getMessage().lower() for r in caplog.records)
    backups = [p for p in tmp_path.iterdir() if p.name.startswith("hmem_store.json.corrupt")]
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == "{ not valid json"
    # the engine keeps working and rewrites a valid store
    eng.record_officer_decision("FAC-DH-01", "MED-007", "EXPEDITED_PO", "APPROVED", "ok")
    assert json.loads(path.read_text(encoding="utf-8"))["episodic_memory"]


def test_missing_store_is_not_an_error(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="app.engines.hmem"):
        eng = _engine(tmp_path / "nope.json")
    assert eng.episodic_memory == []
    assert not caplog.records
