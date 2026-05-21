"""
Memory test for /api/chat/send endpoint.
Verifies that conversation history is properly injected and recalled by the AI.
"""
import os
import sys
import requests
import json

BASE_URL = os.environ.get("BACKEND_URL", "https://ai-chat-demo-26.preview.emergentagent.com")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "rascsarango12345@gmail.com"
ADMIN_PASSWORD = "Rasc2026!RaxAI"

results = []

def log(name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, ok, detail))

def login():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    if r.status_code != 200:
        # Try register fallback
        r2 = requests.post(f"{API}/auth/register", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Admin"}, timeout=30)
        if r2.status_code != 200:
            print(f"Login failed: {r.status_code} {r.text}")
            print(f"Register failed: {r2.status_code} {r2.text}")
            sys.exit(1)
        return r2.json()["token"]
    return r.json()["token"]

def chat_send(token, text, conv_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    body = {"text": text, "user_tz": "America/Guayaquil", "locale": "es"}
    if conv_id:
        body["conversation_id"] = conv_id
    r = requests.post(f"{API}/chat/send", json=body, headers=headers, timeout=120)
    return r

def main():
    print(f"Backend: {API}\n")
    token = login()
    print(f"Got JWT (len={len(token)})\n")

    # ===== TEST 2: Memory Test =====
    print("=" * 70)
    print("TEST 2: Conversation Memory")
    print("=" * 70)

    # 2a: Send first message with personal info
    r1 = chat_send(token, "Hola, mi nombre es Carlos Sarango y tengo 25 años. Soy desarrollador.")
    if r1.status_code != 200:
        log("2a: First message", False, f"HTTP {r1.status_code}: {r1.text[:300]}")
        return
    j1 = r1.json()
    cid = j1["conversation_id"]
    ai1 = j1["message"]["content"]
    log("2a: First message sent", True, f"conv_id={cid}")
    print(f"       AI response (first): {ai1[:250]}...\n")

    # 2b: Ask the name
    r2 = chat_send(token, "¿Cómo me llamo?", conv_id=cid)
    if r2.status_code != 200:
        log("2b: Name recall", False, f"HTTP {r2.status_code}: {r2.text[:300]}")
        return
    ai2 = r2.json()["message"]["content"]
    has_carlos = "carlos" in ai2.lower()
    log("2b: AI remembers 'Carlos'", has_carlos, f"Response: {ai2[:300]}")
    print()

    # 2c: Ask the age + job
    r3 = chat_send(token, "¿Cuántos años tengo y a qué me dedico?", conv_id=cid)
    if r3.status_code != 200:
        log("2c: Age+job recall", False, f"HTTP {r3.status_code}: {r3.text[:300]}")
        return
    ai3 = r3.json()["message"]["content"]
    ai3l = ai3.lower()
    has_25 = "25" in ai3l
    has_job = ("desarrollador" in ai3l) or ("programador" in ai3l) or ("developer" in ai3l)
    log("2c: AI mentions '25'", has_25, f"")
    log("2c: AI mentions 'desarrollador' or similar", has_job, f"")
    print(f"       Response: {ai3[:400]}\n")

    # ===== TEST 3: Isolation Test =====
    print("=" * 70)
    print("TEST 3: Isolation (new conversation should NOT know name)")
    print("=" * 70)
    r4 = chat_send(token, "¿Cómo me llamo?")  # no conv_id => new conv
    if r4.status_code != 200:
        log("3: New conversation", False, f"HTTP {r4.status_code}: {r4.text[:300]}")
        return
    j4 = r4.json()
    new_cid = j4["conversation_id"]
    ai4 = j4["message"]["content"]
    isolated = "carlos" not in ai4.lower()
    log("3: Isolation - new conv does NOT know name", isolated,
        f"new_conv_id={new_cid} (different from {cid}: {new_cid != cid})")
    print(f"       Response: {ai4[:300]}\n")

    # ===== TEST 4: Regression Tests =====
    print("=" * 70)
    print("TEST 4: Regression")
    print("=" * 70)

    # Simple message
    r5 = chat_send(token, "Di solamente 'hola' por favor.")
    if r5.status_code == 200 and "message" in r5.json() and "content" in r5.json()["message"]:
        log("4a: Simple message returns 200 with proper structure", True,
            f"keys={list(r5.json().keys())}, msg_keys={list(r5.json()['message'].keys())}")
    else:
        log("4a: Simple message returns 200", False, f"HTTP {r5.status_code}: {r5.text[:300]}")

    # GET /api/conversations
    headers = {"Authorization": f"Bearer {token}"}
    r6 = requests.get(f"{API}/conversations", headers=headers, timeout=30)
    if r6.status_code == 200:
        convs = r6.json()
        # Response could be a list or dict with conversations
        if isinstance(convs, list):
            count = len(convs)
        elif isinstance(convs, dict) and "conversations" in convs:
            count = len(convs["conversations"])
        else:
            count = -1
        log("4b: GET /api/conversations returns 200", True, f"count={count}")
    else:
        log("4b: GET /api/conversations", False, f"HTTP {r6.status_code}: {r6.text[:300]}")

    # GET /api/conversations/{cid}/messages
    r7 = requests.get(f"{API}/conversations/{cid}/messages", headers=headers, timeout=30)
    if r7.status_code == 200:
        msgs_resp = r7.json()
        if isinstance(msgs_resp, list):
            msgs = msgs_resp
        elif isinstance(msgs_resp, dict) and "messages" in msgs_resp:
            msgs = msgs_resp["messages"]
        else:
            msgs = []
        roles = set(m.get("role") for m in msgs)
        has_user = "user" in roles
        has_assistant = "assistant" in roles
        ok = has_user and has_assistant
        log("4c: GET /messages includes user+assistant", ok,
            f"count={len(msgs)}, roles={roles}")
    else:
        log("4c: GET /messages", False, f"HTTP {r7.status_code}: {r7.text[:300]}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"{passed}/{total} passed")
    for name, ok, _ in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
