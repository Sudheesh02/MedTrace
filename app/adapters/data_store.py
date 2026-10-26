"""
Unified Data Store Adapter (app/adapters/data_store.py)
Reads data from Zetaris REST API if available; otherwise falls back gracefully to local CSV/JSON files.
"""

import os
import csv
import json
import uuid
import requests

from app.envutil import env_bool
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

class DataStore:
    _shared_csv_cache: Dict[str, List[Dict[str, Any]]] = {}
    _shared_pair_indexes: Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]] = {}
    _shared_openfda_cache: Dict[str, List[Dict[str, Any]]] = {}
    # Per-process Zetaris telemetry so traces can prove (or disprove) that Zetaris actually served data.
    zetaris_stats: Dict[str, Any] = {"queries_attempted": 0, "queries_ok": 0, "queries_fallback_to_csv": 0, "tables": {}}

    @classmethod
    def reset_zetaris_stats(cls) -> None:
        cls.zetaris_stats = {"queries_attempted": 0, "queries_ok": 0, "queries_fallback_to_csv": 0, "tables": {}}

    @classmethod
    def get_zetaris_stats(cls) -> Dict[str, Any]:
        s = cls.zetaris_stats
        return {
            "queries_attempted": s["queries_attempted"],
            "queries_ok": s["queries_ok"],
            "queries_fallback_to_csv": s["queries_fallback_to_csv"],
            "tables": dict(s["tables"]),
        }

    def __init__(self, use_zetaris: Optional[bool] = None, sim_dir: Optional[str] = None):
        sample_mode = env_bool("SAMPLE_MODE")
        if use_zetaris is None:
            if sample_mode:
                self.use_zetaris = False
            else:
                self.use_zetaris = env_bool("USE_ZETARIS")
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
        self._openfda_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Clear the class-level shared CSV cache and pair indexes."""
        cls._shared_csv_cache.clear()
        cls._shared_pair_indexes.clear()
        cls._shared_openfda_cache.clear()

    def clear_cache(self) -> None:
        """Clear all in-memory cached CSV tables and indexes for this instance and shared cache."""
        self._csv_cache.clear()
        self._pair_indexes.clear()
        self._openfda_cache.clear()
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

        login_urls = []
        if self.rest_url:
            login_urls.append(f"{self.rest_url}/auth/login")
        login_urls.append(f"{self.base_url}/api/auth/login")
        for login_url in login_urls:
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
                    if self._cached_token:
                        return self._cached_token
            except Exception:
                continue
        return None

    def _query_zetaris(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        """Run one Lightning SQL statement; records telemetry (ok vs. fell back to local CSV)."""
        if not self.use_zetaris:
            return None
        import re as _re
        stats = DataStore.zetaris_stats
        stats["queries_attempted"] += 1
        m = _re.search(r"FROM\s+MEDTRACE_LH\.([A-Za-z0-9_]+)", sql, _re.IGNORECASE)
        table = m.group(1) if m else "other"
        result = self._query_zetaris_raw(sql)
        if result:
            stats["queries_ok"] += 1
            stats["tables"][table] = stats["tables"].get(table, 0) + 1
        else:
            stats["queries_fallback_to_csv"] += 1
        return result

    def _query_zetaris_raw(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        if not self.use_zetaris:
            return None
        token = self._get_token()
        if not token:
            return None

        # Endpoint order. Participant-guide REST route (ZETARIS_REST_URL, e.g. :8888/api/v1.0) first when it is a
        # distinct service; otherwise the UI proxy `run-query` route (verified working on the local stack).
        # NOTE: a rest_url that merely points at the UI proxy (".../api/proxy") must NOT use the `/sqls/run` shape,
        # which expects queryId/source and returns 400.
        proxy_url = f"{self.base_url}/api/proxy/sql-editor/sqls/run-query"
        if self.rest_url and not self.rest_url.rstrip("/").endswith("/api/proxy"):
            urls = [f"{self.rest_url}/sql-editor/sqls/run", proxy_url]
        else:
            urls = [proxy_url]

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Org-ID": str(self.zetaris_org),
            "X-Request-ID": str(uuid.uuid4())
        }
        body = {
            "sql": sql,
            "limit": 5000
        }

        for url in urls:
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
                elif res.status_code not in (400, 404, 405):
                    # Auth failure / server error: do not retry another route
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
            res = self._query_zetaris("SELECT * FROM MEDTRACE_LH.facilities")
            if res:
                return res
        return self._read_csv(os.path.join(self.sim_dir, "facilities.csv"))

    def get_medicines(self) -> List[Dict[str, Any]]:
        if self.use_zetaris:
            res = self._query_zetaris("SELECT * FROM MEDTRACE_LH.medicine_master")
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
            res = self._query_zetaris("SELECT * FROM MEDTRACE_LH.suppliers")
            if res:
                return res
        return self._read_csv(os.path.join(self.sim_dir, "suppliers.csv"))

    def get_batches(self, facility_id: Optional[str] = None, medicine_id: Optional[str] = None, as_of_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if facility_id:
            self._sanitize_id(facility_id)
        if medicine_id:
            self._sanitize_id(medicine_id)
        if self.use_zetaris:
            where_clauses = []
            if facility_id:
                where_clauses.append(f"facility_id = '{facility_id}'")
            if medicine_id:
                where_clauses.append(f"medicine_id = '{medicine_id}'")
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = self._query_zetaris(f"SELECT * FROM MEDTRACE_LH.batches{where_sql}")
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
        self._sanitize_id(facility_id)
        self._sanitize_id(medicine_id)
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM MEDTRACE_LH.ledger_daily WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' ORDER BY date DESC LIMIT 1"
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
        self._sanitize_id(facility_id)
        self._sanitize_id(medicine_id)
        import re
        if date_str and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_str)):
            raise ValueError(f"Invalid date format for SQL query: {date_str}")
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM MEDTRACE_LH.ledger_daily WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' AND date = '{date_str}' LIMIT 1"
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
        self._sanitize_id(facility_id)
        self._sanitize_id(medicine_id)
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM MEDTRACE_LH.physical_audit WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' ORDER BY date DESC LIMIT 1"
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
        self._sanitize_id(facility_id)
        self._sanitize_id(medicine_id)
        if not isinstance(days, int) or days <= 0:
            raise ValueError(f"Invalid days parameter for SQL query: {days}")
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM MEDTRACE_LH.consumption_daily WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}' ORDER BY date DESC LIMIT {days}"
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
        self._sanitize_id(facility_id)
        self._sanitize_id(medicine_id)
        if self.use_zetaris:
            res = self._query_zetaris(
                f"SELECT * FROM MEDTRACE_LH.purchase_orders WHERE facility_id = '{facility_id}' AND medicine_id = '{medicine_id}'"
            )
            if res:
                return res
        rows = self._get_rows_by_pair(os.path.join(self.sim_dir, "purchase_orders.csv"), facility_id, medicine_id)
        return [dict(r) for r in rows]

    def get_deliveries(self, facility_id: Optional[str] = None, medicine_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if facility_id:
            self._sanitize_id(facility_id)
        if medicine_id:
            self._sanitize_id(medicine_id)
        if self.use_zetaris:
            where_clauses = []
            if facility_id:
                where_clauses.append(f"facility_id = '{facility_id}'")
            if medicine_id:
                where_clauses.append(f"medicine_id = '{medicine_id}'")
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = self._query_zetaris(f"SELECT * FROM MEDTRACE_LH.deliveries{where_sql}")
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
        if facility_id:
            self._sanitize_id(facility_id)
        if medicine_id:
            self._sanitize_id(medicine_id)
        if self.use_zetaris:
            where_clauses = []
            if facility_id:
                where_clauses.append(f"(from_facility_id = '{facility_id}' OR to_facility_id = '{facility_id}')")
            if medicine_id:
                where_clauses.append(f"medicine_id = '{medicine_id}'")
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = self._query_zetaris(f"SELECT * FROM MEDTRACE_LH.transfers{where_sql}")
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
        if vendor:
            if "'" in vendor or ";" in vendor or "--" in vendor:
                raise ValueError(f"Invalid characters in vendor name: {vendor}")
        if self.use_zetaris:
            where_sql = f" WHERE vendor = '{vendor}'" if vendor else ""
            res = self._query_zetaris(f"SELECT * FROM MEDTRACE_LH.supplier_slip{where_sql}")
            if res is not None:
                return res
        return self._read_csv("data/real/supplier_slip.csv")

    def fetch_live_openfda_shortages(self, medicine_name: str) -> List[Dict[str, Any]]:
        """
        Fetch real-time drug shortages from openFDA REST API with offline cache-aside.
        Issues HTTP GET to https://api.fda.gov/drug/shortages.json?search=generic_name:{medicine_name}&limit=5
        with a 5-second timeout.
        Updates in-memory cache on HTTP 200.
        Falls back cleanly to local data/real/openfda_shortages.json when offline, on network error/timeout,
        or when SAMPLE_MODE=true.
        """
        if not medicine_name:
            return []
        norm_name = str(medicine_name).strip().lower()
        cache_key = f"shortages:{norm_name}"
        if cache_key in self._openfda_cache:
            return [dict(r) for r in self._openfda_cache[cache_key]]
        if cache_key in DataStore._shared_openfda_cache:
            return [dict(r) for r in DataStore._shared_openfda_cache[cache_key]]

        sample_mode = env_bool("SAMPLE_MODE")
        if sample_mode:
            local_res = self.get_openfda_shortages(medicine_name, live=False)
            self._openfda_cache[cache_key] = local_res
            DataStore._shared_openfda_cache[cache_key] = local_res
            return local_res

        import urllib.parse
        try:
            q = urllib.parse.quote(medicine_name.strip())
            url = f"https://api.fda.gov/drug/shortages.json?search=generic_name:{q}&limit=5"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                self._openfda_cache[cache_key] = results
                DataStore._shared_openfda_cache[cache_key] = results
                return [dict(r) for r in results]
            elif resp.status_code == 404:
                self._openfda_cache[cache_key] = []
                DataStore._shared_openfda_cache[cache_key] = []
                return []
            else:
                local_res = self.get_openfda_shortages(medicine_name, live=False)
                self._openfda_cache[cache_key] = local_res
                DataStore._shared_openfda_cache[cache_key] = local_res
                return local_res
        except Exception:
            local_res = self.get_openfda_shortages(medicine_name, live=False)
            self._openfda_cache[cache_key] = local_res
            DataStore._shared_openfda_cache[cache_key] = local_res
            return local_res

    def fetch_live_openfda_recalls(self, medicine_id: Optional[str] = None, generic_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch real-time drug enforcement recalls from openFDA REST API with offline cache-aside.
        Issues HTTP GET to https://api.fda.gov/drug/enforcement.json?search=product_description:{q}&limit=5
        with a 5-second timeout.
        Updates in-memory cache on HTTP 200.
        Falls back cleanly to local data/real/openfda_enforcement_recalls.json when offline,
        on network error/timeout, or when SAMPLE_MODE=true.
        """
        norm_med = str(medicine_id or "").strip().upper()
        norm_name = str(generic_name or "").strip().lower()
        cache_key = f"recalls:{norm_med}:{norm_name}"
        if cache_key in self._openfda_cache:
            return [dict(r) for r in self._openfda_cache[cache_key]]
        if cache_key in DataStore._shared_openfda_cache:
            return [dict(r) for r in DataStore._shared_openfda_cache[cache_key]]

        sample_mode = env_bool("SAMPLE_MODE")
        if sample_mode:
            local_res = self.get_openfda_recalls(medicine_id=medicine_id, generic_name=generic_name, live=False)
            self._openfda_cache[cache_key] = local_res
            DataStore._shared_openfda_cache[cache_key] = local_res
            return local_res

        q_term = generic_name or ""
        if not q_term and medicine_id:
            try:
                meds = self.get_medicines()
                matched = next((m for m in meds if m.get("medicine_id") == medicine_id), None)
                if matched:
                    q_term = matched.get("name", "")
            except Exception:
                pass

        if not q_term:
            local_res = self.get_openfda_recalls(medicine_id=medicine_id, generic_name=generic_name, live=False)
            self._openfda_cache[cache_key] = local_res
            DataStore._shared_openfda_cache[cache_key] = local_res
            return local_res

        import urllib.parse
        try:
            q = urllib.parse.quote(q_term.strip())
            url = f"https://api.fda.gov/drug/enforcement.json?search=product_description:{q}&limit=5"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                self._openfda_cache[cache_key] = results
                DataStore._shared_openfda_cache[cache_key] = results
                return [dict(r) for r in results]
            elif resp.status_code == 404:
                self._openfda_cache[cache_key] = []
                DataStore._shared_openfda_cache[cache_key] = []
                return []
            else:
                local_res = self.get_openfda_recalls(medicine_id=medicine_id, generic_name=generic_name, live=False)
                self._openfda_cache[cache_key] = local_res
                DataStore._shared_openfda_cache[cache_key] = local_res
                return local_res
        except Exception:
            local_res = self.get_openfda_recalls(medicine_id=medicine_id, generic_name=generic_name, live=False)
            self._openfda_cache[cache_key] = local_res
            DataStore._shared_openfda_cache[cache_key] = local_res
            return local_res

    def get_openfda_shortages(self, generic_name: str, live: bool = False) -> List[Dict[str, Any]]:
        if live:
            return self.fetch_live_openfda_shortages(generic_name)
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

    def get_openfda_recalls(self, medicine_id: Optional[str] = None, generic_name: Optional[str] = None, live: bool = False) -> List[Dict[str, Any]]:
        if live:
            return self.fetch_live_openfda_recalls(medicine_id=medicine_id, generic_name=generic_name)
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

