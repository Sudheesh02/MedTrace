"""Triage tiers must follow documented, data-derived rules (no hard-coded supplier-delay flag on every pair)."""
import pytest

from app.agents.triage_planner import TRIAGE_RULES, TriagePlannerAgent
from app.engine.deterministic import CHRONIC_SUPPLIER_SLIP_DAYS


class FakeStore:
    def __init__(self, slip=None, stock=1000.0, rate=10.0, with_po=True):
        self.slip, self.stock, self.rate, self.with_po = slip, stock, rate, with_po

    def get_latest_ledger(self, f, m):
        return {"ledger_stock": self.stock}

    def get_latest_physical_audit(self, f, m):
        return None

    def get_batches(self, f, m):
        return []

    def get_recent_consumption(self, f, m, days=7):
        return [{"units_issued": self.rate}] * 7

    def get_purchase_orders(self, f, m):
        if not self.with_po:
            return []
        return [{"po_id": "PO-1", "supplier_id": "SUP-X", "order_date": "2026-05-01", "promised_date": "2026-05-07"}]

    def get_ledger_on_date(self, f, m, d):
        return None

    def get_suppliers(self):
        return [] if self.slip is None else [{"supplier_id": "SUP-X", "historical_p90_slip": self.slip}]


def triage(store):
    return TriagePlannerAgent(store).triage_pair("F", "M")


def test_rules_are_exposed_and_match_the_reconciler_threshold():
    assert TRIAGE_RULES["critical_cover_days"] == 7.0
    assert TRIAGE_RULES["warning_cover_days"] == 14.0
    assert TRIAGE_RULES["supplier_slip_flag_days"] == CHRONIC_SUPPLIER_SLIP_DAYS == 7.0


def test_short_supplier_slip_with_ample_cover_is_secure_and_not_flagged():
    item = triage(FakeStore(slip=3, stock=1000))  # 100 days of cover, supplier slips 3 days at p90
    assert item["urgency_tier"] == "SECURE"
    assert "supplier_delay_risk" not in item["discrepancies_detected"]
    assert item["supplier_id"] == "SUP-X" and item["supplier_slip_days"] == 3.0


def test_chronic_supplier_slip_is_a_warning_even_with_ample_cover():
    item = triage(FakeStore(slip=CHRONIC_SUPPLIER_SLIP_DAYS, stock=1000))
    assert item["urgency_tier"] == "WARNING"
    assert "supplier_delay_risk" in item["discrepancies_detected"]


def test_no_purchase_order_means_no_supplier_evidence_so_no_flag():
    item = triage(FakeStore(slip=None, with_po=False, stock=1000))
    assert item["urgency_tier"] == "SECURE"
    assert "supplier_delay_risk" not in item["discrepancies_detected"]
    assert item["supplier_id"] is None


def test_slip_widens_the_shortfall_window_like_the_reconciler_does():
    # 13 days of cover vs a 6 day promise: no shortfall with a 3 day slip, shortfall with a 14 day slip
    short = triage(FakeStore(slip=3, stock=130))
    long_ = triage(FakeStore(slip=14, stock=130))
    assert short["shortfall_units"] == 0 and short["urgency_tier"] == "WARNING"
    assert long_["shortfall_units"] > 0 and long_["urgency_tier"] == "CRITICAL"


def test_low_cover_is_still_critical_regardless_of_supplier():
    assert triage(FakeStore(slip=3, stock=20))["urgency_tier"] == "CRITICAL"


def test_district_tiers_are_consistent_with_the_documented_rules():
    from app.adapters.data_store import DataStore

    res = TriagePlannerAgent(DataStore(use_zetaris=False)).scan_district(top_n=1000)
    assert res["critical_count"] + res["warning_count"] + res["secure_count"] == res["total_evaluated"] == 144
    for it in res["top_urgent_items"]:
        critical = it["trust_cover_days"] < TRIAGE_RULES["critical_cover_days"] or it["shortfall_units"] > TRIAGE_RULES["critical_shortfall_over"]
        warning = it["trust_cover_days"] < TRIAGE_RULES["warning_cover_days"] or len(it["discrepancies_detected"]) > TRIAGE_RULES["warning_discrepancies_over"]
        expected = "CRITICAL" if critical else "WARNING" if warning else "SECURE"
        assert it["urgency_tier"] == expected, it
        if "supplier_delay_risk" in it["discrepancies_detected"]:
            assert it["supplier_slip_days"] >= TRIAGE_RULES["supplier_slip_flag_days"]


def test_scan_district_and_dashboard_snapshot_export_the_rules():
    import json
    import subprocess
    import sys

    from app.adapters.data_store import DataStore

    assert TriagePlannerAgent(DataStore(use_zetaris=False)).scan_district(top_n=1)["rules"] == TRIAGE_RULES
    out = subprocess.run([sys.executable, "dashboard/scripts/triage_snapshot.py"], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-300:]
    snap = json.loads(out.stdout)
    assert snap["rules"] == TRIAGE_RULES
    assert len(snap["items"]) == 144

