"""
scripts/process_real_data.py — Real-World Empirical Data Cleaning & Calibration Pipeline
Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why

Priority 0b Specification:
1. USAID Deliveries:
   - Parse heterogeneous dates (%d-%b-%y, %m/%d/%y, %Y-%m-%d, %d-%b-%Y)
   - Handle 'Date Not Captured', N/A, and empty strings
   - Deduplicate rows across (ID, Scheduled Date, Delivered Date, Vendor)
   - Winsorize / clamp extreme delivery slip values (-60 to +180 days)
   - Minimum threshold n >= 15 records per (vendor, mode) group
   - Compute POOLED_PRIOR for vendor-mode groups below minimum sample threshold
   - Output: data/real/raw/cleaned_usaid_deliveries.csv & data/real/supplier_slip.csv

2. Kaggle Pharma Sales Daily:
   - Handle and document zero-demand days (Sunday/holiday closures vs missing values)
   - Compute baseline daily means per ATC group (M01AB, M01AE, N02BA, N02BE, N05B, N05C, R03, R06)
   - Normalize seasonal multipliers (multiplier = day_val / group_mean)
   - Output: data/real/raw/cleaned_salesdaily.csv & data/real/demand_shapes.csv

3. OpenFDA Recall Registry:
   - Deduplicate enforcement recall events by recall_number
   - Normalize generic medicine identifiers
   - Output: data/real/openfda_enforcement_recalls.json
"""

import os
import csv
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    val = date_str.strip()
    if val.lower() in ("date not captured", "n/a", "null", "none", "", "nan"):
        return None
    for fmt in ("%d-%b-%y", "%m/%d/%y", "%Y-%m-%d", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(val[:19], fmt)
        except ValueError:
            continue
    return None


def clean_usaid_deliveries(
    raw_path: str = "data/real/raw/usaid_deliveries.csv",
    cleaned_csv_path: Optional[str] = "data/real/raw/cleaned_usaid_deliveries.csv",
    out_slip_path: Optional[str] = "data/real/supplier_slip.csv",
    min_vendor_records: int = 15,
    min_slip_clamp: int = -60,
    max_slip_clamp: int = 180
) -> Dict[str, Any]:
    """
    Cleans raw USAID delivery records:
    - Drops invalid/missing date entries
    - Deduplicates identical records
    - Winsorizes extreme delivery slip outliers to [min_slip_clamp, max_slip_clamp]
    - Computes empirical vendor-mode slip distributions and pooled prior fallback
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Missing raw USAID delivery dataset: {raw_path}")

    total_raw = 0
    missing_dates = 0
    duplicates = 0
    winsorized_count = 0
    valid_rows = []
    seen_keys = set()
    all_slips_pooled = []
    vendor_slips = {}

    with open(raw_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_raw += 1
            sched_str = row.get("Scheduled Delivery Date")
            deliv_str = row.get("Delivered to Client Date")
            vendor = (row.get("Vendor") or "Unknown").strip()
            mode = (row.get("Shipment Mode") or "Air").strip()
            po_id = (row.get("PO / SO #") or row.get("ASN/DN #") or "").strip()
            line_id = (row.get("ID") or f"ROW-{total_raw}").strip()
            item_desc = (row.get("Item Description") or "").strip()
            line_qty = (row.get("Line Item Quantity") or "").strip()

            d_sched = parse_date(sched_str)
            d_deliv = parse_date(deliv_str)

            if not d_sched or not d_deliv:
                missing_dates += 1
                continue

            # Grounded deduplication key: includes line item ID, PO, dates, product description, and quantity.
            # Prevents collapsing distinct product line items within the same multi-item purchase order.
            dedup_key = (line_id, po_id, d_sched.strftime("%Y-%m-%d"), d_deliv.strftime("%Y-%m-%d"), item_desc, line_qty, vendor, mode)
            if dedup_key in seen_keys:
                duplicates += 1
                continue
            seen_keys.add(dedup_key)

            raw_slip = (d_deliv - d_sched).days
            # Documented winsorization rule: cap extreme slip noise to [-60, +180] days
            clamped_slip = max(min_slip_clamp, min(max_slip_clamp, raw_slip))
            if clamped_slip != raw_slip:
                winsorized_count += 1

            cleaned_row = {
                "line_id": line_id,
                "po_id": po_id,
                "vendor": vendor,
                "shipment_mode": mode,
                "item_description": item_desc,
                "line_quantity": line_qty,
                "scheduled_date": d_sched.strftime("%Y-%m-%d"),
                "delivered_date": d_deliv.strftime("%Y-%m-%d"),
                "raw_slip_days": raw_slip,
                "clamped_slip_days": clamped_slip
            }
            valid_rows.append(cleaned_row)
            all_slips_pooled.append(clamped_slip)

            v_key = (vendor, mode)
            if v_key not in vendor_slips:
                vendor_slips[v_key] = []
            vendor_slips[v_key].append(clamped_slip)

    # Save cleaned delivery records
    if cleaned_csv_path:
        os.makedirs(os.path.dirname(os.path.abspath(cleaned_csv_path)), exist_ok=True)
        if valid_rows:
            with open(cleaned_csv_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = list(valid_rows[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(valid_rows)

    # Compute vendor-mode slip priors and pooled prior fallback
    slip_records = []
    sorted_vendors = sorted(vendor_slips.items(), key=lambda x: len(x[1]), reverse=True)

    for (vendor, mode), slips in sorted_vendors:
        if len(slips) >= min_vendor_records:
            slips_sorted = sorted(slips)
            n = len(slips)
            mean_slip = sum(slips) / n
            p50 = slips_sorted[int(n * 0.50)]
            p90 = slips_sorted[int(n * 0.90)]
            slip_records.append({
                "vendor": vendor,
                "shipment_mode": mode,
                "n_records": n,
                "mean_slip_days": round(mean_slip, 2),
                "median_p50_days": p50,
                "p90_days": p90,
                "min_days": slips_sorted[0],
                "max_days": slips_sorted[-1]
            })

    # Pooled prior fallback for unseen / sparse vendor-mode combinations
    if all_slips_pooled:
        pooled_sorted = sorted(all_slips_pooled)
        n_p = len(pooled_sorted)
        slip_records.append({
            "vendor": "POOLED_PRIOR",
            "shipment_mode": "ALL",
            "n_records": n_p,
            "mean_slip_days": round(sum(all_slips_pooled) / n_p, 2),
            "median_p50_days": pooled_sorted[int(n_p * 0.50)],
            "p90_days": pooled_sorted[int(n_p * 0.90)],
            "min_days": pooled_sorted[0],
            "max_days": pooled_sorted[-1]
        })

    if out_slip_path and slip_records:
        os.makedirs(os.path.dirname(os.path.abspath(out_slip_path)), exist_ok=True)
        with open(out_slip_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(slip_records[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(slip_records)

    stats = {
        "dataset": "USAID Deliveries",
        "total_raw_rows": total_raw,
        "dropped_missing_dates": missing_dates,
        "dropped_duplicates": duplicates,
        "winsorized_extreme_slips": winsorized_count,
        "cleaned_valid_rows": len(valid_rows),
        "vendor_mode_priors_count": len(slip_records)
    }
    return stats


def clean_pharma_sales(
    raw_path: str = "data/real/raw/salesdaily.csv",
    cleaned_csv_path: Optional[str] = "data/real/raw/cleaned_salesdaily.csv",
    out_shapes_path: Optional[str] = "data/real/demand_shapes.csv"
) -> Dict[str, Any]:
    """
    Cleans raw Pharma Sales Daily data:
    - Validates numeric columns across 8 ATC therapeutic groups
    - Quantifies zero-demand records (documenting retail pharmacy holiday/weekend zero dispensing)
    - Computes baseline daily means per group and normalized multipliers
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Missing raw Pharma Sales dataset: {raw_path}")

    atc_groups = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]
    total_raw = 0
    invalid_rows = 0
    zero_counts = {g: 0 for g in atc_groups}
    group_sums = {g: 0.0 for g in atc_groups}
    group_counts = {g: 0 for g in atc_groups}
    daily_records = []

    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_raw += 1
            datum = row.get("datum", "").strip()
            record = {"datum": datum}
            valid = True

            for g in atc_groups:
                try:
                    val = float(row.get(g, 0.0))
                    record[g] = val
                    if val == 0.0:
                        zero_counts[g] += 1
                    group_sums[g] += val
                    group_counts[g] += 1
                except (ValueError, TypeError):
                    valid = False

            if valid and datum:
                daily_records.append(record)
            else:
                invalid_rows += 1

    # Compute baseline arithmetic means
    group_means = {g: (group_sums[g] / max(1, group_counts[g])) for g in atc_groups}

    # Normalize each day into multiplier = val / mean
    normalized_rows = []
    for r in daily_records:
        row_norm = {"datum": r["datum"]}
        for g in atc_groups:
            mean = group_means[g]
            mult = (r[g] / mean) if mean > 0 else 1.0
            row_norm[f"{g}_multiplier"] = round(mult, 3)
        normalized_rows.append(row_norm)

    # Save cleaned daily sales
    if cleaned_csv_path:
        os.makedirs(os.path.dirname(os.path.abspath(cleaned_csv_path)), exist_ok=True)
        if daily_records:
            with open(cleaned_csv_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = ["datum"] + atc_groups
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(daily_records)

    # Save normalized demand shapes
    if out_shapes_path and normalized_rows:
        os.makedirs(os.path.dirname(os.path.abspath(out_shapes_path)), exist_ok=True)
        with open(out_shapes_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(normalized_rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(normalized_rows)

    stats = {
        "dataset": "Pharma Sales Daily",
        "total_raw_rows": total_raw,
        "dropped_invalid_rows": invalid_rows,
        "cleaned_valid_rows": len(daily_records),
        "zero_demand_counts": zero_counts,
        "group_baseline_means": {k: round(v, 2) for k, v in group_means.items()}
    }
    return stats


def clean_openfda_recalls(
    raw_path: str = "data/real/openfda_enforcement_recalls.json",
    cleaned_json_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cleans OpenFDA drug enforcement recall records:
    - Deduplicates recall records by recall_number
    - Normalizes medicine identifiers and generic names
    """
    if not os.path.exists(raw_path):
        return {"dataset": "OpenFDA Recalls", "status": "FILE_NOT_FOUND"}

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_records = data.get("all_records", [])
    deduped = {}
    duplicates = 0

    for rec in all_records:
        r_num = rec.get("recall_number", "").strip()
        if not r_num:
            continue
        if r_num in deduped:
            duplicates += 1
            continue
        # Normalize fields
        rec["matched_generic"] = rec.get("matched_generic", "").lower().strip()
        rec["matched_medicine_id"] = rec.get("matched_medicine_id", "").upper().strip()
        deduped[r_num] = rec

    cleaned_records = list(deduped.values())

    if cleaned_json_path:
        os.makedirs(os.path.dirname(os.path.abspath(cleaned_json_path)), exist_ok=True)
        with open(cleaned_json_path, "w", encoding="utf-8") as f:
            json.dump({"meta": data.get("meta", {}), "cleaned_records": cleaned_records}, f, indent=2)

    return {
        "dataset": "OpenFDA Recalls",
        "total_raw_records": len(all_records),
        "duplicates_removed": duplicates,
        "cleaned_records_count": len(cleaned_records)
    }


def run_cleaning_pipeline(
    output_dir: str = "data/real",
    raw_dir: str = "data/real/raw",
    reports_dir: str = "reports/eda"
) -> Dict[str, Any]:
    """
    Executes the end-to-end data cleaning pipeline across all real-world data sources.
    Outputs cleaned datasets and logs cleaning summary to reports_dir/cleaning_summary.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    usaid_stats = clean_usaid_deliveries(
        raw_path=os.path.join(raw_dir, "usaid_deliveries.csv"),
        cleaned_csv_path=os.path.join(raw_dir, "cleaned_usaid_deliveries.csv"),
        out_slip_path=os.path.join(output_dir, "supplier_slip.csv")
    )

    pharma_stats = clean_pharma_sales(
        raw_path=os.path.join(raw_dir, "salesdaily.csv"),
        cleaned_csv_path=os.path.join(raw_dir, "cleaned_salesdaily.csv"),
        out_shapes_path=os.path.join(output_dir, "demand_shapes.csv")
    )

    recall_stats = clean_openfda_recalls(
        raw_path=os.path.join(output_dir, "openfda_enforcement_recalls.json")
    )

    summary = {
        "timestamp": datetime.now().isoformat(),
        "usaid_deliveries": usaid_stats,
        "pharma_sales": pharma_stats,
        "openfda_recalls": recall_stats
    }

    summary_file = os.path.join(reports_dir, "cleaning_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[+] Data Cleaning Pipeline finalized:")
    print(f"    - USAID: {usaid_stats['total_raw_rows']} raw -> {usaid_stats['cleaned_valid_rows']} cleaned ({usaid_stats['dropped_missing_dates']} missing dates, {usaid_stats['dropped_duplicates']} dups, {usaid_stats['winsorized_extreme_slips']} clamped)")
    print(f"    - Pharma Sales: {pharma_stats['total_raw_rows']} raw -> {pharma_stats['cleaned_valid_rows']} cleaned")
    print(f"    - OpenFDA: {recall_stats['total_raw_records']} raw -> {recall_stats['cleaned_records_count']} cleaned ({recall_stats['duplicates_removed']} dups)")
    print(f"    - Master cleaning summary saved to: {summary_file}")
    return summary


def main():
    run_cleaning_pipeline()


if __name__ == "__main__":
    main()
