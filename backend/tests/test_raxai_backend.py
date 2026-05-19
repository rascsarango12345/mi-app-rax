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

ADMIN_EMAIL = "rascsarango12345@gmail.com"
ADMIN_PASS = "Rasc2026!RaxAI"


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
        for key in ["total_users", "total_messages", "total_images", "blocked_users", "premium_users", "pro_users", "estimated_revenue_usd", "open_tickets", "today"]:
            assert key in d
        assert d["today"] == "19 de mayo de 2026"

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


# ---------- Module: theme (iteration 2) ----------
class TestTheme:
    def test_get_theme_public_no_auth(self, session):
        r = session.get(f"{API}/theme", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["primary_color", "accent_color", "success_color", "background_color", "preset"]:
            assert k in d

    def test_admin_update_theme_persists(self, session, admin_token):
        token, _ = admin_token
        new_theme = {
            "primary_color": "#FF00AA",
            "accent_color": "#00FFAA",
            "success_color": "#FFFF00",
            "background_color": "#101010",
            "preset": "test_pink",
        }
        r = session.put(
            f"{API}/admin/theme",
            json=new_theme,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        # verify persistence via public endpoint
        r2 = session.get(f"{API}/theme", timeout=30)
        assert r2.status_code == 200
        d = r2.json()
        assert d["primary_color"] == "#FF00AA"
        assert d["preset"] == "test_pink"
        # restore default
        session.put(
            f"{API}/admin/theme",
            json={
                "primary_color": "#00E5FF",
                "accent_color": "#7C4DFF",
                "success_color": "#00FF66",
                "background_color": "#050505",
                "preset": "neon_blue",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

    def test_non_admin_cannot_set_theme(self, session, new_user):
        token, _, _, _ = new_user
        r = session.put(
            f"{API}/admin/theme",
            json={"primary_color": "#000000", "accent_color": "#000000",
                  "success_color": "#000000", "background_color": "#000000", "preset": "hack"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 403


# ---------- Module: subscriptions (iteration 2) ----------
class TestSubscriptions:
    def test_admin_subscriptions_includes_revenue(self, session, admin_token, new_user):
        admin_tok, _ = admin_token
        _, target_user, _, _ = new_user
        hdr = {"Authorization": f"Bearer {admin_tok}"}
        # Upgrade target to premium to ensure at least one subscription besides admin (pro)
        target_id = target_user["user_id"]
        session.patch(f"{API}/admin/users/{target_id}/plan", json={"plan": "premium"}, headers=hdr, timeout=30)

        r = session.get(f"{API}/admin/subscriptions", headers=hdr, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["subscriptions", "total_active", "monthly_revenue_usd", "annual_projection_usd"]:
            assert k in d
        assert isinstance(d["subscriptions"], list)
        assert d["total_active"] >= 1
        # Verify pricing matches new prices ($5.99 / $15.99)
        plans_seen = {s["plan"] for s in d["subscriptions"]}
        for s in d["subscriptions"]:
            assert "_id" not in s
            assert "password_hash" not in s
            if s["plan"] == "premium":
                assert s["monthly_price_usd"] == 5.99
            if s["plan"] == "pro":
                assert s["monthly_price_usd"] == 15.99
        # annual projection = monthly * 12
        assert abs(d["annual_projection_usd"] - d["monthly_revenue_usd"] * 12) < 0.01
        # cleanup
        session.patch(f"{API}/admin/users/{target_id}/plan", json={"plan": "free"}, headers=hdr, timeout=30)

    def test_non_admin_subscriptions_forbidden(self, session, new_user):
        token, _, _, _ = new_user
        r = session.get(f"{API}/admin/subscriptions", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        assert r.status_code == 403


# ---------- Module: support tickets (iteration 2) ----------
class TestSupportTickets:
    def test_user_create_ticket_and_get(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        r = session.post(
            f"{API}/support/tickets",
            json={"subject": "TEST issue de prueba", "message": "Hola, necesito ayuda con X"},
            headers=hdr, timeout=30,
        )
        assert r.status_code == 200, r.text
        tid = r.json()["ticket_id"]
        assert r.json()["status"] == "open"

        # User can list own tickets
        rl = session.get(f"{API}/support/tickets", headers=hdr, timeout=30)
        assert rl.status_code == 200
        tickets = rl.json()
        assert any(t["ticket_id"] == tid for t in tickets)

        # Get ticket detail
        rd = session.get(f"{API}/support/tickets/{tid}", headers=hdr, timeout=30)
        assert rd.status_code == 200
        body = rd.json()
        assert body["ticket"]["ticket_id"] == tid
        assert len(body["messages"]) >= 1
        assert body["messages"][0]["sender_role"] == "user"

    def test_user_reply_keeps_status_open(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        tid = session.post(
            f"{API}/support/tickets",
            json={"subject": "TEST reply flow", "message": "msg 1"},
            headers=hdr, timeout=30,
        ).json()["ticket_id"]

        rr = session.post(
            f"{API}/support/tickets/{tid}/reply",
            json={"message": "follow-up user"},
            headers=hdr, timeout=30,
        )
        assert rr.status_code == 200
        assert rr.json()["sender_role"] == "user"
        # Status stays open
        det = session.get(f"{API}/support/tickets/{tid}", headers=hdr, timeout=30).json()
        assert det["ticket"]["status"] == "open"

    def test_admin_reply_sets_answered_and_lists_all(self, session, admin_token, new_user):
        admin_tok, _ = admin_token
        u_tok, _, _, _ = new_user
        hdr_u = {"Authorization": f"Bearer {u_tok}"}
        hdr_a = {"Authorization": f"Bearer {admin_tok}"}

        # User creates
        tid = session.post(
            f"{API}/support/tickets",
            json={"subject": "TEST admin reply", "message": "user msg"},
            headers=hdr_u, timeout=30,
        ).json()["ticket_id"]

        # Admin lists all (should include user's ticket)
        all_list = session.get(f"{API}/support/tickets", headers=hdr_a, timeout=30).json()
        assert any(t["ticket_id"] == tid for t in all_list)

        # Admin replies
        rr = session.post(
            f"{API}/support/tickets/{tid}/reply",
            json={"message": "admin response"},
            headers=hdr_a, timeout=30,
        )
        assert rr.status_code == 200
        assert rr.json()["sender_role"] == "admin"

        # Status now answered
        det = session.get(f"{API}/support/tickets/{tid}", headers=hdr_a, timeout=30).json()
        assert det["ticket"]["status"] == "answered"

        # Admin updates status to closed
        rs = session.patch(
            f"{API}/admin/support/tickets/{tid}/status",
            json={"status": "closed"},
            headers=hdr_a, timeout=30,
        )
        assert rs.status_code == 200
        assert rs.json()["status"] == "closed"
        det2 = session.get(f"{API}/support/tickets/{tid}", headers=hdr_a, timeout=30).json()
        assert det2["ticket"]["status"] == "closed"

    def test_other_user_cannot_access_ticket(self, session, new_user):
        # Create ticket as new_user
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        tid = session.post(
            f"{API}/support/tickets",
            json={"subject": "TEST private", "message": "secret"},
            headers=hdr, timeout=30,
        ).json()["ticket_id"]

        # Register another user
        email2 = f"TEST_other_{uuid.uuid4().hex[:8]}@example.com"
        reg = session.post(f"{API}/auth/register", json={"email": email2, "password": "Pass1234!"}, timeout=30).json()
        other_tok = reg["token"]
        r = session.get(
            f"{API}/support/tickets/{tid}",
            headers={"Authorization": f"Bearer {other_tok}"}, timeout=30,
        )
        assert r.status_code == 403

    def test_non_admin_patch_status_forbidden(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        tid = session.post(
            f"{API}/support/tickets",
            json={"subject": "TEST status forbidden", "message": "msg"},
            headers=hdr, timeout=30,
        ).json()["ticket_id"]
        r = session.patch(
            f"{API}/admin/support/tickets/{tid}/status",
            json={"status": "closed"},
            headers=hdr, timeout=30,
        )
        assert r.status_code == 403


# ---------- Module: admin email allowlist (iteration 2) ----------
class TestOwnerAdminAllowlist:
    def test_admin_login_returns_pro_and_name_rasc(self, session):
        r = session.post(f"{API}/auth/login", json={"email": "rascsarango12345@gmail.com", "password": "Rasc2026!RaxAI"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u["is_admin"] is True
        assert u["plan"] == "pro"
        assert u["name"] == "RASC"
        assert u["email"] == "rascsarango12345@gmail.com"

    def test_new_registered_email_is_not_admin(self, session):
        email = f"TEST_random_{uuid.uuid4().hex[:8]}@example.com"
        r = session.post(f"{API}/auth/register", json={"email": email, "password": "Pass1234!"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["is_admin"] is False


# ---------- Module: chat date awareness (iteration 2) ----------
class TestChatDate:
    def test_chat_mentions_may_19_2026(self, session, new_user):
        token, _, _, _ = new_user
        hdr = {"Authorization": f"Bearer {token}"}
        r = session.post(
            f"{API}/chat/send",
            json={"text": "¿Qué fecha es hoy? Responde solo con la fecha."},
            headers=hdr,
            timeout=90,
        )
        assert r.status_code == 200, r.text
        content = r.json()["message"]["content"].lower()
        assert ("19" in content and ("mayo" in content or "may" in content) and "2026" in content), f"Unexpected: {content}"
