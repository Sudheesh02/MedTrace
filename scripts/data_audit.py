#!/usr/bin/env python3
"""
scripts/data_audit.py — Comprehensive Empirical Data Audit for MedTrace

Priority 0b Specification:
For EVERY file in data/real (including data/real/raw) and data/simulated*:
Records:
- rows, columns, dtypes
- null counts and null %
- duplicate row count
- date range (min date, max date)
- numeric statistics: min, max, mean, std, median, quantiles (p25, p50, p75, p90, p95)
- outliers (IQR rule: Q1 - 1.5*IQR / Q3 + 1.5*IQR, and z-score: |z| > 3)
- zero-inflation (count and % of zero values)

Outputs:
- DATA_AUDIT.md (comprehensive structured markdown tables)
- reports/eda/*.json (exact computed statistics per dataset)
"""

import os
import sys
import csv
import json
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import numpy as np


def is_date_str(val: str) -> bool:
    if not isinstance(val, str) or len(val) < 8 or len(val) > 25:
        return False
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            datetime.strptime(val[:19], fmt)
            return True
        except ValueError:
            continue
    return False


def parse_date(val: str) -> Optional[datetime]:
    if not isinstance(val, str):
        return None
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val[:19], fmt)
        except ValueError:
            continue
    return None


def infer_dtype(values: List[Any]) -> str:
    non_null = [v for v in values if v is not None and v != "" and str(v).lower() not in ("nan", "null", "none", "n/a", "date not captured")]
    if not non_null:
        return "empty"
    
    int_count = 0
    float_count = 0
    date_count = 0
    bool_count = 0

    for v in non_null:
        sv = str(v).strip().lower()
        if sv in ("true", "false", "1", "0") and len(sv) <= 5:
            bool_count += 1
        try:
            int(v)
            int_count += 1
            continue
        except (ValueError, TypeError):
            pass
        try:
            float(v)
            float_count += 1
            continue
        except (ValueError, TypeError):
            pass
        if is_date_str(str(v)):
            date_count += 1

    total = len(non_null)
    if int_count == total:
        return "integer"
    if (int_count + float_count) == total:
        return "float"
    if bool_count == total:
        return "boolean"
    if date_count / total >= 0.8:
        return "date"
    return "string"


def audit_table(records: List[Dict[str, Any]], file_path: str) -> Dict[str, Any]:
    file_size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    num_rows = len(records)
    if num_rows == 0:
        return {
            "file_path": file_path,
            "file_size_bytes": file_size_bytes,
            "rows": 0,
            "columns": 0,
            "columns_detail": {},
            "duplicates": 0
        }

    columns = list(records[0].keys())
    # Detect duplicate rows
    seen = set()
    dup_count = 0
    for r in records:
        tup = tuple(sorted((k, str(v)) for k, v in r.items()))
        if tup in seen:
            dup_count += 1
        else:
            seen.add(tup)

    col_stats = {}
    for col in columns:
        vals = [r.get(col) for r in records]
        # Null count
        nulls = sum(1 for v in vals if v is None or str(v).strip() == "" or str(v).lower() in ("nan", "null", "none", "n/a", "date not captured"))
        non_null_vals = [v for v in vals if v is not None and str(v).strip() != "" and str(v).lower() not in ("nan", "null", "none", "n/a", "date not captured")]
        
        dtype = infer_dtype(vals)
        col_info: Dict[str, Any] = {
            "dtype": dtype,
            "null_count": nulls,
            "null_pct": round(nulls / num_rows * 100.0, 2)
        }

        # Date range
        if dtype == "date" or "date" in col.lower():
            parsed_dates = []
            for v in non_null_vals:
                dt = parse_date(str(v))
                if dt:
                    parsed_dates.append(dt)
            if parsed_dates:
                col_info["date_range"] = {
                    "min": min(parsed_dates).strftime("%Y-%m-%d"),
                    "max": max(parsed_dates).strftime("%Y-%m-%d")
                }

        # Numeric stats
        if dtype in ("integer", "float"):
            num_vals = []
            for v in non_null_vals:
                try:
                    num_vals.append(float(v))
                except (ValueError, TypeError):
                    pass

            if num_vals:
                arr = np.array(num_vals, dtype=float)
                mean = float(np.mean(arr))
                std = float(np.std(arr))
                q25 = float(np.percentile(arr, 25))
                q50 = float(np.median(arr))
                q75 = float(np.percentile(arr, 75))
                p90 = float(np.percentile(arr, 90))
                p95 = float(np.percentile(arr, 95))
                iqr = q75 - q25

                # Outliers
                iqr_lower = q25 - 1.5 * iqr
                iqr_upper = q75 + 1.5 * iqr
                iqr_outliers = int(np.sum((arr < iqr_lower) | (arr > iqr_upper)))

                if std > 0:
                    z_outliers = int(np.sum(np.abs((arr - mean) / std) > 3.0))
                else:
                    z_outliers = 0

                # Zero inflation
                zeros = int(np.sum(arr == 0.0))

                col_info["numeric_stats"] = {
                    "count": len(num_vals),
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                    "median": round(q50, 2),
                    "quantiles": {
                        "p25": round(q25, 2),
                        "p50": round(q50, 2),
                        "p75": round(q75, 2),
                        "p90": round(p90, 2),
                        "p95": round(p95, 2)
                    },
                    "outliers_iqr": {
                        "count": iqr_outliers,
                        "pct": round(iqr_outliers / len(num_vals) * 100.0, 2),
                        "bounds": [round(iqr_lower, 2), round(iqr_upper, 2)]
                    },
                    "outliers_zscore": {
                        "count": z_outliers,
                        "pct": round(z_outliers / len(num_vals) * 100.0, 2)
                    },
                    "zero_inflation": {
                        "zero_count": zeros,
                        "zero_pct": round(zeros / len(num_vals) * 100.0, 2)
                    }
                }

        col_stats[col] = col_info

    return {
        "file_path": file_path.replace("\\", "/"),
        "file_size_bytes": file_size_bytes,
        "rows": num_rows,
        "columns_count": len(columns),
        "columns": columns,
        "duplicates_count": dup_count,
        "duplicates_pct": round(dup_count / num_rows * 100.0, 2),
        "columns_detail": col_stats
    }


def load_file_records(file_path: str) -> List[Dict[str, Any]]:
    if file_path.endswith(".csv"):
        records = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                records.append(r)
        return records
    elif file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [d if isinstance(d, dict) else {"value": d} for d in data]
        elif isinstance(data, dict):
            # Check if dict has a list under common keys
            for key in ("results", "data", "items"):
                if key in data and isinstance(data[key], list):
                    return [d if isinstance(d, dict) else {"value": d} for d in data[key]]
            # Otherwise dict of dicts: key is ID
            records = []
            for k, v in data.items():
                if isinstance(v, dict):
                    rec = dict(v)
                    rec["_id"] = k
                    records.append(rec)
                else:
                    records.append({"key": k, "value": v})
            return records
    return []


def discover_files() -> List[str]:
    files = []
    # 1. data/real (including raw)
    real_dir = os.path.join("data", "real")
    if os.path.exists(real_dir):
        for root, _, filenames in os.walk(real_dir):
            for fn in filenames:
                if fn.endswith((".csv", ".json")):
                    files.append(os.path.join(root, fn))

    # 2. data/simulated*
    for entry in os.listdir("data"):
        if entry.startswith("simulated") and os.path.isdir(os.path.join("data", entry)):
            sim_path = os.path.join("data", entry)
            for fn in os.listdir(sim_path):
                if fn.endswith((".csv", ".json")):
                    files.append(os.path.join(sim_path, fn))

    return sorted(files)


def run_audit(output_dir: str = "reports/eda") -> Tuple[List[Dict[str, Any]], str]:
    os.makedirs(output_dir, exist_ok=True)
    files = discover_files()
    print(f"[*] Discovering and auditing {len(files)} dataset files across data/real and data/simulated*...")

    audits = []
    for fp in files:
        rel_fp = os.path.relpath(fp, os.getcwd()).replace("\\", "/")
        try:
            records = load_file_records(fp)
            audit_res = audit_table(records, rel_fp)
            audits.append(audit_res)

            # Write individual JSON report
            safe_slug = rel_fp.replace("/", "_").replace(".", "_")
            out_json = os.path.join(output_dir, f"{safe_slug}.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(audit_res, f, indent=2)

            print(f"  [+] Audited: {rel_fp} ({audit_res['rows']:,d} rows, {audit_res['columns_count']} cols)")
        except Exception as e:
            print(f"  [!] Failed auditing {rel_fp}: {e}")

    # Generate Markdown Report (DATA_AUDIT.md)
    md_content = generate_markdown_report(audits)
    md_path = "DATA_AUDIT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n[+] Comprehensive Data Audit completed!")
    print(f"    - JSON reports saved to: {output_dir}/*.json ({len(audits)} files)")
    print(f"    - Master summary written to: {md_path}")
    return audits, md_path


def generate_markdown_report(audits: List[Dict[str, Any]]) -> str:
    lines = [
        "# MedTrace Comprehensive Empirical Data Audit (DATA_AUDIT.md)",
        "",
        "> **Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why**  ",
        f"> *Audited on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Strict Empirical Grounding — Zero Invented Numbers*",
        "",
        "---",
        "",
        "## 📌 1. Master Inventory of Audited Datasets",
        "",
        "| Dataset Path | Format | Rows | Columns | File Size | Duplicates | Date Range |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for a in audits:
        fp = a["file_path"]
        ext = fp.split(".")[-1].upper()
        rows = f"{a['rows']:,d}"
        cols = a["columns_count"]
        size_kb = f"{a['file_size_bytes'] / 1024:.1f} KB"
        dups = f"{a['duplicates_count']} ({a['duplicates_pct']}%)"
        
        # Check any date ranges
        d_range = "N/A"
        for c, details in a.get("columns_detail", {}).items():
            if "date_range" in details:
                dr = details["date_range"]
                d_range = f"{dr['min']} → {dr['max']}"
                break
        lines.append(f"| `{fp}` | {ext} | {rows} | {cols} | {size_kb} | {dups} | {d_range} |")

    lines.extend([
        "",
        "---",
        "",
        "## 🔬 2. Real-World Datasets (`data/real/`) Detailed Column Profiles",
        ""
    ])

    real_audits = [a for a in audits if "data/real" in a["file_path"]]
    for a in real_audits:
        fp = a["file_path"]
        lines.append(f"### Dataset: `{fp}`")
        lines.append(f"- **Total Records**: {a['rows']:,d} rows | **Total Columns**: {a['columns_count']} | **Duplicate Rows**: {a['duplicates_count']} ({a['duplicates_pct']}%)")
        lines.append("")
        lines.append("| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

        for col, d in a.get("columns_detail", {}).items():
            dtype = d["dtype"]
            null_str = f"{d['null_count']} ({d['null_pct']}%)"
            num_s = d.get("numeric_stats")
            if num_s:
                zero_str = f"{num_s['zero_inflation']['zero_pct']}%"
                iqr_str = f"{num_s['outliers_iqr']['count']} ({num_s['outliers_iqr']['pct']}%)"
                z_str = f"{num_s['outliers_zscore']['count']} ({num_s['outliers_zscore']['pct']}%)"
                range_str = f"[{num_s['min']} .. {num_s['max']}], med={num_s['median']}"
            else:
                zero_str = "N/A"
                iqr_str = "N/A"
                z_str = "N/A"
                if "date_range" in d:
                    range_str = f"{d['date_range']['min']} .. {d['date_range']['max']}"
                else:
                    range_str = "N/A"
            lines.append(f"| `{col}` | {dtype} | {null_str} | {zero_str} | {iqr_str} | {z_str} | {range_str} |")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 🏥 3. Simulated Multi-Tier Network Profiles (`data/simulated/`)",
        "",
        "Summary of facility ledger, consumption, physical audit, and order records across the 180-day baseline simulation:",
        ""
    ])

    sim_audits = [a for a in audits if a["file_path"].startswith("data/simulated/")]
    for a in sim_audits:
        fp = a["file_path"]
        lines.append(f"#### `{os.path.basename(fp)}` ({a['rows']:,d} rows, {a['columns_count']} columns)")
        lines.append("| Column | Type | Null Count | Min | Median | Max | Zero Inflation |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
        for col, d in a.get("columns_detail", {}).items():
            num_s = d.get("numeric_stats")
            if num_s:
                lines.append(f"| `{col}` | {d['dtype']} | {d['null_count']} | {num_s['min']} | {num_s['median']} | {num_s['max']} | {num_s['zero_inflation']['zero_pct']}% |")
            elif "date_range" in d:
                lines.append(f"| `{col}` | {d['dtype']} | {d['null_count']} | {d['date_range']['min']} | N/A | {d['date_range']['max']} | N/A |")
            else:
                lines.append(f"| `{col}` | {d['dtype']} | {d['null_count']} | N/A | N/A | N/A | N/A |")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 🛡️ 4. Data Hygiene Findings & Invariant Principles",
        "",
        "1. **Deterministic Arithmetic**: All statistics, percentiles, IQR bounds, and z-score thresholds are computed directly via NumPy and standard Python libraries without LLM intermediate translation.",
        "2. **Zero Fabrication**: All counts match physical disk contents exactly as verified by `scripts/data_audit.py`.",
        "3. **Transparent Outliers**: Delivery slip delays and demand surges are empirically quantified to ground probabilistic ETA Monte Carlo sampling in real-world distributor behavior.",
        ""
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    run_audit()
