"""
RAX AI - PDF + Enhanced Chat Backend Test
Tests:
  1. POST /api/chat/send with PDF attachment (text + pdf)
  2. POST /api/chat/send with PDF-only (no text)
  3. POST /api/chat/send with empty / corrupt PDF
  4. POST /api/pdf/generate
  5. POST /api/pdf/extract (using PDF from #4)
  6. PDF + Image combined in same chat message
  7. System prompt enhancement (¿quién eres?)
  8. PDF generation tag in chat ([GENERATE_PDF:...])
"""
import io
import base64
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

BASE = "https://ai-chat-demo-26.preview.emergentagent.com/api"
ADMIN_EMAIL = "rascsarango12345@gmail.com"
ADMIN_PASS = "Rasc2026!RaxAI"

results = []  # (name, passed, info)


def log(name, ok, info=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {info}")
    results.append((name, ok, info))


def make_test_pdf(text="Hola mundo. Esto es un test. Capital de Francia: Paris. 2+2=4."):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 14)
    y = 750
    for line in text.split(". "):
        c.drawString(72, y, line + ".")
        y -= 30
    c.showPage()
    c.save()
    return buf.getvalue()


def make_test_jpeg():
    from PIL import Image
    img = Image.new("RGB", (256, 256), (180, 200, 220))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def login():
    r = requests.post(f"{BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def main():
    print(f"=== RAX AI PDF + Enhanced Chat Test ===\nBackend: {BASE}\n")

    try:
        token = login()
        log("0. Admin login", True, "JWT obtained")
    except Exception as e:
        log("0. Admin login", False, str(e))
        return False
    H = {"Authorization": f"Bearer {token}"}

    pdf_bytes = make_test_pdf()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    print(f"Test PDF generated: {len(pdf_bytes)} bytes ({len(pdf_b64)} b64 chars)\n")

    # ===== Test 1: chat/send with PDF + text =====
    try:
        body = {
            "text": "¿Qué dice este PDF?",
            "pdf_base64": pdf_b64,
            "pdf_filename": "test.pdf",
            "locale": "es",
            "user_tz": "America/Bogota",
        }
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=120)
        ok = r.status_code == 200
        info = f"status={r.status_code}"
        if ok:
            content = r.json().get("message", {}).get("content", "")
            ref = any(kw.lower() in content.lower() for kw in ["paris", "parís", "hola mundo", "francia", "test"])
            ok = ref
            info += f" | response_len={len(content)} | references_pdf={ref}"
            if not ref:
                info += f" | content[:200]={content[:200]!r}"
        else:
            info += f" body={r.text[:300]}"
        log("1. chat/send with text + PDF", ok, info)
    except Exception as e:
        log("1. chat/send with text + PDF", False, f"exception: {e}")

    # ===== Test 2: chat/send with PDF-only (no text) =====
    try:
        body = {
            "pdf_base64": pdf_b64,
            "pdf_filename": "test.pdf",
            "locale": "es",
            "user_tz": "America/Bogota",
        }
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=120)
        ok = r.status_code == 200
        info = f"status={r.status_code}"
        if ok:
            content = r.json().get("message", {}).get("content", "")
            ok = len(content) > 30
            info += f" | summary_len={len(content)}"
        else:
            info += f" body={r.text[:300]}"
        log("2. chat/send with PDF-only (no text)", ok, info)
    except Exception as e:
        log("2. chat/send with PDF-only", False, f"exception: {e}")

    # ===== Test 3a: empty PDF (pdf_base64="") =====
    try:
        body = {"text": "test", "pdf_base64": "", "locale": "es"}
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=60)
        ok_400 = r.status_code == 400
        info = f"status={r.status_code} body={r.text[:200]}"
        log("3a. chat/send empty pdf_base64 -> expect 400", ok_400, info)
    except Exception as e:
        log("3a. chat/send empty pdf_base64", False, f"exception: {e}")

    # ===== Test 3b: corrupt PDF ',,,'  =====
    try:
        body = {"text": "¿Qué dice?", "pdf_base64": ",,,", "locale": "es"}
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=60)
        ok = r.status_code == 400
        info = f"status={r.status_code} body={r.text[:200]}"
        if ok:
            pdf_err = "pdf" in r.text.lower()
            ok = pdf_err
            info += f" | pdf_in_error={pdf_err}"
        log("3b. chat/send corrupt pdf ',,,' -> expect 400 with PDF error", ok, info)
    except Exception as e:
        log("3b. chat/send corrupt pdf ',,,'", False, f"exception: {e}")

    # ===== Test 4: POST /api/pdf/generate =====
    generated_pdf_b64 = None
    try:
        body = {
            "title": "Mi Informe",
            "content": "# Resumen\n\nHola **mundo**. Este es un *test*.\n\n## Sección 2\n- Item 1\n- Item 2",
        }
        r = requests.post(f"{BASE}/pdf/generate", json=body, headers=H, timeout=30)
        ok = r.status_code == 200
        info = f"status={r.status_code}"
        if ok:
            data = r.json()
            generated_pdf_b64 = data.get("pdf_base64")
            size = data.get("size_bytes", 0)
            fname = data.get("filename", "")
            try:
                raw = base64.b64decode(generated_pdf_b64)
                is_pdf = raw[:5] == b"%PDF-"
            except Exception:
                is_pdf = False
            ok = bool(generated_pdf_b64) and size > 1000 and is_pdf and fname.endswith(".pdf")
            info += f" | size={size} | filename={fname} | starts_with_%PDF-={is_pdf}"
        else:
            info += f" body={r.text[:300]}"
        log("4. POST /api/pdf/generate", ok, info)
    except Exception as e:
        log("4. POST /api/pdf/generate", False, f"exception: {e}")

    # ===== Test 5: POST /api/pdf/extract =====
    try:
        if not generated_pdf_b64:
            log("5. POST /api/pdf/extract", False, "skipped: no PDF from test 4")
        else:
            body = {"pdf_base64": generated_pdf_b64}
            r = requests.post(f"{BASE}/pdf/extract", json=body, headers=H, timeout=30)
            ok = r.status_code == 200
            info = f"status={r.status_code}"
            if ok:
                data = r.json()
                pages = data.get("pages", [])
                full = data.get("full_text", "")
                total_pages = data.get("total_pages", 0)
                contains_text = any(kw in full for kw in ["Mi Informe", "Resumen", "mundo"])
                ok = total_pages >= 1 and len(pages) >= 1 and contains_text
                info += f" | total_pages={total_pages} | pages_count={len(pages)} | contains_expected={contains_text}"
                if not contains_text:
                    info += f" | full_text[:300]={full[:300]!r}"
            else:
                info += f" body={r.text[:300]}"
            log("5. POST /api/pdf/extract", ok, info)
    except Exception as e:
        log("5. POST /api/pdf/extract", False, f"exception: {e}")

    # ===== Test 6: PDF + Image combined =====
    try:
        jpg = make_test_jpeg()
        img_b64 = base64.b64encode(jpg).decode("utf-8")
        body = {
            "text": "Analiza tanto la imagen como el PDF y dime qué ves.",
            "pdf_base64": pdf_b64,
            "pdf_filename": "test.pdf",
            "image_base64": img_b64,
            "locale": "es",
            "user_tz": "America/Bogota",
        }
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=180)
        ok = r.status_code == 200
        info = f"status={r.status_code}"
        if ok:
            content = r.json().get("message", {}).get("content", "")
            ok = len(content) > 50
            info += f" | response_len={len(content)} | preview={content[:200]!r}"
        else:
            info += f" body={r.text[:300]}"
        log("6. chat/send with PDF + image combined", ok, info)
    except Exception as e:
        log("6. chat/send with PDF + image combined", False, f"exception: {e}")

    # ===== Test 7: System prompt enhancement (¿quién eres?) =====
    try:
        body = {"text": "¿quién eres?", "locale": "es", "user_tz": "America/Bogota"}
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=60)
        ok = r.status_code == 200
        info = f"status={r.status_code}"
        if ok:
            content = r.json().get("message", {}).get("content", "")
            says_rax = "rax" in content.lower()
            says_rasc = "rasc" in content.lower()
            not_chatgpt = "chatgpt" not in content.lower() and "claude" not in content.lower()
            ok = says_rax and says_rasc and not_chatgpt
            info += (f" | says_RAX={says_rax} | says_RASC={says_rasc} | "
                     f"no_chatgpt_claude={not_chatgpt} | preview={content[:200]!r}")
        else:
            info += f" body={r.text[:300]}"
        log("7. system prompt: ¿quién eres? -> RAX AI / RASC", ok, info)
    except Exception as e:
        log("7. system prompt ¿quién eres?", False, f"exception: {e}")

    # ===== Test 8: PDF generation tag in chat =====
    try:
        body = {
            "text": "Hazme un PDF con un resumen de la fotosíntesis",
            "locale": "es",
            "user_tz": "America/Bogota",
        }
        r = requests.post(f"{BASE}/chat/send", json=body, headers=H, timeout=90)
        ok = r.status_code == 200
        info = f"status={r.status_code}"
        if ok:
            content = r.json().get("message", {}).get("content", "")
            has_tag = "[GENERATE_PDF:" in content
            ok = has_tag
            info += f" | has_GENERATE_PDF_tag={has_tag} | tail={content[-200:]!r}"
        else:
            info += f" body={r.text[:300]}"
        log("8. chat asks for PDF -> AI returns [GENERATE_PDF:...] tag", ok, info)
    except Exception as e:
        log("8. PDF generation tag in chat", False, f"exception: {e}")

    # ===== Summary =====
    print("\n=== SUMMARY ===")
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"Passed: {passed} / {len(results)}")
    print(f"Failed: {failed} / {len(results)}")
    for name, ok, info in results:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}")
    print()
    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
