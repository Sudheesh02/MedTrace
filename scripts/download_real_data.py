"""
Download real-world external datasets for MedTrace:
1. openFDA drug shortages (DC-4) via api.fda.gov
2. USAID GHSC-PSM commodity delivery dataset (DC-2) via open source mirror
3. Pharma sales daily time-series (DC-5) via open source mirror
"""

import os
import json
import urllib.request
import sys

def download_file(url, target_path, desc):
    print(f"[*] Downloading {desc} from {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MedTrace/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response, open(target_path, "wb") as out_file:
        data = response.read()
        out_file.write(data)
        print(f"[+] Saved {desc} to {target_path} ({len(data)} bytes)")

def fetch_openfda():
    target = os.path.join("data", "real", "openfda_shortages.json")
    if os.path.exists(target):
        print(f"[=] openFDA shortages already exists at {target}")
        return
    print("[*] Fetching openFDA shortages (limit=1000)...")
    url = "https://api.fda.gov/drug/shortages.json?limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MedTrace/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
            data = json.loads(raw)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[+] Saved openFDA shortages ({len(data.get('results', []))} records) to {target}")
    except Exception as e:
        print(f"[-] Failed to fetch openFDA: {e}")

def main():
    os.makedirs(os.path.join("data", "real", "raw"), exist_ok=True)
    
    # 1. openFDA
    fetch_openfda()
    
    # 2. USAID SCMS Delivery History
    usaid_target = os.path.join("data", "real", "raw", "usaid_deliveries.csv")
    if not os.path.exists(usaid_target):
        usaid_url = "https://raw.githubusercontent.com/MSadriAghdam/Supply-Chain-Prediction_Neural-Network-ML/main/SCMS_Delivery_History_Dataset.csv"
        download_file(usaid_url, usaid_target, "USAID SCMS Delivery History (DC-2)")
    else:
        print(f"[=] USAID deliveries already exists at {usaid_target}")
    
    # 3. Pharma Sales Daily
    sales_target = os.path.join("data", "real", "raw", "salesdaily.csv")
    sales_url = "https://raw.githubusercontent.com/SaibalPatraDS/Pharma-Sales-Analysis-and-Forecasting/master/salesdaily.csv"
    download_file(sales_url, sales_target, "Pharma Sales Daily (DC-5)")

if __name__ == "__main__":
    main()
