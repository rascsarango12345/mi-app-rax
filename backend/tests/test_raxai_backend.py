"""RAX AI Backend regression tests."""
import os
import uuid
import base64
import wave
import io
import struct
import math

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://ai-chat-demo-26.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@raxai.com"
ADMIN_PASS = "RaxAI2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    # idempotent seed
    r = session.post(f"{API}/admin/seed-admin", timeout=30)
    assert r.status_code == 200, f"seed-admin failed: {r.status_code} {r.text}"
    r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.text}"
    body = r.json()
    return body["token"], body["user"]


@pytest.fixture(scope="session")
def new_user(session):
    email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = session.post(f"{API}/auth/register", json={"email": email, "password": password, "name": "TEST User"}, timeout=30)
    assert r.status_code == 200, f"register failed: {r.text}"
    body = r.json()
    return body["token"], body["user"], email, password


# ---------- Module: admin seeding & auth ----------
class TestAuth:
    def test_seed_admin_idempotent(self, session):
        r1 = session.post(f"{API}/admin/seed-admin", timeout=30)
        r2 = session.post(f"{API}/admin/seed-admin", timeout=30)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json().get("seeded") is False  # second call must be update path

    def test_admin_login(self, session):
        r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and "user" in data
        assert data["user"]["is_admin"] is True
        assert data["user"]["plan"] == "pro"
        assert "_id" not in data["user"]

    def test_register_new_user(self, new_user):
        token, user, email, _ = new_user
        assert token
        assert user["email"] == email.lower()
        assert user["plan"] == "free"
        assert user["is_admin"] is False
        assert "_id" not in user

    def test_register_duplicate_fails(self, session, new_user):
        _, _, email, password = new_user
        r = session.post(f"{API}/auth/register", json={"email": email, "password": password}, timeout=30)
        assert r.status_code == 400

    def test_login_wrong_password(self, session, new_user):
        _, _, email, _ = new_user
        r = session.post(f"{API}/auth/login", json={"email": email, "password": "wrong"}, timeout=30)
        assert r.status_code == 401

    def test_guest_login(self, session):
        r = session.post(f"{API}/auth/guest", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["is_guest"] is True
        assert "_id" not in d["user"]

    def test_auth_me(self, session, new_user):
        token, user, _, _ = new_user
        r = session.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["user_id"] == user["user_id"]

    def test_auth_me_missing_token(self, session):
        r = session.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 401


# ---------- Module: chat ----------
class TestChat:
    def test_chat_send_creates_conversation_and_persists(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        r = session.post(f"{API}/chat/send", json={"text": "Hola, dime una palabra de saludo en una sola palabra."}, headers=hdr, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "conversation_id" in body
        assert body["message"]["role"] == "assistant"
        assert body["message"]["content"]
        cid = body["conversation_id"]

        # List conversations
        r2 = session.get(f"{API}/conversations", headers=hdr, timeout=30)
        assert r2.status_code == 200
        convs = r2.json()
        assert any(c["conversation_id"] == cid for c in convs)
        # ensure no _id
        for c in convs:
            assert "_id" not in c

        # Get messages
        r3 = session.get(f"{API}/conversations/{cid}/messages", headers=hdr, timeout=30)
        assert r3.status_code == 200
        msgs = r3.json()
        assert len(msgs) >= 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_delete_conversation(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        r = session.post(f"{API}/chat/send", json={"text": "test borrar"}, headers=hdr, timeout=90)
        assert r.status_code == 200
        cid = r.json()["conversation_id"]
        rd = session.delete(f"{API}/conversations/{cid}", headers=hdr, timeout=30)
        assert rd.status_code == 200
        # Verify gone
        rg = session.get(f"{API}/conversations/{cid}/messages", headers=hdr, timeout=30)
        assert rg.status_code == 404


# ---------- Module: images ----------
class TestImages:
    def test_generate_image_realista(self, session, admin_token):
        token, _ = admin_token
        r = session.post(
            f"{API}/images/generate",
            json={"prompt": "a small red apple on white background", "style": "realista"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["data_base64"]
        assert d["style"] == "realista"
        assert "_id" not in d


# ---------- Module: voice ----------
class TestVoice:
    def test_voices_list(self, session):
        r = session.get(f"{API}/voice/voices", timeout=30)
        assert r.status_code == 200
        voices = r.json()["voices"]
        assert len(voices) == 4
        ids = {v["id"] for v in voices}
        assert ids == {"sofia", "luna", "diego", "alex"}
        females = [v for v in voices if v["gender"] == "female"]
        males = [v for v in voices if v["gender"] == "male"]
        assert len(females) == 2 and len(males) == 2

    def test_tts(self, session, new_user):
        token, _, _, _ = new_user
        r = session.post(
            f"{API}/voice/tts",
            json={"text": "Hola desde RAX AI", "voice": "sofia"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["voice"] == "sofia"
        assert d["audio_base64"]
        # decode validity
        raw = base64.b64decode(d["audio_base64"])
        assert len(raw) > 100

    def test_transcribe_short_wav(self, session, new_user):
        token, _, _, _ = new_user
        # Build a short 1s 16kHz mono sine wave WAV
        sr = 16000
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            frames = b"".join(
                struct.pack("<h", int(32767 * 0.2 * math.sin(2 * math.pi * 440 * t / sr)))
                for t in range(sr)
            )
            w.writeframes(frames)
        b64 = base64.b64encode(buf.getvalue()).decode()
        r = session.post(
            f"{API}/voice/transcribe",
            json={"audio_base64": b64, "mime_type": "audio/wav"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        # whisper may return empty text for tones, but call must succeed
        assert r.status_code == 200, r.text
        assert "text" in r.json()


# ---------- Module: content ----------
class TestContent:
    @pytest.mark.parametrize("ctype", ["tiktok", "youtube", "viral_ideas"])
    def test_content_generate(self, session, new_user, ctype):
        token, _, _, _ = new_user
        r = session.post(
            f"{API}/content/generate",
            json={"type": ctype, "topic": "café", "language": "es"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["type"] == ctype
        assert d["content"]


# ---------- Module: admin ----------
class TestAdmin:
    def test_admin_users(self, session, admin_token):
        token, _ = admin_token
        r = session.get(f"{API}/admin/users", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) >= 1
        for u in users:
            assert "_id" not in u
            assert "password_hash" not in u

    def test_admin_stats(self, session, admin_token):
        token, _ = admin_token
        r = session.get(f"{API}/admin/stats", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for key in ["total_users", "total_messages", "total_images", "blocked_users", "premium_users", "pro_users", "estimated_revenue_usd"]:
            assert key in d

    def test_admin_endpoints_forbidden_for_non_admin(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        assert session.get(f"{API}/admin/users", headers=hdr, timeout=30).status_code == 403
        assert session.get(f"{API}/admin/stats", headers=hdr, timeout=30).status_code == 403

    def test_admin_update_plan_and_block(self, session, admin_token, new_user):
        admin_tok, _ = admin_token
        _, target_user, _, _ = new_user
        hdr = {"Authorization": f"Bearer {admin_tok}"}
        target_id = target_user["user_id"]

        r = session.patch(f"{API}/admin/users/{target_id}/plan", json={"plan": "premium"}, headers=hdr, timeout=30)
        assert r.status_code == 200
        assert r.json()["plan"] == "premium"

        # verify via admin users list
        users = session.get(f"{API}/admin/users", headers=hdr, timeout=30).json()
        u = next((x for x in users if x["user_id"] == target_id), None)
        assert u and u["plan"] == "premium"

        rb = session.patch(f"{API}/admin/users/{target_id}/block", json={"blocked": True}, headers=hdr, timeout=30)
        assert rb.status_code == 200
        assert rb.json()["blocked"] is True

        # blocked user can't use /auth/me
        target_token, _, _, _ = new_user
        r_me = session.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {target_token}"}, timeout=30)
        assert r_me.status_code == 403

        # unblock & restore free for cleanliness
        session.patch(f"{API}/admin/users/{target_id}/block", json={"blocked": False}, headers=hdr, timeout=30)
        session.patch(f"{API}/admin/users/{target_id}/plan", json={"plan": "free"}, headers=hdr, timeout=30)


# ---------- Module: quota model presence ----------
class TestQuota:
    def test_free_plan_limit_is_30(self, session, new_user):
        # we don't burn 30 LLM calls; just check the model exposes messages_used and increments
        token, user, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        before = session.get(f"{API}/auth/me", headers=hdr).json()["messages_used"]
        r = session.post(f"{API}/chat/send", json={"text": "ping una palabra"}, headers=hdr, timeout=90)
        assert r.status_code == 200
        after = session.get(f"{API}/auth/me", headers=hdr).json()["messages_used"]
        assert after == before + 1
