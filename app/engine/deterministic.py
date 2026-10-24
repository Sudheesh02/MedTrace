"""
MedTrace Deterministic Engine (app/engine/deterministic.py)
Core Rule: LLMs never generate or manipulate inventory numbers.
All arithmetic, lead times, gap days, and risk bounds are deterministically computed here.
"""

from typing import Dict, List, Optional, Tuple, Any
import random
import math

class DeterministicEngine:
    """
    Pure deterministic calculations for:
    1. Trust-adjusted usable inventory
    2. Days of cover & consumption forecasting
    3. Monte Carlo arrival date & stockout probability
    4. Deterministic discrepancy detection (auditing the ledger)
    """

    @staticmethod
    def compute_trust_adjusted_stock(
        ledger_stock: float,
        audit_drift: float = 0.0,
        quarantined_stock: float = 0.0,
        expiring_stock: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculates usable physical stock by subtracting phantom, quarantined, and expiring units.
        Formula: usable_stock = ledger_stock - audit_drift - quarantined_stock - expiring_stock
        """
        deductions = audit_drift + quarantined_stock + expiring_stock
        usable_stock = max(0.0, ledger_stock - deductions)
        return {
            "ledger_stock": round(ledger_stock, 2),
            "audit_drift": round(audit_drift, 2),
            "quarantined_stock": round(quarantined_stock, 2),
            "expiring_stock": round(expiring_stock, 2),
            "total_unusable_deductions": round(deductions, 2),
            "usable_stock": round(usable_stock, 2)
        }

    @staticmethod
    def compute_days_of_cover(usable_stock: float, daily_rate: float) -> float:
        """
        Computes days of stock cover.
        """
        if daily_rate <= 0:
            return 999.0  # infinite cover if no consumption
        return round(usable_stock / daily_rate, 2)

    @staticmethod
    def compute_shortfall(
        days_of_cover: float,
        delivery_day: float,
        daily_rate: float
    ) -> Dict[str, float]:
        """
        Computes gap in days and unit shortfall before delivery arrives.
        Gap = delivery_day - days_of_cover (clamped to >= 0)
        Shortfall = gap * daily_rate
        """
        gap_days = max(0.0, delivery_day - days_of_cover)
        shortfall_units = gap_days * daily_rate
        return {
            "days_of_cover": round(days_of_cover, 2),
            "delivery_day": round(delivery_day, 2),
            "gap_days": round(gap_days, 2),
            "shortfall_units": round(shortfall_units, 2)
        }

    @staticmethod
    def simulate_monte_carlo_eta(
        promised_days: float,
        slip_distribution: List[float],
        days_of_cover: float,
        num_simulations: int = 1000,
        seed: Optional[int] = 42
    ) -> Dict[str, Any]:
        """
        Runs Monte Carlo simulation of delivery arrivals using empirical supplier slip data.
        Returns expected arrival, p50, p90, and P(stockout before delivery).
        """
        if not slip_distribution:
            slip_distribution = [0.0]

        rng = random.Random(seed)
        sampled_arrivals = []
        stockout_count = 0

        for _ in range(num_simulations):
            slip = rng.choice(slip_distribution)
            arrival = max(1.0, promised_days + slip)
            sampled_arrivals.append(arrival)
            if arrival > days_of_cover:
                stockout_count += 1

        sampled_arrivals.sort()
        mean_arrival = sum(sampled_arrivals) / len(sampled_arrivals)
        p50_arrival = sampled_arrivals[int(len(sampled_arrivals) * 0.50)]
        p90_arrival = sampled_arrivals[int(len(sampled_arrivals) * 0.90)]
        p_stockout = stockout_count / num_simulations

        return {
            "promised_days": promised_days,
            "mean_arrival_days": round(mean_arrival, 2),
            "p50_arrival_days": round(p50_arrival, 2),
            "p90_arrival_days": round(p90_arrival, 2),
            "p_stockout_before_arrival": round(p_stockout, 3),
            "num_simulations": num_simulations
        }

    @staticmethod
    def audit_reconcile_item(
        ledger_stock: float,
        last_counted_audit: Optional[float],
        batches: List[Dict[str, Any]],
        daily_rate: float,
        promised_delivery_days: float,
        historical_slip_days: float = 0.0
    ) -> Dict[str, Any]:
        """
        Full deterministic audit of an inventory item against multiple records.
        """
        # 1. Audit drift (ghost stock)
        audit_drift = 0.0
        if last_counted_audit is not None and ledger_stock > last_counted_audit:
            audit_drift = ledger_stock - last_counted_audit

        # 2. Batch scrutiny: quarantined and near-expiry
        quarantined_qty = 0.0
        expiring_qty = 0.0
        for b in batches:
            qty = float(b.get("quantity", 0))
            if b.get("quarantined", False):
                quarantined_qty += qty
            elif b.get("days_to_expiry", 999) < promised_delivery_days:
                expiring_qty += qty

        # 3. Trust-adjusted stock
        stock_eval = DeterministicEngine.compute_trust_adjusted_stock(
            ledger_stock=ledger_stock,
            audit_drift=audit_drift,
            quarantined_stock=quarantined_qty,
            expiring_stock=expiring_qty
        )

        usable_stock = stock_eval["usable_stock"]
        naive_cover = DeterministicEngine.compute_days_of_cover(ledger_stock, daily_rate)
        trust_cover = DeterministicEngine.compute_days_of_cover(usable_stock, daily_rate)

        # 4. Naive vs Trust-adjusted shortfalls
        naive_shortfall = DeterministicEngine.compute_shortfall(
            naive_cover, promised_delivery_days, daily_rate
        )
        trust_shortfall = DeterministicEngine.compute_shortfall(
            trust_cover, promised_delivery_days + historical_slip_days, daily_rate
        )

        understated_gap_percent = 0.0
        if trust_shortfall["gap_days"] > 0:
            diff = trust_shortfall["gap_days"] - naive_shortfall["gap_days"]
            understated_gap_percent = round((diff / trust_shortfall["gap_days"]) * 100, 1)

        return {
            "stock_evaluation": stock_eval,
            "naive_cover_days": naive_cover,
            "trust_cover_days": trust_cover,
            "naive_shortfall": naive_shortfall,
            "trust_shortfall": trust_shortfall,
            "understated_gap_percent": understated_gap_percent,
            "anomalies_detected": {
                "ghost_stock": audit_drift > 0,
                "quarantined_batches": quarantined_qty > 0,
                "expiring_batches": expiring_qty > 0,
                "supplier_delay_risk": historical_slip_days > 0
            }
        }
