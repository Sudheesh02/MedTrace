"""
Unit tests for MedTrace Deterministic Engine.
Verifies Section 5.2 worked example in MedTrace_Research_and_Execution_Plan.md:
Assumptions:
- Ledger: 120 units
- Usage: 30 units/day
- Delivery promised: Day 6
- Physical count implies 50 phantom units (true stock 70)
- Supplier history shows +3 day typical slip (arrival Day 9)
"""

import pytest
from app.engine.deterministic import DeterministicEngine

def test_section_5_2_worked_example():
    ledger = 120.0
    daily_rate = 30.0
    promised_day = 6.0
    drift = 50.0
    supplier_slip = 3.0

    # 1. Naive calculation (ledger + promise)
    naive_cover = DeterministicEngine.compute_days_of_cover(ledger, daily_rate)
    assert naive_cover == 4.00
    naive_shortfall = DeterministicEngine.compute_shortfall(naive_cover, promised_day, daily_rate)
    assert naive_shortfall["gap_days"] == 2.00
    assert naive_shortfall["shortfall_units"] == 60.0

    # 2. Trust-adjusted stock only (usable 70, delivery day 6)
    stock_eval = DeterministicEngine.compute_trust_adjusted_stock(ledger_stock=ledger, audit_drift=drift)
    usable_stock = stock_eval["usable_stock"]
    assert usable_stock == 70.0
    trust_cover = DeterministicEngine.compute_days_of_cover(usable_stock, daily_rate)
    assert trust_cover == 2.33
    trust_stock_only = DeterministicEngine.compute_shortfall(trust_cover, promised_day, daily_rate)
    assert abs(trust_stock_only["gap_days"] - 3.67) < 0.05
    assert abs(trust_stock_only["shortfall_units"] - 110.0) <= 1.0

    # 3. Trust-adjusted stock + slip (usable 70, delivery day 9)
    actual_day = promised_day + supplier_slip
    assert actual_day == 9.0
    trust_stock_slip = DeterministicEngine.compute_shortfall(trust_cover, actual_day, daily_rate)
    assert abs(trust_stock_slip["gap_days"] - 6.67) < 0.05
    assert abs(trust_stock_slip["shortfall_units"] - 200.0) <= 1.0

    # 4. Understatement %
    # Stock only: 1.67 / 3.67 = ~45.5%
    understatement_stock_only = (trust_stock_only["gap_days"] - naive_shortfall["gap_days"]) / trust_stock_only["gap_days"]
    assert 0.44 <= understatement_stock_only <= 0.46

    # Stock + slip: 4.67 / 6.67 = ~70.0%
    understatement_stock_slip = (trust_stock_slip["gap_days"] - naive_shortfall["gap_days"]) / trust_stock_slip["gap_days"]
    assert 0.69 <= understatement_stock_slip <= 0.71

def test_monte_carlo_eta():
    promised_days = 6.0
    empirical_slips = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0]
    days_of_cover = 2.33

    mc_result = DeterministicEngine.simulate_monte_carlo_eta(
        promised_days=promised_days,
        slip_distribution=empirical_slips,
        days_of_cover=days_of_cover,
        num_simulations=500,
        seed=123
    )

    assert mc_result["promised_days"] == 6.0
    assert mc_result["mean_arrival_days"] >= 6.0
    # Since arrival is >= 6.0 and days of cover is 2.33, stockout is 100% certain before delivery arrives
    assert mc_result["p_stockout_before_arrival"] == 1.0

def test_full_reconciliation_anomaly_detection():
    batches = [
        {"batch_id": "BAT-01", "quantity": 30, "days_to_expiry": 180, "quarantined": False},
        {"batch_id": "BAT-02", "quantity": 20, "days_to_expiry": 2, "quarantined": False},   # near-expiry
        {"batch_id": "BAT-03", "quantity": 20, "days_to_expiry": 120, "quarantined": True},   # quarantined
    ]
    res = DeterministicEngine.audit_reconcile_item(
        ledger_stock=120.0,
        last_counted_audit=70.0,
        batches=batches,
        daily_rate=30.0,
        promised_delivery_days=6.0,
        historical_slip_days=3.0
    )

    assert res["anomalies_detected"]["ghost_stock"] is True
    assert res["anomalies_detected"]["quarantined_batches"] is True
    assert res["anomalies_detected"]["expiring_batches"] is True
    assert res["anomalies_detected"]["supplier_delay_risk"] is True
    assert res["stock_evaluation"]["usable_stock"] < 70.0
