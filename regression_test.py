"""
RAX AI - Full Regression Test after i18n + RevenueCat + legal-pages refactors.
Backend: http://localhost:8001 (via REACT_APP_BACKEND_URL configured for the app).
Run: python /app/regression_test.py
"""
import base64
import io
import os
import sys
import uuid
import json
import time
import requests

BASE = "https://ai-chat-demo-26.preview.emergentagent.com/api"
ADMIN_EMAIL = "rascsarango12345@gmail.com"
ADMIN_PASS = "Rasc2026!RaxAI"
RVCK_SECRET = "kcHgaiBPYYh_Cu82RE1zUqCIOnemAK-EKRf9WyVSCvo"

PASS = []
FAIL = []


def record(name, ok, http=None, excerpt=""):
    tag = "PASS" if ok else "FAIL"
    line = f"[{tag}] {name} | HTTP {http} | {excerpt[:200]}"
    print(line)
    (PASS if ok else FAIL).append(line)


def reg_new_user():
    em = f"qa.lucia.{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/auth/register", json={"email": em, "password": "Lucia2026!QA", "name": "Lucía QA"})
    r.raise_for_status()
    data = r.json()
    return data["token"], em


def admin_login():
    r = requests.post(f"{BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    r.raise_for_status()
    return r.json()["token"], r.json()["user"]


# =========== A) Health & legal ===========
def test_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("db") == "ok"
    record("A1 GET /api/health", ok, r.status_code, str(r.json()))


LEGAL_PRIVACY_KW = {
    "en": "Privacy Policy",
    "es": "Política de Privacidad",
    "hi": "गोपनीयता नीति",
    "zh": "隐私政策",
    "ru": "Политика конфиденциальности",
}
LEGAL_TERMS_KW = {
    "en": "Terms",
    "es": "Términos",
    "hi": "सेवा",
    "zh": "服务",
    "ru": "Условия",
}


def test_legal_multilang():
    for lang, kw in LEGAL_PRIVACY_KW.items():
        r = requests.get(f"{BASE}/legal/privacy", params={"lang": lang})
        body = r.text
        has_kw = kw in body
        has_picker = 'class="lang"' in body or "select class=\"lang\"" in body or "select class='lang'" in body
        ok = r.status_code == 200 and has_kw and has_picker
        record(f"A2 GET /api/legal/privacy?lang={lang} (kw='{kw}', picker={has_picker})", ok, r.status_code,
               f"len={len(body)} kw_found={has_kw}")
    for lang, kw in LEGAL_TERMS_KW.items():
        r = requests.get(f"{BASE}/legal/terms", params={"lang": lang})
        body = r.text
        has_kw = kw in body
        has_picker = 'class="lang"' in body
        ok = r.status_code == 200 and has_kw and has_picker
        record(f"A2 GET /api/legal/terms?lang={lang} (kw='{kw}', picker={has_picker})", ok, r.status_code,
               f"len={len(body)} kw_found={has_kw}")


def test_legal_default_and_invalid():
    r = requests.get(f"{BASE}/legal/privacy")
    ok = r.status_code == 200 and "Privacy Policy" in r.text
    record("A3 GET /api/legal/privacy (no lang → en)", ok, r.status_code, f"contains_en_title={'Privacy Policy' in r.text}")
    r2 = requests.get(f"{BASE}/legal/privacy", params={"lang": "invalidlang"})
    ok2 = r2.status_code == 200 and "Privacy Policy" in r2.text
    record("A4 GET /api/legal/privacy?lang=invalidlang (→ en)", ok2, r2.status_code,
           f"contains_en_title={'Privacy Policy' in r2.text}")


def test_legal_index():
    r = requests.get(f"{BASE}/legal")
    try:
        j = r.json()
    except Exception:
        j = {}
    langs = j.get("supported_languages")
    ok = r.status_code == 200 and isinstance(langs, list) and set(["en", "es", "hi", "zh", "ru"]).issubset(set(langs))
    record("A5 GET /api/legal returns supported_languages JSON", ok, r.status_code, str(j))


# =========== B) Chat + memory ===========
def test_chat_memory():
    token, _ = reg_new_user()
    H = {"Authorization": f"Bearer {token}"}

    # 6) first message: name + city in Spanish
    r1 = requests.post(f"{BASE}/chat/send", json={"text": "Mi nombre es Lucía y vivo en Madrid"}, headers=H)
    ok1 = r1.status_code == 200
    cid = None
    a1 = ""
    if ok1:
        j = r1.json()
        cid = j.get("conversation_id")
        a1 = (j.get("message") or {}).get("content", "")
    record("B6 POST /api/chat/send (introducing Lucía, Madrid)", ok1 and bool(cid), r1.status_code,
           f"conv={cid} reply_len={len(a1)}")
    if not cid:
        return

    # 7) recall in same conversation
    r2 = requests.post(f"{BASE}/chat/send",
                       json={"text": "¿Cómo me llamo y dónde vivo?", "conversation_id": cid},
                       headers=H)
    a2 = (r2.json().get("message") or {}).get("content", "") if r2.status_code == 200 else ""
    has_lucia = "Lucía" in a2 or "Lucia" in a2
    has_madrid = "Madrid" in a2
    ok2 = r2.status_code == 200 and has_lucia and has_madrid
    record("B7 same conv: recall name + city", ok2, r2.status_code,
           f"has_Lucía={has_lucia} has_Madrid={has_madrid} reply={a2[:150]!r}")

    # 8) ask in English with locale=en
    r3 = requests.post(f"{BASE}/chat/send",
                       json={"text": "What's my name?", "conversation_id": cid, "locale": "en"},
                       headers=H)
    a3 = (r3.json().get("message") or {}).get("content", "") if r3.status_code == 200 else ""
    has_lucia2 = "Lucía" in a3 or "Lucia" in a3
    # crude English heuristic: contains an English word like "your" or "name"
    english_words = ["your", "name", "you", "the", "is"]
    looks_en = sum(1 for w in english_words if w.lower() in a3.lower()) >= 2
    ok3 = r3.status_code == 200 and has_lucia2 and looks_en
    record("B8 locale=en switch: English reply mentions Lucía", ok3, r3.status_code,
           f"has_Lucía={has_lucia2} looks_english={looks_en} reply={a3[:200]!r}")


# =========== C) RevenueCat endpoints ===========
def test_revenuecat_webhook_valid():
    payload = {"event": {"type": "TEST", "id": f"test_{uuid.uuid4().hex[:8]}"}}
    H = {"Authorization": f"Bearer {RVCK_SECRET}"}
    r = requests.post(f"{BASE}/revenuecat/webhook", json=payload, headers=H)
    ok = r.status_code == 200
    record("C9 POST /api/revenuecat/webhook (TEST + valid bearer)", ok, r.status_code, r.text[:200])


def test_revenuecat_webhook_no_auth():
    payload = {"event": {"type": "TEST", "id": "t1"}}
    r = requests.post(f"{BASE}/revenuecat/webhook", json=payload)
    ok = r.status_code == 401
    record("C10 POST /api/revenuecat/webhook (no auth → 401)", ok, r.status_code, r.text[:200])


def test_revenuecat_sync_no_jwt():
    r = requests.post(f"{BASE}/revenuecat/sync", json={"app_user_id": "xxx", "plan": "premium"})
    ok = r.status_code == 401
    record("C11 POST /api/revenuecat/sync (no JWT → 401)", ok, r.status_code, r.text[:200])


def test_revenuecat_sync_mismatch():
    token, _ = reg_new_user()
    H = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE}/revenuecat/sync",
                     json={"app_user_id": "some_other_user_id", "plan": "premium"},
                     headers=H)
    ok = r.status_code == 403
    record("C12 POST /api/revenuecat/sync (mismatched app_user_id → 403)", ok, r.status_code, r.text[:200])


# =========== D) Stripe ===========
def test_stripe_checkout():
    token, _ = admin_login()
    H = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE}/stripe/create-checkout-session",
                     json={"plan": "premium", "origin_url": "https://example.com"},
                     headers=H)
    j = {}
    try:
        j = r.json()
    except Exception:
        pass
    ok = r.status_code == 200 and isinstance(j.get("checkout_url"), str) and j["checkout_url"].startswith("https://")
    record("D13 POST /api/stripe/create-checkout-session", ok, r.status_code,
           f"checkout_url={(j.get('checkout_url') or '')[:80]}")


# =========== E) Voice converse normalization ===========
def test_voice_converse_text_input():
    token, _ = admin_login()
    H = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE}/voice/converse",
                     json={"text_input": "Hola", "voice": "jennifer"},
                     headers=H, timeout=120)
    j = {}
    try:
        j = r.json()
    except Exception:
        pass
    ai_text = j.get("ai_text", "")
    audio_b64 = j.get("audio_base64", "")
    ok = r.status_code == 200 and bool(ai_text) and len(audio_b64) > 1000
    record("E14 POST /api/voice/converse text_input='Hola'", ok, r.status_code,
           f"ai_text_len={len(ai_text)} audio_b64_len={len(audio_b64)}")


# =========== F) Image generation ===========
def test_image_generate():
    token, _ = admin_login()
    H = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE}/images/generate",
                     json={"prompt": "A red apple on a white plate", "style": "realista"},
                     headers=H, timeout=180)
    j = {}
    try:
        j = r.json()
    except Exception:
        pass
    img_b64 = j.get("image_base64") or j.get("data_base64") or j.get("b64") or j.get("image") or ""
    ok = r.status_code == 200 and len(img_b64) > 500
    record("F15 POST /api/images/generate", ok, r.status_code,
           f"image_b64_len={len(img_b64)} keys={list(j.keys())}")


def main():
    print(f"Target: {BASE}\n")
    # A
    test_health()
    test_legal_multilang()
    test_legal_default_and_invalid()
    test_legal_index()
    # B
    test_chat_memory()
    # C
    test_revenuecat_webhook_valid()
    test_revenuecat_webhook_no_auth()
    test_revenuecat_sync_no_jwt()
    test_revenuecat_sync_mismatch()
    # D
    test_stripe_checkout()
    # E
    test_voice_converse_text_input()
    # F
    test_image_generate()

    print("\n========== SUMMARY ==========")
    print(f"PASS: {len(PASS)}")
    print(f"FAIL: {len(FAIL)}")
    if FAIL:
        print("\nFAILED CASES:")
        for f in FAIL:
            print("  " + f)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
