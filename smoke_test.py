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
    rest_url = os.environ.get("ZETARIS_REST_URL", "").rstrip("/")
    base_url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000").rstrip("/")
    token = os.environ.get("ZETARIS_API_KEY")
    org_id = os.environ.get("ZETARIS_ORG_ID", "1")
    
    if not token or token == "your-zetaris-api-key":
        username = os.environ.get("ZETARIS_USERNAME", "admin@zetaris.com")
        password = os.environ.get("ZETARIS_PASSWORD")
        if not password or password in ("YourPassword", "your-password-here"):
            raise ValueError("ZETARIS_PASSWORD is not set in .env. Configure valid Zetaris credentials to verify live SQL endpoint.")
        login_urls = []
        if rest_url:
            login_urls.append(f"{rest_url}/auth/login")
            login_urls.append(f"{rest_url.replace('/api/v1.0', '')}/api/auth/login")
        login_urls.append(f"{base_url}/api/auth/login")

        token = None
        for l_url in login_urls:
            try:
                login_res = requests.post(
                    l_url,
                    json={"username": username, "password": password},
                    timeout=10
                )
                if login_res.status_code == 200:
                    login_data = login_res.json()
                    token = login_data.get("idToken") or login_data.get("token")
                    org_id = str(login_data.get("orgId", org_id))
                    if token:
                        break
            except Exception:
                continue
        assert token, "Failed to retrieve access token from Zetaris login"

    # Query using candidate endpoints (Participant Setup Guide port 8888 or UI proxy port 3000)
    candidate_urls = []
    if rest_url:
        candidate_urls.append(f"{rest_url}/sql-editor/sqls/run")
        candidate_urls.append(f"{rest_url}/sql-editor/sqls/run-query")
    candidate_urls.append(f"{base_url}/api/proxy/sql-editor/sqls/run-query")
    candidate_urls.append(f"{base_url}/sql-editor/sqls/run")

    last_error = None
    for url in candidate_urls:
        try:
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
            if response.status_code == 200:
                data = response.json().get("data")
                assert data and str(data[0][0]) == "1", f"Unexpected response: {response.text[:80]}"
                return
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:100]}"
        except Exception as e:
            last_error = str(e)
            continue
    raise RuntimeError(f"All Zetaris SQL candidate endpoints failed. Last error: {last_error}")

def power_model():
    meterless_token = os.environ.get("METERLESS_RUNTIME_TOKEN")
    if meterless_token and meterless_token not in ("your-meterless-token", "your-token-here", ""):
        base_url = os.environ.get("METERLESS_BASE_URL", "http://127.0.0.1:8088/v1")
        model = os.environ.get("METERLESS_MODEL") or os.environ.get("NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
        client = OpenAI(
            base_url=base_url,
            api_key=meterless_token,
            default_headers={"meterless-app": "medtrace", "meterless-scope": "user"}
        )
        provider_name = f"Meterless Nightshift ({model})"
    else:
        need("MODEL_BASE_URL", "MODEL_API_KEY", "NEMOTRON_MODEL")
        if os.environ.get("MODEL_API_KEY") in ("your-nvapi-key", "your-api-key-here", ""):
            raise ValueError("MODEL_API_KEY is not configured with an active key in .env.")
        client = OpenAI(
            base_url=os.environ["MODEL_BASE_URL"],
            api_key=os.environ["MODEL_API_KEY"]
        )
        model = os.environ["NEMOTRON_MODEL"]
        provider_name = f"NVIDIA Nemotron ({model})"

    reply = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with single word: ready"}],
        max_tokens=300
    )
    assert reply.choices, "No reply from model"
    msg = reply.choices[0].message
    content = msg.content or msg.reasoning_content or ""
    assert content, f"Empty response from model via {provider_name}"

def main():
    print("="*60)
    print("RUNNING MEDTRACE PRE-FLIGHT SMOKE TEST (GATE G1)")
    print("="*60)
    
    check("Power: LLM Provider responds (Meterless Nightshift / NVIDIA)", power_model)
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
