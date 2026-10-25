"""
Unit and Integration Tests for Enriched Data & Multi-Agent Loop (tests/test_enriched_data.py)
Validates:
1. DataStore accessors for newly ingested public health datasets.
2. DeterministicEngine UOM normalization and WHO GHO demand multipliers.
3. Reconciler discrepancy generation for UOM mismatch and FDA recalls.
4. Investigator and Skeptic adversarial review loop.
"""

import pytest
from app.adapters.data_store import DataStore
from app.engine.deterministic import DeterministicEngine
from app.engines.world_model import WorldStoreService, IngestPipelineService
from app.agents.reconciler import ReconcilerAgent
from app.agents.investigator import InvestigatorAgent
from app.agents.skeptic import SkepticAgent
from app.adapters.llm_client import LLMClient

@pytest.fixture
def store():
    return DataStore(use_zetaris=False)

def test_datastore_enriched_accessors(store):
    # Test openFDA enforcement recalls
    recalls = store.get_openfda_recalls(medicine_id="MED-001")
    assert isinstance(recalls, list)
    assert len(recalls) > 0
    assert "reason_for_recall" in recalls[0]

    # Test RxNorm standards
    rxnorm = store.get_rxnorm_standard("MED-001")
    assert rxnorm is not None
    assert rxnorm["rxcui"] == "161"
    assert "acetaminophen" in rxnorm["rxnorm_name"].lower()

    # Test DailyMed packaging standards
    pkg = store.get_packaging_standard("MED-001")
    assert pkg is not None
    assert "storage_condition" in pkg

    # Test WHO disease surveillance
    surv = store.get_disease_surveillance("MED-009")
    assert surv is not None
    assert surv["epidemiological_risk_tier"] == "ELEVATED"

    # Test cross-border shortages
    shortage = store.get_cross_border_shortages(medicine_id="MED-007")
    assert shortage is not None
    assert "root_cause_classification" in shortage

    # Test deliveries
    deliveries = store.get_deliveries()
    assert isinstance(deliveries, list)
    assert len(deliveries) > 0

def test_deterministic_uom_normalization():
    # Box of 100 tablets vs individual tablet
    res = DeterministicEngine.normalize_uom_quantity(
        reported_quantity=5,
        reported_unit="box",
        dispensing_unit="tablet"
    )
    assert res["uom_mismatch_detected"] is True
    assert res["pack_multiplier"] == 100.0
    assert res["normalized_quantity"] == 500.0

    # Custom pack size multiplier
    res_custom = DeterministicEngine.normalize_uom_quantity(
        reported_quantity=10,
        reported_unit="strip",
        dispensing_unit="tablet",
        pack_size_units=10
    )
    assert res_custom["uom_mismatch_detected"] is True
    assert res_custom["normalized_quantity"] == 100.0

def test_deterministic_epidemiological_multiplier():
    # Standard risk tier
    res_std = DeterministicEngine.compute_epidemiological_demand_multiplier(
        base_rate=20.0,
        surveillance_data={"epidemiological_risk_tier": "STANDARD"}
    )
    assert res_std["who_surveillance_multiplier"] == 1.0
    assert res_std["adjusted_daily_demand"] == 20.0
    assert res_std["demand_spike_detected"] is False

    # Elevated risk tier (outbreak surge)
    res_elevated = DeterministicEngine.compute_epidemiological_demand_multiplier(
        base_rate=20.0,
        atc_seasonal_multiplier=1.1,
        surveillance_data={"epidemiological_risk_tier": "ELEVATED"}
    )
    assert res_elevated["who_surveillance_multiplier"] == 1.35
    assert res_elevated["combined_multiplier"] >= 1.40
    assert res_elevated["demand_spike_detected"] is True
    assert res_elevated["adjusted_daily_demand"] > 25.0

def test_reconciler_and_skeptic_loop(store):
    world_store = WorldStoreService()
    ingest = IngestPipelineService(world_store)
    reconciler = ReconcilerAgent(store, ingest)
    llm = LLMClient()
    investigator = InvestigatorAgent(llm)
    skeptic = SkepticAgent(llm)

    # Reconcile quarantined item
    recon = reconciler.reconcile_item("FAC-CHC-01", "MED-001")
    assert recon["facility_id"] == "FAC-CHC-01"
    assert recon["medicine_id"] == "MED-001"
    discs = recon["discrepancies"]
    assert any(d["anomaly_type"] == "QUARANTINED_BATCH" for d in discs)

    # Investigator generates hypotheses
    hypotheses = investigator.investigate(recon, context={})
    assert len(hypotheses) == 3

    # Skeptic reviews and audits numbers
    top_hyp, review = skeptic.review_and_audit(
        hypotheses=hypotheses,
        deterministic_recon=recon["deterministic_reconciliation"],
        round_number=1
    )
    assert review.audited_numbers_valid is True
    assert review.confidence_score > 0.0

def test_datastore_uom_pack_multiplier_grounding(store):
    """
    Validates that DataStore derives packaging multipliers directly from
    DailyMed and RxNorm standards without hardcoding.
    """
    # Dispensing unit for MED-001 is tablet, MED-004 is capsule
    assert store.get_uom_pack_multiplier("MED-001", "tablet") == 1.0
    assert store.get_uom_pack_multiplier("MED-001", "strip") == 10.0
    assert store.get_uom_pack_multiplier("MED-001", "box") == 100.0
    assert store.get_uom_pack_multiplier("MED-001", "carton") == 100.0

    assert store.get_uom_pack_multiplier("MED-004", "capsule") == 1.0
    assert store.get_uom_pack_multiplier("MED-004", "blister") == 10.0
    assert store.get_uom_pack_multiplier("MED-004", "box of 100") == 100.0

def test_reconciler_uom_mismatch_uses_packaging_standards(store):
    """
    Validates that ReconcilerAgent extracts dispensing unit and packaging spec
    from DailyMed / RxNorm data when reconciling PO vs delivery quantities.
    """
    world_store = WorldStoreService()
    ingest = IngestPipelineService(world_store)
    reconciler = ReconcilerAgent(store, ingest)

    # Mock deliveries with a 10x pack mismatch
    mock_deliveries = [{
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-004",
        "po_id": "PO-TEST-001",
        "received_qty": 50.0,
        "delivery_date": "2026-03-01"
    }]
    mock_pos = [{
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-004",
        "po_id": "PO-TEST-001",
        "quantity": 500.0,
        "status": "DELIVERED"
    }]

    # Temporarily monkeypatch get_deliveries and get_purchase_orders
    orig_deliv = store.get_deliveries
    orig_pos = store.get_purchase_orders
    try:
        store.get_deliveries = lambda fac, med: mock_deliveries
        store.get_purchase_orders = lambda fac, med: mock_pos

        recon = reconciler.reconcile_item("FAC-DH-01", "MED-004")
        uom_disc = next((d for d in recon["discrepancies"] if d["anomaly_type"] == "UOM_MISMATCH"), None)
        assert uom_disc is not None
        # MED-004 dispensing unit is capsule from DailyMed / RxNorm
        assert "capsule" in uom_disc["description"].lower()
    finally:
        store.get_deliveries = orig_deliv
        store.get_purchase_orders = orig_pos


def test_data_audit_execution_and_artifacts(tmp_path):
    """
    Priority 0b Gate: Verifies that scripts/data_audit.py executes cleanly,
    outputs DATA_AUDIT.md and reports/eda/*.json, and computes exact statistics
    from disk with zero invented numbers.
    """
    import os
    import json
    from scripts.data_audit import run_audit

    tmp_md = tmp_path / "DATA_AUDIT.md"
    tmp_eda = tmp_path / "eda"
    audits, md_path = run_audit(output_dir=str(tmp_eda), md_path=str(tmp_md))
    assert len(audits) >= 50
    assert os.path.exists(md_path)

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "# MedTrace Comprehensive Empirical Data Audit (DATA_AUDIT.md)" in md_text
    assert "data/real/raw/salesdaily.csv" in md_text
    assert "data/real/raw/usaid_deliveries.csv" in md_text
    assert "data/simulated/ledger_daily.csv" in md_text

    # Verify JSON reports exist
    report_files = [f for f in os.listdir(str(tmp_eda)) if f.endswith(".json")]
    assert len(report_files) >= 50

    sample_report_path = os.path.join(str(tmp_eda), report_files[0])
    with open(sample_report_path, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    assert "file_path" in sample_data
    assert "rows" in sample_data
    assert "columns_count" in sample_data
    assert "columns_detail" in sample_data


def test_process_real_data_cleaning_pipeline(tmp_path):
    """
    Priority 0b Gate: Verifies that scripts/process_real_data.py cleans raw datasets,
    handles missing/invalid dates, deduplicates records, winsorizes extreme slips,
    computes empirical priors with pooled fallbacks, and writes summary reports.
    """
    import os
    import csv
    from scripts.process_real_data import clean_usaid_deliveries, clean_pharma_sales, clean_openfda_recalls

    # 1. Clean USAID Deliveries into temp dir
    cleaned_usaid = tmp_path / "cleaned_usaid.csv"
    out_slip = tmp_path / "supplier_slip.csv"
    u_stats = clean_usaid_deliveries(
        raw_path="data/real/raw/usaid_deliveries.csv",
        cleaned_csv_path=str(cleaned_usaid),
        out_slip_path=str(out_slip)
    )
    assert u_stats["total_raw_rows"] > 5000
    assert u_stats["cleaned_valid_rows"] > 0
    assert u_stats["cleaned_valid_rows"] <= u_stats["total_raw_rows"]
    assert u_stats["dropped_duplicates"] >= 0
    assert u_stats["winsorized_extreme_slips"] > 0
    assert os.path.exists(cleaned_usaid)
    assert os.path.exists(out_slip)

    # Verify supplier_slip has pooled prior fallback
    with open(out_slip, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) >= 5
    assert any(r["vendor"] == "POOLED_PRIOR" for r in reader)

    # 2. Clean Pharma Sales into temp dir
    cleaned_sales = tmp_path / "cleaned_sales.csv"
    out_shapes = tmp_path / "demand_shapes.csv"
    p_stats = clean_pharma_sales(
        raw_path="data/real/raw/salesdaily.csv",
        cleaned_csv_path=str(cleaned_sales),
        out_shapes_path=str(out_shapes)
    )
    assert p_stats["total_raw_rows"] > 2000
    assert p_stats["cleaned_valid_rows"] > 0
    assert len(p_stats["zero_demand_counts"]) == 8
    assert os.path.exists(cleaned_sales)
    assert os.path.exists(out_shapes)

def test_usaid_multiline_po_preservation(tmp_path):
    """
    Anti-Hardcoding & Data Rigor Audit Test:
    Verifies that multi-line-item purchase orders sharing the same PO number,
    vendor, mode, and scheduled/delivered dates are preserved as distinct deliveries,
    while true exact duplicate rows are correctly dropped.
    """
    import csv
    from scripts.process_real_data import clean_usaid_deliveries

    raw_csv = tmp_path / "raw_usaid.csv"
    cleaned_csv = tmp_path / "cleaned_usaid.csv"
    slip_csv = tmp_path / "slip.csv"

    headers = [
        "ID", "PO / SO #", "Vendor", "Shipment Mode",
        "Scheduled Delivery Date", "Delivered to Client Date",
        "Item Description", "Line Item Quantity"
    ]
    rows = [
        # Line 1: Saquinavir under PO SCMS-19800
        {"ID": "422", "PO / SO #": "SCMS-19800", "Vendor": "VendorA", "Shipment Mode": "Air",
         "Scheduled Delivery Date": "2-Jun-06", "Delivered to Client Date": "2-Jun-06",
         "Item Description": "Saquinavir 200mg", "Line Item Quantity": "6"},
        # Line 2: Stavudine under same PO SCMS-19800 on same dates (distinct item)
        {"ID": "423", "PO / SO #": "SCMS-19800", "Vendor": "VendorA", "Shipment Mode": "Air",
         "Scheduled Delivery Date": "2-Jun-06", "Delivered to Client Date": "2-Jun-06",
         "Item Description": "Stavudine 1mg/ml", "Line Item Quantity": "600"},
        # Line 3: True exact duplicate of Line 2
        {"ID": "423", "PO / SO #": "SCMS-19800", "Vendor": "VendorA", "Shipment Mode": "Air",
         "Scheduled Delivery Date": "2-Jun-06", "Delivered to Client Date": "2-Jun-06",
         "Item Description": "Stavudine 1mg/ml", "Line Item Quantity": "600"},
    ]

    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    stats = clean_usaid_deliveries(
        raw_path=str(raw_csv),
        cleaned_csv_path=str(cleaned_csv),
        out_slip_path=str(slip_csv)
    )

    assert stats["total_raw_rows"] == 3
    assert stats["dropped_duplicates"] == 1
    assert stats["cleaned_valid_rows"] == 2

    with open(cleaned_csv, "r", encoding="utf-8") as f:
        cleaned_records = list(csv.DictReader(f))

    assert len(cleaned_records) == 2
    items = [r["item_description"] for r in cleaned_records]
    assert "Saquinavir 200mg" in items
    assert "Stavudine 1mg/ml" in items


def test_eda_charts_generation(tmp_path):
    """
    Priority 0b Item 3 Gate: Verifies that scripts/generate_eda_charts.py generates
    all 5 high-resolution empirical EDA figures in PNG format:
    1. supplier_slip_distribution.png
    2. demand_seasonality_patterns.png
    3. zero_demand_share.png
    4. simulated_vs_real_comparison.png
    5. stockout_lead_time_distribution.png
    """
    import os
    from scripts.generate_eda_charts import generate_all_eda_charts

    out_dir = str(tmp_path / "eda_test_output")
    charts = generate_all_eda_charts(data_dir="data", output_dir=out_dir)

    expected_names = [
        "supplier_slip_distribution.png",
        "demand_seasonality_patterns.png",
        "zero_demand_share.png",
        "simulated_vs_real_comparison.png",
        "stockout_lead_time_distribution.png"
    ]

    assert len(charts) == 5
    for name in expected_names:
        expected_path = os.path.join(out_dir, name)
        assert os.path.exists(expected_path), f"Missing expected chart: {expected_path}"
        # Validate file size (> 15 KB)
        fsize = os.path.getsize(expected_path)
        assert fsize > 15000, f"Chart {name} suspiciously small: {fsize} bytes"
        # Validate PNG magic bytes header
        with open(expected_path, "rb") as f:
            header = f.read(8)
            assert header == b"\x89PNG\r\n\x1a\n", f"File {name} is not a valid PNG image"

    # Verify reports/eda/README.md exists and documents the visual findings
    readme_path = os.path.join("reports", "eda", "README.md")
    assert os.path.exists(readme_path), "reports/eda/README.md documentation must exist"
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()
    for name in expected_names:
        assert name in readme_content, f"README.md must reference {name}"


def test_generate_eda_charts_cli(tmp_path):
    """
    Verifies that scripts/generate_eda_charts.py executes cleanly as a standalone CLI script.
    """
    import sys
    import subprocess
    import os

    cli_out = str(tmp_path / "cli_eda")
    cmd = [sys.executable, "scripts/generate_eda_charts.py", "--output-dir", cli_out, "--quiet"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"CLI execution failed: {res.stderr}"

    png_files = [f for f in os.listdir(cli_out) if f.endswith(".png")]
    assert len(png_files) == 5


def test_generate_eda_charts_fails_loudly_when_backtest_missing_or_corrupt(tmp_path, monkeypatch):
    """
    Priority 0b Corrective Gate: Verifies that scripts/generate_eda_charts.py has zero
    silent fallback arrays or defaults, and fails loudly with FileNotFoundError if
    any seed file is missing, or KeyError if required metrics are missing.
    """
    import os
    import pytest
    from scripts.generate_eda_charts import generate_stockout_lead_time_chart

    out_dir = str(tmp_path / "fail_loud_eda")

    # 1. Missing seed file triggers FileNotFoundError
    orig_exists = os.path.exists
    def mock_exists_missing_seed(path):
        if "backtest_seed_4.json" in str(path):
            return False
        return orig_exists(path)

    monkeypatch.setattr(os.path, "exists", mock_exists_missing_seed)
    with pytest.raises(FileNotFoundError, match="Required backtest output file not found"):
        generate_stockout_lead_time_chart(data_dir="data", output_dir=out_dir)

    monkeypatch.undo()

    # 2. Missing naive_lmis_f1 key triggers KeyError
    import json
    orig_load = json.load
    def mock_load_missing_key(fp):
        data = orig_load(fp)
        if isinstance(data, dict) and "metrics" in data:
            ad = data.get("metrics", {}).get("anomaly_detection", {})
            if "naive_lmis_f1" in ad:
                del ad["naive_lmis_f1"]
        return data

    monkeypatch.setattr(json, "load", mock_load_missing_key)
    with pytest.raises(KeyError, match="Missing required metric 'naive_lmis_f1'"):
        generate_stockout_lead_time_chart(data_dir="data", output_dir=out_dir)



