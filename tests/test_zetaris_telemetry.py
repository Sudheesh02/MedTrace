"""Zetaris telemetry: traces must say honestly whether Zetaris or local CSV served the data."""
import json
import os

from app.adapters.data_store import DataStore
from app.engines.hmem import HMemEngine
from app.orchestrator import MedTraceOrchestrator


def test_zetaris_stats_count_ok_and_fallback(monkeypatch):
    ds = DataStore(use_zetaris=True)
    DataStore.reset_zetaris_stats()
    calls = {"n": 0}

    def fake_raw(sql):
        calls["n"] += 1
        return [{"facility_id": "FAC-DH-01"}] if calls["n"] == 1 else None

    monkeypatch.setattr(ds, "_query_zetaris_raw", fake_raw)
    assert ds._query_zetaris("SELECT * FROM MEDTRACE_LH.facilities")
    assert ds._query_zetaris("SELECT * FROM MEDTRACE_LH.batches") is None
    s = DataStore.get_zetaris_stats()
    assert s["queries_attempted"] == 2
    assert s["queries_ok"] == 1
    assert s["queries_fallback_to_csv"] == 1
    assert s["tables"] == {"facilities": 1}


def test_zetaris_disabled_records_nothing():
    ds = DataStore(use_zetaris=False)
    DataStore.reset_zetaris_stats()
    assert ds._query_zetaris("SELECT 1") is None
    assert DataStore.get_zetaris_stats()["queries_attempted"] == 0


def test_run_trace_contains_data_source_summary(tmp_path):
    orch = MedTraceOrchestrator(logs_dir=str(tmp_path), hmem=HMemEngine(persistence_file=None))
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    rows = [json.loads(l) for l in open(pack.trace_file, encoding="utf-8") if l.strip()]
    summary = [r for r in rows if r["action"] == "DATA_SOURCE_SUMMARY"]
    assert len(summary) == 1
    d = summary[0]["details"]
    assert d["use_zetaris"] is False
    assert d["source"] == "local-csv-sample-data"
    assert d["queries_ok"] == 0
    assert rows[-1]["action"] == "RUN_COMPLETE"

