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
    def normalize_uom_quantity(
        reported_quantity: float,
        reported_unit: str = "strip",
        dispensing_unit: str = "tablet",
        packaging_spec: Optional[str] = None,
        pack_size_units: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Normalizes unit-of-measure quantities using DailyMed and RxNorm standards.
        Detects UOM_MISMATCH when pack counts (e.g. 10x strips) conflict with single units.
        """
        u_rep = (reported_unit or "").lower().strip()
        u_disp = (dispensing_unit or "tablet").lower().strip()
        multiplier = 1.0
        mismatch_flag = False

        if pack_size_units is not None:
            multiplier = float(pack_size_units)
            mismatch_flag = (multiplier != 1.0)
        elif u_rep in ["strip", "blister", "strip of 10"] and u_disp in ["tablet", "capsule"]:
            multiplier = 10.0
            mismatch_flag = True
        elif u_rep in ["box", "pack", "box of 100", "carton"] and u_disp in ["tablet", "capsule"]:
            multiplier = 100.0
            mismatch_flag = True
        elif u_rep in ["vial_box", "box of 10 vials"] and u_disp in ["vial", "ampoule"]:
            multiplier = 10.0
            mismatch_flag = True

        normalized_qty = reported_quantity * multiplier
        return {
            "reported_quantity": reported_quantity,
            "reported_unit": reported_unit,
            "dispensing_unit": dispensing_unit,
            "pack_multiplier": multiplier,
            "normalized_quantity": normalized_qty,
            "uom_mismatch_detected": mismatch_flag
        }

    @staticmethod
    def compute_epidemiological_demand_multiplier(
        base_rate: float,
        atc_seasonal_multiplier: float = 1.0,
        surveillance_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calibrates consumption demand using WHO GHO epidemiological disease trends
        fused with Pharma Sales ATC seasonality patterns.
        """
        epi_multiplier = 1.0
        risk_tier = "STANDARD"
        if surveillance_data:
            risk_tier = surveillance_data.get("epidemiological_risk_tier", "STANDARD")
            if risk_tier == "ELEVATED":
                epi_multiplier = 1.35
            elif risk_tier == "MODERATE":
                epi_multiplier = 1.15

        combined_multiplier = round(atc_seasonal_multiplier * epi_multiplier, 3)
        adjusted_demand = round(base_rate * combined_multiplier, 2)
        demand_spike = combined_multiplier >= 1.40

        return {
            "base_daily_rate": base_rate,
            "atc_seasonal_multiplier": atc_seasonal_multiplier,
            "who_surveillance_multiplier": epi_multiplier,
            "epidemiological_risk_tier": risk_tier,
            "combined_multiplier": combined_multiplier,
            "adjusted_daily_demand": adjusted_demand,
            "demand_spike_detected": demand_spike
        }

    @staticmethod
    def audit_reconcile_item(
        ledger_stock: float,
        last_counted_audit: Optional[float],
        batches: List[Dict[str, Any]],
        daily_rate: float,
        promised_delivery_days: float,
        historical_slip_days: float = 0.0,
        surveillance_data: Optional[Dict[str, Any]] = None,
        shortage_signal: Optional[Dict[str, Any]] = None,
        uom_info: Optional[Dict[str, Any]] = None,
        audit_drift: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Full deterministic audit of an inventory item against multiple records.
        """
        # 1. Audit drift (ghost stock)
        if audit_drift is None:
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

        # 4. Epidemiological demand forecast adjustment
        demand_eval = DeterministicEngine.compute_epidemiological_demand_multiplier(
            base_rate=daily_rate,
            surveillance_data=surveillance_data
        )
        effective_daily_rate = demand_eval["adjusted_daily_demand"] if demand_eval["adjusted_daily_demand"] > 0 else daily_rate

        usable_stock = stock_eval["usable_stock"]
        naive_cover = DeterministicEngine.compute_days_of_cover(ledger_stock, daily_rate)
        trust_cover = DeterministicEngine.compute_days_of_cover(usable_stock, effective_daily_rate)

        # 5. Naive vs Trust-adjusted shortfalls
        naive_shortfall = DeterministicEngine.compute_shortfall(
            naive_cover, promised_delivery_days, daily_rate
        )
        trust_shortfall = DeterministicEngine.compute_shortfall(
            trust_cover, promised_delivery_days + historical_slip_days, effective_daily_rate
        )

        understated_gap_percent = 0.0
        if trust_shortfall["gap_days"] > 0:
            diff = trust_shortfall["gap_days"] - naive_shortfall["gap_days"]
            understated_gap_percent = round((diff / trust_shortfall["gap_days"]) * 100, 1)

        # 6. Global shortage & UOM mismatch flags
        global_shortage_flag = False
        if shortage_signal and shortage_signal.get("active_shortage_flag"):
            global_shortage_flag = True

        uom_mismatch_flag = False
        if uom_info and uom_info.get("uom_mismatch_detected"):
            uom_mismatch_flag = True

        return {
            "stock_evaluation": stock_eval,
            "demand_evaluation": demand_eval,
            "naive_cover_days": naive_cover,
            "trust_cover_days": trust_cover,
            "naive_shortfall": naive_shortfall,
            "trust_shortfall": trust_shortfall,
            "understated_gap_percent": understated_gap_percent,
            "anomalies_detected": {
                "ghost_stock": audit_drift > 0,
                "quarantined_batches": quarantined_qty > 0,
                "expiring_batches": expiring_qty > 0,
                "supplier_delay_risk": historical_slip_days > 0,
                "demand_spike": demand_eval["demand_spike_detected"],
                "global_shortage": global_shortage_flag,
                "uom_mismatch": uom_mismatch_flag
            }
        }
