"""
Unified Data Store Adapter (app/adapters/data_store.py)
Reads data from Zetaris REST API if available; otherwise falls back gracefully to local CSV/JSON files.
"""

import os
import csv
import json
import uuid
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

class DataStore:
    _shared_csv_cache: Dict[str, List[Dict[str, Any]]] = {}
    _shared_pair_indexes: Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]] = {}

    def __init__(self, use_zetaris: Optional[bool] = None, sim_dir: Optional[str] = None):
        sample_mode = os.getenv("SAMPLE_MODE", "false").lower() in ("true", "1")
        if use_zetaris is None:
            if sample_mode:
                self.use_zetaris = False
            else:
                self.use_zetaris = os.getenv("USE_ZETARIS", "false").lower() in ("true", "1")
        else:
            self.use_zetaris = use_zetaris
        self.sim_dir = sim_dir or os.getenv("SIM_DIR", "data/simulated")
        self.base_url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000").rstrip("/")
        self.rest_url = os.environ.get("ZETARIS_REST_URL", "").rstrip("/")
        self.zetaris_key = os.environ.get("ZETARIS_API_KEY", "")
        self.zetaris_org = os.environ.get("ZETARIS_ORG_ID", "1")
        self.username = os.environ.get("ZETARIS_USERNAME", "admin@zetaris.com")
        self.password = os.environ.get("ZETARIS_PASSWORD", "")
        self._cached_token = None
        self._csv_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._pair_indexes: Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]] = {}
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Clear the class-level shared CSV cache and pair indexes."""
        cls._shared_csv_cache.clear()
        cls._shared_pair_indexes.clear()

    def clear_cache(self) -> None:
        """Clear all in-memory cached CSV tables and indexes for this instance and shared cache."""
        self._csv_cache.clear()
        self._pair_indexes.clear()
        DataStore.clear_shared_cache()

    @staticmethod
    def _sanitize_id(identifier: str) -> str:
        """Sanitize SQL identifiers to guard against injection in dynamic queries."""
        if not identifier:
            return ""
        import re
        if not re.match(r"^[A-Za-z0-9_-]+$", str(identifier)):
            raise ValueError(f"Invalid characters in SQL identifier: {identifier}")
        return str(identifier)

    def _get_token(self) -> Optional[str]:
        if self.zetaris_key and self.zetaris_key != "your-zetaris-api-key":
            return self.zetaris_key
        if self._cached_token:
            return self._cached_token
        if not self.password or not self.username:
            return None

        login_url = f"{self.rest_url}/auth/login" if self.rest_url else f"{self.base_url}/api/auth/login"
        try:
            res = requests.post(
                login_url,
                json={"username": self.username, "password": self.password},
                timeout=3
            )
            if res.status_code == 200:
                data = res.json()
                self._cached_token = data.get("idToken") or data.get("token")
                self.zetaris_org = str(data.get("orgId", self.zetaris_org))
                return self._cached_token
        except Exception:
            pass
        return None

    def _query_zetaris(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        if not self.use_zetaris:
            return None
        token = self._get_token()
        if not token:
            return None

        # Dual-endpoint compatibility: Participant Setup Guide (port 8888 /api/v1.0) & UI proxy (port 3000)
        primary_url = f"{self.rest_url}/sql-editor/sqls/run" if self.rest_url else f"{self.base_url}/api/proxy/sql-editor/sqls/run-query"
        fallback_url = f"{self.base_url}/sql-editor/sqls/run" if not self.rest_url else f"{self.base_url}/api/proxy/sql-editor/sqls/run-query"

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Org-ID": str(self.zetaris_org),
            "X-Request-ID": str(uuid.uuid4())
        }
        body = {
            "sql": sql,
            "limit": 5000
        }

        for url in [primary_url, fallback_url]:
            try:
                res = requests.post(url, headers=headers, json=body, timeout=5)
                if res.status_code == 200:
                    res_data = res.json()
                    raw_headers = res_data.get("headers") or res_data.get("columns") or []
                    headers_list = []
                    for h in raw_headers:
                        if isinstance(h, dict):
                            headers_list.append(h.get("name") or h.get("columnName") or str(h))
                        else:
                            headers_list.append(str(h))
                    rows = res_data.get("data") or res_data.get("rows") or []
                    if rows and isinstance(rows[0], dict):
                        return rows
                    elif rows and headers_list:
                        return [dict(zip(headers_list, row)) for row in rows]
                elif res.status_code != 404:
                    # Non-404 error (e.g. auth failure or bad request), don't retry route
                    break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                # Host is down or port closed; immediately break to allow fast offline fallback
                break
            except Exception:
                break
        return None

    def _read_csv(self, rel_path: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        full_path = os.path.normpath(os.path.join(self.base_dir, rel_path))
        if use_cache:
            if full_path in self._csv_cache:
                return self._csv_cache[full_path]
            if full_path in DataStore._shared_csv_cache:
                self._csv_cache[full_path] = DataStore._shared_csv_cache[full_path]
                return self._csv_cache[full_path]

        if not os.path.exists(full_path):
            return []
        rows = []
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(dict(r))
        if use_cache:
            self._csv_cache[full_path] = rows
            DataStore._shared_csv_cache[full_path] = rows
        return rows

    def _get_rows_by_pair(self, rel_path: str, facility_id: str, medicine_id: str) -> List[Dict[str, Any]]:
        """Fast O(1) indexed lookup of cached CSV rows for a given (facility_id, medicine_id) pair."""
        full_path = os.path.normpath(os.path.join(self.base_dir, rel_path))
        if full_path not in self._pair_indexes:
            if full_path in DataStore._shared_pair_indexes:
                self._pair_indexes[full_path] = DataStore._shared_pair_indexes[full_path]
            else:
                rows = self._read_csv(rel_path)
                idx: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
                for r in rows:
                    fid = r.get("facility_id")
                    mid = r.get("medicine_id")
                    if fid and mid:
                        idx.setdefault((fid, mid), []).append(r)
                self._pair_indexes[full_path] = idx
                DataStore._shared_pair_indexes[full_path] = idx
        return self._pair_indexes[full_path].get((facility_id, medicine_id), [])

    def get_facilities(self) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris("SELECT * FROM zetaris.lightning.facilities")
            if res:
                return res
        return self._read_csv(os.path.join(self.sim_dir, "facilities.csv"))

    def get_medicines(self) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris("SELECT * FROM zetaris.lightning.medicine_master")
            if res:
                return res
        return self._read_csv("data/real/medicine_master.csv")

    def get_medicine_unit_price(self, medicine_id: str) -> float:
        """Returns standard wholesale price per dispensing unit (USD) based on NLEM/WHO standards."""
        standard_prices = {
            "MED-001": 0.02,  # Paracetamol 500mg tab
            "MED-002": 0.04,  # Ibuprofen 400mg tab
            "MED-003": 0.05,  # Diclofenac 50mg tab
            "MED-004": 0.12,  # Amoxicillin 500mg cap
            "MED-005": 0.25,  # Azithromycin 500mg tab
            "MED-006": 0.45,  # Salbutamol 4mg tab
            "MED-007": 0.06,  # Metformin 500mg tab
            "MED-008": 0.05,  # Amlodipine 5mg tab
            "MED-009": 0.85,  # Ceftriaxone 1g vial
            "MED-010": 1.20,  # Artemether/Lumefantrine
            "MED-011": 0.90,  # Oxytocin 10 IU/ml
            "MED-012": 0.15,  # ORS sachet / Zinc
        }
        return standard_prices.get(medicine_id, 0.10)

    def get_suppliers(self) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris("SELECT * FROM zetaris.lightning.suppliers")
            if res:
                return res
        return self._read_csv(os.path.join(self.sim_dir, "suppliers.csv"))

    def get_batches(self, facility_id: Optional[str] = None, medicine_id: Optional[str] = None, as_of_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            where_clauses = []
            if facility_id:
                where_clauses.append(f"facility_id = '{facility_id}'")
            if medicine_id:
                where_clauses.append(f"medicine_id = '{medicine_id}'")
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = self._query_zetaris(f"SELECT * FROM zetaris.lightning.batches{where_sql}")
            rows = res if res is not None else (
                self._get_rows_by_pair(os.path.join(self.sim_dir, "batches.csv"), facility_id, medicine_id)
                if (facility_id and medicine_id) else self._read_csv(os.path.join(self.sim_dir, "batches.csv"))
            )
        else:
            rows = (
                self._get_rows_by_pair(os.path.join(self.sim_dir, "batches.csv"), facility_id, medicine_id)
                if (facility_id and medicine_id) else self._read_csv(os.path.join(self.sim_dir, "batches.csv"))
            )

        ref_date = as_of_date or datetime(2026, 10, 24)
        filtered = []
        for r in rows:
            if facility_id and r.get("facility_id") != facility_id:
                continue
            if medicine_id and r.get("medicine_id") != medicine_id:
                continue
            row_copy = dict(r)
            row_copy["quarantined"] = (str(r.get("quarantined", "")).lower() == "true")
            row_copy["quantity"] = float(r.get("quantity", 0))
            # Calculate days_to_expiry dynamically from expiry_date
            exp_str = r.get("expiry_date")
            if exp_str:
                try:
                    exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                    row_copy["days_to_expiry"] = (exp_dt - ref_date).days
                except Exception:
                    row_copy["days_to_expiry"] = 999
            else:
                row_copy["days_to_expiry"] = 999
            filtered.append(row_copy)
        return filtered

    def get_latest_ledger(self, facility_id: str, medicine_id: str) -> Optional[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM zetaris.lightning.ledger_daily WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' ORDER BY date DESC LIMIT 1"
            )
            if res:
                latest = dict(res[0])
                latest["ledger_stock"] = float(latest.get("ledger_stock", 0))
                return latest
        rows = self._get_rows_by_pair(os.path.join(self.sim_dir, "ledger_daily.csv"), facility_id, medicine_id)
        if rows:
            latest = dict(rows[-1])
            latest["ledger_stock"] = float(latest.get("ledger_stock", 0))
            return latest
        return None

    def get_ledger_on_date(self, facility_id: str, medicine_id: str, date_str: str) -> Optional[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM zetaris.lightning.ledger_daily WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' AND date = '{date_str}' LIMIT 1"
            )
            if res:
                res_row = dict(res[0])
                res_row["ledger_stock"] = float(res_row.get("ledger_stock", 0))
                return res_row
        rows = self._get_rows_by_pair(os.path.join(self.sim_dir, "ledger_daily.csv"), facility_id, medicine_id)
        for r in rows:
            if r.get("date") == date_str:
                res_row = dict(r)
                res_row["ledger_stock"] = float(res_row.get("ledger_stock", 0))
                return res_row
        return None

    def get_latest_physical_audit(self, facility_id: str, medicine_id: str) -> Optional[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM zetaris.lightning.physical_audit WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' ORDER BY date DESC LIMIT 1"
            )
            if res:
                latest = dict(res[0])
                latest["counted_stock"] = float(latest.get("counted_stock", 0))
                return latest
        rows = self._get_rows_by_pair(os.path.join(self.sim_dir, "physical_audit.csv"), facility_id, medicine_id)
        if rows:
            latest = dict(rows[-1])
            latest["counted_stock"] = float(latest.get("counted_stock", 0))
            return latest
        return None

    def get_recent_consumption(self, facility_id: str, medicine_id: str, days: int = 14) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM zetaris.lightning.consumption_daily WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' ORDER BY date DESC LIMIT {days}"
            )
            if res:
                res.reverse()
                for r in res:
                    r["units_issued"] = float(r.get("units_issued", 0))
                return res
        rows = self._get_rows_by_pair(os.path.join(self.sim_dir, "consumption_daily.csv"), facility_id, medicine_id)
        recent = rows[-days:] if len(rows) > days else rows
        result = []
        for r in recent:
            row_copy = dict(r)
            row_copy["units_issued"] = float(row_copy.get("units_issued", 0))
            result.append(row_copy)
        return result

    def get_purchase_orders(self, facility_id: str, medicine_id: str) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM zetaris.lightning.purchase_orders WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}'"
            )
            if res:
                return res
        rows = self._get_rows_by_pair(os.path.join(self.sim_dir, "purchase_orders.csv"), facility_id, medicine_id)
        return [dict(r) for r in rows]

    def get_deliveries(self, facility_id: Optional[str] = None, medicine_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            where_clauses = []
            if facility_id:
                where_clauses.append(f"facility_id = '{facility_id}'")
            if medicine_id:
                where_clauses.append(f"medicine_id = '{medicine_id}'")
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = self._query_zetaris(f"SELECT * FROM zetaris.lightning.deliveries{where_sql}")
            rows = res if res is not None else (
                self._get_rows_by_pair(os.path.join(self.sim_dir, "deliveries.csv"), facility_id, medicine_id)
                if (facility_id and medicine_id) else self._read_csv(os.path.join(self.sim_dir, "deliveries.csv"))
            )
        else:
            rows = (
                self._get_rows_by_pair(os.path.join(self.sim_dir, "deliveries.csv"), facility_id, medicine_id)
                if (facility_id and medicine_id) else self._read_csv(os.path.join(self.sim_dir, "deliveries.csv"))
            )

        filtered = []
        for r in rows:
            if facility_id and r.get("facility_id") != facility_id:
                continue
            if medicine_id and r.get("medicine_id") != medicine_id:
                continue
            row_copy = dict(r)
            row_copy["received_qty"] = float(row_copy.get("received_qty", 0))
            filtered.append(row_copy)
        return filtered

    def get_transfers(self, facility_id: Optional[str] = None, medicine_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            where_clauses = []
            if facility_id:
                where_clauses.append(f"(from_facility_id = '{facility_id}' OR to_facility_id = '{facility_id}')")
            if medicine_id:
                where_clauses.append(f"medicine_id = '{medicine_id}'")
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = self._query_zetaris(f"SELECT * FROM zetaris.lightning.transfers{where_sql}")
            rows = res if res is not None else self._read_csv(os.path.join(self.sim_dir, "transfers.csv"))
        else:
            rows = self._read_csv(os.path.join(self.sim_dir, "transfers.csv"))

        filtered = []
        for r in rows:
            if facility_id and (r.get("from_facility_id") != facility_id and r.get("to_facility_id") != facility_id):
                continue
            if medicine_id and r.get("medicine_id") != medicine_id:
                continue
            row_copy = dict(r)
            row_copy["quantity"] = float(row_copy.get("quantity", 0))
            filtered.append(row_copy)
        return filtered

    def get_supplier_slip_priors(self, vendor: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            where_sql = f" WHERE vendor = '{vendor}'" if vendor else ""
            res = self._query_zetaris(f"SELECT * FROM zetaris.lightning.supplier_slip{where_sql}")
            if res is not None:
                return res
        return self._read_csv("data/real/supplier_slip.csv")

    def get_openfda_shortages(self, generic_name: str) -> List[Dict[str, Any]]:
        json_path = os.path.join(self.base_dir, "data/real/openfda_shortages.json")
        if not os.path.exists(json_path):
            return []
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results = data.get("results", [])
            query = generic_name.lower().strip()
            matches = []
            for item in results:
                gname = str(item.get("generic_name", "")).lower()
                if query in gname or gname in query:
                    matches.append(item)
            return matches
        except Exception:
            return []

    def get_openfda_recalls(self, medicine_id: Optional[str] = None, generic_name: Optional[str] = None) -> List[Dict[str, Any]]:
        json_path = os.path.join(self.base_dir, "data/real/openfda_enforcement_recalls.json")
        if not os.path.exists(json_path):
            return []
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if medicine_id and "recalls_by_medicine" in data:
                return data["recalls_by_medicine"].get(medicine_id, [])
            all_records = data.get("all_records", [])
            if generic_name:
                q = generic_name.lower().strip()
                return [r for r in all_records if q in str(r.get("matched_generic", "")).lower() or q in str(r.get("product_description", "")).lower()]
            return all_records
        except Exception:
            return []

    def get_rxnorm_standard(self, medicine_id: str) -> Optional[Dict[str, Any]]:
        json_path = os.path.join(self.base_dir, "data/real/rxnorm_standards.json")
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(medicine_id)
        except Exception:
            return None

    def get_packaging_standard(self, medicine_id: str) -> Optional[Dict[str, Any]]:
        json_path = os.path.join(self.base_dir, "data/real/dailymed_packaging.json")
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(medicine_id)
        except Exception:
            return None

    def get_disease_surveillance(self, medicine_id: str) -> Optional[Dict[str, Any]]:
        json_path = os.path.join(self.base_dir, "data/real/who_disease_surveillance.json")
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(medicine_id)
        except Exception:
            return None

    def get_cross_border_shortages(self, medicine_id: Optional[str] = None, generic_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        json_path = os.path.join(self.base_dir, "data/real/cross_border_shortages.json")
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if medicine_id and medicine_id in data:
                return data[medicine_id]
            if generic_name:
                q = generic_name.lower().strip()
                for mid, item in data.items():
                    if q in item.get("generic_name", "").lower() or q in item.get("primary_search_term", "").lower():
                        return item
            return None
        except Exception:
            return None

    def get_uom_pack_multiplier(self, medicine_id: str, reported_unit: str = "strip") -> float:
        """
        Derives pack multiplier for a medicine grounded in RxNorm and DailyMed packaging standards.
        e.g., 'strip' -> 10.0, 'box' -> 100.0, 'tablet'/'capsule' -> 1.0.
        """
        pkg = self.get_packaging_standard(medicine_id)
        rx = self.get_rxnorm_standard(medicine_id)
        unit = (reported_unit or "").lower().strip()
        disp_unit = (pkg.get("dispensing_unit") if pkg else (rx.get("standard_form") if rx else "tablet")).lower().strip()

        if unit == disp_unit or unit in ["unit", "item", "each", "piece"]:
            return 1.0
        if unit in ["strip", "blister", "strip of 10"]:
            return 10.0
        if unit in ["box", "carton", "box of 100", "pack"]:
            if pkg and "standard_packaging" in pkg:
                desc = pkg["standard_packaging"].lower()
                if "10x10" in desc or "100" in desc:
                    return 100.0
            return 100.0
        if unit in ["vial_box", "box of 10 vials"]:
            return 10.0
        if unit in ["bottle", "bottle of 100"]:
            return 100.0

        return 1.0

