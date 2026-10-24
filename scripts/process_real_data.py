"""
Process DC-2 (USAID Deliveries) and DC-5 (Pharma Sales Daily) into clean derived tables:
1. DC-3: data/real/supplier_slip.csv (Vendor delay distributions & slip priors)
2. DC-5: data/real/demand_shapes.csv (Normalized seasonal daily multipliers per ATC group)
"""

import os
import csv
from datetime import datetime

def parse_date(date_str):
    if not date_str or date_str in ["Date Not Captured", "N/A", ""]:
        return None
    # formats seen in USAID: 2-Jun-06, 11/13/06, 2015-06-15, etc.
    for fmt in ["%d-%b-%y", "%m/%d/%y", "%Y-%m-%d", "%d-%b-%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None

def process_usaid_deliveries():
    raw_path = os.path.join("data", "real", "raw", "usaid_deliveries.csv")
    out_slip_path = os.path.join("data", "real", "supplier_slip.csv")
    if not os.path.exists(raw_path):
        print(f"[-] Missing {raw_path}")
        return

    print("[*] Processing USAID deliveries into supplier slip priors (DC-3)...")
    vendor_slips = {}
    total_rows = 0
    valid_rows = 0

    with open(raw_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            sched_str = row.get("Scheduled Delivery Date")
            deliv_str = row.get("Delivered to Client Date")
            vendor = row.get("Vendor", "Unknown").strip()
            mode = row.get("Shipment Mode", "Air").strip()

            d_sched = parse_date(sched_str)
            d_deliv = parse_date(deliv_str)

            if d_sched and d_deliv and vendor:
                slip = (d_deliv - d_sched).days
                # clamp extreme noise (-60 to +180 days)
                if -60 <= slip <= 180:
                    key = (vendor, mode)
                    if key not in vendor_slips:
                        vendor_slips[key] = []
                    vendor_slips[key].append(slip)
                    valid_rows += 1

    print(f"[+] Total raw rows: {total_rows}, Valid dated delivery records: {valid_rows}")
    
    # Select top vendor-mode pairs with n >= 15
    slip_records = []
    sorted_vendors = sorted(vendor_slips.items(), key=lambda x: len(x[1]), reverse=True)
    
    for (vendor, mode), slips in sorted_vendors:
        if len(slips) >= 15:
            slips_sorted = sorted(slips)
            n = len(slips)
            mean_slip = sum(slips) / n
            p50 = slips_sorted[int(n * 0.50)]
            p90 = slips_sorted[int(n * 0.90)]
            min_slip = slips_sorted[0]
            max_slip = slips_sorted[-1]
            slip_records.append({
                "vendor": vendor,
                "shipment_mode": mode,
                "n_records": n,
                "mean_slip_days": round(mean_slip, 2),
                "median_p50_days": p50,
                "p90_days": p90,
                "min_days": min_slip,
                "max_days": max_slip
            })

    # Save to CSV
    if slip_records:
        with open(out_slip_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(slip_records[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(slip_records)
        print(f"[+] Wrote {len(slip_records)} vendor-mode delay distributions to {out_slip_path}")

def process_pharma_sales():
    raw_path = os.path.join("data", "real", "raw", "salesdaily.csv")
    out_shapes_path = os.path.join("data", "real", "demand_shapes.csv")
    if not os.path.exists(raw_path):
        print(f"[-] Missing {raw_path}")
        return

    print("[*] Processing Pharma Sales Daily into seasonal demand multipliers (DC-5)...")
    atc_groups = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]
    
    daily_records = []
    group_sums = {g: 0.0 for g in atc_groups}
    group_counts = {g: 0 for g in atc_groups}

    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {"datum": row.get("datum", "")}
            valid = True
            for g in atc_groups:
                try:
                    val = float(row.get(g, 0.0))
                    record[g] = val
                    group_sums[g] += val
                    group_counts[g] += 1
                except ValueError:
                    valid = False
            if valid:
                daily_records.append(record)

    # Compute means
    group_means = {g: (group_sums[g] / max(1, group_counts[g])) for g in atc_groups}
    print("[+] Computed baseline means per ATC group:", {k: round(v, 2) for k, v in group_means.items()})

    # Normalize each day into multiplier = val / mean
    normalized_rows = []
    for r in daily_records:
        row_norm = {"datum": r["datum"]}
        for g in atc_groups:
            mean = group_means[g]
            mult = (r[g] / mean) if mean > 0 else 1.0
            row_norm[f"{g}_multiplier"] = round(mult, 3)
        normalized_rows.append(row_norm)

    with open(out_shapes_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(normalized_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized_rows)
    print(f"[+] Wrote {len(normalized_rows)} normalized daily demand shapes to {out_shapes_path}")

def main():
    process_usaid_deliveries()
    process_pharma_sales()

if __name__ == "__main__":
    main()
