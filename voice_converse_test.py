"""
Test the FIXED /api/voice/converse endpoint.

Strategy:
  - Login as admin (rascsarango12345@gmail.com)
  - Generate a real MP3 (valid audio) via /api/voice/tts
  - Round-trip the MP3 into /api/voice/converse using various mime_type values
  - Test invalid inputs
  - Test text_input fallback
"""
import os
import sys
import json
import base64
import requests

BACKEND = "https://ai-chat-demo-26.preview.emergentagent.com/api"
EMAIL = "rascsarango12345@gmail.com"
PASSWORD = "Rasc2026!RaxAI"

results = []  # list of (name, passed, details)


def record(name, passed, details=""):
    results.append((name, passed, details))
    icon = "✅" if passed else "❌"
    print(f"{icon} {name}")
    if details:
        print(f"   {details}")


def login():
    r = requests.post(f"{BACKEND}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        print(f"LOGIN FAILED: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json()["token"]
    print(f"✓ Logged in as admin. plan={r.json().get('user',{}).get('plan')}")
    return token


def gen_audio_mp3(token, text="Hola, ¿cómo estás? Quiero saber qué tiempo hace hoy en Madrid."):
    """Use /api/voice/tts to get a real MP3 base64."""
    r = requests.post(
        f"{BACKEND}/voice/tts",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": text, "voice": "sofia"},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"TTS FAILED: {r.status_code} {r.text}")
        sys.exit(1)
    audio_b64 = r.json()["audio_base64"]
    raw = base64.b64decode(audio_b64)
    print(f"✓ Got TTS MP3: {len(raw)} bytes, b64 len={len(audio_b64)}")
    return audio_b64


def converse(token, payload):
    return requests.post(
        f"{BACKEND}/voice/converse",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=120,
    )


def main():
    token = login()
    audio_b64 = gen_audio_mp3(token)

    base_payload = {
        "audio_base64": audio_b64,
        "voice": "thalia",
        "history": [],
        "locale": "es",
        "user_tz": "America/New_York",
    }

    # ---------------------------------------------------------------
    # Test 1: Happy path - supported mime type "audio/m4a"
    # The audio is actually MP3 → first try m4a will fail at Whisper,
    # the retry loop should try m4a then... wait. m4a is the first try,
    # if that fails, retry with m4a (skip), then webm (fail), then mp4 (m4a-compatible? mp3?),
    # then wav. MP3 sent as m4a might actually work in some cases but unlikely.
    # Let's test with the actual correct mime first: "audio/mp3"
    # ---------------------------------------------------------------
    print("\n" + "="*60)
    print("TEST 1: Happy path with audio/mp3 (matches actual format)")
    print("="*60)
    p = {**base_payload, "mime_type": "audio/mp3"}
    r = converse(token, p)
    ok = r.status_code == 200
    body = {}
    try:
        body = r.json()
    except Exception:
        pass
    if ok:
        user_text = body.get("user_text", "")
        ai_text = body.get("ai_text", "")
        audio_out = body.get("audio_base64", "")
        details = (
            f"status=200, user_text='{user_text[:80]}' ai_text len={len(ai_text)} audio_b64 len={len(audio_out)}"
        )
        ok = bool(user_text) and bool(ai_text)
    else:
        details = f"status={r.status_code} body={r.text[:300]}"
    record("Test 1: happy path audio/mp3", ok, details)

    # ---------------------------------------------------------------
    # Test 2: Mime type normalization tests - retry loop should make these all work
    # The audio is MP3, but mime_type is wrong. Since MP3 base64 is supplied:
    #   - "audio/x-m4a" → ext=m4a (after x- strip). m4a fails → retry m4a skip → webm fail → mp4 fail → wav fail
    #   - Wait, this means ALL these tests need to succeed. The retry loop ends with [ext, m4a, webm, mp4, wav].
    #     "mp3" is not in that list. Looking at code again:
    #         for candidate in [ext, "m4a", "webm", "mp4", "wav"]
    #     So if the audio is MP3, none of m4a/webm/mp4/wav technically match. BUT — OpenAI Whisper
    #     might still accept MP3 bytes regardless of the filename extension. Actually Whisper sniffs
    #     the bytes; the extension is used for content-type detection in some clients. Let's see.
    # ---------------------------------------------------------------
    print("\n" + "="*60)
    print("TEST 2: Mime type normalization (5 variants)")
    print("="*60)
    variants = [
        ("audio/x-m4a", "should map to m4a"),
        ("audio/aac", "should map to m4a"),
        ("audio/3gpp", "should map to mp4"),
        ("audio/opus", "should map to ogg"),
        ("", "empty should default to m4a"),
        ("audio/unknown-format", "should fall back via retry loop"),
    ]
    for mt, note in variants:
        p = {**base_payload, "mime_type": mt}
        r = converse(token, p)
        ok = r.status_code == 200
        try:
            body = r.json()
        except Exception:
            body = {}
        if ok:
            details = f"mime='{mt}' → 200, user_text='{body.get('user_text','')[:60]}'"
            ok = bool(body.get("user_text"))
        else:
            details = f"mime='{mt}' → status={r.status_code} body={r.text[:200]}"
        record(f"Test 2: mime_type='{mt}' ({note})", ok, details)

    # ---------------------------------------------------------------
    # Test 3a: empty audio_base64 + no text_input → 400
    # ---------------------------------------------------------------
    print("\n" + "="*60)
    print("TEST 3a: Empty audio + no text_input → 400")
    print("="*60)
    r = converse(token, {"voice": "thalia", "history": [], "locale": "es", "user_tz": "America/New_York"})
    code = r.status_code
    details = f"status={code} body={r.text[:200]}"
    record("Test 3a: empty input → 400", code == 400, details)

    # ---------------------------------------------------------------
    # Test 3b: audio_base64 < 200 bytes after decode → 400 "Audio vacío"
    # ---------------------------------------------------------------
    print("\n" + "="*60)
    print("TEST 3b: Tiny audio (<200 bytes) → 400 with 'Audio vacío'")
    print("="*60)
    tiny_b64 = base64.b64encode(b"x" * 50).decode()
    r = converse(token, {**base_payload, "audio_base64": tiny_b64, "mime_type": "audio/m4a"})
    code = r.status_code
    body_text = r.text
    details = f"status={code} body={body_text[:200]}"
    record("Test 3b: tiny audio → 400 'Audio vacío'", code == 400 and "vac" in body_text.lower(), details)

    # ---------------------------------------------------------------
    # Test 4: text_input fallback
    # ---------------------------------------------------------------
    print("\n" + "="*60)
    print("TEST 4: text_input fallback (no audio)")
    print("="*60)
    p = {
        "text_input": "Hola, ¿cómo estás?",
        "voice": "jennifer",
        "history": [],
        "locale": "es",
        "user_tz": "America/New_York",
    }
    r = converse(token, p)
    ok = r.status_code == 200
    try:
        body = r.json()
    except Exception:
        body = {}
    if ok:
        ai_text = body.get("ai_text", "")
        audio_out = body.get("audio_base64", "")
        details = f"status=200, ai_text len={len(ai_text)} audio_b64 len={len(audio_out)}"
        ok = bool(ai_text) and bool(audio_out)
    else:
        details = f"status={r.status_code} body={r.text[:300]}"
    record("Test 4: text_input fallback", ok, details)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    for name, p, _ in results:
        icon = "✅" if p else "❌"
        print(f"  {icon} {name}")
    print(f"\n{passed}/{total} PASSED")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
