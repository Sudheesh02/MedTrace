"""
Unit Tests for DataStore and Zetaris SQL Integration (tests/test_data_store.py)
Verifies:
1. Offline CSV data retrieval across all entity types.
2. Graceful offline fallback when Zetaris is unreachable (no crashes or unhandled exceptions).
3. Mocked Zetaris REST SQL querying, authentication flow, and header parsing.
4. Correct SQL WHERE/ORDER BY query generation for batches, ledgers, and deliveries.
5. Dynamic environment variable toggle for USE_ZETARIS.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from app.adapters.data_store import DataStore

def test_data_store_offline_csv_reads():
    """Verify default offline CSV reads return properly typed data."""
    store = DataStore(use_zetaris=False)

    facilities = store.get_facilities()
    assert len(facilities) >= 12
    assert any(f.get("facility_id") == "FAC-DH-01" for f in facilities)

    medicines = store.get_medicines()
    assert len(medicines) >= 12
    assert any(m.get("medicine_id") == "MED-007" for m in medicines)

    suppliers = store.get_suppliers()
    assert len(suppliers) >= 3

    batches = store.get_batches(facility_id="FAC-DH-01", medicine_id="MED-007")
    assert len(batches) > 0
    assert isinstance(batches[0]["quantity"], float)
    assert isinstance(batches[0]["quarantined"], bool)
    assert "days_to_expiry" in batches[0]

    ledger = store.get_latest_ledger("FAC-DH-01", "MED-007")
    assert ledger is not None
    assert isinstance(ledger["ledger_stock"], float)

    audit = store.get_latest_physical_audit("FAC-DH-01", "MED-007")
    assert audit is not None
    assert isinstance(audit["counted_stock"], float)

    pos = store.get_purchase_orders("FAC-DH-01", "MED-007")
    assert isinstance(pos, list)

    deliveries = store.get_deliveries("FAC-DH-01", "MED-007")
    assert isinstance(deliveries, list)

    transfers = store.get_transfers()
    assert isinstance(transfers, list)

    consumption = store.get_recent_consumption("FAC-DH-01", "MED-007", days=7)
    assert len(consumption) <= 7
    if consumption:
        assert isinstance(consumption[0]["units_issued"], float)

    priors = store.get_supplier_slip_priors()
    assert len(priors) > 0

def test_data_store_graceful_fallback_when_zetaris_unreachable():
    """When Zetaris endpoint is unreachable, getters must fall back gracefully to CSV without crashing."""
    store = DataStore(use_zetaris=True)
    store.base_url = "http://127.0.0.1:59999"  # Non-existent port

    # All getters must return valid CSV fallback data and never raise ConnectionError
    facilities = store.get_facilities()
    assert len(facilities) >= 12

    medicines = store.get_medicines()
    assert len(medicines) >= 12

    batches = store.get_batches("FAC-DH-01", "MED-007")
    assert len(batches) > 0

    ledger = store.get_latest_ledger("FAC-DH-01", "MED-007")
    assert ledger is not None
    assert isinstance(ledger["ledger_stock"], float)

    pos = store.get_purchase_orders("FAC-DH-01", "MED-007")
    assert isinstance(pos, list)

def test_data_store_zetaris_mocked_query_success():
    """Verify that when Zetaris is reachable, DataStore issues SQL and parses response correctly."""
    store = DataStore(use_zetaris=True)
    store.base_url = "http://mock-zetaris:3000"

    mock_login_resp = MagicMock()
    mock_login_resp.status_code = 200
    mock_login_resp.json.return_value = {
        "idToken": "test-jwt-token-12345",
        "orgId": "42"
    }

    mock_query_resp = MagicMock()
    mock_query_resp.status_code = 200
    mock_query_resp.json.return_value = {
        "headers": ["facility_id", "facility_name", "tier"],
        "data": [
            ["FAC-MOCK-01", "Mock District Hospital", "DISTRICT_HOSPITAL"],
            ["FAC-MOCK-02", "Mock Clinic", "PRIMARY_HEALTH_CENTER"]
        ]
    }

    with patch("requests.post") as mock_post:
        # First call is login, second call is query
        mock_post.side_effect = [mock_login_resp, mock_query_resp]

        facilities = store.get_facilities()
        assert len(facilities) == 2
        assert facilities[0]["facility_id"] == "FAC-MOCK-01"
        assert facilities[0]["facility_name"] == "Mock District Hospital"
        assert facilities[1]["tier"] == "PRIMARY_HEALTH_CENTER"

        # Verify second call headers
        query_call = mock_post.call_args_list[1]
        headers = query_call.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-jwt-token-12345"
        assert headers["X-Org-ID"] == "42"
        assert "X-Request-ID" in headers

def test_data_store_sql_query_construction():
    """Verify that DataStore constructs appropriate SQL statements with filters."""
    store = DataStore(use_zetaris=True)
    store._cached_token = "mock-token"

    executed_queries = []

    def fake_query(sql):
        executed_queries.append(sql)
        if "batches" in sql:
            return [{"batch_id": "B-01", "facility_id": "FAC-DH-01", "medicine_id": "MED-007", "quantity": 100, "quarantined": "false", "expiry_date": "2027-01-01"}]
        if "ledger_daily" in sql:
            return [{"facility_id": "FAC-DH-01", "medicine_id": "MED-007", "ledger_stock": 500, "date": "2026-10-24"}]
        if "purchase_orders" in sql:
            return [{"po_id": "PO-01", "facility_id": "FAC-DH-01", "medicine_id": "MED-007", "quantity": 200}]
        if "deliveries" in sql:
            return [{"delivery_id": "DEL-01", "facility_id": "FAC-DH-01", "medicine_id": "MED-007", "received_qty": 200}]
        return []

    with patch.object(store, "_query_zetaris", side_effect=fake_query):
        batches = store.get_batches(facility_id="FAC-DH-01", medicine_id="MED-007")
        assert len(batches) == 1
        assert any("facility_id = 'FAC-DH-01'" in q and "medicine_id = 'MED-007'" in q for q in executed_queries)

        ledger = store.get_latest_ledger("FAC-DH-01", "MED-007")
        assert ledger is not None
        assert any("ORDER BY date DESC LIMIT 1" in q for q in executed_queries)

        pos = store.get_purchase_orders("FAC-DH-01", "MED-007")
        assert len(pos) == 1
        assert any("purchase_orders" in q for q in executed_queries)

        delivs = store.get_deliveries("FAC-DH-01", "MED-007")
        assert len(delivs) == 1
        assert any("deliveries" in q for q in executed_queries)

def test_data_store_env_toggle(monkeypatch):
    """Verify USE_ZETARIS environment variable initializes DataStore properly."""
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("USE_ZETARIS", "true")
    s1 = DataStore()
    assert s1.use_zetaris is True

    monkeypatch.setenv("USE_ZETARIS", "false")
    s2 = DataStore()
    assert s2.use_zetaris is False

    # Explicit parameter overrides environment variable
    s3 = DataStore(use_zetaris=True)
    assert s3.use_zetaris is True
    s4 = DataStore(use_zetaris=False)
    assert s4.use_zetaris is False

def test_data_store_sample_mode_disables_zetaris_by_default(monkeypatch):
    """Verify that SAMPLE_MODE=true forces use_zetaris to False unless explicitly overridden."""
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("USE_ZETARIS", "true")
    store = DataStore()
    assert store.use_zetaris is False

    # Explicit override still respected if requested
    store_override = DataStore(use_zetaris=True)
    assert store_override.use_zetaris is True

def test_data_store_configurable_simulation_dir(tmp_path, monkeypatch):
    """
    Verify that DataStore accepts a custom simulation directory via constructor
    or SIM_DIR environment variable, enabling dynamic multi-seed evaluations.
    """
    # Create custom dummy simulation directory
    custom_sim = tmp_path / "custom_sim"
    custom_sim.mkdir()
    fac_csv = custom_sim / "facilities.csv"
    fac_csv.write_text("facility_id,name,level,catchment_scale\nFAC-CUSTOM-01,Custom Clinic,PHC,1.5\n", encoding="utf-8")

    # 1. Via constructor parameter
    store = DataStore(use_zetaris=False, sim_dir=str(custom_sim))
    assert store.sim_dir == str(custom_sim)
    facs = store.get_facilities()
    assert len(facs) == 1
    assert facs[0]["facility_id"] == "FAC-CUSTOM-01"

    # 2. Via SIM_DIR environment variable
    monkeypatch.setenv("SIM_DIR", str(custom_sim))
    store_env = DataStore(use_zetaris=False)
    assert store_env.sim_dir == str(custom_sim)
    facs_env = store_env.get_facilities()
    assert len(facs_env) == 1
    assert facs_env[0]["facility_id"] == "FAC-CUSTOM-01"

def test_data_store_in_memory_caching(tmp_path):
    """
    Verify DataStore in-memory CSV caching and O(1) pair indexing:
    1. Caches parsed rows and pair indexes across repeated reads.
    2. Returns isolated copies so mutations do not taint cached rows.
    3. clear_cache() resets instance and shared caches cleanly.
    4. TriagePlannerAgent district scan completes in <0.5 seconds.
    """
    import time
    from app.agents.triage_planner import TriagePlannerAgent

    store = DataStore(use_zetaris=False)
    store.clear_cache()

    # Initial state: caches empty
    assert len(store._csv_cache) == 0
    assert len(store._pair_indexes) == 0

    # 1. Fetch ledger & consumption
    ledger1 = store.get_latest_ledger("FAC-DH-01", "MED-007")
    assert ledger1 is not None
    assert len(store._csv_cache) > 0
    assert len(store._pair_indexes) > 0

    # 2. Verify mutation isolation (modifying returned dict does not alter subsequent calls)
    orig_stock = ledger1["ledger_stock"]
    ledger1["ledger_stock"] = 999999.0
    ledger2 = store.get_latest_ledger("FAC-DH-01", "MED-007")
    assert ledger2["ledger_stock"] == orig_stock

    # 3. Verify batches isolation
    batches1 = store.get_batches("FAC-DH-01", "MED-007")
    assert len(batches1) > 0
    orig_qty = batches1[0]["quantity"]
    batches1[0]["quantity"] = -42.0
    batches2 = store.get_batches("FAC-DH-01", "MED-007")
    assert batches2[0]["quantity"] == orig_qty

    # 4. Verify TriagePlannerAgent performance with warm cache (<0.5s)
    planner = TriagePlannerAgent(store)
    t0 = time.time()
    res = planner.scan_district()
    elapsed = time.time() - t0
    assert res["total_evaluated"] == 144
    assert elapsed < 0.5, f"Expected scan_district() < 0.5s, got {elapsed:.3f}s"

    # 5. Verify clear_cache() resets both caches
    store.clear_cache()
    assert len(store._csv_cache) == 0
    assert len(store._pair_indexes) == 0
    assert len(DataStore._shared_csv_cache) == 0
    assert len(DataStore._shared_pair_indexes) == 0


def test_data_store_federated_cross_source_query():
    """
    Verify 4-way federated cross-source join execution via Zetaris Lightning REST API
    (as documented in SPONSOR_TECH.md §2.3).
    Spans PostgreSQL ledger, physical audits, purchase orders, and Parquet supplier slip.
    """
    store = DataStore(use_zetaris=True)
    store._cached_token = "mock-jwt-token"

    federated_sql = """
    SELECT
        l.facility_id,
        l.medicine_id,
        l.ledger_stock,
        a.counted_stock,
        (l.ledger_stock - a.counted_stock) AS phantom_drift,
        po.po_id,
        po.promised_date,
        s.mean_slip_days,
        s.p90_days
    FROM zetaris.lightning.ledger_daily l
    LEFT JOIN zetaris.lightning.physical_audit a
        ON l.facility_id = a.facility_id AND l.medicine_id = a.medicine_id
    LEFT JOIN zetaris.lightning.purchase_orders po
        ON l.facility_id = po.facility_id AND l.medicine_id = po.medicine_id
    LEFT JOIN zetaris.lightning.supplier_slip s
        ON po.supplier_id = s.supplier_id
    WHERE l.facility_id = 'FAC-DH-01' AND l.medicine_id = 'MED-007'
    ORDER BY l.date DESC LIMIT 1;
    """

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "headers": ["facility_id", "medicine_id", "ledger_stock", "counted_stock", "phantom_drift", "po_id", "promised_date", "mean_slip_days", "p90_days"],
        "rows": [["FAC-DH-01", "MED-007", 6462.0, 6412.0, 50.0, "PO-0001", "2026-10-30", 3.0, 15.0]]
    }

    with patch("requests.post", return_value=mock_response) as mock_post:
        res = store._query_zetaris(federated_sql)
        assert res is not None
        assert len(res) == 1
        row = res[0]
        assert row["facility_id"] == "FAC-DH-01"
        assert row["medicine_id"] == "MED-007"
        assert row["phantom_drift"] == 50.0
        assert row["p90_days"] == 15.0
        # Verify request headers to proxy
        called_headers = mock_post.call_args[1]["headers"]
        assert called_headers["Authorization"] == "Bearer mock-jwt-token"
        assert "X-Request-ID" in called_headers



