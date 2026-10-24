"""
MedTrace Gate G1 Smoke Test (smoke_test.py)
Validates Data Layer (Zetaris) and Power Layer (Meterless Nightshift / NVIDIA Nemotron).
"""

import os
import uuid
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
results = []

def check(name, fn):
    try:
        fn()
        results.append(("PASS", name, ""))
    except Exception as error:
        results.append(("FAIL", name, str(error)[:150]))

def need(*names):
    for name in names:
        assert os.environ.get(name), f"{name} is missing from .env"

def zetaris_sql():
    base_url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000").rstrip("/")
    token = os.environ.get("ZETARIS_API_KEY")
    org_id = os.environ.get("ZETARIS_ORG_ID", "1")
    
    if not token or token == "your-zetaris-api-key":
        username = os.environ.get("ZETARIS_USERNAME", "admin@zetaris.com")
        password = os.environ.get("ZETARIS_PASSWORD", "<REDACTED>")
        login_res = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        login_res.raise_for_status()
        login_data = login_res.json()
        token = login_data.get("idToken") or login_data.get("token")
        org_id = str(login_data.get("orgId", org_id))
        assert token, "Failed to retrieve access token from login"

    # Query using Zetaris UI proxy endpoint
    url = f"{base_url}/api/proxy/sql-editor/sqls/run-query"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Org-ID": str(org_id),
            "X-Request-ID": str(uuid.uuid4()),
        },
        json={
            "sql": "SELECT 1 AS num",
            "limit": 1
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json().get("data")
    assert data and str(data[0][0]) == "1", f"Unexpected response: {response.text[:80]}"

def power_model():
    need("MODEL_BASE_URL", "MODEL_API_KEY", "NEMOTRON_MODEL")
    client = OpenAI(
        base_url=os.environ["MODEL_BASE_URL"],
        api_key=os.environ["MODEL_API_KEY"]
    )
    reply = client.chat.completions.create(
        model=os.environ["NEMOTRON_MODEL"],
        messages=[{"role": "user", "content": "Reply with single word: ready"}],
        max_tokens=300
    )
    assert reply.choices, "No reply from model"
    msg = reply.choices[0].message
    content = msg.content or msg.reasoning_content or ""
    assert content, "Empty response from model"

def main():
    print("="*60)
    print("RUNNING MEDTRACE PRE-FLIGHT SMOKE TEST (GATE G1)")
    print("="*60)
    
    check("Power: NVIDIA Nemotron responds", power_model)
    check("Data: Zetaris REST SQL API responds", zetaris_sql)

    all_passed = True
    for status, name, detail in results:
        indicator = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{indicator} - {name} {f'({detail})' if detail else ''}")
        if status == "FAIL":
            all_passed = False

    print("="*60)
    if all_passed:
        print("[SUCCESS] Gate G1 verified! Both Data and Power layers are operational.")
    else:
        print("[NOTE] If Zetaris is not running yet, that is expected until Phase B completes.")

if __name__ == "__main__":
    main()
