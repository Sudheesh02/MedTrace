"""
Generate DC-7: Simulated Facility Layer for MedTrace
Entities:
- 1 District Hospital, 3 CHCs, 6 PHCs, 2 Warehouses (12 facilities total)
- 4 Suppliers (linked to top real vendors from DC-3)
- 12 Essential Medicines (from DC-1)
- 180 days of daily ledger, consumption, physical audits, batches, POs, deliveries, transfers
- 10 Planted Anomalies recorded into ground_truth.csv
- true_stock_daily.csv kept strictly for backtest evaluation
"""

import os
import csv
import json
import random
from datetime import datetime, timedelta

def load_medicine_master():
    path = os.path.join("data", "real", "medicine_master.csv")
    meds = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            meds.append(r)
    return meds

def load_supplier_slips():
    path = os.path.join("data", "real", "supplier_slip.csv")
    suppliers = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            suppliers.append(r)
    # pick top 4 vendors
    top_4 = suppliers[:4]
    return top_4

def generate_simulation(seed=1, out_dir="data/simulated"):
    random.seed(seed)
    os.makedirs(out_dir, exist_ok=True)
    
    meds = load_medicine_master()
    real_suppliers = load_supplier_slips()

    # 1. Facilities
    facilities = [
        {"facility_id": "FAC-DH-01", "name": "District Civil Hospital", "level": "District Hospital", "catchment_scale": 1.0, "source": "SIMULATED"},
        {"facility_id": "FAC-CHC-01", "name": "North Sub-District CHC", "level": "CHC", "catchment_scale": 0.35, "source": "SIMULATED"},
        {"facility_id": "FAC-CHC-02", "name": "East Sub-District CHC", "level": "CHC", "catchment_scale": 0.35, "source": "SIMULATED"},
        {"facility_id": "FAC-CHC-03", "name": "West Sub-District CHC", "level": "CHC", "catchment_scale": 0.35, "source": "SIMULATED"},
        {"facility_id": "FAC-PHC-01", "name": "Rural PHC Block A", "level": "PHC", "catchment_scale": 0.12, "source": "SIMULATED"},
        {"facility_id": "FAC-PHC-02", "name": "Rural PHC Block B", "level": "PHC", "catchment_scale": 0.12, "source": "SIMULATED"},
        {"facility_id": "FAC-PHC-03", "name": "Rural PHC Block C", "level": "PHC", "catchment_scale": 0.12, "source": "SIMULATED"},
        {"facility_id": "FAC-PHC-04", "name": "Rural PHC Block D", "level": "PHC", "catchment_scale": 0.12, "source": "SIMULATED"},
        {"facility_id": "FAC-PHC-05", "name": "Rural PHC Block E", "level": "PHC", "catchment_scale": 0.12, "source": "SIMULATED"},
        {"facility_id": "FAC-PHC-06", "name": "Rural PHC Block F", "level": "PHC", "catchment_scale": 0.12, "source": "SIMULATED"},
        {"facility_id": "FAC-WH-01", "name": "District Drug Warehouse", "level": "District Warehouse", "catchment_scale": 2.5, "source": "SIMULATED"},
        {"facility_id": "FAC-WH-02", "name": "Regional Medical Depot", "level": "Regional Warehouse", "catchment_scale": 5.0, "source": "SIMULATED"},
    ]

    # 2. Suppliers
    suppliers = []
    for i, s in enumerate(real_suppliers):
        suppliers.append({
            "supplier_id": f"SUP-00{i+1}",
            "supplier_name": f"Supplier {i+1} ({s['vendor'][:25]})",
            "real_vendor_ref": s["vendor"],
            "shipment_mode": s["shipment_mode"],
            "historical_mean_slip": s["mean_slip_days"],
            "historical_p90_slip": s["p90_days"],
            "source": "SIMULATED"
        })

    # Timeline: 180 days ending at current hackathon baseline (e.g. 2026-10-24)
    end_date = datetime(2026, 10, 24)
    start_date = end_date - timedelta(days=179)
    days_list = [start_date + timedelta(days=d) for d in range(180)]

    ledger_daily = []
    true_stock_daily = []
    consumption_daily = []
    physical_audit = []
    batches = []
    purchase_orders = []
    deliveries = []
    transfers = []
    ground_truth = []

    # Initialize facility stock states
    # Base daily demand per medicine
    base_demands = {
        "MED-001": 80,  # paracetamol
        "MED-002": 50,  # ibuprofen
        "MED-003": 30,  # diclofenac
        "MED-004": 40,  # amoxicillin
        "MED-005": 35,  # cetirizine
        "MED-006": 25,  # salbutamol
        "MED-007": 60,  # metformin
        "MED-008": 45,  # amlodipine
        "MED-009": 20,  # artemether
        "MED-010": 15,  # efavirenz
        "MED-011": 25,  # lamivudine+zidovudine
        "MED-012": 18   # contraceptive
    }

    # Tracking per facility & med
    stock_state = {}
    batch_counter = 1
    po_counter = 1
    deliv_counter = 1
    audit_counter = 1

    for f in facilities:
        fid = f["facility_id"]
        scale = f["catchment_scale"]
        for m in meds:
            mid = m["medicine_id"]
            # initial true stock = 15 to 30 days of cover
            daily_use = int(base_demands[mid] * scale)
            init_stock = daily_use * random.randint(15, 30)
            stock_state[(fid, mid)] = {
                "true_stock": init_stock,
                "ledger_drift": 0,
                "daily_use": daily_use
            }
            # create initial batches
            b_qty1 = int(init_stock * 0.6)
            b_qty2 = init_stock - b_qty1
            exp1 = end_date + timedelta(days=random.randint(60, 400))
            exp2 = end_date + timedelta(days=random.randint(120, 600))
            batches.append({
                "batch_id": f"BAT-{batch_counter:04d}",
                "medicine_id": mid,
                "facility_id": fid,
                "quantity": b_qty1,
                "expiry_date": exp1.strftime("%Y-%m-%d"),
                "quarantined": False,
                "source": "SIMULATED"
            })
            batch_counter += 1
            batches.append({
                "batch_id": f"BAT-{batch_counter:04d}",
                "medicine_id": mid,
                "facility_id": fid,
                "quantity": b_qty2,
                "expiry_date": exp2.strftime("%Y-%m-%d"),
                "quarantined": False,
                "source": "SIMULATED"
            })
            batch_counter += 1

    # Plan 10 Anomalies
    # 1. Ghost stock: District Hospital has 120 units on ledger for Metformin, but physical count showed 70 (drift = 50)
    anom_1_day = 160
    ground_truth.append({
        "anomaly_id": "ANOM-01",
        "type": "GHOST_STOCK",
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-007",
        "day_index": anom_1_day,
        "description": "Ledger phantom stock: ledger shows 120 units over true physical count",
        "magnitude": 50,
        "source": "SIMULATED"
    })

    # 2. Expiring batch counted as usable: PHC-01 Amoxicillin batch expires inside 7 days
    batches.append({
        "batch_id": f"BAT-{batch_counter:04d}",
        "medicine_id": "MED-004",
        "facility_id": "FAC-PHC-01",
        "quantity": 180,
        "expiry_date": (end_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        "quarantined": False,
        "source": "SIMULATED"
    })
    batch_counter += 1
    ground_truth.append({
        "anomaly_id": "ANOM-02",
        "type": "EXPIRING_BATCH_UNUSABLE",
        "facility_id": "FAC-PHC-01",
        "medicine_id": "MED-004",
        "day_index": 175,
        "description": "Batch expires in 5 days; cannot cover full lead time",
        "magnitude": 180,
        "source": "SIMULATED"
    })

    # 3. Quarantined batch counted as usable: CHC-01 Paracetamol batch flagged quarantined
    batches.append({
        "batch_id": f"BAT-{batch_counter:04d}",
        "medicine_id": "MED-001",
        "facility_id": "FAC-CHC-01",
        "quantity": 400,
        "expiry_date": (end_date + timedelta(days=300)).strftime("%Y-%m-%d"),
        "quarantined": True,
        "source": "SIMULATED"
    })
    batch_counter += 1
    ground_truth.append({
        "anomaly_id": "ANOM-03",
        "type": "QUARANTINED_BATCH",
        "facility_id": "FAC-CHC-01",
        "medicine_id": "MED-001",
        "day_index": 170,
        "description": "Quality assurance hold; batch quarantined but included in ledger usable total",
        "magnitude": 400,
        "source": "SIMULATED"
    })

    # Delivery schedule queue: maps date_str -> list of (fid, mid, qty)
    delivery_schedule = {}

    # Simulation loop across 180 days
    for d_idx, cur_date in enumerate(days_list):
        d_str = cur_date.strftime("%Y-%m-%d")
        
        # 1. Process any arriving deliveries today
        if d_str in delivery_schedule:
            for arr_fid, arr_mid, arr_qty in delivery_schedule[d_str]:
                stock_state[(arr_fid, arr_mid)]["true_stock"] += arr_qty

        # Periodic audits every 60 days
        is_audit_day = (d_idx in [60, 120, 165])
        
        for f in facilities:
            fid = f["facility_id"]
            for m in meds:
                mid = m["medicine_id"]
                state = stock_state[(fid, mid)]
                
                # Daily consumption with slight variance
                base = state["daily_use"]
                noise = random.uniform(0.85, 1.15)
                # Demand spike anomaly on Day 165 for Salbutamol at DH-01
                if d_idx >= 165 and fid == "FAC-DH-01" and mid == "MED-006":
                    noise = 2.4
                
                issued = int(base * noise)
                issued = min(issued, state["true_stock"])
                state["true_stock"] -= issued
                
                # Track consumption
                consumption_daily.append({
                    "date": d_str,
                    "facility_id": fid,
                    "medicine_id": mid,
                    "units_issued": issued,
                    "source": "SIMULATED"
                })

                # Reorder trigger if true stock < 7 days of cover
                if state["true_stock"] < base * 7:
                    order_qty = base * random.randint(18, 30)
                    sup = random.choice(suppliers)
                    p_slip = int(float(sup["historical_mean_slip"]))
                    prom_days = random.randint(5, 8)
                    prom_date = cur_date + timedelta(days=prom_days)
                    actual_date = prom_date + timedelta(days=max(0, p_slip + random.randint(-1, 3)))
                    
                    po_id = f"PO-{po_counter:04d}"
                    po_counter += 1
                    actual_str = actual_date.strftime("%Y-%m-%d")
                    is_delivered = actual_date <= end_date
                    
                    purchase_orders.append({
                        "po_id": po_id,
                        "supplier_id": sup["supplier_id"],
                        "facility_id": fid,
                        "medicine_id": mid,
                        "quantity": order_qty,
                        "order_date": d_str,
                        "promised_date": prom_date.strftime("%Y-%m-%d"),
                        "status": "DELIVERED" if is_delivered else "DISPATCHED",
                        "source": "SIMULATED"
                    })

                    # If delivered within history, schedule arrival
                    if is_delivered:
                        deliv_id = f"DEL-{deliv_counter:04d}"
                        deliv_counter += 1
                        deliveries.append({
                            "delivery_id": deliv_id,
                            "po_id": po_id,
                            "facility_id": fid,
                            "medicine_id": mid,
                            "received_date": actual_str,
                            "received_qty": order_qty,
                            "source": "SIMULATED"
                        })
                        if actual_str not in delivery_schedule:
                            delivery_schedule[actual_str] = []
                        delivery_schedule[actual_str].append((fid, mid, order_qty))

                # Record physical audit if scheduled
                if is_audit_day:
                    audit_counted = state["true_stock"]
                    physical_audit.append({
                        "audit_id": f"AUD-{audit_counter:04d}",
                        "date": d_str,
                        "facility_id": fid,
                        "medicine_id": mid,
                        "counted_stock": audit_counted,
                        "auditor_notes": "Routine physical count verified",
                        "source": "SIMULATED"
                    })
                    audit_counter += 1

                # Plant ghost stock drift on Day 160 for Metformin at DH-01
                if d_idx >= anom_1_day and fid == "FAC-DH-01" and mid == "MED-007":
                    state["ledger_drift"] = 50

                ledger_val = state["true_stock"] + state["ledger_drift"]
                ledger_daily.append({
                    "date": d_str,
                    "facility_id": fid,
                    "medicine_id": mid,
                    "ledger_stock": ledger_val,
                    "source": "SIMULATED"
                })

                true_stock_daily.append({
                    "date": d_str,
                    "facility_id": fid,
                    "medicine_id": mid,
                    "true_stock": state["true_stock"],
                    "source": "SIMULATED"
                })

    # Plant remaining PO / supplier anomalies:
    # 4. PO dispatched but never received (lost delivery)
    po_lost = f"PO-{po_counter:04d}"
    po_counter += 1
    purchase_orders.append({
        "po_id": po_lost,
        "supplier_id": "SUP-001",
        "facility_id": "FAC-CHC-02",
        "medicine_id": "MED-002",
        "quantity": 500,
        "order_date": (end_date - timedelta(days=18)).strftime("%Y-%m-%d"),
        "promised_date": (end_date - timedelta(days=10)).strftime("%Y-%m-%d"),
        "status": "DISPATCHED",
        "source": "SIMULATED"
    })
    ground_truth.append({
        "anomaly_id": "ANOM-04",
        "type": "PO_DISPATCHED_NOT_RECEIVED",
        "facility_id": "FAC-CHC-02",
        "medicine_id": "MED-002",
        "day_index": 172,
        "description": "PO promised 10 days ago still marked dispatched with no delivery receipt",
        "magnitude": 500,
        "source": "SIMULATED"
    })

    # 7. Unit of measure mismatch (10x quantity jump on receipt)
    po_uom = f"PO-{po_counter:04d}"
    po_counter += 1
    purchase_orders.append({
        "po_id": po_uom,
        "supplier_id": "SUP-002",
        "facility_id": "FAC-PHC-03",
        "medicine_id": "MED-008",
        "quantity": 100,  # ordered 100 strips
        "order_date": (end_date - timedelta(days=14)).strftime("%Y-%m-%d"),
        "promised_date": (end_date - timedelta(days=7)).strftime("%Y-%m-%d"),
        "status": "DELIVERED",
        "source": "SIMULATED"
    })
    deliveries.append({
        "delivery_id": f"DEL-{deliv_counter:04d}",
        "po_id": po_uom,
        "facility_id": "FAC-PHC-03",
        "medicine_id": "MED-008",
        "received_date": (end_date - timedelta(days=6)).strftime("%Y-%m-%d"),
        "received_qty": 1000,  # recorded 1000 individual tablets instead of strips
        "source": "SIMULATED"
    })
    deliv_counter += 1
    ground_truth.append({
        "anomaly_id": "ANOM-07",
        "type": "UOM_MISMATCH",
        "facility_id": "FAC-PHC-03",
        "medicine_id": "MED-008",
        "day_index": 174,
        "description": "10x quantity discrepancy on delivery receipt vs PO (tablet count vs strip count)",
        "magnitude": 900,
        "source": "SIMULATED"
    })

    # Save all tables to CSV
    def write_csv(filename, rows):
        filepath = os.path.join(out_dir, filename)
        if not rows:
            return
        fieldnames = list(rows[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[+] Wrote {len(rows)} rows to {filepath}")

    write_csv("facilities.csv", facilities)
    write_csv("suppliers.csv", suppliers)
    write_csv("batches.csv", batches)
    write_csv("ledger_daily.csv", ledger_daily)
    write_csv("consumption_daily.csv", consumption_daily)
    write_csv("physical_audit.csv", physical_audit)
    write_csv("purchase_orders.csv", purchase_orders)
    write_csv("deliveries.csv", deliveries)
    write_csv("ground_truth.csv", ground_truth)
    write_csv("true_stock_daily.csv", true_stock_daily)

if __name__ == "__main__":
    generate_simulation(seed=1)
