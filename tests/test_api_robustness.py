"""API robustness: /run serialisation, /memo semantics, and 404 passthrough on the trace routes."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

import run


@pytest.fixture
def client():
    return TestClient(run.app)


# ---- P1-1: /run must not interleave -------------------------------------------------------------------------------

def test_concurrent_runs_are_serialised_and_global_state_restored(client, monkeypatch):
    active = {"now": 0, "max": 0}
    seen_modes = []
    guard = threading.Lock()
    real = run.orchestrator.run_investigation

    def slow_run(*a, **k):
        with guard:
            active["now"] += 1
            active["max"] = max(active["max"], active["now"])
            seen_modes.append((run.orchestrator.llm_client.sample_mode, run.orchestrator.data_store.use_zetaris))
        time.sleep(0.15)
        try:
            return real(*a, **k)
        finally:
            with guard:
                active["now"] -= 1

    monkeypatch.setattr(run.orchestrator, "run_investigation", slow_run)
    orig_sample = run.orchestrator.llm_client.sample_mode
    orig_zet = run.orchestrator.data_store.use_zetaris

    results = []

    def call(sample):
        r = client.post("/run", json={"facility_id": "FAC-DH-01", "medicine_id": "MED-007", "options": {"sample_mode": sample}})
        results.append(r.status_code)

    threads = [threading.Thread(target=call, args=(True,)) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert results == [200, 200, 200]
    assert active["max"] == 1, "two /run requests executed concurrently on shared orchestrator state"
    assert all(mode == (True, False) for mode in seen_modes)
    assert run.orchestrator.llm_client.sample_mode == orig_sample
    assert run.orchestrator.data_store.use_zetaris == orig_zet


def test_run_returns_503_when_server_is_busy(client, monkeypatch):
    monkeypatch.setattr(run, "RUN_LOCK_TIMEOUT_S", 0.05)
    assert run._exclusive_lock.acquire(timeout=1)
    try:
        r = client.post("/run", json={"facility_id": "FAC-DH-01", "medicine_id": "MED-007", "options": {"sample_mode": True}})
    finally:
        run._exclusive_lock.release()
    assert r.status_code == 503
    assert "busy" in r.json()["detail"].lower()


# ---- P1-5: GET /memo is read-only; POST generates ------------------------------------------------------------------

def test_get_memo_does_not_run_an_investigation(client, monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError("GET /memo must not run an investigation")

    monkeypatch.setattr(run.orchestrator, "run_investigation", forbidden)
    r = client.get("/memo/FAC-DH-01/MED-007")  # a stored memo for this pair is committed under output/
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert "MEMORANDUM" in r.text


def test_get_memo_404_when_none_stored_and_points_to_post(client, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDTRACE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(run, "REPO_OUTPUT_DIR", str(tmp_path))
    r = client.get("/memo/FAC-CHC-01/MED-001")
    assert r.status_code == 404
    assert "POST" in r.json()["detail"]


def test_get_memo_rejects_path_traversal_ids(client):
    r = client.get("/memo/..%2F..%2Fetc/passwd")
    assert r.status_code in (400, 404)
    r = client.get("/memo/FAC-DH-01/MED-007%00")
    assert r.status_code in (400, 404)


def test_post_memo_generates_stores_and_get_then_serves_it(client, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDTRACE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(run, "REPO_OUTPUT_DIR", str(tmp_path))
    created = client.post("/memo/FAC-DH-01/MED-007")
    assert created.status_code == 200
    assert "MEMORANDUM" in created.text
    assert (tmp_path / "memo_FAC-DH-01_MED-007.md").exists()
    served = client.get("/memo/FAC-DH-01/MED-007")
    assert served.status_code == 200 and served.text == created.text


def test_post_memo_unknown_pair_is_404(client):
    assert client.post("/memo/FAC-NOPE/MED-007").status_code == 404


# ---- P2: HTTPException passthrough on trace routes ----------------------------------------------------------------

@pytest.mark.parametrize("path", ["/trace/latest", "/trace/verdict-flip"])
def test_trace_routes_return_404_not_500_when_no_trace(client, monkeypatch, path):
    import scripts.explain_trace as et

    monkeypatch.setattr(et, "find_latest_trace", lambda *a, **k: None)
    r = client.get(path)
    assert r.status_code == 404
    assert "No trace files" in r.json()["detail"]
