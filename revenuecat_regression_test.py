#!/usr/bin/env python3
"""
RevenueCat new endpoints + regression test for chat/voice/legal endpoints.
Tests against public REACT_APP_BACKEND_URL (frontend/.env EXPO_PUBLIC_BACKEND_URL).
"""
import os
import sys
import time
import json
import uuid
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = "https://ai-chat-demo-26.preview.emergentagent.com"
API = f"{BASE_URL}/api"
WEBHOOK_SECRET = os.getenv("REVENUECAT_WEBHOOK_SECRET", "")

results = []

def log(name, passed, details=""):
    icon = "✅" if passed else "❌"
    line = f"{icon} {name}"
    if details:
        line += f" | {details}"
    print(line)
    results.append({"name": name, "passed": passed, "details": details})


def short(body, n=200):
    try:
        if isinstance(body, (dict, list)):
            s = json.dumps(body, ensure_ascii=False)
        else:
            s = str(body)
        return s[:n].replace("\n", " ")
    except Exception:
        return str(body)[:n]


def register_user():
    """Register a fresh user, return (token, user_id, email)."""
    email = f"test.user.{uuid.uuid4().hex[:8]}@raxtest.com"
    password = "TestPass2026!"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": password, "name": "Test User"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"register failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("token") or data.get("access_token")
    user_id = data.get("user", {}).get("user_id") or data.get("user_id")
    if not token or not user_id:
        # Try fetching /auth/me
        if token:
            me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=20)
            if me.status_code == 200:
                user_id = me.json().get("user_id") or me.json().get("user", {}).get("user_id")
        if not token or not user_id:
            raise RuntimeError(f"register response missing token/user_id: {data}")
    return token, user_id, email


def get_plan(token):
    r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code != 200:
        return None, r
    return r.json().get("plan"), r


# ============================================================
# Section 0 — preflight
# ============================================================
print("=" * 70)
print("RAX AI - RevenueCat + Regression Tests")
print("=" * 70)
print(f"BASE_URL: {BASE_URL}")
print(f"REVENUECAT_WEBHOOK_SECRET present: {bool(WEBHOOK_SECRET)} (len={len(WEBHOOK_SECRET)})")
print()

if not WEBHOOK_SECRET:
    log("PREFLIGHT - read REVENUECAT_WEBHOOK_SECRET", False, "Secret is empty")
    sys.exit(1)
else:
    log("PREFLIGHT - read REVENUECAT_WEBHOOK_SECRET", True, f"len={len(WEBHOOK_SECRET)}")


# ============================================================
# Section 1 — POST /api/revenuecat/webhook
# ============================================================
print("\n" + "=" * 70)
print("[1] POST /api/revenuecat/webhook")
print("=" * 70)

# (a) No Authorization header → 401
r = requests.post(f"{API}/revenuecat/webhook", json={"event": {"type": "TEST", "id": "t1"}}, timeout=20)
ok = r.status_code == 401 and "Invalid Authorization header" in r.text
log("1a) No Authorization → 401 + 'Invalid Authorization header'",
    ok, f"HTTP {r.status_code} body={short(r.text)}")

# (b) Wrong bearer → 401
r = requests.post(f"{API}/revenuecat/webhook",
                  headers={"Authorization": "Bearer WRONG_SECRET"},
                  json={"event": {"type": "TEST", "id": "t1"}}, timeout=20)
ok = r.status_code == 401
log("1b) Wrong bearer → 401", ok, f"HTTP {r.status_code} body={short(r.text)}")

# (c) Valid bearer + TEST event → 200 ok
r = requests.post(f"{API}/revenuecat/webhook",
                  headers={"Authorization": f"Bearer {WEBHOOK_SECRET}"},
                  json={"event": {"type": "TEST", "id": "t1"}}, timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and j.get("status") == "ok" and "Test webhook" in (j.get("note") or "")
log("1c) Valid bearer + TEST → 200 {status:ok, note:'Test webhook ...'}",
    ok, f"HTTP {r.status_code} body={short(j)}")

# Register a fresh user for (d), (e), (f)
try:
    token_d, user_id_d, email_d = register_user()
    log("Setup - register fresh user for webhook tests", True, f"user_id={user_id_d} email={email_d}")
except Exception as e:
    log("Setup - register fresh user for webhook tests", False, str(e))
    sys.exit(1)

# (d) Valid bearer + INITIAL_PURCHASE → plan=premium
payload_d = {
    "event": {
        "type": "INITIAL_PURCHASE",
        "id": "ev_x",
        "app_user_id": user_id_d,
        "product_id": "raxai_premium_monthly",
        "entitlement_ids": ["premium"],
    }
}
r = requests.post(f"{API}/revenuecat/webhook",
                  headers={"Authorization": f"Bearer {WEBHOOK_SECRET}"},
                  json=payload_d, timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and j.get("plan") == "premium"
log("1d.1) INITIAL_PURCHASE entitlement=premium → 200 plan=premium",
    ok, f"HTTP {r.status_code} body={short(j)}")

# Verify via /auth/me
plan_after, _ = get_plan(token_d)
ok = plan_after == "premium"
log("1d.2) /auth/me confirms plan=premium",
    ok, f"plan={plan_after}")

# (e) CANCELLATION for same user → plan becomes free
payload_e = {
    "event": {
        "type": "CANCELLATION",
        "id": "ev_e",
        "app_user_id": user_id_d,
        "product_id": "raxai_premium_monthly",
    }
}
r = requests.post(f"{API}/revenuecat/webhook",
                  headers={"Authorization": f"Bearer {WEBHOOK_SECRET}"},
                  json=payload_e, timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and j.get("plan") == "free"
log("1e.1) CANCELLATION → 200 plan=free",
    ok, f"HTTP {r.status_code} body={short(j)}")

plan_after, _ = get_plan(token_d)
ok = plan_after == "free"
log("1e.2) /auth/me confirms plan=free",
    ok, f"plan={plan_after}")

# (f) Product fallback: no entitlements but product_id=raxai_pro_monthly1 → plan=pro
try:
    token_f, user_id_f, email_f = register_user()
except Exception as e:
    log("Setup - register user for (f)", False, str(e))
    sys.exit(1)

payload_f = {
    "event": {
        "type": "INITIAL_PURCHASE",
        "id": "ev_f",
        "app_user_id": user_id_f,
        "product_id": "raxai_pro_monthly1",
    }
}
r = requests.post(f"{API}/revenuecat/webhook",
                  headers={"Authorization": f"Bearer {WEBHOOK_SECRET}"},
                  json=payload_f, timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and j.get("plan") == "pro"
log("1f.1) Product fallback (product_id contains 'pro') → plan=pro",
    ok, f"HTTP {r.status_code} body={short(j)}")

plan_after, _ = get_plan(token_f)
ok = plan_after == "pro"
log("1f.2) /auth/me confirms plan=pro",
    ok, f"plan={plan_after}")


# ============================================================
# Section 2 — POST /api/revenuecat/sync
# ============================================================
print("\n" + "=" * 70)
print("[2] POST /api/revenuecat/sync")
print("=" * 70)

# (a) No JWT → 401
r = requests.post(f"{API}/revenuecat/sync",
                  json={"app_user_id": "x", "plan": "premium"}, timeout=20)
ok = r.status_code == 401
log("2a) No JWT → 401", ok, f"HTTP {r.status_code} body={short(r.text)}")

# Use a fresh user for sync
try:
    token_s, user_id_s, _ = register_user()
except Exception as e:
    log("Setup - register user for sync", False, str(e))
    sys.exit(1)

# (b) JWT + mismatched app_user_id → 403
r = requests.post(f"{API}/revenuecat/sync",
                  headers={"Authorization": f"Bearer {token_s}"},
                  json={"app_user_id": "not_my_user_id_x", "plan": "premium"}, timeout=20)
ok = r.status_code == 403 and "does not match" in r.text.lower()
log("2b) Mismatched app_user_id → 403 'does not match'",
    ok, f"HTTP {r.status_code} body={short(r.text)}")

# (c) Valid JWT + matching id + plan=premium → 200
r = requests.post(f"{API}/revenuecat/sync",
                  headers={"Authorization": f"Bearer {token_s}"},
                  json={"app_user_id": user_id_s, "plan": "premium"}, timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and j.get("status") == "ok" and j.get("plan") == "premium"
log("2c.1) Valid sync → 200 {status:ok, plan:premium}",
    ok, f"HTTP {r.status_code} body={short(j)}")

plan_after, _ = get_plan(token_s)
ok = plan_after == "premium"
log("2c.2) /auth/me confirms plan=premium after sync",
    ok, f"plan={plan_after}")


# ============================================================
# Section 3 — Regression: GET /api/health
# ============================================================
print("\n" + "=" * 70)
print("[3] GET /api/health")
print("=" * 70)

r = requests.get(f"{API}/health", timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and j.get("db") == "ok"
log("3) /health → 200 db:ok", ok, f"HTTP {r.status_code} body={short(j)}")


# ============================================================
# Section 4 + 5 — Regression: POST /api/chat/send (fresh user)
# ============================================================
print("\n" + "=" * 70)
print("[4-5] POST /api/chat/send + memory regression")
print("=" * 70)

try:
    token_c, user_id_c, _ = register_user()
except Exception as e:
    log("Setup - register user for chat tests", False, str(e))
    sys.exit(1)

hdr_c = {"Authorization": f"Bearer {token_c}"}

# (4) "hola"
r = requests.post(f"{API}/chat/send",
                  headers=hdr_c,
                  json={"text": "hola"}, timeout=60)
try:
    j = r.json()
except Exception:
    j = {}
ai_text = (j.get("message") or {}).get("content") or j.get("ai_text") or ""
conv_id = j.get("conversation_id") or (j.get("message") or {}).get("conversation_id")
ok = r.status_code == 200 and len(ai_text) > 5
log("4) Chat send 'hola' → 200 with AI reply",
    ok, f"HTTP {r.status_code} ai_len={len(ai_text)} conv_id={conv_id} preview={short(ai_text, 120)}")

# (5) memory regression
# 5a. "Me llamo Pedro y tengo 30 años."
r = requests.post(f"{API}/chat/send",
                  headers=hdr_c,
                  json={"text": "Me llamo Pedro y tengo 30 años.", "conversation_id": conv_id}, timeout=60)
try:
    j = r.json()
except Exception:
    j = {}
mem_conv_id = j.get("conversation_id") or (j.get("message") or {}).get("conversation_id") or conv_id
ai_text_1 = (j.get("message") or {}).get("content") or ""
ok = r.status_code == 200 and len(ai_text_1) > 5
log("5a) Send 'Me llamo Pedro...' → 200",
    ok, f"HTTP {r.status_code} conv_id={mem_conv_id} preview={short(ai_text_1, 100)}")

# 5b. "¿Cómo me llamo?" in same conversation
r = requests.post(f"{API}/chat/send",
                  headers=hdr_c,
                  json={"text": "¿Cómo me llamo?", "conversation_id": mem_conv_id}, timeout=60)
try:
    j = r.json()
except Exception:
    j = {}
ai_text_2 = (j.get("message") or {}).get("content") or ""
mentions_pedro = "pedro" in ai_text_2.lower()
ok = r.status_code == 200 and mentions_pedro
log("5b) '¿Cómo me llamo?' → AI mentions 'Pedro'",
    ok, f"HTTP {r.status_code} mentions_pedro={mentions_pedro} preview={short(ai_text_2, 160)}")


# ============================================================
# Section 6+7 — Legal endpoints
# ============================================================
print("\n" + "=" * 70)
print("[6-7] Legal endpoints")
print("=" * 70)

r = requests.get(f"{API}/legal/privacy", timeout=20)
ok = r.status_code == 200 and "Privacy Policy" in r.text
log("6) /legal/privacy → 200 + 'Privacy Policy'",
    ok, f"HTTP {r.status_code} ctype={r.headers.get('content-type')} len={len(r.text)}")

r = requests.get(f"{API}/legal/terms", timeout=20)
ok = r.status_code == 200 and "Terms of Service" in r.text
log("7) /legal/terms → 200 + 'Terms of Service'",
    ok, f"HTTP {r.status_code} ctype={r.headers.get('content-type')} len={len(r.text)}")


# ============================================================
# Section 8 — GET /api/conversations
# ============================================================
print("\n" + "=" * 70)
print("[8] GET /api/conversations")
print("=" * 70)

r = requests.get(f"{API}/conversations",
                 headers={"Authorization": f"Bearer {token_c}"}, timeout=20)
try:
    j = r.json()
except Exception:
    j = {}
ok = r.status_code == 200 and isinstance(j, list)
log("8) /conversations → 200 list",
    ok, f"HTTP {r.status_code} type={type(j).__name__} count={len(j) if isinstance(j, list) else 'n/a'}")


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
passed = sum(1 for r in results if r["passed"])
failed = sum(1 for r in results if not r["passed"])
print(f"RESULT: {passed} PASSED, {failed} FAILED")
print("=" * 70)
if failed:
    print("\nFAILED:")
    for r in results:
        if not r["passed"]:
            print(f"  - {r['name']}: {r['details']}")
sys.exit(0 if failed == 0 else 1)
