"""
Backend tests for RAX AI - CRITICAL bug fix verification:
POST /api/chat/send with image_base64

Fixes verified:
1. today_date / used_photos NameError when uploading images
2. check_chat_photo_quota now actually called
3. Empty text + image only doesn't crash on title gen
4. data: URL prefix stripping
5. Empty/corrupt image base64 -> 400
6. Conversation persistence (has_image flag)
7. chat_photos_today increments
"""
import os
import sys
import base64
import io
import json
import requests
from PIL import Image


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


def make_jpeg_b64(color1=(200, 50, 50), color2=(50, 100, 200)):
    """Create a valid 256x256 RGB JPEG so Claude vision accepts it."""
    img = Image.new('RGB', (256, 256), color=color1)
    for x in range(50, 200):
        for y in range(50, 200):
            img.putpixel((x, y), color2)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return base64.b64encode(buf.getvalue()).decode()


class Result:
    def __init__(self):
        self.passed = []
        self.failed = []

    def ok(self, name, msg=""):
        self.passed.append((name, msg))
        print(f"  PASS: {name}" + (f" - {msg}" if msg else ""))

    def fail(self, name, msg):
        self.failed.append((name, msg))
        print(f"  FAIL: {name} - {msg}")

    def summary(self):
        print("\n" + "=" * 70)
        print(f"PASSED: {len(self.passed)} | FAILED: {len(self.failed)}")
        if self.failed:
            print("\nFAILED tests:")
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
        R.ok("admin login", f"user_id={user.get('user_id')}, plan={user.get('plan')}")
        return token, user
    except Exception as e:
        R.fail("admin login", str(e))
        sys.exit(1)


def get_me(token):
    r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def test_image_only_chat(token):
    section("Test 1: image-only chat (no text)")
    img = make_jpeg_b64()
    r = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "image_base64": img,
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=90,
    )
    if r.status_code != 200:
        R.fail("image-only chat", f"HTTP {r.status_code} - {r.text[:400]}")
        return None
    data = r.json()
    cid = data.get("conversation_id")
    content = data.get("message", {}).get("content", "")
    if not cid:
        R.fail("image-only chat", "No conversation_id in response")
        return None
    if not content or len(content) < 10:
        R.fail("image-only chat", f"AI response too short: {content[:100]!r}")
        return None
    R.ok("image-only chat", f"cid={cid}, AI response len={len(content)}")
    return cid


def test_text_plus_image(token, cid=None):
    section("Test 2: text + image chat")
    img = make_jpeg_b64(color1=(20, 180, 60), color2=(255, 255, 100))
    body = {
        "text": "¿Qué ves en esta imagen?",
        "image_base64": img,
        "user_tz": "America/Bogota",
        "locale": "es",
    }
    if cid:
        body["conversation_id"] = cid
    r = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=90,
    )
    if r.status_code != 200:
        R.fail("text+image chat", f"HTTP {r.status_code} - {r.text[:400]}")
        return None
    data = r.json()
    content = data.get("message", {}).get("content", "")
    if len(content) < 10:
        R.fail("text+image chat", f"AI response too short: {content[:100]!r}")
        return None
    R.ok("text+image chat", f"AI response len={len(content)}")
    return data.get("conversation_id")


def test_data_url_prefix(token):
    section("Test 3: data: URL prefix handling")
    img = make_jpeg_b64(color1=(80, 80, 200))
    prefixed = "data:image/jpeg;base64," + img
    r = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "image_base64": prefixed,
            "text": "Describe la imagen brevemente",
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=90,
    )
    if r.status_code != 200:
        R.fail("data: URL prefix", f"HTTP {r.status_code} - {r.text[:400]}")
        return
    R.ok("data: URL prefix", "200 OK, prefix stripped correctly")


def test_conversation_persistence(token):
    section("Test 5: conversation persistence (has_image flag on saved msgs)")
    # First message creates conversation
    img1 = make_jpeg_b64(color1=(120, 30, 30))
    r1 = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Foto 1",
            "image_base64": img1,
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=90,
    )
    if r1.status_code != 200:
        R.fail("persistence msg1", f"HTTP {r1.status_code} - {r1.text[:300]}")
        return
    cid = r1.json()["conversation_id"]

    img2 = make_jpeg_b64(color1=(30, 120, 30))
    r2 = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "conversation_id": cid,
            "text": "Foto 2",
            "image_base64": img2,
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=90,
    )
    if r2.status_code != 200:
        R.fail("persistence msg2", f"HTTP {r2.status_code} - {r2.text[:300]}")
        return

    # Fetch messages
    r3 = requests.get(
        f"{BASE}/conversations/{cid}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r3.status_code != 200:
        R.fail("persistence fetch", f"HTTP {r3.status_code}")
        return
    msgs = r3.json()
    user_msgs = [m for m in msgs if m["role"] == "user"]
    img_msgs = [m for m in user_msgs if m.get("has_image")]
    if len(img_msgs) < 2:
        R.fail("persistence has_image",
               f"Expected >=2 user messages with has_image=true, got {len(img_msgs)} (total user msgs={len(user_msgs)})")
        return
    R.ok("conversation persistence", f"{len(img_msgs)} user messages saved with has_image=true in conv {cid}")


def test_no_text_no_image(token):
    section("Test 6: no text + no image -> 400")
    r = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=30,
    )
    if r.status_code != 400:
        R.fail("no text/image -> 400", f"Expected 400, got {r.status_code} - {r.text[:200]}")
        return
    if "texto" not in r.text.lower() and "imagen" not in r.text.lower():
        R.fail("no text/image msg", f"Unexpected error body: {r.text[:200]}")
        return
    R.ok("no text + no image -> 400", r.json().get("detail", ""))


def test_corrupt_empty_image(token):
    section("Test 7: corrupt / empty image -> 400")
    # Case A: image_base64 = "" - but this is treated as has_image=False, so should be 400 "Envía texto o imagen"
    # Actually bool("") is False, so has_image=False. Let's send with text="" too.
    rA = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "image_base64": "",
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=30,
    )
    # Empty string is falsy -> has_image=False, no text -> "Envía un texto o una imagen"
    if rA.status_code != 400:
        R.fail("empty string image -> 400", f"Got {rA.status_code} - {rA.text[:200]}")
    else:
        R.ok("empty string image -> 400", rA.json().get("detail", ""))

    # Case B: ",,," -> has_image=True (truthy string), but after strip("data:..." split) becomes "" -> "Imagen vacía o corrupta"
    rB = requests.post(
        f"{BASE}/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "image_base64": ",,,",
            "text": "test",
            "user_tz": "America/Bogota",
            "locale": "es",
        },
        timeout=30,
    )
    if rB.status_code != 400:
        R.fail("corrupt ',,,' image -> 400", f"Got {rB.status_code} - {rB.text[:200]}")
    else:
        detail = rB.json().get("detail", "")
        if "vací" in detail.lower() or "corrupt" in detail.lower() or "imagen" in detail.lower():
            R.ok("corrupt ',,,' image -> 400", detail)
        else:
            R.ok("corrupt ',,,' image -> 400 (with different msg)", detail)


def test_quota_tracking(token, before_count):
    section("Test 8: verify chat_photos_today increments after images")
    me = get_me(token)
    after_count = me.get("chat_photos_today", 0)
    delta = after_count - before_count
    # We sent: image-only (1) + text+image (1) + data url (1) + persistence (2) + maybe corrupt tries (0) = ~5
    # The exact number depends on what passed, but it should be > 0.
    if delta <= 0:
        R.fail("chat_photos_today increment",
               f"Before: {before_count}, After: {after_count}, Δ={delta}. Quota not bumped — bug NOT fixed.")
        return
    R.ok("chat_photos_today incremented",
         f"Before: {before_count}, After: {after_count}, Δ={delta}")


def main():
    print("=" * 70)
    print("RAX AI - chat/send image upload bug fix verification")
    print(f"Backend: {BASE}")
    print("=" * 70)

    token, user = login_admin()
    me_before = get_me(token)
    before_count = me_before.get("chat_photos_today", 0)
    print(f"  chat_photos_today before tests: {before_count}")

    cid = test_image_only_chat(token)
    test_text_plus_image(token, cid=cid)
    test_data_url_prefix(token)
    test_conversation_persistence(token)
    test_no_text_no_image(token)
    test_corrupt_empty_image(token)
    test_quota_tracking(token, before_count)

    R.summary()
    sys.exit(0 if not R.failed else 1)


if __name__ == "__main__":
    main()
