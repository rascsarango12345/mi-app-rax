"""
Backend tests for RAX AI - new features:
- Cámara Mágica (POST /api/lens/scan)
- Modo Roast (POST /api/roast)
- Diario Inteligente (POST/GET/DELETE /api/journal/*)
- Personal Shopper (POST /api/shopper/recommend)
"""
import os
import sys
import base64
import json
import requests

# Load EXPO_PUBLIC_BACKEND_URL from frontend/.env
def get_backend_url():
    env_path = "/app/frontend/.env"
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("EXPO_PUBLIC_BACKEND_URL not found")


BASE = get_backend_url().rstrip("/") + "/api"
ADMIN_EMAIL = "rascsarango12345@gmail.com"
ADMIN_PASSWORD = "Rasc2026!RaxAI"

# Generate a small but valid 256x256 JPEG (Claude vision needs >1x1)
def _make_jpeg_b64():
    from PIL import Image
    import io, base64 as b64lib
    img = Image.new('RGB', (256, 256), color=(200, 50, 50))
    for x in range(50, 200):
        for y in range(50, 200):
            img.putpixel((x, y), (50, 100, 200))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return b64lib.b64encode(buf.getvalue()).decode()

TINY_RED_JPEG_B64 = _make_jpeg_b64()


class Result:
    def __init__(self):
        self.passed = []
        self.failed = []

    def ok(self, name, msg=""):
        self.passed.append((name, msg))
        print(f"  PASS: {name} {('- ' + msg) if msg else ''}")

    def fail(self, name, msg):
        self.failed.append((name, msg))
        print(f"  FAIL: {name} - {msg}")

    def summary(self):
        print("\n" + "=" * 70)
        print(f"PASSED: {len(self.passed)} | FAILED: {len(self.failed)}")
        if self.failed:
            print("\nFailed tests:")
            for n, m in self.failed:
                print(f"  - {n}: {m}")
        print("=" * 70)


R = Result()


def section(title):
    print("\n" + "=" * 70)
    print(f"[ {title} ]")
    print("=" * 70)


def login_admin():
    section("Auth: login admin")
    try:
        # Ensure admin is seeded (idempotent)
        try:
            requests.post(f"{BASE}/admin/seed-admin", timeout=20)
        except Exception:
            pass
        r = requests.post(
            f"{BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30,
        )
        if r.status_code != 200:
            R.fail("admin login", f"HTTP {r.status_code} - {r.text[:200]}")
            sys.exit(1)
        data = r.json()
        token = data["token"]
        user = data["user"]
        if user.get("plan") != "pro":
            R.fail("admin pro plan", f"Got plan {user.get('plan')}")
        else:
            R.ok("admin login + pro plan", f"user_id={user.get('user_id')}")
        return token, user
    except Exception as e:
        R.fail("admin login", str(e))
        sys.exit(1)


def test_lens(headers):
    section("POST /api/lens/scan")
    try:
        r = requests.post(
            f"{BASE}/lens/scan",
            headers=headers,
            json={"image_base64": TINY_RED_JPEG_B64, "locale": "es"},
            timeout=120,
        )
        if r.status_code != 200:
            R.fail("lens/scan", f"HTTP {r.status_code} - {r.text[:400]}")
            return
        data = r.json()
        if "result" not in data or "used_today" not in data or "limit" not in data:
            R.fail("lens/scan shape", f"Got keys: {list(data.keys())}")
            return
        if data["limit"] != 99999:
            R.fail("lens/scan limit", f"Expected 99999 for pro plan, got {data['limit']}")
        else:
            R.ok("lens/scan", f"limit=99999, used_today={data['used_today']}, result_len={len(str(data['result']))}")
    except Exception as e:
        R.fail("lens/scan", str(e))


def test_roast(headers):
    section("POST /api/roast")
    try:
        r = requests.post(
            f"{BASE}/roast",
            headers=headers,
            json={"image_base64": TINY_RED_JPEG_B64, "intensity": "medio", "locale": "es"},
            timeout=120,
        )
        if r.status_code != 200:
            R.fail("roast", f"HTTP {r.status_code} - {r.text[:400]}")
            return
        data = r.json()
        required = {"roast", "intensity", "used_today", "limit"}
        if not required.issubset(data.keys()):
            R.fail("roast shape", f"missing {required - set(data.keys())}")
            return
        if data["intensity"] != "medio":
            R.fail("roast intensity", f"got {data['intensity']}")
        if data["limit"] != 99999:
            R.fail("roast limit", f"Expected 99999 for pro plan, got {data['limit']}")
        else:
            R.ok("roast", f"limit=99999, used_today={data['used_today']}, roast_len={len(str(data['roast']))}")
    except Exception as e:
        R.fail("roast", str(e))


def test_journal(headers):
    section("Journal: entry → history → insights → delete")
    entry_id = None
    # 1) Create entry
    try:
        r = requests.post(
            f"{BASE}/journal/entry",
            headers=headers,
            json={"content": "Hoy fue un buen día, trabajé en RAX AI y dormí bien.", "mood": "feliz", "locale": "es"},
            timeout=120,
        )
        if r.status_code != 200:
            R.fail("journal/entry POST", f"HTTP {r.status_code} - {r.text[:400]}")
            return
        data = r.json()
        if "entry_id" not in data or "ai_insight" not in data:
            R.fail("journal/entry shape", f"keys={list(data.keys())}")
            return
        entry_id = data["entry_id"]
        R.ok("journal/entry POST", f"entry_id={entry_id}, ai_insight_len={len(str(data['ai_insight']))}")
    except Exception as e:
        R.fail("journal/entry POST", str(e))
        return

    # 2) history
    try:
        r = requests.get(f"{BASE}/journal/history", headers=headers, timeout=30)
        if r.status_code != 200:
            R.fail("journal/history", f"HTTP {r.status_code} - {r.text[:400]}")
        else:
            arr = r.json()
            if not isinstance(arr, list):
                R.fail("journal/history", f"expected list, got {type(arr).__name__}")
            elif not any(e.get("entry_id") == entry_id for e in arr):
                R.fail("journal/history", f"new entry not found in history (count={len(arr)})")
            else:
                R.ok("journal/history", f"contains new entry, total={len(arr)}")
    except Exception as e:
        R.fail("journal/history", str(e))

    # 3) insights
    try:
        r = requests.get(f"{BASE}/journal/insights", headers=headers, timeout=120)
        if r.status_code != 200:
            R.fail("journal/insights", f"HTTP {r.status_code} - {r.text[:400]}")
        else:
            data = r.json()
            required = {"summary", "mood_counts", "total"}
            if not required.issubset(data.keys()):
                R.fail("journal/insights shape", f"missing {required - set(data.keys())}")
            else:
                R.ok("journal/insights", f"total={data['total']}, moods={data['mood_counts']}, summary_len={len(str(data['summary']))}")
    except Exception as e:
        R.fail("journal/insights", str(e))

    # 4) delete
    try:
        r = requests.delete(f"{BASE}/journal/entry/{entry_id}", headers=headers, timeout=30)
        if r.status_code != 200:
            R.fail("journal/entry DELETE", f"HTTP {r.status_code} - {r.text[:400]}")
        else:
            data = r.json()
            if data.get("ok") is True:
                R.ok("journal/entry DELETE", f"deleted {entry_id}")
            else:
                R.fail("journal/entry DELETE", f"response={data}")
    except Exception as e:
        R.fail("journal/entry DELETE", str(e))

    # 5) verify deleted
    try:
        r = requests.get(f"{BASE}/journal/history", headers=headers, timeout=30)
        if r.status_code == 200:
            arr = r.json()
            if any(e.get("entry_id") == entry_id for e in arr):
                R.fail("journal delete verification", "entry still present after delete")
            else:
                R.ok("journal delete verification", "entry no longer in history")
    except Exception as e:
        R.fail("journal delete verification", str(e))


def test_shopper(headers):
    section("POST /api/shopper/recommend")
    try:
        r = requests.post(
            f"{BASE}/shopper/recommend",
            headers=headers,
            json={"query": "Audífonos inalámbricos bajo $100", "budget_usd": 100, "locale": "es"},
            timeout=180,
        )
        if r.status_code != 200:
            R.fail("shopper/recommend", f"HTTP {r.status_code} - {r.text[:400]}")
            return
        data = r.json()
        required = {"recommendations", "used_today", "limit"}
        if not required.issubset(data.keys()):
            R.fail("shopper/recommend shape", f"missing {required - set(data.keys())}")
            return
        if data["limit"] != 99999:
            R.fail("shopper/recommend limit", f"Expected 99999 for pro plan, got {data['limit']}")
        else:
            R.ok("shopper/recommend", f"limit=99999, used_today={data['used_today']}, rec_len={len(str(data['recommendations']))}")
    except Exception as e:
        R.fail("shopper/recommend", str(e))


def test_auth_required():
    section("Auth required: 401/403 without token")
    endpoints = [
        ("POST", "/lens/scan", {"image_base64": TINY_RED_JPEG_B64, "locale": "es"}),
        ("POST", "/roast", {"image_base64": TINY_RED_JPEG_B64, "intensity": "medio", "locale": "es"}),
        ("POST", "/journal/entry", {"content": "abc", "mood": "neutral", "locale": "es"}),
        ("GET", "/journal/history", None),
        ("GET", "/journal/insights", None),
        ("POST", "/shopper/recommend", {"query": "tv", "locale": "es"}),
    ]
    for method, path, body in endpoints:
        try:
            if method == "POST":
                r = requests.post(f"{BASE}{path}", json=body, timeout=30)
            else:
                r = requests.get(f"{BASE}{path}", timeout=30)
            if r.status_code in (401, 403):
                R.ok(f"auth-required {method} {path}", f"got {r.status_code}")
            else:
                R.fail(f"auth-required {method} {path}", f"expected 401/403, got {r.status_code}")
        except Exception as e:
            R.fail(f"auth-required {method} {path}", str(e))


def main():
    print(f"Backend URL: {BASE}")
    test_auth_required()
    token, user = login_admin()
    headers = {"Authorization": f"Bearer {token}"}
    test_lens(headers)
    test_roast(headers)
    test_journal(headers)
    test_shopper(headers)
    R.summary()
    sys.exit(0 if not R.failed else 1)


if __name__ == "__main__":
    main()
