"""
Unified Data Store Adapter (app/adapters/data_store.py)
Reads data from Zetaris REST API if available; otherwise falls back gracefully to local CSV/JSON files.
"""

import os
import csv
import json
import uuid
import requests
from typing import Dict, List, Optional, Any

class DataStore:
    def __init__(self, use_zetaris: bool = False):
        self.use_zetaris = use_zetaris
        self.base_url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000").rstrip("/")
        self.zetaris_key = os.environ.get("ZETARIS_API_KEY", "")
        self.zetaris_org = os.environ.get("ZETARIS_ORG_ID", "1")
        self.username = os.environ.get("ZETARIS_USERNAME", "admin@zetaris.com")
        self.password = os.environ.get("ZETARIS_PASSWORD", "Zetaris1@")
        self._cached_token = None
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _get_token(self) -> Optional[str]:
        if self.zetaris_key and self.zetaris_key != "your-zetaris-api-key":
            return self.zetaris_key
        if self._cached_token:
            return self._cached_token
        try:
            res = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=10
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
        url = f"{self.base_url}/api/proxy/sql-editor/sqls/run-query"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Org-ID": str(self.zetaris_org),
            "X-Request-ID": str(uuid.uuid4())
        }
        body = {
            "sql": sql,
            "limit": 5000
        }
        try:
            res = requests.post(url, headers=headers, json=body, timeout=30)
            if res.status_code == 200:
                res_data = res.json()
                headers_list = res_data.get("headers", [])
                rows = res_data.get("data", [])
                return [dict(zip(headers_list, row)) for row in rows]
        except Exception:
            pass
        return None

    def _read_csv(self, rel_path: str) -> List[Dict[str, Any]]:
        full_path = os.path.join(self.base_dir, rel_path)
        if not os.path.exists(full_path):
            return []
        rows = []
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        return rows

    def get_facilities(self) -> List[Dict[str, Any]]:
        return self._read_csv("data/simulated/facilities.csv")

    def get_medicines(self) -> List[Dict[str, Any]]:
        return self._read_csv("data/real/medicine_master.csv")

    def get_suppliers(self) -> List[Dict[str, Any]]:
        return self._read_csv("data/simulated/suppliers.csv")

    def get_batches(self, facility_id: Optional[str] = None, medicine_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self._read_csv("data/simulated/batches.csv")
        filtered = []
        for r in rows:
            if facility_id and r.get("facility_id") != facility_id:
                continue
            if medicine_id and r.get("medicine_id") != medicine_id:
                continue
            # convert boolean
            r["quarantined"] = (str(r.get("quarantined", "")).lower() == "true")
            r["quantity"] = float(r.get("quantity", 0))
            filtered.append(r)
        return filtered

    def get_latest_ledger(self, facility_id: str, medicine_id: str) -> Optional[Dict[str, Any]]:
        rows = self._read_csv("data/simulated/ledger_daily.csv")
        matching = [r for r in rows if r.get("facility_id") == facility_id and r.get("medicine_id") == medicine_id]
        if matching:
            latest = matching[-1]
            latest["ledger_stock"] = float(latest.get("ledger_stock", 0))
            return latest
        return None

    def get_latest_physical_audit(self, facility_id: str, medicine_id: str) -> Optional[Dict[str, Any]]:
        rows = self._read_csv("data/simulated/physical_audit.csv")
        matching = [r for r in rows if r.get("facility_id") == facility_id and r.get("medicine_id") == medicine_id]
        if matching:
            latest = matching[-1]
            latest["counted_stock"] = float(latest.get("counted_stock", 0))
            return latest
        return None

    def get_recent_consumption(self, facility_id: str, medicine_id: str, days: int = 14) -> List[Dict[str, Any]]:
        rows = self._read_csv("data/simulated/consumption_daily.csv")
        matching = [r for r in rows if r.get("facility_id") == facility_id and r.get("medicine_id") == medicine_id]
        recent = matching[-days:] if len(matching) > days else matching
        for r in recent:
            r["units_issued"] = float(r.get("units_issued", 0))
        return recent

    def get_purchase_orders(self, facility_id: str, medicine_id: str) -> List[Dict[str, Any]]:
        rows = self._read_csv("data/simulated/purchase_orders.csv")
        return [r for r in rows if r.get("facility_id") == facility_id and r.get("medicine_id") == medicine_id]

    def get_supplier_slip_priors(self, vendor: Optional[str] = None) -> List[Dict[str, Any]]:
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
