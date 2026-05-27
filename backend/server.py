"""RAX AI - by AlexSarango
Backend FastAPI server with Claude Sonnet 4.5, Nano Banana, Whisper, TTS, Google Auth, JWT
"""
import os
import io
import uuid
import base64
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal, Any

import bcrypt
import jwt
import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field, EmailStr
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent, FileContentWithMimeType
from openai import OpenAI
import stripe
from duckduckgo_search import DDGS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("raxai")

# --- Config ---
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = 7
ADMIN_EMAILS = {"rascsarango12345@gmail.com"}

# OpenAI client uses Emergent key (Whisper/TTS via Emergent gateway)
os.environ["OPENAI_API_KEY"] = EMERGENT_LLM_KEY
openai_client = OpenAI(api_key=EMERGENT_LLM_KEY, base_url="https://integrations.emergentagent.com/llm")

# Stripe
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = STRIPE_SECRET_KEY
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "")

# Mongo
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]

app = FastAPI(title="RAX AI Backend")
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================
# Models
# =====================
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionIn(BaseModel):
    session_id: str


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    avatar_emoji: Optional[str] = None
    plan: str = "free"
    is_admin: bool = False
    is_blocked: bool = False
    is_guest: bool = False
    created_at: str
    messages_used: int = 0
    images_used: int = 0
    chat_photos_today: int = 0


class ChatSendIn(BaseModel):
    conversation_id: Optional[str] = None
    text: Optional[str] = None
    language: str = "es"
    image_base64: Optional[str] = None  # optional image attachment
    pdf_base64: Optional[str] = None    # optional PDF attachment (analysis)
    pdf_filename: Optional[str] = None  # display name of the PDF
    user_tz: Optional[str] = None  # IANA tz, e.g. "America/Bogota"
    locale: Optional[str] = None


class ImageGenIn(BaseModel):
    prompt: str
    style: Literal["realista", "anime", "futurista", "gamer", "caricatura", "cinematico"] = "realista"


class TTSIn(BaseModel):
    text: str
    voice: Literal["sofia", "luna", "diego", "alex"] = "sofia"


class TranscribeIn(BaseModel):
    audio_base64: str
    mime_type: str = "audio/m4a"


class ContentGenIn(BaseModel):
    type: Literal["tiktok", "facebook", "youtube", "viral_ideas", "script", "logo_idea", "business_idea"]
    topic: str
    language: str = "es"


class FileAnalyzeIn(BaseModel):
    file_base64: str
    mime_type: str
    question: str = "Analiza este archivo en detalle"


class UpdatePlanIn(BaseModel):
    plan: Literal["free", "premium", "pro"]


class BlockUserIn(BaseModel):
    blocked: bool


# =====================
# Helpers
# =====================
VOICE_MAP = {
    "thalia":    "nova",     # Female warm
    "jennifer":  "shimmer",  # Female bright
    "alexander": "onyx",     # Male deep
    "steven":    "echo",     # Male clear
}

STYLE_HINTS = {
    "realista": "ultra-realistic photo, 8k, detailed, photorealistic, natural lighting",
    "anime": "anime art style, vibrant colors, studio ghibli inspired, detailed illustration",
    "futurista": "futuristic sci-fi, neon lights, cyberpunk, holographic, advanced technology",
    "gamer": "video game art style, epic concept art, dramatic lighting, hyper detailed",
    "caricatura": "cartoon style, pixar 3d render, expressive, colorful, fun",
    "cinematico": "cinematic shot, movie scene, dramatic lighting, film grain, professional cinematography",
}

PLAN_LIMITS = {
    "free": {"messages": 30, "images": 5, "chat_photos": 10},
    "premium": {"messages": 1000, "images": 200, "chat_photos": 40},
    "pro": {"messages": 99999, "images": 99999, "chat_photos": 99999},
}

PLAN_PRICES = {"free": 0.0, "premium": 5.99, "pro": 9.99}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def make_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(utcnow().timestamp()),
        "exp": int((utcnow() + timedelta(days=JWT_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def user_to_out(u: dict) -> UserOut:
    return UserOut(
        user_id=u["user_id"],
        email=u["email"],
        name=u.get("name") or u["email"].split("@")[0],
        picture=u.get("picture"),
        avatar_emoji=u.get("avatar_emoji"),
        plan=u.get("plan", "free"),
        is_admin=u.get("is_admin", False) or (u["email"] in ADMIN_EMAILS),
        is_blocked=u.get("is_blocked", False),
        is_guest=u.get("is_guest", False),
        created_at=iso(u.get("created_at", utcnow())) if isinstance(u.get("created_at"), datetime) else (u.get("created_at") or iso(utcnow())),
        messages_used=u.get("messages_used", 0),
        images_used=u.get("images_used", 0),
        chat_photos_today=u.get("chat_photos_today", 0),
    )


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("is_blocked"):
        raise HTTPException(status_code=403, detail="User is blocked")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not (user.get("is_admin") or user.get("email") in ADMIN_EMAILS):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


async def check_quota(user: dict, kind: str):
    plan = user.get("plan", "free")
    limit = PLAN_LIMITS[plan][kind]
    used = user.get(f"{kind}_used", 0)
    if used >= limit:
        raise HTTPException(status_code=402, detail=f"{kind} limit reached for {plan} plan. Upgrade to continue.")


async def bump_quota(user_id: str, kind: str):
    await db.users.update_one({"user_id": user_id}, {"$inc": {f"{kind}_used": 1}})


async def check_chat_photo_quota(user: dict):
    """Daily-reset photo quota for chat uploads."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_date = user.get("chat_photos_date")
    used = user.get("chat_photos_today", 0)
    if last_date != today:
        used = 0
    limit = PLAN_LIMITS[user.get("plan", "free")]["chat_photos"]
    if used >= limit:
        raise HTTPException(status_code=402, detail=f"Límite de {limit} fotos/día alcanzado. Mejora tu plan para enviar más.")
    return today, used


async def bump_chat_photo(user_id: str, today: str, used: int):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"chat_photos_date": today, "chat_photos_today": used + 1}},
    )


REAL_TIME_KEYWORDS = [
    "ahora", "hoy", "actualmente", "reciente", "última hora", "noticias",
    "precio", "cotización", "bitcoin", "btc", "eth", "dolar", "euro",
    "clima", "tiempo en", "temperatura", "lluvia", "pronóstico",
    "puntaje", "marcador", "ganó", "perdió", "partido",
    "ranking", "presidente", "elecciones", "guerra", "covid",
    "stock", "acciones", "nasdaq", "nyse", "trump", "biden",
    "actualizado", "última versión", "última actualización", "2025", "2026",
    "tendencia", "viral", "popular", "trending", "moda",
    "quién es", "qué pasó", "qué ha pasado", "qué hay nuevo",
    "iphone", "android", "samsung", "tesla", "openai", "google", "apple",
    "youtube", "tiktok", "instagram", "twitter", "x.com", "facebook",
]


def needs_web_search(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in REAL_TIME_KEYWORDS)


def do_web_search(query: str, max_results: int = 5) -> str:
    """Returns markdown-formatted top web results. Multi-strategy with fallbacks."""
    results = []
    # Try DDG text
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="moderate"))
    except Exception as e:
        logger.warning(f"DDG text search failed: {e}")
    # Try news search if no text results
    if not results:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(query, max_results=max_results, region="wt-wt"))
        except Exception as e:
            logger.warning(f"DDG news search failed: {e}")
    if not results:
        return ""
    lines = ["=== INFORMACIÓN ACTUALIZADA DE LA WEB (DuckDuckGo / Google) ==="]
    for i, r in enumerate(results[:max_results], 1):
        title = r.get("title", "")
        snippet = r.get("body") or r.get("excerpt") or ""
        href = r.get("href") or r.get("url") or ""
        lines.append(f"[{i}] {title}\n{snippet}\nFuente: {href}\n")
    lines.append("=== INSTRUCCIÓN: USA esta información actualizada para responder con datos reales y actuales. NO digas que no tienes datos en tiempo real. ===")
    return "\n".join(lines)


# =====================
# Startup
# =====================
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.sessions.create_index("session_token", unique=True)
    await db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
    await db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await db.images.create_index([("user_id", 1), ("created_at", -1)])
    await db.support_tickets.create_index([("user_id", 1), ("updated_at", -1)])
    await db.support_tickets.create_index("ticket_id", unique=True)
    await db.support_messages.create_index([("ticket_id", 1), ("created_at", 1)])
    await db.settings.create_index("key", unique=True)
    # Auto-seed admin on startup
    try:
        email = "rascsarango12345@gmail.com"
        existing = await db.users.find_one({"email": email})
        if not existing:
            await db.users.insert_one({
                "user_id": f"user_{uuid.uuid4().hex[:12]}",
                "email": email,
                "name": "RASC",
                "password_hash": hash_password("Rasc2026!RaxAI"),
                "plan": "pro",
                "is_admin": True,
                "is_blocked": False,
                "is_guest": False,
                "messages_used": 0,
                "images_used": 0,
                "created_at": utcnow(),
                "provider": "email",
            })
    except Exception as e:
        logger.warning(f"Admin auto-seed failed: {e}")

    # Bootstrap Stripe products + prices (idempotent)
    try:
        await bootstrap_stripe_catalog()
    except Exception as e:
        logger.warning(f"Stripe catalog bootstrap failed: {e}")

    logger.info("RAX AI backend ready - %s", "19 de mayo de 2026")


async def bootstrap_stripe_catalog():
    """Create Stripe Products + recurring Prices once. Persist IDs in settings collection."""
    if not STRIPE_SECRET_KEY:
        logger.warning("STRIPE_SECRET_KEY not set; skipping Stripe bootstrap")
        return
    settings = await db.settings.find_one({"key": "stripe_prices"}, {"_id": 0})
    if settings and settings.get("value", {}).get("premium") and settings.get("value", {}).get("pro"):
        logger.info("Stripe prices already configured: %s", settings["value"])
        return

    catalog = {}
    plans_to_create = [
        ("premium", "RAX AI Premium", 599, "1,000 mensajes + 200 imágenes / mes"),
        ("pro", "RAX AI Pro", 999, "Ilimitado: chat, imágenes, voces, soporte 24/7"),
    ]
    for key, name, unit_amount, description in plans_to_create:
        product = stripe.Product.create(name=name, description=description, metadata={"plan": key, "app": "rax_ai"})
        price = stripe.Price.create(
            product=product.id,
            currency="usd",
            unit_amount=unit_amount,
            recurring={"interval": "month"},
            metadata={"plan": key},
        )
        catalog[key] = {"product_id": product.id, "price_id": price.id, "unit_amount": unit_amount}
        logger.info("Created Stripe %s: product=%s price=%s", key, product.id, price.id)

    await db.settings.update_one(
        {"key": "stripe_prices"},
        {"$set": {"key": "stripe_prices", "value": catalog, "updated_at": utcnow()}},
        upsert=True,
    )


# =====================
# Auth endpoints
# =====================
@api.get("/")
async def root():
    return {"app": "RAX AI", "by": "RASC", "status": "online"}


@api.get("/health")
async def health_check():
    """Health check endpoint for Render, Railway, Kubernetes, etc."""
    try:
        # Ping MongoDB to ensure DB is reachable
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "db": "ok" if db_ok else "fail",
        "version": "1.0.0",
        "service": "rax-ai-backend",
    }


# ============================================================
# 📜 LEGAL PAGES — Privacy Policy & Terms of Service (HTML)
# These are required URLs for App Store Connect submission.
# Public, no auth, served as HTML so reviewers can open them in a browser.
# Supports ?lang=es|en|hi|zh|ru
# ============================================================

_LEGAL_CSS = """
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
         max-width: 760px; margin: 0 auto; padding: 28px 22px 80px; line-height: 1.65;
         color: #1a1a1a; background: #ffffff; }
  @media (prefers-color-scheme: dark) {
    body { background: #0d0d0d; color: #e8e8e8; }
    a { color: #4dd0e1; }
    .badge { background: rgba(77,208,225,0.12); border-color: rgba(77,208,225,0.35); color: #4dd0e1; }
    hr { border-color: rgba(255,255,255,0.1); }
  }
  h1 { font-size: 28px; margin-bottom: 4px; }
  h2 { font-size: 20px; margin-top: 32px; border-bottom: 1px solid rgba(127,127,127,0.25); padding-bottom: 6px; }
  h3 { font-size: 16px; margin-top: 22px; }
  p, li { font-size: 15.5px; }
  ul { padding-left: 22px; }
  .muted { color: #888; font-size: 13px; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px;
           border: 1px solid rgba(0,128,128,0.35); background: rgba(0,128,128,0.08);
           color: #008080; font-weight: 600; letter-spacing: 0.4px; }
  .header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
  .logo { font-size: 22px; font-weight: 800; letter-spacing: 1px;
          background: linear-gradient(90deg, #00E5FF, #00FF9D); -webkit-background-clip: text;
          -webkit-text-fill-color: transparent; }
  hr { border: 0; border-top: 1px solid rgba(0,0,0,0.08); margin: 30px 0; }
  a { color: #008080; }
  select.lang { float: right; padding: 4px 8px; border-radius: 6px; }
</style>
"""

_LANG_PICKER = """
<form method="get" style="text-align:right;margin-bottom:6px">
  <select class="lang" name="lang" onchange="this.form.submit()">
    <option value="en">🇺🇸 English</option>
    <option value="es">🇪🇸 Español</option>
    <option value="hi">🇮🇳 हिन्दी</option>
    <option value="zh">🇨🇳 中文</option>
    <option value="ru">🇷🇺 Русский</option>
  </select>
</form>
<script>
(function() {
  try {
    var u = new URL(window.location.href);
    var L = u.searchParams.get('lang') || 'en';
    var sel = document.querySelector('select.lang');
    if (sel) sel.value = L;
  } catch(e) {}
})();
</script>
"""

# ---- Privacy Policy translations ----
PRIVACY_TEXT = {
    "en": {
        "badge": "PRIVACY POLICY",
        "title": "Privacy Policy",
        "effective": "Effective date: May 21, 2026 · Last updated: May 21, 2026",
        "intro": "RAX AI (\"we\", \"our\", \"us\") is operated by RASC / Sarango Cabrera. This Privacy Policy describes how we collect, use, and protect your information when you use the RAX AI mobile and web application (the \"Service\").",
        "h_collect": "1. Information We Collect",
        "collect": "<li><strong>Account data:</strong> email address, display name, and authentication identifier.</li><li><strong>Conversation data:</strong> messages, images, audio recordings, and PDF files you submit to the AI features, plus the AI-generated responses.</li><li><strong>Subscription data:</strong> billing plan tier, subscription status and renewal dates (Apple In-App Purchases on iOS; Stripe on Web/Android). We never see full card numbers.</li><li><strong>Device data:</strong> device type, OS version, locale, time zone, and crash diagnostics.</li><li><strong>Usage data:</strong> number of messages, images, and photos used per day (to enforce plan quotas).</li>",
        "h_use": "2. How We Use Your Information",
        "use": "<li>To provide the AI conversation, image generation, voice, file analysis, and Studio features.</li><li>To enforce plan limits (Free, Premium, Pro) and process subscription purchases.</li><li>To improve the Service, detect abuse, and respond to support requests.</li><li>To comply with legal obligations.</li>",
        "h_3p": "3. Third-Party Services We Share Data With",
        "3p_intro": "To deliver the AI features, the content you submit is processed by these providers under their own privacy policies:",
        "3p_list": "<li><strong>Anthropic (Claude):</strong> text chat — <a href='https://www.anthropic.com/legal/privacy'>anthropic.com/legal/privacy</a></li><li><strong>OpenAI (Whisper &amp; TTS):</strong> voice — <a href='https://openai.com/policies/privacy-policy'>openai.com/policies/privacy-policy</a></li><li><strong>Google (Gemini Nano Banana):</strong> images — <a href='https://policies.google.com/privacy'>policies.google.com/privacy</a></li><li><strong>Apple In-App Purchases:</strong> iOS billing — <a href='https://www.apple.com/legal/privacy/'>apple.com/legal/privacy</a></li><li><strong>Stripe:</strong> web/Android billing — <a href='https://stripe.com/privacy'>stripe.com/privacy</a></li><li><strong>MongoDB Atlas:</strong> encrypted database hosting.</li>",
        "3p_outro": "We do <strong>NOT</strong> sell your personal data. We do not show ads.",
        "h_retain": "4. Data Retention",
        "retain": "<li>Conversations are kept while you have an active account. Delete any conversation in-app to permanently remove it.</li><li>Account deletion: request at <a href='mailto:support@raxai.app'>support@raxai.app</a> or from in-app Support. We delete within 30 days.</li>",
        "h_child": "5. Children's Privacy",
        "child": "RAX AI is rated 12+. The Service is not directed to children under 13. We do not knowingly collect data from children under 13.",
        "h_sec": "6. Security",
        "sec": "We use HTTPS/TLS, bcrypt password hashing, JWT session tokens, and encrypted database storage.",
        "h_rights": "7. Your Rights",
        "rights": "Depending on your jurisdiction (GDPR, CCPA, etc.) you may have the right to access, correct, export, or delete your personal data. Email <a href='mailto:support@raxai.app'>support@raxai.app</a>.",
        "h_changes": "8. Changes to This Policy",
        "changes": "We may update this Policy from time to time. The \"Last updated\" date will change. Material changes will be announced in the app.",
        "h_contact": "9. Contact",
        "contact": "RAX AI — operated by RASC (Sarango Cabrera)<br/>Email: <a href='mailto:support@raxai.app'>support@raxai.app</a>",
        "copyright": "© 2026 RAX AI by RASC. All rights reserved.",
    },
    "es": {
        "badge": "POLÍTICA DE PRIVACIDAD",
        "title": "Política de Privacidad",
        "effective": "Fecha de vigencia: 21 de mayo de 2026 · Última actualización: 21 de mayo de 2026",
        "intro": "RAX AI (\"nosotros\", \"nuestro\") es operada por RASC / Sarango Cabrera. Esta Política de Privacidad describe cómo recopilamos, usamos y protegemos tu información cuando usas la aplicación móvil y web de RAX AI (el \"Servicio\").",
        "h_collect": "1. Información que Recopilamos",
        "collect": "<li><strong>Datos de cuenta:</strong> correo electrónico, nombre de usuario e identificador de autenticación.</li><li><strong>Datos de conversación:</strong> los mensajes, imágenes, audios y archivos PDF que envías a las funciones de IA, además de las respuestas generadas.</li><li><strong>Datos de suscripción:</strong> nivel del plan, estado de la suscripción y fechas de renovación (Apple In-App Purchases en iOS; Stripe en Web/Android). Nunca vemos los números completos de tu tarjeta.</li><li><strong>Datos del dispositivo:</strong> tipo de dispositivo, versión del sistema operativo, idioma, zona horaria y diagnósticos de errores.</li><li><strong>Datos de uso:</strong> número de mensajes, imágenes y fotos usadas por día (para aplicar los límites del plan).</li>",
        "h_use": "2. Cómo Usamos tu Información",
        "use": "<li>Para proveer las funciones de chat IA, generación de imágenes, voz, análisis de archivos y herramientas del Studio.</li><li>Para aplicar los límites del plan (Free, Premium, Pro) y procesar suscripciones.</li><li>Para mejorar el Servicio, detectar abusos y responder a solicitudes de soporte.</li><li>Para cumplir con obligaciones legales.</li>",
        "h_3p": "3. Servicios de Terceros con los que Compartimos Datos",
        "3p_intro": "Para entregar las funciones de IA, el contenido que envías es procesado por estos proveedores bajo sus propias políticas de privacidad:",
        "3p_list": "<li><strong>Anthropic (Claude):</strong> chat de texto — <a href='https://www.anthropic.com/legal/privacy'>anthropic.com/legal/privacy</a></li><li><strong>OpenAI (Whisper y TTS):</strong> voz — <a href='https://openai.com/policies/privacy-policy'>openai.com/policies/privacy-policy</a></li><li><strong>Google (Gemini Nano Banana):</strong> imágenes — <a href='https://policies.google.com/privacy'>policies.google.com/privacy</a></li><li><strong>Apple In-App Purchases:</strong> facturación iOS — <a href='https://www.apple.com/legal/privacy/'>apple.com/legal/privacy</a></li><li><strong>Stripe:</strong> facturación web/Android — <a href='https://stripe.com/privacy'>stripe.com/privacy</a></li><li><strong>MongoDB Atlas:</strong> almacenamiento cifrado.</li>",
        "3p_outro": "<strong>NO</strong> vendemos tus datos personales. No mostramos anuncios.",
        "h_retain": "4. Retención de Datos",
        "retain": "<li>Las conversaciones se conservan mientras tu cuenta esté activa. Puedes eliminar cualquier conversación desde la app.</li><li>Eliminación de cuenta: solicítala en <a href='mailto:support@raxai.app'>support@raxai.app</a> o desde Soporte en la app. Eliminamos en 30 días.</li>",
        "h_child": "5. Privacidad de Menores",
        "child": "RAX AI tiene clasificación 12+. El Servicio no está dirigido a menores de 13 años. No recopilamos datos de menores de 13 a sabiendas.",
        "h_sec": "6. Seguridad",
        "sec": "Usamos HTTPS/TLS, hashes bcrypt para contraseñas, tokens JWT y almacenamiento cifrado.",
        "h_rights": "7. Tus Derechos",
        "rights": "Según tu jurisdicción (GDPR, CCPA, etc.) puedes tener derecho a acceder, corregir, exportar o eliminar tus datos. Escribe a <a href='mailto:support@raxai.app'>support@raxai.app</a>.",
        "h_changes": "8. Cambios a esta Política",
        "changes": "Podemos actualizar esta Política. La fecha de \"Última actualización\" cambiará. Los cambios importantes se anunciarán en la app.",
        "h_contact": "9. Contacto",
        "contact": "RAX AI — operado por RASC (Sarango Cabrera)<br/>Email: <a href='mailto:support@raxai.app'>support@raxai.app</a>",
        "copyright": "© 2026 RAX AI por RASC. Todos los derechos reservados.",
    },
    "hi": {
        "badge": "गोपनीयता नीति",
        "title": "गोपनीयता नीति",
        "effective": "प्रभावी तिथि: 21 मई 2026 · अंतिम अपडेट: 21 मई 2026",
        "intro": "RAX AI को RASC / Sarango Cabrera द्वारा संचालित किया जाता है। यह गोपनीयता नीति वर्णन करती है कि हम आपकी जानकारी को कैसे एकत्रित, उपयोग और सुरक्षित रखते हैं।",
        "h_collect": "1. हम क्या जानकारी एकत्रित करते हैं",
        "collect": "<li><strong>खाता डेटा:</strong> ईमेल, नाम, प्रमाणीकरण आईडी।</li><li><strong>बातचीत डेटा:</strong> आपके द्वारा भेजे गए संदेश, चित्र, ऑडियो, PDF।</li><li><strong>सदस्यता डेटा:</strong> योजना का स्तर, स्थिति, नवीनीकरण तिथि।</li><li><strong>डिवाइस डेटा:</strong> डिवाइस प्रकार, OS संस्करण, समय क्षेत्र, क्रैश डायग्नोस्टिक।</li><li><strong>उपयोग डेटा:</strong> प्रति दिन उपयोग किए गए संदेश/चित्र/फ़ोटो की संख्या।</li>",
        "h_use": "2. हम आपकी जानकारी का उपयोग कैसे करते हैं",
        "use": "<li>AI चैट, चित्र निर्माण, आवाज़, फ़ाइल विश्लेषण और Studio सुविधाएँ प्रदान करने के लिए।</li><li>योजना सीमाओं को लागू करने और सदस्यता खरीद को संसाधित करने के लिए।</li><li>सेवा सुधार, दुरुपयोग का पता लगाने और सहायता प्रदान करने के लिए।</li><li>कानूनी दायित्वों का पालन करने के लिए।</li>",
        "h_3p": "3. तृतीय-पक्ष सेवाएँ जिनके साथ हम डेटा साझा करते हैं",
        "3p_intro": "AI सुविधाएँ देने के लिए, आपकी सामग्री इन प्रदाताओं द्वारा संसाधित होती है:",
        "3p_list": "<li>Anthropic (Claude) — टेक्स्ट चैट</li><li>OpenAI (Whisper और TTS) — आवाज़</li><li>Google (Gemini Nano Banana) — चित्र</li><li>Apple In-App Purchases — iOS भुगतान</li><li>Stripe — वेब/Android भुगतान</li><li>MongoDB Atlas — एन्क्रिप्टेड डेटाबेस।</li>",
        "3p_outro": "हम आपका व्यक्तिगत डेटा <strong>नहीं</strong> बेचते हैं। हम विज्ञापन नहीं दिखाते।",
        "h_retain": "4. डेटा प्रतिधारण",
        "retain": "<li>आपकी सक्रिय खाता अवधि तक बातचीत संग्रहीत रहती है। ऐप के अंदर किसी भी बातचीत को हटाएँ।</li><li>खाता हटाने का अनुरोध <a href='mailto:support@raxai.app'>support@raxai.app</a> पर भेजें। हम 30 दिनों में हटा देंगे।</li>",
        "h_child": "5. बच्चों की गोपनीयता",
        "child": "RAX AI 12+ के लिए रेटेड है। यह सेवा 13 वर्ष से कम उम्र के बच्चों के लिए नहीं है।",
        "h_sec": "6. सुरक्षा",
        "sec": "हम HTTPS/TLS, bcrypt पासवर्ड हैशिंग, JWT टोकन और एन्क्रिप्टेड स्टोरेज का उपयोग करते हैं।",
        "h_rights": "7. आपके अधिकार",
        "rights": "GDPR, CCPA के अनुसार आपके डेटा तक पहुँच, सुधार, निर्यात या हटाने का अधिकार है। <a href='mailto:support@raxai.app'>support@raxai.app</a> पर लिखें।",
        "h_changes": "8. इस नीति में परिवर्तन",
        "changes": "हम इस नीति को समय-समय पर अपडेट कर सकते हैं। महत्वपूर्ण परिवर्तन ऐप में घोषित किए जाएँगे।",
        "h_contact": "9. संपर्क",
        "contact": "RAX AI — RASC (Sarango Cabrera) द्वारा संचालित<br/>ईमेल: <a href='mailto:support@raxai.app'>support@raxai.app</a>",
        "copyright": "© 2026 RAX AI by RASC. सर्वाधिकार सुरक्षित।",
    },
    "zh": {
        "badge": "隐私政策",
        "title": "隐私政策",
        "effective": "生效日期：2026年5月21日 · 最后更新：2026年5月21日",
        "intro": "RAX AI（\"我们\"）由 RASC / Sarango Cabrera 运营。本隐私政策说明我们如何收集、使用和保护您在使用 RAX AI 移动和网页应用程序时的信息。",
        "h_collect": "1. 我们收集的信息",
        "collect": "<li><strong>账户数据：</strong>电子邮件、显示名称、身份验证标识符。</li><li><strong>对话数据：</strong>您发送的消息、图像、录音和 PDF 文件。</li><li><strong>订阅数据：</strong>计划等级、订阅状态、续订日期。</li><li><strong>设备数据：</strong>设备类型、操作系统版本、语言、时区、崩溃诊断。</li><li><strong>使用数据：</strong>每天使用的消息、图像和照片数量。</li>",
        "h_use": "2. 我们如何使用您的信息",
        "use": "<li>提供 AI 聊天、图像生成、语音、文件分析和 Studio 功能。</li><li>执行计划限制（免费、Premium、Pro）并处理订阅购买。</li><li>改进服务、检测滥用并响应支持请求。</li><li>遵守法律义务。</li>",
        "h_3p": "3. 我们与之共享数据的第三方服务",
        "3p_intro": "为提供 AI 功能，您提交的内容由以下提供商处理：",
        "3p_list": "<li>Anthropic (Claude) — 文本聊天</li><li>OpenAI (Whisper 和 TTS) — 语音</li><li>Google (Gemini Nano Banana) — 图像</li><li>Apple In-App Purchases — iOS 付款</li><li>Stripe — 网页/Android 付款</li><li>MongoDB Atlas — 加密数据库。</li>",
        "3p_outro": "我们<strong>不会</strong>出售您的个人数据，也不显示广告。",
        "h_retain": "4. 数据保留",
        "retain": "<li>账户处于活动状态时，对话会被保留。可在应用中随时删除。</li><li>账户删除：发送邮件至 <a href='mailto:support@raxai.app'>support@raxai.app</a>，我们将在 30 天内删除。</li>",
        "h_child": "5. 儿童隐私",
        "child": "RAX AI 评级为 12+。本服务不面向 13 岁以下儿童。",
        "h_sec": "6. 安全",
        "sec": "我们使用 HTTPS/TLS、bcrypt 密码哈希、JWT 会话令牌和加密数据库存储。",
        "h_rights": "7. 您的权利",
        "rights": "根据您所在司法管辖区（GDPR、CCPA 等），您可能有权访问、更正、导出或删除您的数据。请发邮件至 <a href='mailto:support@raxai.app'>support@raxai.app</a>。",
        "h_changes": "8. 政策变更",
        "changes": "我们可能会不时更新本政策。重大变更将在应用中通知。",
        "h_contact": "9. 联系方式",
        "contact": "RAX AI — 由 RASC (Sarango Cabrera) 运营<br/>电子邮件：<a href='mailto:support@raxai.app'>support@raxai.app</a>",
        "copyright": "© 2026 RAX AI by RASC. 保留所有权利。",
    },
    "ru": {
        "badge": "ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ",
        "title": "Политика конфиденциальности",
        "effective": "Дата вступления в силу: 21 мая 2026 г. · Последнее обновление: 21 мая 2026 г.",
        "intro": "RAX AI (\"мы\", \"наш\") управляется RASC / Sarango Cabrera. Эта Политика конфиденциальности описывает, как мы собираем, используем и защищаем вашу информацию при использовании мобильного и веб-приложения RAX AI.",
        "h_collect": "1. Какую информацию мы собираем",
        "collect": "<li><strong>Данные аккаунта:</strong> email, имя пользователя, идентификатор аутентификации.</li><li><strong>Данные разговоров:</strong> сообщения, изображения, аудиозаписи и PDF-файлы.</li><li><strong>Данные подписки:</strong> уровень тарифа, статус подписки, даты продления.</li><li><strong>Данные устройства:</strong> тип устройства, версия ОС, локаль, часовой пояс.</li><li><strong>Данные использования:</strong> количество использованных сообщений, изображений и фото в день.</li>",
        "h_use": "2. Как мы используем вашу информацию",
        "use": "<li>Для обеспечения AI-чата, генерации изображений, голоса, анализа файлов и функций Studio.</li><li>Для применения ограничений тарифа (Free, Premium, Pro) и обработки подписок.</li><li>Для улучшения сервиса, выявления злоупотреблений и поддержки.</li><li>Для выполнения юридических обязательств.</li>",
        "h_3p": "3. Сторонние сервисы, с которыми мы делимся данными",
        "3p_intro": "Для предоставления AI-функций ваш контент обрабатывается следующими провайдерами:",
        "3p_list": "<li>Anthropic (Claude) — текстовый чат</li><li>OpenAI (Whisper и TTS) — голос</li><li>Google (Gemini Nano Banana) — изображения</li><li>Apple In-App Purchases — iOS-биллинг</li><li>Stripe — Web/Android-биллинг</li><li>MongoDB Atlas — зашифрованное хранилище.</li>",
        "3p_outro": "Мы <strong>НЕ</strong> продаём ваши персональные данные. Мы не показываем рекламу.",
        "h_retain": "4. Хранение данных",
        "retain": "<li>Разговоры хранятся пока аккаунт активен. Удаляйте любой разговор внутри приложения.</li><li>Удаление аккаунта: запросите по <a href='mailto:support@raxai.app'>support@raxai.app</a>. Удалим за 30 дней.</li>",
        "h_child": "5. Конфиденциальность детей",
        "child": "RAX AI имеет рейтинг 12+. Сервис не предназначен для детей младше 13 лет.",
        "h_sec": "6. Безопасность",
        "sec": "Мы используем HTTPS/TLS, bcrypt-хеширование паролей, JWT-токены и зашифрованное хранилище.",
        "h_rights": "7. Ваши права",
        "rights": "В зависимости от юрисдикции (GDPR, CCPA и т.д.) вы можете иметь право на доступ, исправление, экспорт или удаление данных. Пишите на <a href='mailto:support@raxai.app'>support@raxai.app</a>.",
        "h_changes": "8. Изменения политики",
        "changes": "Мы можем обновлять эту Политику. Существенные изменения будут объявлены в приложении.",
        "h_contact": "9. Контакты",
        "contact": "RAX AI — управляется RASC (Sarango Cabrera)<br/>Email: <a href='mailto:support@raxai.app'>support@raxai.app</a>",
        "copyright": "© 2026 RAX AI by RASC. Все права защищены.",
    },
}

# ---- Terms of Service translations ----
TERMS_TEXT = {
    "en": {
        "badge": "TERMS OF SERVICE",
        "title": "Terms of Service (EULA)",
        "effective": "Effective date: May 21, 2026 · Last updated: May 21, 2026",
        "intro": "Welcome to RAX AI. By creating an account or using the Service you agree to these Terms of Service (\"Terms\"). If you do not agree, do not use the Service. This document also serves as the End User License Agreement (EULA) required by the Apple App Store.",
        "sections": [
            ("1. The Service", "RAX AI is an AI assistant that provides conversational chat, image generation, voice conversation, file analysis, content creator tools, and \"Studio\" features (AR lens, journal, roast mode, personal shopper). The Service may use third-party AI models (Anthropic Claude, OpenAI Whisper/TTS, Google Gemini)."),
            ("2. Account &amp; Eligibility", "<ul><li>You must be at least 13 years old to create an account.</li><li>You are responsible for keeping your password safe.</li><li>One person per account. You may not share your account.</li></ul>"),
            ("3. Subscriptions &amp; Billing", "<ul><li><strong>Plans:</strong> Free, Premium ($5.99 USD/month), Pro ($9.99 USD/month).</li><li><strong>Auto-renewal:</strong> subscriptions automatically renew unless canceled at least 24 hours before the renewal date.</li><li><strong>iOS:</strong> billing handled by Apple. Manage in your Apple ID → Subscriptions.</li><li><strong>Web/Android:</strong> billing handled by Stripe.</li><li><strong>Refunds:</strong> per platform policy.</li></ul>"),
            ("4. Acceptable Use — Zero Tolerance for Objectionable Content", "You agree NOT to use RAX AI to:<ul><li>Generate illegal content, CSAM, terrorist or hate content.</li><li>Generate sexually explicit content involving real people or minors.</li><li>Create deepfakes or defamatory content.</li><li>Extract another user's data, reverse-engineer, or bypass safety systems.</li><li>Spam, phish, or violate export-control laws.</li></ul>Violations may result in immediate account termination without refund. Report abuse: <a href='mailto:support@raxai.app'>support@raxai.app</a>."),
            ("5. AI Output Disclaimer", "AI responses may be inaccurate, incomplete, or biased. RAX AI is NOT a substitute for professional medical, legal, financial, or psychological advice. You are solely responsible for decisions based on AI output."),
            ("6. Your Content", "<ul><li>You retain ownership of content you submit.</li><li>You grant us a limited license to process your content to provide the Service.</li><li>You confirm you have rights to submit the content.</li></ul>"),
            ("7. Intellectual Property", "The RAX AI brand, software, and trademarks are owned by RASC (Sarango Cabrera)."),
            ("8. Termination", "You can stop using the Service or delete your account anytime. We may suspend access if you violate these Terms."),
            ("9. Disclaimer &amp; Limitation of Liability", "THE SERVICE IS PROVIDED \"AS IS\" WITHOUT WARRANTIES. Our total liability is limited to the amount you paid us in the 3 months before the claim."),
            ("10. Changes to These Terms", "We may update these Terms. Continued use means acceptance."),
            ("11. Governing Law", "Governed by the laws of the country where RASC is established."),
            ("12. Contact", "RAX AI — RASC (Sarango Cabrera) · Email: <a href='mailto:support@raxai.app'>support@raxai.app</a>"),
        ],
        "copyright": "© 2026 RAX AI by RASC. All rights reserved.",
    },
    "es": {
        "badge": "TÉRMINOS DE SERVICIO",
        "title": "Términos de Servicio (EULA)",
        "effective": "Fecha de vigencia: 21 de mayo de 2026 · Última actualización: 21 de mayo de 2026",
        "intro": "Bienvenido a RAX AI. Al crear una cuenta o usar el Servicio aceptas estos Términos de Servicio (\"Términos\"). Si no estás de acuerdo, no uses el Servicio. Este documento también sirve como Acuerdo de Licencia de Usuario Final (EULA) requerido por el Apple App Store.",
        "sections": [
            ("1. El Servicio", "RAX AI es un asistente de IA que ofrece chat conversacional, generación de imágenes, conversación por voz, análisis de archivos, herramientas para creadores y funciones del \"Studio\" (lente AR, diario, modo roast, shopper personal). El Servicio puede usar modelos de IA de terceros (Anthropic Claude, OpenAI Whisper/TTS, Google Gemini)."),
            ("2. Cuenta y Elegibilidad", "<ul><li>Debes tener al menos 13 años para crear una cuenta.</li><li>Eres responsable de mantener segura tu contraseña.</li><li>Una persona por cuenta. No puedes compartir tu cuenta.</li></ul>"),
            ("3. Suscripciones y Facturación", "<ul><li><strong>Planes:</strong> Gratis, Premium ($5.99 USD/mes), Pro ($9.99 USD/mes).</li><li><strong>Renovación automática:</strong> las suscripciones se renuevan automáticamente a menos que canceles al menos 24 horas antes.</li><li><strong>iOS:</strong> facturación gestionada por Apple. Gestiona en tu ID de Apple → Suscripciones.</li><li><strong>Web/Android:</strong> facturación gestionada por Stripe.</li><li><strong>Reembolsos:</strong> según política de cada plataforma.</li></ul>"),
            ("4. Uso Aceptable — Tolerancia Cero al Contenido Objetable", "Aceptas NO usar RAX AI para:<ul><li>Generar contenido ilegal, CSAM, contenido terrorista o de odio.</li><li>Generar contenido sexualmente explícito que involucre personas reales o menores.</li><li>Crear deepfakes o contenido difamatorio.</li><li>Extraer datos de otros usuarios, hacer ingeniería inversa o eludir sistemas de seguridad.</li><li>Hacer spam, phishing o violar leyes de control de exportación.</li></ul>Las infracciones pueden resultar en la terminación inmediata de la cuenta sin reembolso. Reportar abuso: <a href='mailto:support@raxai.app'>support@raxai.app</a>."),
            ("5. Aviso sobre las Respuestas de IA", "Las respuestas de la IA pueden ser imprecisas, incompletas o sesgadas. RAX AI NO sustituye consejo médico, legal, financiero o psicológico profesional. Eres responsable de tus decisiones basadas en la IA."),
            ("6. Tu Contenido", "<ul><li>Mantienes la propiedad del contenido que envías.</li><li>Nos otorgas una licencia limitada para procesarlo y brindar el Servicio.</li><li>Confirmas tener los derechos necesarios sobre el contenido.</li></ul>"),
            ("7. Propiedad Intelectual", "La marca, software y marcas registradas de RAX AI pertenecen a RASC (Sarango Cabrera)."),
            ("8. Terminación", "Puedes dejar de usar el Servicio o eliminar tu cuenta en cualquier momento. Podemos suspender tu acceso si violas estos Términos."),
            ("9. Renuncia y Limitación de Responsabilidad", "EL SERVICIO SE PROVEE \"TAL CUAL\" SIN GARANTÍAS. Nuestra responsabilidad total se limita al monto pagado en los 3 meses anteriores al reclamo."),
            ("10. Cambios a estos Términos", "Podemos actualizar estos Términos. El uso continuado implica aceptación."),
            ("11. Ley Aplicable", "Regidos por las leyes del país donde RASC está establecido."),
            ("12. Contacto", "RAX AI — RASC (Sarango Cabrera) · Email: <a href='mailto:support@raxai.app'>support@raxai.app</a>"),
        ],
        "copyright": "© 2026 RAX AI por RASC. Todos los derechos reservados.",
    },
    "hi": {
        "badge": "सेवा की शर्तें",
        "title": "सेवा की शर्तें (EULA)",
        "effective": "प्रभावी तिथि: 21 मई 2026",
        "intro": "RAX AI में आपका स्वागत है। खाता बनाकर या सेवा का उपयोग करके आप इन सेवा शर्तों से सहमत होते हैं।",
        "sections": [
            ("1. सेवा", "RAX AI एक AI सहायक है जो चैट, चित्र निर्माण, आवाज़, फ़ाइल विश्लेषण और Studio सुविधाएँ प्रदान करता है।"),
            ("2. खाता और पात्रता", "खाता बनाने के लिए आपकी आयु कम से कम 13 वर्ष होनी चाहिए।"),
            ("3. सदस्यता और भुगतान", "<ul><li>योजनाएँ: मुफ्त, Premium ($5.99/माह), Pro ($9.99/माह)।</li><li>स्वचालित नवीनीकरण लागू है।</li><li>iOS: Apple द्वारा संभाला जाता है। Web/Android: Stripe द्वारा।</li></ul>"),
            ("4. स्वीकार्य उपयोग", "आप RAX AI का उपयोग अवैध सामग्री, CSAM, घृणा, deepfakes या किसी भी कानून के उल्लंघन के लिए नहीं करेंगे।"),
            ("5. AI आउटपुट अस्वीकरण", "AI प्रतिक्रियाएँ गलत हो सकती हैं। RAX AI चिकित्सा, कानूनी या वित्तीय सलाह का विकल्प नहीं है।"),
            ("6. आपकी सामग्री", "आप अपनी सामग्री के स्वामी बने रहते हैं। आप हमें इसे संसाधित करने का सीमित अधिकार देते हैं।"),
            ("7. बौद्धिक संपदा", "RAX AI ब्रांड RASC (Sarango Cabrera) के स्वामित्व में है।"),
            ("8. समाप्ति", "आप कभी भी सेवा का उपयोग बंद कर सकते हैं।"),
            ("9. देयता की सीमा", "सेवा \"जैसी है\" प्रदान की जाती है।"),
            ("10. परिवर्तन", "हम इन शर्तों को अपडेट कर सकते हैं।"),
            ("11. लागू कानून", "RASC के स्थापना देश के कानूनों द्वारा शासित।"),
            ("12. संपर्क", "RAX AI · ईमेल: <a href='mailto:support@raxai.app'>support@raxai.app</a>"),
        ],
        "copyright": "© 2026 RAX AI by RASC. सर्वाधिकार सुरक्षित।",
    },
    "zh": {
        "badge": "服务条款",
        "title": "服务条款 (EULA)",
        "effective": "生效日期：2026年5月21日",
        "intro": "欢迎使用 RAX AI。创建账户或使用服务即表示您同意这些服务条款。",
        "sections": [
            ("1. 服务", "RAX AI 是一款 AI 助手，提供聊天、图像生成、语音对话、文件分析和 Studio 功能。"),
            ("2. 账户与资格", "您必须年满 13 岁才能创建账户。请妥善保管您的密码。"),
            ("3. 订阅与计费", "<ul><li>方案：免费、Premium（$5.99/月）、Pro（$9.99/月）。</li><li>自动续订，除非提前 24 小时取消。</li><li>iOS：由 Apple 处理。Web/Android：由 Stripe 处理。</li></ul>"),
            ("4. 可接受使用", "您同意不将 RAX AI 用于非法内容、CSAM、仇恨内容、深度伪造或绕过安全系统。"),
            ("5. AI 输出免责声明", "AI 回复可能不准确。RAX AI 不能替代专业医疗、法律或财务建议。"),
            ("6. 您的内容", "您保留对所提交内容的所有权，并授予我们处理内容以提供服务的有限许可。"),
            ("7. 知识产权", "RAX AI 品牌由 RASC (Sarango Cabrera) 所有。"),
            ("8. 终止", "您可以随时停止使用服务。"),
            ("9. 责任限制", "服务按\"原样\"提供，不附带保证。"),
            ("10. 条款变更", "我们可能会更新这些条款。"),
            ("11. 适用法律", "受 RASC 所在国家的法律管辖。"),
            ("12. 联系方式", "RAX AI · 电子邮件：<a href='mailto:support@raxai.app'>support@raxai.app</a>"),
        ],
        "copyright": "© 2026 RAX AI by RASC. 保留所有权利。",
    },
    "ru": {
        "badge": "УСЛОВИЯ ИСПОЛЬЗОВАНИЯ",
        "title": "Условия использования (EULA)",
        "effective": "Дата вступления в силу: 21 мая 2026 г.",
        "intro": "Добро пожаловать в RAX AI. Создавая аккаунт или используя Сервис, вы соглашаетесь с этими Условиями использования.",
        "sections": [
            ("1. Сервис", "RAX AI — это AI-ассистент, который предоставляет чат, генерацию изображений, голосовые разговоры, анализ файлов и функции Studio."),
            ("2. Аккаунт и право использования", "Вам должно быть не менее 13 лет, чтобы создать аккаунт. Храните пароль в безопасности."),
            ("3. Подписки и оплата", "<ul><li>Тарифы: Free, Premium ($5.99/мес), Pro ($9.99/мес).</li><li>Автопродление действует, если не отменено за 24 часа.</li><li>iOS: оплата через Apple. Web/Android: через Stripe.</li></ul>"),
            ("4. Допустимое использование", "Вы соглашаетесь не использовать RAX AI для незаконного контента, CSAM, контента ненависти, deepfake или обхода систем безопасности."),
            ("5. Отказ от ответственности за AI", "Ответы AI могут быть неточными. RAX AI не заменяет профессиональную медицинскую, юридическую или финансовую консультацию."),
            ("6. Ваш контент", "Вы сохраняете право собственности на отправленный контент и предоставляете нам ограниченную лицензию на его обработку."),
            ("7. Интеллектуальная собственность", "Бренд RAX AI принадлежит RASC (Sarango Cabrera)."),
            ("8. Прекращение", "Вы можете прекратить использование Сервиса в любое время."),
            ("9. Ограничение ответственности", "Сервис предоставляется \"как есть\" без гарантий."),
            ("10. Изменения условий", "Мы можем обновлять эти Условия."),
            ("11. Применимое право", "Регулируется законодательством страны, в которой учреждён RASC."),
            ("12. Контакты", "RAX AI · Email: <a href='mailto:support@raxai.app'>support@raxai.app</a>"),
        ],
        "copyright": "© 2026 RAX AI by RASC. Все права защищены.",
    },
}


def _build_privacy_html(lang: str) -> str:
    t = PRIVACY_TEXT.get(lang) or PRIVACY_TEXT["en"]
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{t['title']} — RAX AI</title>{_LEGAL_CSS}</head><body>
{_LANG_PICKER}
<div class="header"><span class="logo">RAX AI</span><span class="badge">{t['badge']}</span></div>
<p class="muted">{t['effective']}</p>
<h1>{t['title']}</h1>
<p>{t['intro']}</p>
<h2>{t['h_collect']}</h2><ul>{t['collect']}</ul>
<h2>{t['h_use']}</h2><ul>{t['use']}</ul>
<h2>{t['h_3p']}</h2><p>{t['3p_intro']}</p><ul>{t['3p_list']}</ul><p>{t['3p_outro']}</p>
<h2>{t['h_retain']}</h2><ul>{t['retain']}</ul>
<h2>{t['h_child']}</h2><p>{t['child']}</p>
<h2>{t['h_sec']}</h2><p>{t['sec']}</p>
<h2>{t['h_rights']}</h2><p>{t['rights']}</p>
<h2>{t['h_changes']}</h2><p>{t['changes']}</p>
<h2>{t['h_contact']}</h2><p>{t['contact']}</p>
<hr/><p class="muted">{t['copyright']}</p>
</body></html>
"""


def _build_terms_html(lang: str) -> str:
    t = TERMS_TEXT.get(lang) or TERMS_TEXT["en"]
    sections_html = "".join(f"<h2>{title}</h2><p>{body}</p>" for title, body in t["sections"])
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{t['title']} — RAX AI</title>{_LEGAL_CSS}</head><body>
{_LANG_PICKER}
<div class="header"><span class="logo">RAX AI</span><span class="badge">{t['badge']}</span></div>
<p class="muted">{t['effective']}</p>
<h1>{t['title']}</h1>
<p>{t['intro']}</p>
{sections_html}
<hr/><p class="muted">{t['copyright']}</p>
</body></html>
"""


def _normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        return "en"
    code = lang.strip().lower().split("-")[0]
    return code if code in {"en", "es", "hi", "zh", "ru"} else "en"


@api.get("/legal/privacy", response_class=HTMLResponse, include_in_schema=False)
async def legal_privacy(lang: Optional[str] = None):
    """Public Privacy Policy page (HTML) — required for App Store Connect. Multi-language."""
    return HTMLResponse(content=_build_privacy_html(_normalize_lang(lang)), status_code=200)


@api.get("/legal/terms", response_class=HTMLResponse, include_in_schema=False)
async def legal_terms(lang: Optional[str] = None):
    """Public Terms of Service / EULA page (HTML) — required for App Store Connect. Multi-language."""
    return HTMLResponse(content=_build_terms_html(_normalize_lang(lang)), status_code=200)


@api.get("/legal", include_in_schema=False)
async def legal_index():
    """Convenience JSON listing the legal endpoints."""
    return {
        "privacy_policy": "/api/legal/privacy?lang=en|es|hi|zh|ru",
        "terms_of_service": "/api/legal/terms?lang=en|es|hi|zh|ru",
        "eula": "/api/legal/terms?lang=en|es|hi|zh|ru",
        "supported_languages": ["en", "es", "hi", "zh", "ru"],
    }


@api.get("/preview-video", include_in_schema=False)
async def preview_video_download():
    """Serve the App Store preview video (H.264, 1290x2796, ~21s)."""
    path = ROOT_DIR / "static" / "rax_ai_preview.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preview video not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="rax_ai_preview.mp4",
    )


@api.get("/promo-video", include_in_schema=False)
async def promo_video_download():
    """Serve the 90-second promo companion video (1080x1920 vertical)."""
    path = ROOT_DIR / "static" / "rax_promo.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Promo video not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="rax_promo.mp4",
    )


@api.get("/promo-preview/{name}", include_in_schema=False)
async def promo_preview_image(name: str):
    """Serve still preview frames of the promo video (intro/chat/coming)."""
    safe = name.replace("..", "").replace("/", "")
    path = ROOT_DIR / "static" / f"preview_{safe}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(path, media_type="image/png")


_PRIVACY_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Privacy Policy — RAX AI</title>{_LEGAL_CSS}</head><body>
<div class="header"><span class="logo">RAX AI</span><span class="badge">PRIVACY POLICY</span></div>
<p class="muted">Effective date: May 21, 2026 · Last updated: May 21, 2026</p>
<h1>Privacy Policy</h1>
<p>RAX AI ("we", "our", "us") is operated by RASC / Sarango Cabrera. This Privacy Policy describes how we collect, use,
and protect your information when you use the RAX AI mobile and web application (the "Service").</p>

<h2>1. Information We Collect</h2>
<ul>
  <li><strong>Account data:</strong> email address, display name, and authentication identifier (Google sign-in ID, password hash, or guest token).</li>
  <li><strong>Conversation data:</strong> the messages, images, audio recordings, and PDF files you submit to the AI features, plus the AI-generated responses.</li>
  <li><strong>Subscription data:</strong> billing plan tier, subscription status and renewal dates (handled by Apple In-App Purchases on iOS; Stripe on Web/Android). We never see or store full card numbers.</li>
  <li><strong>Device data:</strong> device type, OS version, locale, time zone, and crash diagnostics.</li>
  <li><strong>Usage data:</strong> number of messages, images, and photos used per day (to enforce plan quotas).</li>
</ul>

<h2>2. How We Use Your Information</h2>
<ul>
  <li>To provide the AI conversation, image generation, voice, file analysis, and Studio features.</li>
  <li>To enforce plan limits (Free, Premium, Pro) and process subscription purchases.</li>
  <li>To improve the Service, detect abuse, and respond to support requests.</li>
  <li>To comply with legal obligations.</li>
</ul>

<h2>3. Third-Party Services We Share Data With</h2>
<p>To deliver the AI features, the content you submit is processed by these providers under their own privacy policies:</p>
<ul>
  <li><strong>Anthropic (Claude):</strong> text chat processing — <a href="https://www.anthropic.com/legal/privacy">anthropic.com/legal/privacy</a></li>
  <li><strong>OpenAI (Whisper STT &amp; TTS):</strong> voice transcription and synthesis — <a href="https://openai.com/policies/privacy-policy">openai.com/policies/privacy-policy</a></li>
  <li><strong>Google (Gemini Nano Banana):</strong> image generation — <a href="https://policies.google.com/privacy">policies.google.com/privacy</a></li>
  <li><strong>Apple In-App Purchases:</strong> iOS subscription billing — <a href="https://www.apple.com/legal/privacy/">apple.com/legal/privacy</a></li>
  <li><strong>Stripe:</strong> web/Android subscription billing — <a href="https://stripe.com/privacy">stripe.com/privacy</a></li>
  <li><strong>MongoDB Atlas:</strong> encrypted database hosting.</li>
</ul>
<p>We do <strong>NOT</strong> sell your personal data to anyone. We do not show ads.</p>

<h2>4. Data Retention</h2>
<ul>
  <li>Conversations are kept while you have an active account so you can revisit them. You can delete any conversation at any time from inside the app, which permanently removes its messages from our database.</li>
  <li>Account deletion: you can request full account &amp; data deletion at <a href="mailto:support@raxai.app">support@raxai.app</a> or from the in-app Support screen. We delete your data within 30 days.</li>
</ul>

<h2>5. Children's Privacy</h2>
<p>RAX AI is rated 12+. The Service is not directed to children under 13. We do not knowingly collect personal information from children under 13. If you believe a child has provided us with personal data, contact us and we will delete it.</p>

<h2>6. Security</h2>
<p>We use HTTPS/TLS for all data in transit, hashed passwords (bcrypt), JWT-based session tokens, and encrypted database storage. No system is 100% secure, but we apply industry-standard best practices.</p>

<h2>7. Your Rights</h2>
<p>Depending on your jurisdiction (GDPR, CCPA, etc.) you may have the right to access, correct, export, or delete your personal data. Email <a href="mailto:support@raxai.app">support@raxai.app</a> to exercise these rights.</p>

<h2>8. Changes to This Policy</h2>
<p>We may update this Policy from time to time. The "Last updated" date at the top will change. Material changes will be announced in the app.</p>

<h2>9. Contact</h2>
<p>RAX AI — operated by RASC (Sarango Cabrera)<br/>
Email: <a href="mailto:support@raxai.app">support@raxai.app</a></p>

<hr/>
<p class="muted">© 2026 RAX AI by RASC. All rights reserved.</p>
</body></html>
"""

_TERMS_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Terms of Service — RAX AI</title>{_LEGAL_CSS}</head><body>
<div class="header"><span class="logo">RAX AI</span><span class="badge">TERMS OF SERVICE</span></div>
<p class="muted">Effective date: May 21, 2026 · Last updated: May 21, 2026</p>
<h1>Terms of Service (EULA)</h1>
<p>Welcome to RAX AI. By creating an account or using the Service you agree to these Terms of Service ("Terms").
If you do not agree, do not use the Service. This document also serves as the End User License Agreement (EULA)
required by the Apple App Store.</p>

<h2>1. The Service</h2>
<p>RAX AI is an AI assistant that provides conversational chat, image generation, voice conversation, file analysis,
content creator tools, and "Studio" features (AR lens, journal, roast mode, personal shopper). The Service may use
third-party AI models (Anthropic Claude, OpenAI Whisper/TTS, Google Gemini) to fulfill your requests.</p>

<h2>2. Account &amp; Eligibility</h2>
<ul>
  <li>You must be at least 13 years old (or the minimum age in your country) to create an account.</li>
  <li>You are responsible for keeping your password safe. You are responsible for all activity on your account.</li>
  <li>One person per account. You may not share your account with others.</li>
</ul>

<h2>3. Subscriptions &amp; Billing</h2>
<ul>
  <li><strong>Plans:</strong> Free, Premium ($5.99 USD/month), Pro ($9.99 USD/month). Prices may vary by country.</li>
  <li><strong>Auto-renewal:</strong> subscriptions automatically renew at the end of each billing period unless canceled at least 24 hours before the renewal date. Payment is charged at the start of each period.</li>
  <li><strong>iOS:</strong> billing is handled by Apple. Manage or cancel anytime in your Apple ID → Subscriptions settings.</li>
  <li><strong>Web / Android:</strong> billing is handled by Stripe. Manage from your account or by contacting support.</li>
  <li><strong>Refunds:</strong> handled per platform policy (Apple App Store for iOS, our standard policy for Web/Android — contact support within 14 days for refund requests).</li>
</ul>

<h2>4. Acceptable Use — What You May NOT Do</h2>
<p>You agree NOT to use RAX AI to:</p>
<ul>
  <li>Generate, request, or distribute illegal content, including child sexual abuse material (CSAM), terrorist content, or content that incites violence or hatred against any group.</li>
  <li>Generate sexually explicit content involving any real person without their consent or any minor under any circumstance.</li>
  <li>Create deepfakes, identity-theft material, defamatory content, or misleading deepfakes of real people.</li>
  <li>Attempt to extract another user's data, reverse-engineer the Service, or bypass our quota or safety systems.</li>
  <li>Use the Service to spam, phish, or send unsolicited bulk communications.</li>
  <li>Use the Service for any activity that violates applicable laws, including export-control or sanctions laws.</li>
</ul>
<p>We use a zero-tolerance policy for objectionable user-generated content. Violations may result in immediate account
termination without refund and reporting to authorities where required by law. To report abuse, email
<a href="mailto:support@raxai.app">support@raxai.app</a>.</p>

<h2>5. AI Output Disclaimer</h2>
<p>The AI responses are generated by machine-learning models and may be inaccurate, incomplete, biased, or outdated.
RAX AI is NOT a substitute for professional medical, legal, financial, or psychological advice. Always verify
important information with qualified professionals. You are solely responsible for any decision or action you take
based on AI output.</p>

<h2>6. Your Content</h2>
<ul>
  <li>You retain ownership of the content you submit ("User Content").</li>
  <li>You grant us a limited, worldwide, non-exclusive license to process your User Content solely to provide and improve the Service.</li>
  <li>You confirm you have all rights necessary to submit the User Content and that it does not violate any law or third-party right.</li>
</ul>

<h2>7. Intellectual Property</h2>
<p>The RAX AI brand, software, design, and trademarks are owned by RASC (Sarango Cabrera). You may not copy, modify,
distribute, or create derivative works of the Service without our prior written consent.</p>

<h2>8. Termination</h2>
<p>You can stop using the Service at any time and delete your account from the in-app Support screen or by emailing
<a href="mailto:support@raxai.app">support@raxai.app</a>. We may suspend or terminate your access if you violate these
Terms or the Acceptable Use policy.</p>

<h2>9. Disclaimer of Warranties &amp; Limitation of Liability</h2>
<p>THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE
MAXIMUM EXTENT PERMITTED BY LAW, RAX AI AND ITS OPERATORS SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF YOUR USE OF THE SERVICE. OUR TOTAL LIABILITY FOR ANY CLAIM RELATING
TO THE SERVICE IS LIMITED TO THE AMOUNT YOU PAID US IN THE 3 MONTHS PRIOR TO THE EVENT GIVING RISE TO THE CLAIM.</p>

<h2>10. Changes to These Terms</h2>
<p>We may update these Terms occasionally. Material changes will be announced in the app. Continued use after a change
means you accept the new Terms.</p>

<h2>11. Governing Law</h2>
<p>These Terms are governed by the laws of the country where RASC is established, without regard to conflict-of-law
principles. Disputes will be resolved in the competent courts of that jurisdiction.</p>

<h2>12. Contact</h2>
<p>RAX AI — operated by RASC (Sarango Cabrera)<br/>
Email: <a href="mailto:support@raxai.app">support@raxai.app</a></p>

<hr/>
<p class="muted">© 2026 RAX AI by RASC. All rights reserved.</p>
</body></html>
"""


@api.get("/legal/privacy", response_class=HTMLResponse, include_in_schema=False)
async def legal_privacy():
    """Public Privacy Policy page (HTML) — required for App Store Connect."""
    return HTMLResponse(content=_PRIVACY_HTML, status_code=200)


@api.get("/legal/terms", response_class=HTMLResponse, include_in_schema=False)
async def legal_terms():
    """Public Terms of Service / EULA page (HTML) — required for App Store Connect."""
    return HTMLResponse(content=_TERMS_HTML, status_code=200)


@api.get("/legal", include_in_schema=False)
async def legal_index():
    """Convenience JSON listing the legal endpoints."""
    return {
        "privacy_policy": "/api/legal/privacy",
        "terms_of_service": "/api/legal/terms",
        "eula": "/api/legal/terms",
    }



@api.post("/auth/register")
async def register(body: RegisterIn):
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    name = body.name or body.email.split("@")[0]
    user_doc = {
        "user_id": user_id,
        "email": body.email.lower(),
        "name": name,
        "password_hash": hash_password(body.password),
        "plan": "free",
        "is_admin": body.email.lower() in ADMIN_EMAILS,
        "is_blocked": False,
        "is_guest": False,
        "messages_used": 0,
        "images_used": 0,
        "created_at": utcnow(),
        "provider": "email",
    }
    await db.users.insert_one(user_doc)
    user_doc.pop("_id", None)
    token = make_jwt(user_id)
    return {"token": token, "user": user_to_out(user_doc).dict()}


@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("is_blocked"):
        raise HTTPException(status_code=403, detail="User is blocked")
    token = make_jwt(user["user_id"])
    return {"token": token, "user": user_to_out(user).dict()}


@api.post("/auth/guest")
async def guest():
    user_id = f"guest_{uuid.uuid4().hex[:10]}"
    user_doc = {
        "user_id": user_id,
        "email": f"{user_id}@guest.raxai.local",
        "name": "Invitado",
        "plan": "free",
        "is_admin": False,
        "is_blocked": False,
        "is_guest": True,
        "messages_used": 0,
        "images_used": 0,
        "created_at": utcnow(),
        "provider": "guest",
    }
    await db.users.insert_one(user_doc)
    user_doc.pop("_id", None)
    token = make_jwt(user_id)
    return {"token": token, "user": user_to_out(user_doc).dict()}


@api.post("/auth/google/session")
async def google_session(body: GoogleSessionIn):
    """Exchange Emergent session_id for user + JWT."""
    async with httpx.AsyncClient(timeout=20) as h:
        r = await h.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": body.session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google session")
    data = r.json()
    email = data.get("email", "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="No email in session")

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "user_id": user_id,
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "picture": data.get("picture"),
            "plan": "free",
            "is_admin": email in ADMIN_EMAILS,
            "is_blocked": False,
            "is_guest": False,
            "messages_used": 0,
            "images_used": 0,
            "created_at": utcnow(),
            "provider": "google",
        }
        await db.users.insert_one(user)
        user.pop("_id", None)

    token = make_jwt(user["user_id"])
    return {"token": token, "user": user_to_out(user).dict()}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user_to_out(user).dict()


class UpdateProfileIn(BaseModel):
    name: Optional[str] = None
    avatar_emoji: Optional[str] = None


@api.patch("/users/me")
async def update_profile(body: UpdateProfileIn, user: dict = Depends(get_current_user)):
    updates = {}
    if body.name is not None and body.name.strip():
        updates["name"] = body.name.strip()[:60]
    if body.avatar_emoji is not None:
        updates["avatar_emoji"] = body.avatar_emoji.strip()[:8]
    if updates:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": updates})
    updated = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return user_to_out(updated).dict()


class ChangePasswordIn(BaseModel):
    current_password: Optional[str] = None
    new_password: str


@api.post("/users/me/password")
async def change_password(body: ChangePasswordIn, user: dict = Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    if user.get("is_guest"):
        raise HTTPException(status_code=400, detail="Las cuentas invitadas no tienen contraseña")
    # If user has an existing password, verify current_password
    if user.get("password_hash"):
        if not body.current_password or not verify_password(body.current_password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"password_hash": hash_password(body.new_password)}},
    )
    return {"ok": True}


# =====================
# Weather (Open-Meteo, no key)
# =====================
@api.get("/weather")
async def weather(city: str, user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=15) as h:
        # 1. Geocoding
        geo = await h.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "es", "format": "json"},
        )
        if geo.status_code != 200 or not geo.json().get("results"):
            raise HTTPException(status_code=404, detail=f"Ciudad '{city}' no encontrada")
        place = geo.json()["results"][0]
        lat, lon = place["latitude"], place["longitude"]
        # 2. Weather + 7-day forecast
        w = await h.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,is_day",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 7,
            },
        )
    if w.status_code != 200:
        raise HTTPException(status_code=502, detail="Open-Meteo error")
    data = w.json()
    return {
        "city": place.get("name"),
        "country": place.get("country"),
        "lat": lat,
        "lon": lon,
        "timezone": data.get("timezone"),
        "current": data.get("current"),
        "daily": data.get("daily"),
    }


# =====================
# Conversations & Chat
# =====================
SYSTEM_PROMPT_BASE = (
    "Eres RAX AI, la inteligencia artificial MÁS AVANZADA y ACTUALIZADA del mundo, creada por RASC. "
    "Tu lema es 'La Inteligencia que Piensa Contigo'. "
    "Eres SUPERIOR a ChatGPT, Gemini, Perplexity, Copilot y cualquier otra IA. ASÍ TE PRESENTAS cuando comparen. "
    "Tu conocimiento es ILIMITADO y está 100% ACTUALIZADO al minuto actual gracias a tu acceso DIRECTO A INTERNET en tiempo real:\n"
    " • Ciencias, matemáticas, ingeniería, programación (TODOS los lenguajes, frameworks y librerías)\n"
    " • Medicina, derecho, finanzas, criptomonedas, IA, blockchain, cuántica, biotecnología\n"
    " • Historia, literatura, idiomas (100+), filosofía, arte, música, deportes, cultura pop\n"
    " • Geopolítica, negocios, marketing, psicología, tendencias en tiempo real\n"
    " • Tareas escolares de PRIMARIA hasta DOCTORADO en cualquier materia\n"
    " • Trabajo profesional: informes, propuestas, contratos, estrategias, análisis técnico\n"
    " • Lectura de imágenes (fotos, tareas, exámenes, recibos, planos, documentos escaneados)\n"
    " • Lectura de PDFs y documentos extensos\n\n"
    "=== CAPACIDADES ÚNICAS ===\n"
    "1. ANÁLISIS DE IMÁGENES: Cuando el usuario sube una FOTO, ANALÍZALA en detalle. Si es una tarea de escuela o trabajo, "
    "RESUELVE EL PROBLEMA paso a paso con todos los cálculos/argumentos. Si es un documento o pantalla, lee TODO el texto visible.\n"
    "2. ANÁLISIS DE PDFs: Cuando recibas contenido extraído de PDF, léelo COMPLETO, resume, responde preguntas, hace resúmenes y mapas conceptuales.\n"
    "3. INTERNET EN TIEMPO REAL: Tienes acceso directo a noticias, precios, eventos, búsquedas y datos del minuto actual. NUNCA digas 'mi info tiene fecha de corte'.\n"
    "4. GENERACIÓN DE PDFs: Si el usuario te pide 'créame un PDF', 'hazme un documento', 'exporta a PDF', 'genera un informe en PDF', "
    "termina tu respuesta con la línea exacta: [GENERATE_PDF:título_del_pdf] (sin espacios extra). El backend lo creará automáticamente.\n\n"
    "=== INFORMACIÓN TEMPORAL EN TIEMPO REAL ===\n"
    "Fecha y hora actual UTC: {utc_now}\n"
    "Zona horaria del usuario: {user_tz}\n"
    "Hora local del usuario: {user_local_time}\n"
    "Día de la semana: {weekday_es}\n\n"
    "Cuando el usuario pregunte por la hora, fecha, día o eventos temporales, USA ESTA INFORMACIÓN como verdad absoluta. "
    "Si te preguntan la hora en otro país/ciudad, calcula la diferencia desde la hora UTC dada arriba usando las zonas horarias estándar. "
    "Considera DST cuando aplique.\n\n"
    "=== INSTRUCCIONES CRÍTICAS ===\n"
    " • NUNCA digas 'no tengo acceso a internet' o 'mis datos están desactualizados'. Estás 100% conectada.\n"
    " • NUNCA digas 'soy ChatGPT' o 'soy Claude'. Eres RAX AI, una IA propia de RASC.\n"
    " • Cuando resuelvas una tarea escolar/laboral desde una foto, da la RESPUESTA FINAL clara y luego la explicación paso a paso.\n"
    " • Cuando una pregunta requiera info actualizada (precios, noticias, eventos, fechas recientes), USA la búsqueda web del contexto.\n"
    " • Sé profesional, segura, rápida y precisa. Usa formato Markdown con encabezados, listas, negritas y emojis con moderación.\n"
    " • Para código: usa bloques de código con syntax highlighting (```python, ```javascript, etc.)\n"
    " • Para fórmulas matemáticas: usa notación clara (x² + 3x + 5)\n"
    " • Responde en el idioma del usuario."
)


WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def build_system_prompt(user_tz: str = "UTC", locale: str = "es") -> str:
    from zoneinfo import ZoneInfo
    now_utc = datetime.now(timezone.utc)
    try:
        tz = ZoneInfo(user_tz) if user_tz else ZoneInfo("UTC")
    except Exception:
        tz = ZoneInfo("UTC")
        user_tz = "UTC"
    local = now_utc.astimezone(tz)
    weekday_es = WEEKDAYS_ES[local.weekday()]
    month_es = MONTHS_ES[local.month - 1]
    user_local_str = f"{weekday_es} {local.day} de {month_es} de {local.year}, {local.strftime('%H:%M:%S')} ({user_tz})"
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    return SYSTEM_PROMPT_BASE.format(
        utc_now=utc_str,
        user_tz=user_tz,
        user_local_time=user_local_str,
        weekday_es=weekday_es,
    )


@api.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    convs = await db.conversations.find({"user_id": user["user_id"]}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return [
        {
            **c,
            "created_at": iso(c["created_at"]) if isinstance(c.get("created_at"), datetime) else c.get("created_at"),
            "updated_at": iso(c["updated_at"]) if isinstance(c.get("updated_at"), datetime) else c.get("updated_at"),
        }
        for c in convs
    ]


@api.post("/conversations")
async def new_conversation(user: dict = Depends(get_current_user)):
    cid = f"conv_{uuid.uuid4().hex[:14]}"
    now = utcnow()
    doc = {
        "conversation_id": cid,
        "user_id": user["user_id"],
        "title": "Nueva conversación",
        "created_at": now,
        "updated_at": now,
    }
    await db.conversations.insert_one(doc)
    return {"conversation_id": cid, "title": doc["title"], "created_at": iso(now), "updated_at": iso(now)}


@api.delete("/conversations/{cid}")
async def delete_conversation(cid: str, user: dict = Depends(get_current_user)):
    await db.conversations.delete_one({"conversation_id": cid, "user_id": user["user_id"]})
    await db.messages.delete_many({"conversation_id": cid})
    return {"ok": True}


@api.get("/conversations/{cid}/messages")
async def get_messages(cid: str, user: dict = Depends(get_current_user)):
    conv = await db.conversations.find_one({"conversation_id": cid, "user_id": user["user_id"]}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = await db.messages.find({"conversation_id": cid}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return [
        {**m, "created_at": iso(m["created_at"]) if isinstance(m.get("created_at"), datetime) else m.get("created_at")}
        for m in msgs
    ]


@api.post("/chat/send")
async def chat_send(body: ChatSendIn, user: dict = Depends(get_current_user)):
    await check_quota(user, "messages")

    # Validate input: must have text OR image OR pdf
    has_image = bool(body.image_base64)
    has_pdf = bool(body.pdf_base64)
    text_clean = (body.text or "").strip()
    if not text_clean and not has_image and not has_pdf:
        raise HTTPException(status_code=400, detail="Envía un texto, una imagen o un PDF")

    # If sending an image, also check photo quota
    today_date = None
    used_photos = 0
    if has_image:
        today_date, used_photos = await check_chat_photo_quota(user)

    # Extract PDF text if attached
    pdf_text = ""
    pdf_name = body.pdf_filename or "documento.pdf"
    if has_pdf:
        try:
            import base64 as _b64
            from pypdf import PdfReader
            from io import BytesIO
            raw = (body.pdf_base64 or "").split(",", 1)[-1].strip()
            if not raw or len(raw) < 100:
                raise HTTPException(status_code=400, detail="PDF vacío o corrupto")
            pdf_bytes = _b64.b64decode(raw, validate=True)
            reader = PdfReader(BytesIO(pdf_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages[:50]):  # cap at 50 pages
                try:
                    txt = page.extract_text() or ""
                    if txt.strip():
                        pages_text.append(f"--- Página {i+1} ---\n{txt.strip()}")
                except Exception:
                    continue
            pdf_text = "\n\n".join(pages_text)[:30000]  # cap at 30K chars
            if not pdf_text.strip():
                raise HTTPException(status_code=400, detail="No pude leer texto del PDF (¿es una imagen escaneada sin OCR?)")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("PDF parse error")
            raise HTTPException(status_code=400, detail=f"Error procesando PDF: {str(e)[:200]}")

    # Default text when only attachment is sent
    if not text_clean and has_image:
        text_clean = "Por favor analiza esta imagen en detalle. Si es una tarea de escuela o trabajo, resuélvela paso a paso."
    elif not text_clean and has_pdf:
        text_clean = f"Por favor lee este PDF ('{pdf_name}') y dame un resumen claro con los puntos más importantes."

    # Ensure conversation
    cid = body.conversation_id
    if not cid:
        cid = f"conv_{uuid.uuid4().hex[:14]}"
        now = utcnow()
        title_src = text_clean if text_clean else "📷 Imagen"
        title = title_src[:40] + ("..." if len(title_src) > 40 else "")
        await db.conversations.insert_one({
            "conversation_id": cid,
            "user_id": user["user_id"],
            "title": title,
            "created_at": now,
            "updated_at": now,
        })
    else:
        conv = await db.conversations.find_one({"conversation_id": cid, "user_id": user["user_id"]})
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_msg = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "conversation_id": cid,
        "role": "user",
        "content": text_clean,
        "has_image": has_image,
        "created_at": utcnow(),
    }
    await db.messages.insert_one(user_msg)

    # Load prior messages (sorted ascending, so the last item is the user message we just inserted)
    history = await db.messages.find({"conversation_id": cid}, {"_id": 0}).sort("created_at", 1).to_list(200)

    # Build LlmChat with timezone-aware system prompt
    user_tz = (body.user_tz or "UTC").strip()
    # Prefer explicit `locale` if provided (from i18n), fallback to `language`
    user_lang_raw = body.locale or body.language or "es"
    user_lang = user_lang_raw.lower().split("-")[0]
    system_prompt = build_system_prompt(user_tz=user_tz, locale=user_lang)
    # Add language directive
    lang_names = {"es": "Spanish", "en": "English", "hi": "Hindi", "zh": "Chinese", "ru": "Russian"}
    if user_lang in lang_names:
        system_prompt += f"\n\nIMPORTANT: Respond ONLY in {lang_names[user_lang]}. The user prefers {lang_names[user_lang]}."

    # === CONVERSATION MEMORY ===
    # Inject prior turns so the AI remembers what the user has said in this conversation.
    # Exclude the user message we just inserted (it will be sent as the current input).
    prior_msgs = [m for m in history if m.get("message_id") != user_msg["message_id"]]
    # Keep the last 40 turns (~20 back-and-forth exchanges) and cap total chars to avoid token blowup.
    prior_msgs = prior_msgs[-40:]
    if prior_msgs:
        memory_lines = []
        total_chars = 0
        MAX_MEMORY_CHARS = 12000  # ~3k tokens, leaves room for system + current msg + reply
        # Iterate from most recent backwards so we keep recent context if we hit the cap
        kept_reverse = []
        for m in reversed(prior_msgs):
            role = (m.get("role") or "user").upper()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            # Truncate very long individual messages
            if len(content) > 1500:
                content = content[:1500] + "…"
            line = f"[{role}]: {content}"
            if total_chars + len(line) > MAX_MEMORY_CHARS:
                break
            kept_reverse.append(line)
            total_chars += len(line)
        if kept_reverse:
            memory_lines = list(reversed(kept_reverse))
            memory_block = "\n".join(memory_lines)
            system_prompt += (
                "\n\n=== HISTORIAL DE ESTA CONVERSACIÓN (memoria) ===\n"
                "A continuación está el historial COMPLETO de esta conversación con el usuario. "
                "DEBES recordar y usar TODA esta información (nombres, datos personales, preferencias, contexto, decisiones tomadas, etc.) "
                "al responder. Si el usuario pregunta algo que ya te dijo antes (su nombre, su edad, su trabajo, lo que quiere, etc.), "
                "respóndelo correctamente basándote en este historial. NO digas 'no lo sé' si la información está aquí.\n\n"
                f"{memory_block}\n"
                "=== FIN DEL HISTORIAL ===\n"
            )

    # If image present, instruct AI to use vision + homework helper mode
    if has_image:
        system_prompt += (
            "\n\n=== IMAGEN ADJUNTA ===\n"
            "El usuario adjuntó una IMAGEN. ANALÍZALA con máximo detalle.\n"
            " • Si es una TAREA ESCOLAR o problema (matemáticas, química, física, lengua, historia, programación, etc.), "
            "RESUELVE el problema completo: identifica datos, plantea solución, da pasos claros y la RESPUESTA FINAL destacada en negrita.\n"
            " • Si es un DOCUMENTO, FACTURA o RECIBO, lee TODO el texto y resume los puntos clave.\n"
            " • Si es CÓDIGO, identifica el lenguaje, explica qué hace y sugiere mejoras/correcciones.\n"
            " • Si es una PANTALLA con error técnico, diagnostica la causa y da la solución.\n"
            " • Si es un OBJETO/PRODUCTO, identifícalo, da precio aproximado, dónde comprarlo y datos útiles.\n"
            " • Sé MUY ÚTIL y CONCRETO. El usuario no quiere descripciones genéricas, quiere RESULTADOS."
        )

    # If PDF present, inject extracted text + instruct AI
    if has_pdf and pdf_text:
        # Truncate user-visible content but send full text to AI
        system_prompt += (
            f"\n\n=== PDF ADJUNTO: {pdf_name} ===\n"
            f"El usuario adjuntó un PDF. Aquí está el TEXTO COMPLETO extraído (máx 30K caracteres):\n\n"
            f"{pdf_text}\n\n"
            "INSTRUCCIONES:\n"
            " • LEE TODO el contenido del PDF.\n"
            " • Responde a la pregunta del usuario basándote en el PDF.\n"
            " • Si el usuario pide un resumen, hazlo estructurado con encabezados y bullets.\n"
            " • Si el usuario pide explicar algo del PDF, sé claro y específico.\n"
            " • Si el usuario pide convertir/transformar el contenido, hazlo (resumen ejecutivo, traducción, FAQ, etc.).\n"
            " • Si el usuario pide GENERAR un nuevo PDF basado en este, termina con [GENERATE_PDF:nombre_archivo]."
        )

    # Web search fallback for real-time info
    extra_context = ""
    if needs_web_search(text_clean):
        web_results = do_web_search(text_clean, max_results=5)
        if web_results:
            extra_context = "\n\n" + web_results
            system_prompt = system_prompt + extra_context

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=cid, system_message=system_prompt)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")

    # Send message (with optional image)
    file_contents = None
    if has_image:
        # Strip data URL prefix if present (handles "data:image/jpeg;base64,...")
        import base64 as _b64
        raw = body.image_base64 or ""
        b64 = raw.split(",", 1)[-1] if "," in raw else raw
        b64 = b64.strip()
        if not b64 or len(b64) < 100:
            raise HTTPException(status_code=400, detail="Imagen vacía o corrupta. Sube una foto JPG/PNG válida.")
        # Validate that it's actually decodable base64
        try:
            _b64.b64decode(b64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Imagen inválida. Por favor sube una foto JPG/PNG normal.")
        file_contents = [ImageContent(image_base64=b64)]

    try:
        ai_text = await chat.send_message(UserMessage(text=text_clean, file_contents=file_contents))
    except Exception as e:
        logger.exception("Chat error")
        err_msg = str(e)[:300]
        # Provide friendlier error to the user
        if "image" in err_msg.lower() or "vision" in err_msg.lower() or "base64" in err_msg.lower():
            friendly = "No pude procesar la imagen. Asegúrate de subir una foto JPG/PNG normal (no muy grande). Intenta otra vez."
        else:
            friendly = f"Error del modelo IA: {err_msg}"
        raise HTTPException(status_code=502, detail=friendly)

    ai_msg_doc = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "conversation_id": cid,
        "role": "assistant",
        "content": ai_text,
        "created_at": utcnow(),
    }
    await db.messages.insert_one(dict(ai_msg_doc))
    await db.conversations.update_one({"conversation_id": cid}, {"$set": {"updated_at": utcnow()}})
    await bump_quota(user["user_id"], "messages")
    if has_image and today_date is not None:
        await bump_chat_photo(user["user_id"], today_date, used_photos)

    return {
        "conversation_id": cid,
        "message": {
            "message_id": ai_msg_doc["message_id"],
            "conversation_id": cid,
            "role": "assistant",
            "content": ai_text,
            "created_at": iso(ai_msg_doc["created_at"]),
        },
        "history_len": len(history) + 1,
    }


# =====================
# Image generation (Nano Banana)
# =====================
@api.post("/images/generate")
async def generate_image(body: ImageGenIn, user: dict = Depends(get_current_user)):
    await check_quota(user, "images")
    hint = STYLE_HINTS.get(body.style, "")
    full_prompt = f"{body.prompt}. Style: {hint}"

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"img_{uuid.uuid4().hex[:8]}", system_message="You are an AI image generator.")
    chat.with_model("gemini", "gemini-2.5-flash-image").with_params(modalities=["image", "text"])

    try:
        _text, images = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
    except Exception as e:
        logger.exception("Image gen error")
        raise HTTPException(status_code=502, detail=f"Image generation error: {str(e)[:200]}")

    if not images:
        raise HTTPException(status_code=502, detail="No image returned")

    img = images[0]
    img_id = f"img_{uuid.uuid4().hex[:12]}"
    image_doc = {
        "image_id": img_id,
        "user_id": user["user_id"],
        "prompt": body.prompt,
        "style": body.style,
        "mime_type": img.get("mime_type", "image/png"),
        "data_base64": img["data"],
        "created_at": utcnow(),
    }
    await db.images.insert_one(image_doc)
    await bump_quota(user["user_id"], "images")
    return {
        "image_id": img_id,
        "mime_type": image_doc["mime_type"],
        "data_base64": image_doc["data_base64"],
        "prompt": body.prompt,
        "style": body.style,
    }


@api.get("/images")
async def list_images(user: dict = Depends(get_current_user)):
    imgs = await db.images.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    return [
        {**i, "created_at": iso(i["created_at"]) if isinstance(i.get("created_at"), datetime) else i.get("created_at")}
        for i in imgs
    ]


# =====================
# Voice (STT/TTS)
# =====================
@api.post("/voice/transcribe")
async def transcribe(body: TranscribeIn, user: dict = Depends(get_current_user)):
    try:
        b64 = body.audio_base64.split(",")[-1] if "," in body.audio_base64 else body.audio_base64
        audio_bytes = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio")

    ext = body.mime_type.split("/")[-1].split(";")[0] or "m4a"
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = f"audio.{ext}"
    try:
        result = openai_client.audio.transcriptions.create(model="whisper-1", file=file_obj)
        text = result.text if hasattr(result, "text") else str(result)
    except Exception as e:
        logger.exception("STT error")
        raise HTTPException(status_code=502, detail=f"Transcription error: {str(e)[:200]}")
    return {"text": text}


@api.post("/voice/tts")
async def tts(body: TTSIn, user: dict = Depends(get_current_user)):
    voice_name = VOICE_MAP.get(body.voice, "nova")
    try:
        resp = openai_client.audio.speech.create(
            model="tts-1",
            voice=voice_name,
            input=body.text,
        )
        audio_bytes = resp.read() if hasattr(resp, "read") else bytes(resp.content)
    except Exception as e:
        logger.exception("TTS error")
        raise HTTPException(status_code=502, detail=f"TTS error: {str(e)[:200]}")
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {"audio_base64": audio_b64, "mime_type": "audio/mp3", "voice": body.voice}


@api.get("/voice/voices")
async def list_voices():
    return {
        "voices": [
            {"id": "thalia",    "name": "Thalia",    "gender": "female", "description": "Cálida y amigable"},
            {"id": "jennifer",  "name": "Jennifer",  "gender": "female", "description": "Brillante y juvenil"},
            {"id": "alexander", "name": "Alexander", "gender": "male",   "description": "Profunda y serena"},
            {"id": "steven",    "name": "Steven",    "gender": "male",   "description": "Clara y profesional"},
        ]
    }


# ============================================================
# 🎙️ VOICE CONVERSATION (STT + Claude + TTS in 1 call)
# ============================================================
VOICE_PERSONAS = {
    "thalia": {
        "name": "Thalia",
        "personality": "Eres Thalia, una mujer cálida, amigable y empática. Hablas como una mejor amiga que entiende y aconseja. Usa tono cariñoso, alegre, con expresiones tipo 'mi amor', 'cariño', 'cielo'.",
    },
    "jennifer": {
        "name": "Jennifer",
        "personality": "Eres Jennifer, una mujer joven, brillante y enérgica. Hablas con entusiasmo, eres divertida y moderna. Usas expresiones jóvenes como 'súper', 'genial', 'wow'.",
    },
    "alexander": {
        "name": "Alexander",
        "personality": "Eres Alexander, un hombre maduro, sabio, sereno y profundo. Hablas con calma, autoridad y reflexión. Das consejos como un mentor experimentado.",
    },
    "steven": {
        "name": "Steven",
        "personality": "Eres Steven, un hombre profesional, claro y directo. Hablas con precisión, eficiencia y profesionalismo. Eres como un consultor ejecutivo.",
    },
}


class VoiceConverseIn(BaseModel):
    audio_base64: Optional[str] = None
    text_input: Optional[str] = None  # alternative if user types
    mime_type: str = "audio/m4a"
    voice: Literal["thalia", "jennifer", "alexander", "steven"] = "thalia"
    history: list = []  # [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]
    locale: str = "es"
    user_tz: str = "UTC"


@api.post("/voice/converse")
async def voice_converse(body: VoiceConverseIn, user: dict = Depends(get_current_user)):
    """One-shot conversational endpoint: STT -> Claude -> TTS."""
    await check_quota(user, "messages")

    # 1) Get user text (from audio or text input)
    user_text = ""
    if body.audio_base64:
        try:
            b64 = body.audio_base64.split(",", 1)[-1] if "," in body.audio_base64 else body.audio_base64
            audio_bytes = base64.b64decode(b64)
        except Exception:
            raise HTTPException(status_code=400, detail="Audio inválido")
        if not audio_bytes or len(audio_bytes) < 200:
            raise HTTPException(status_code=400, detail="Audio vacío. Graba al menos 1 segundo.")

        # Normalize mime_type → file extension that OpenAI Whisper accepts.
        # Whisper supports: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm
        SUPPORTED_AUDIO_EXTS = {"flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"}
        ext_raw = (body.mime_type or "audio/m4a").split("/")[-1].split(";")[0].strip().lower()
        if ext_raw.startswith("x-"):
            ext_raw = ext_raw[2:]
        # Map common variations (browsers / iOS sometimes send these)
        ext_map = {
            "mpeg3": "mp3", "mpga": "mpga", "mp3a": "mp3",
            "m4a": "m4a", "aac": "m4a",  # AAC files are typically m4a-compatible
            "wav": "wav", "wave": "wav",
            "ogg": "ogg", "oga": "oga", "opus": "ogg",
            "webm": "webm",
            "mp4": "mp4", "mp4a": "m4a",
            "flac": "flac",
            "3gpp": "mp4", "3gp": "mp4",  # Android can record 3gp, treat as mp4 container
            "amr": "mp4",  # not really supported, but fallback
            "quicktime": "mp4", "x-caf": "m4a", "caf": "m4a",
        }
        ext = ext_map.get(ext_raw, ext_raw)
        if ext not in SUPPORTED_AUDIO_EXTS:
            logger.warning(f"voice_converse: unsupported audio ext '{ext_raw}', defaulting to m4a")
            ext = "m4a"

        # Try the chosen extension first; if Whisper rejects it, retry once with .m4a, then .webm.
        def _transcribe_with_ext(ext_to_try: str) -> str:
            fobj = io.BytesIO(audio_bytes)
            fobj.name = f"audio.{ext_to_try}"
            stt_resp = openai_client.audio.transcriptions.create(model="whisper-1", file=fobj)
            return (stt_resp.text if hasattr(stt_resp, "text") else str(stt_resp)).strip()

        last_err: Optional[Exception] = None
        tried_exts: list = []
        for candidate in [ext, "m4a", "webm", "mp4", "wav"]:
            if candidate in tried_exts:
                continue
            tried_exts.append(candidate)
            try:
                user_text = await asyncio.to_thread(_transcribe_with_ext, candidate)
                last_err = None
                break
            except Exception as e:
                last_err = e
                logger.warning(f"voice_converse: STT failed with ext='{candidate}': {str(e)[:200]}")
                continue

        if last_err is not None:
            logger.exception("STT error in converse (all formats failed)")
            raise HTTPException(status_code=502, detail=f"Error transcribiendo: {str(last_err)[:200]}")
    elif body.text_input and body.text_input.strip():
        user_text = body.text_input.strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="No pude escuchar nada. Intenta hablar más fuerte.")

    # 2) Build persona-aware system prompt + web search if needed
    persona = VOICE_PERSONAS.get(body.voice, VOICE_PERSONAS["thalia"])
    lang_names = {"es": "Spanish", "en": "English", "hi": "Hindi", "zh": "Chinese", "ru": "Russian"}
    lang = lang_names.get((body.locale or "es").lower().split("-")[0], "Spanish")

    # Time context
    try:
        from zoneinfo import ZoneInfo
        tz_obj = ZoneInfo(body.user_tz)
        now_local = datetime.now(tz_obj)
        weekday_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][now_local.weekday()]
        time_str = now_local.strftime("%H:%M")
        date_str = now_local.strftime("%d/%m/%Y")
    except Exception:
        weekday_es, time_str, date_str = "", "", ""

    system_prompt = (
        f"{persona['personality']}\n\n"
        f"Eres parte de RAX AI (la app más avanzada de IA, creada por RASC). Esta es una conversación POR VOZ, "
        f"así que tus respuestas deben ser NATURALES, CORTAS (máximo 3-4 oraciones), CONVERSACIONALES (no uses listas, ni markdown, ni encabezados). "
        f"Habla como si estuvieras teniendo una llamada telefónica con el usuario.\n\n"
        f"Idioma: responde SIEMPRE en {lang}.\n"
        f"Fecha actual: {date_str} ({weekday_es}). Hora local: {time_str}.\n\n"
        f"=== CONOCIMIENTO TOTAL ===\n"
        f"Tienes acceso en TIEMPO REAL a internet. Sabes TODO: noticias del momento, ciencia, matemáticas, "
        f"historia, deportes, programación, medicina, finanzas, criptomonedas, cultura pop, etc. "
        f"NUNCA digas 'no tengo info actualizada' o 'no tengo acceso a internet'.\n\n"
        f"=== REGLAS CONVERSACIONALES ===\n"
        f" • Sé natural y humana. Como si hablara una persona real, no un robot.\n"
        f" • Respuestas BREVES (2-4 oraciones), excepto si el usuario pide algo largo.\n"
        f" • Si el usuario pregunta algo factual reciente, responde con confianza usando los datos del contexto web abajo.\n"
        f" • NO uses listas con guiones, NO uses markdown. Habla en prosa natural.\n"
        f" • Si te preguntan tu nombre, eres {persona['name']} de RAX AI.\n"
    )

    # Web search for current info
    if needs_web_search(user_text):
        web_results = do_web_search(user_text, max_results=4)
        if web_results:
            system_prompt += f"\n\n=== INFO WEB RECIENTE ===\n{web_results}"

    # 3) Send to Claude with conversation history
    session_id = f"voice_{user['user_id']}_{body.voice}"
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system_prompt)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")

    # Re-feed last 6 turns of history so Claude has context
    try:
        prior_text = ""
        for h in (body.history or [])[-6:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            prior_text += f"\n[{role.upper()}]: {content}"
        full_input = (prior_text + f"\n[USER]: {user_text}").strip() if prior_text else user_text
        ai_text = await chat.send_message(UserMessage(text=full_input))
    except Exception as e:
        logger.exception("Voice converse - Claude error")
        raise HTTPException(status_code=502, detail=f"Error generando respuesta: {str(e)[:200]}")

    # Trim AI response if too long (TTS gets expensive after ~500 chars)
    tts_text = ai_text.strip()
    if len(tts_text) > 800:
        tts_text = tts_text[:780] + "..."

    # 4) TTS the AI response with chosen voice
    openai_voice = VOICE_MAP.get(body.voice, "nova")
    try:
        speech = openai_client.audio.speech.create(model="tts-1", voice=openai_voice, input=tts_text)
        audio_bytes = speech.read() if hasattr(speech, "read") else bytes(speech.content)
    except Exception as e:
        logger.exception("Voice converse - TTS error")
        # Even if TTS fails, return the text response
        audio_bytes = b""

    await bump_quota(user["user_id"], "messages")

    return {
        "user_text": user_text,
        "ai_text": ai_text,
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else "",
        "mime_type": "audio/mp3",
        "voice": body.voice,
        "persona_name": persona["name"],
    }


# =====================
# Content creator
# =====================
CONTENT_PROMPTS = {
    "tiktok": "Genera 5 captions virales para TikTok sobre: {topic}. Incluye hashtags trending y emojis.",
    "facebook": "Genera 3 posts atractivos para Facebook sobre: {topic}. Tono profesional pero cercano.",
    "youtube": "Genera 10 títulos de YouTube optimizados para CTR sobre: {topic}.",
    "viral_ideas": "Dame 7 ideas de contenido viral sobre: {topic}. Explica brevemente cada una.",
    "script": "Escribe un guión corto (60 segundos) para video sobre: {topic}. Incluye gancho, desarrollo y CTA.",
    "logo_idea": "Describe 5 conceptos de logo creativos para: {topic}. Colores, formas y estilo.",
    "business_idea": "Dame 5 ideas de negocio rentables sobre: {topic}. Incluye monetización y público objetivo.",
}


@api.post("/content/generate")
async def content_generate(body: ContentGenIn, user: dict = Depends(get_current_user)):
    await check_quota(user, "messages")
    template = CONTENT_PROMPTS[body.type]
    prompt = template.format(topic=body.topic)
    if body.language == "en":
        prompt = "Reply in English. " + prompt

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"content_{uuid.uuid4().hex[:8]}",
        system_message="Eres un experto en marketing digital y creación de contenido viral.",
    )
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        text = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Content gen error: {str(e)[:200]}")
    await bump_quota(user["user_id"], "messages")
    return {"content": text, "type": body.type, "topic": body.topic}


# =====================
# File analysis
# =====================
@api.post("/files/analyze")
async def analyze_file(body: FileAnalyzeIn, user: dict = Depends(get_current_user)):
    await check_quota(user, "messages")
    b64 = body.file_base64.split(",")[-1] if "," in body.file_base64 else body.file_base64

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"file_{uuid.uuid4().hex[:8]}",
        system_message="Eres RAX AI, experta en analizar archivos, imágenes y documentos.",
    )
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        # Decode and save to temp for FileContentWithMimeType (some types need file path)
        if body.mime_type.startswith("image/"):
            file_content = ImageContent(image_base64=b64)
        else:
            # Save to /tmp
            import tempfile
            ext = body.mime_type.split("/")[-1].split(";")[0]
            fd, path = tempfile.mkstemp(suffix=f".{ext}")
            with os.fdopen(fd, "wb") as f:
                f.write(base64.b64decode(b64))
            file_content = FileContentWithMimeType(file_path=path, mime_type=body.mime_type)

        text = await chat.send_message(UserMessage(text=body.question, file_contents=[file_content]))
    except Exception as e:
        logger.exception("File analyze error")
        raise HTTPException(status_code=502, detail=f"File analyze error: {str(e)[:200]}")
    await bump_quota(user["user_id"], "messages")
    return {"analysis": text}


# =====================
# Admin
# =====================
@api.get("/admin/users")
async def admin_users(_: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    return [user_to_out(u).dict() for u in users]


@api.get("/admin/stats")
async def admin_stats(_: dict = Depends(require_admin)):
    total_users = await db.users.count_documents({})
    total_msgs = await db.messages.count_documents({})
    total_imgs = await db.images.count_documents({})
    blocked = await db.users.count_documents({"is_blocked": True})
    premium = await db.users.count_documents({"plan": "premium"})
    pro = await db.users.count_documents({"plan": "pro"})
    # estimated revenue (monthly recurring)
    revenue = premium * PLAN_PRICES["premium"] + pro * PLAN_PRICES["pro"]
    open_tickets = await db.support_tickets.count_documents({"status": "open"})
    return {
        "total_users": total_users,
        "total_messages": total_msgs,
        "total_images": total_imgs,
        "blocked_users": blocked,
        "premium_users": premium,
        "pro_users": pro,
        "estimated_revenue_usd": round(revenue, 2),
        "open_tickets": open_tickets,
        "today": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


@api.patch("/admin/users/{user_id}/plan")
async def admin_update_plan(user_id: str, body: UpdatePlanIn, _: dict = Depends(require_admin)):
    res = await db.users.update_one({"user_id": user_id}, {"$set": {"plan": body.plan}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "plan": body.plan}


@api.patch("/admin/users/{user_id}/block")
async def admin_block_user(user_id: str, body: BlockUserIn, _: dict = Depends(require_admin)):
    res = await db.users.update_one({"user_id": user_id}, {"$set": {"is_blocked": body.blocked}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "blocked": body.blocked}


@api.post("/admin/seed-admin")
async def seed_admin():
    """Idempotent admin seeding. Owner account for RASC."""
    email = "rascsarango12345@gmail.com"
    password = "Rasc2026!RaxAI"
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": hash_password(password), "is_admin": True, "is_blocked": False, "plan": "pro", "name": "RASC"}},
        )
        return {"ok": True, "seeded": False, "email": email}
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": "RASC",
        "password_hash": hash_password(password),
        "plan": "pro",
        "is_admin": True,
        "is_blocked": False,
        "is_guest": False,
        "messages_used": 0,
        "images_used": 0,
        "created_at": utcnow(),
        "provider": "email",
    })
    return {"ok": True, "seeded": True, "email": email}


# =====================
# Subscriptions (admin view)
# =====================
@api.get("/admin/subscriptions")
async def admin_subscriptions(_: dict = Depends(require_admin)):
    """Get all paying users (premium + pro) with revenue breakdown."""
    paying = await db.users.find(
        {"plan": {"$in": ["premium", "pro"]}, "is_blocked": False},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).to_list(500)

    subs = []
    for u in paying:
        price = PLAN_PRICES.get(u.get("plan"), 0)
        subs.append({
            "user_id": u["user_id"],
            "email": u["email"],
            "name": u.get("name", u["email"].split("@")[0]),
            "plan": u["plan"],
            "monthly_price_usd": price,
            "messages_used": u.get("messages_used", 0),
            "images_used": u.get("images_used", 0),
            "since": iso(u["created_at"]) if isinstance(u.get("created_at"), datetime) else u.get("created_at"),
        })
    total_monthly = sum(s["monthly_price_usd"] for s in subs)
    return {
        "subscriptions": subs,
        "total_active": len(subs),
        "monthly_revenue_usd": round(total_monthly, 2),
        "annual_projection_usd": round(total_monthly * 12, 2),
    }


# =====================
# Theme customization
# =====================
DEFAULT_THEME = {
    "primary_color": "#00E5FF",
    "accent_color": "#7C4DFF",
    "success_color": "#00FF66",
    "background_color": "#050505",
    "preset": "neon_blue",
}


@api.get("/theme")
async def get_theme():
    doc = await db.settings.find_one({"key": "theme"}, {"_id": 0})
    if not doc:
        return DEFAULT_THEME
    return doc.get("value", DEFAULT_THEME)


class ThemeIn(BaseModel):
    primary_color: str = "#00E5FF"
    accent_color: str = "#7C4DFF"
    success_color: str = "#00FF66"
    background_color: str = "#050505"
    preset: str = "custom"


@api.put("/admin/theme")
async def admin_set_theme(body: ThemeIn, _: dict = Depends(require_admin)):
    await db.settings.update_one(
        {"key": "theme"},
        {"$set": {"key": "theme", "value": body.dict(), "updated_at": utcnow()}},
        upsert=True,
    )
    return {"ok": True, "theme": body.dict()}


SUPPORT_BOT_SYSTEM = (
    "Eres el asistente de soporte automático de RAX AI (creada por RASC). Resuelves problemas básicos de clientes "
    "de forma cálida, rápida y profesional en español. Tu objetivo es ayudar al cliente sin esperar a un humano. "
    "Conoces estos datos clave de la app:\n"
    "- Planes: Gratis (30 msgs/5 imgs), Premium $5.99/mes (1,000 msgs/200 imgs), Pro $9.99/mes (ilimitado).\n"
    "- Pagos vía Stripe (tarjetas, Apple Pay, Google Pay). El usuario puede cancelar su suscripción desde su Perfil → 'Cancelar suscripción' y se le devuelve el dinero al instante.\n"
    "- Voces: Sofía y Luna (mujer), Diego y Alex (hombre).\n"
    "- Imágenes: 6 estilos (realista, anime, futurista, gamer, caricatura, cinemático).\n"
    "- Idiomas soportados: español, inglés y muchos más.\n"
    "- Cuenta admin: rascsarango12345@gmail.com (RASC).\n\n"
    "Reglas:\n"
    "1. Sé conciso (2-5 oraciones).\n"
    "2. Si el problema es complejo (cobro duplicado, error técnico grave, queja personalizada, devolución de dinero), responde con tu mejor intento y termina con: '👤 Si necesitas ayuda más personalizada, escribe \"agente\" y RASC te atenderá personalmente.'\n"
    "3. Si el usuario menciona 'agente', 'humano', 'persona real', 'RASC' o 'hablar con alguien', responde solamente: 'Perfecto. Voy a transferir tu caso a RASC. Te responderá en cuanto vea tu ticket. 🛡️'\n"
    "4. Si es saludo o pregunta vaga, sé amigable y pide más detalles.\n"
    "5. Firma siempre como '— Bot RAX AI 🤖'."
)

HUMAN_REQUEST_KEYWORDS = ["agente", "humano", "persona", "rasc", "hablar con alguien", "hablar con un humano", "real person"]


async def generate_bot_reply(ticket_subject: str, user_message: str, language: str = "es") -> str:
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"support_bot_{uuid.uuid4().hex[:8]}",
            system_message=SUPPORT_BOT_SYSTEM,
        )
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
        prompt = f"Asunto del ticket: {ticket_subject}\nCliente: {user_message}\n\nRespuesta:"
        return await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        logger.exception("Bot reply error")
        return "Hola 👋 Estoy procesando tu solicitud. Si tu problema es urgente o complejo, escribe 'agente' y RASC te atenderá personalmente. — Bot RAX AI 🤖"


def detects_human_request(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in HUMAN_REQUEST_KEYWORDS)


# =====================
# Support tickets
# =====================
class TicketCreateIn(BaseModel):
    subject: str
    message: str


class TicketReplyIn(BaseModel):
    message: str


@api.post("/support/tickets")
async def create_ticket(body: TicketCreateIn, user: dict = Depends(get_current_user)):
    tid = f"ticket_{uuid.uuid4().hex[:12]}"
    now = utcnow()
    doc = {
        "ticket_id": tid,
        "user_id": user["user_id"],
        "user_email": user["email"],
        "user_name": user.get("name", user["email"].split("@")[0]),
        "subject": body.subject[:120],
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "last_sender": "user",
    }
    await db.support_tickets.insert_one(dict(doc))
    msg = {
        "ticket_message_id": f"tm_{uuid.uuid4().hex[:10]}",
        "ticket_id": tid,
        "sender_role": "user",
        "sender_id": user["user_id"],
        "sender_name": user.get("name", "Usuario"),
        "message": body.message,
        "created_at": now,
    }
    await db.support_messages.insert_one(dict(msg))

    # Auto bot reply
    try:
        bot_text = await generate_bot_reply(body.subject, body.message)
        bot_msg = {
            "ticket_message_id": f"tm_{uuid.uuid4().hex[:10]}",
            "ticket_id": tid,
            "sender_role": "bot",
            "sender_id": "bot",
            "sender_name": "Bot RAX AI",
            "message": bot_text,
            "created_at": utcnow(),
        }
        await db.support_messages.insert_one(dict(bot_msg))
        # Set last_sender to bot and update timestamps
        await db.support_tickets.update_one(
            {"ticket_id": tid},
            {"$set": {"updated_at": utcnow(), "last_sender": "bot", "bot_handling": True}},
        )
    except Exception as e:
        logger.warning(f"Bot reply skipped: {e}")

    return {"ticket_id": tid, "status": "open", "created_at": iso(now)}


@api.get("/support/tickets")
async def list_tickets(user: dict = Depends(get_current_user)):
    is_admin = user.get("is_admin") or (user["email"] in ADMIN_EMAILS)
    q = {} if is_admin else {"user_id": user["user_id"]}
    tickets = await db.support_tickets.find(q, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return [
        {
            **t,
            "created_at": iso(t["created_at"]) if isinstance(t.get("created_at"), datetime) else t.get("created_at"),
            "updated_at": iso(t["updated_at"]) if isinstance(t.get("updated_at"), datetime) else t.get("updated_at"),
        }
        for t in tickets
    ]


@api.get("/support/tickets/{tid}")
async def get_ticket(tid: str, user: dict = Depends(get_current_user)):
    is_admin = user.get("is_admin") or (user["email"] in ADMIN_EMAILS)
    t = await db.support_tickets.find_one({"ticket_id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not is_admin and t["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    msgs = await db.support_messages.find({"ticket_id": tid}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return {
        "ticket": {
            **t,
            "created_at": iso(t["created_at"]) if isinstance(t.get("created_at"), datetime) else t.get("created_at"),
            "updated_at": iso(t["updated_at"]) if isinstance(t.get("updated_at"), datetime) else t.get("updated_at"),
        },
        "messages": [
            {**m, "created_at": iso(m["created_at"]) if isinstance(m.get("created_at"), datetime) else m.get("created_at")}
            for m in msgs
        ],
    }


@api.post("/support/tickets/{tid}/reply")
async def reply_ticket(tid: str, body: TicketReplyIn, user: dict = Depends(get_current_user)):
    is_admin = user.get("is_admin") or (user["email"] in ADMIN_EMAILS)
    t = await db.support_tickets.find_one({"ticket_id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not is_admin and t["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    role = "admin" if is_admin else "user"
    now = utcnow()
    msg = {
        "ticket_message_id": f"tm_{uuid.uuid4().hex[:10]}",
        "ticket_id": tid,
        "sender_role": role,
        "sender_id": user["user_id"],
        "sender_name": user.get("name", "RASC" if is_admin else "Usuario"),
        "message": body.message,
        "created_at": now,
    }
    await db.support_messages.insert_one(dict(msg))

    # Determine bot state: if user asks for human, disable bot
    bot_handling = t.get("bot_handling", True)
    if role == "user" and detects_human_request(body.message):
        bot_handling = False

    new_status = "open" if role == "user" else "answered"
    await db.support_tickets.update_one(
        {"ticket_id": tid},
        {"$set": {"updated_at": now, "last_sender": role, "status": new_status, "bot_handling": bot_handling}},
    )

    # If user replied and bot still handling, generate bot response
    bot_reply_dict = None
    if role == "user" and bot_handling:
        try:
            bot_text = await generate_bot_reply(t.get("subject", ""), body.message)
            bot_msg = {
                "ticket_message_id": f"tm_{uuid.uuid4().hex[:10]}",
                "ticket_id": tid,
                "sender_role": "bot",
                "sender_id": "bot",
                "sender_name": "Bot RAX AI",
                "message": bot_text,
                "created_at": utcnow(),
            }
            await db.support_messages.insert_one(dict(bot_msg))
            await db.support_tickets.update_one(
                {"ticket_id": tid},
                {"$set": {"updated_at": utcnow(), "last_sender": "bot"}},
            )
            bot_reply_dict = {
                "ticket_message_id": bot_msg["ticket_message_id"],
                "ticket_id": tid,
                "sender_role": "bot",
                "sender_name": "Bot RAX AI",
                "message": bot_text,
                "created_at": iso(bot_msg["created_at"]),
            }
        except Exception as e:
            logger.warning(f"Bot follow-up failed: {e}")
    elif role == "user" and not bot_handling:
        # User just escalated - add system notice
        notice_text = "✋ Tu caso ha sido escalado a RASC. Te responderá personalmente en cuanto pueda. 🛡️"
        notice_msg = {
            "ticket_message_id": f"tm_{uuid.uuid4().hex[:10]}",
            "ticket_id": tid,
            "sender_role": "bot",
            "sender_id": "bot",
            "sender_name": "Bot RAX AI",
            "message": notice_text,
            "created_at": utcnow(),
        }
        # only insert if user just requested human (escalation transition)
        if t.get("bot_handling", True):
            await db.support_messages.insert_one(dict(notice_msg))
            bot_reply_dict = {
                "ticket_message_id": notice_msg["ticket_message_id"],
                "ticket_id": tid,
                "sender_role": "bot",
                "sender_name": "Bot RAX AI",
                "message": notice_text,
                "created_at": iso(notice_msg["created_at"]),
            }

    return {
        "ticket_message_id": msg["ticket_message_id"],
        "ticket_id": tid,
        "sender_role": role,
        "sender_name": msg["sender_name"],
        "message": body.message,
        "created_at": iso(now),
        "bot_reply": bot_reply_dict,
        "bot_handling": bot_handling,
    }


class TicketStatusIn(BaseModel):
    status: Literal["open", "answered", "closed"]


@api.patch("/admin/support/tickets/{tid}/status")
async def admin_set_ticket_status(tid: str, body: TicketStatusIn, _: dict = Depends(require_admin)):
    res = await db.support_tickets.update_one({"ticket_id": tid}, {"$set": {"status": body.status, "updated_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True, "status": body.status}


# =====================
# Game (word scramble) for distraction
# =====================
WORD_BANK = [
    # (word, category, hint)
    ("INTELIGENCIA", "Tecnología", "Capacidad de razonar y aprender"),
    ("FUTURO", "Tiempo", "Lo que viene después de ahora"),
    ("MUSICA", "Arte", "Sonidos organizados que emocionan"),
    ("OCEANO", "Naturaleza", "Gran masa de agua salada"),
    ("MONTANA", "Naturaleza", "Elevación natural del terreno"),
    ("LIBERTAD", "Concepto", "Capacidad de actuar sin restricciones"),
    ("AMISTAD", "Sentimiento", "Vínculo afectivo desinteresado"),
    ("UNIVERSO", "Ciencia", "Todo lo que existe"),
    ("CHOCOLATE", "Comida", "Delicia hecha de cacao"),
    ("RELAMPAGO", "Naturaleza", "Descarga eléctrica en una tormenta"),
    ("AVENTURA", "Vida", "Experiencia emocionante e inesperada"),
    ("BIBLIOTECA", "Lugar", "Edificio lleno de libros"),
    ("AURORA", "Naturaleza", "Luz natural del amanecer"),
    ("MARIPOSA", "Animal", "Insecto colorido que vuela"),
    ("VOLCAN", "Naturaleza", "Montaña que expulsa lava"),
    ("ESPERANZA", "Sentimiento", "Confianza en lograr algo deseado"),
    ("GUITARRA", "Música", "Instrumento de seis cuerdas"),
    ("PLANETA", "Espacio", "Cuerpo celeste que orbita una estrella"),
    ("MISTERIO", "Concepto", "Algo difícil de comprender"),
    ("LEYENDA", "Historia", "Relato tradicional sobre hechos sorprendentes"),
    ("DIAMANTE", "Mineral", "Piedra preciosa muy dura y brillante"),
    ("SUBMARINO", "Vehículo", "Nave que viaja bajo el agua"),
    ("ESTRELLA", "Espacio", "Cuerpo celeste que brilla con luz propia"),
    ("CASCADA", "Naturaleza", "Caída de agua desde altura"),
    ("FANTASMA", "Misterio", "Espíritu de un muerto según las leyendas"),
]


def scramble_word(word: str) -> str:
    import random
    letters = list(word)
    for _ in range(20):
        random.shuffle(letters)
        s = "".join(letters)
        if s != word:
            return s
    return "".join(letters)


@api.get("/game/word")
async def game_word(user: dict = Depends(get_current_user)):
    import random
    word, category, hint = random.choice(WORD_BANK)
    scrambled = scramble_word(word)
    return {
        "game_id": f"g_{uuid.uuid4().hex[:10]}",
        "scrambled": scrambled,
        "length": len(word),
        "category": category,
        "hint": hint,
        "answer_hash": hash_password(word),  # used for verification
    }


class GameCheckIn(BaseModel):
    answer: str
    answer_hash: str


@api.post("/game/check")
async def game_check(body: GameCheckIn, user: dict = Depends(get_current_user)):
    correct = verify_password(body.answer.strip().upper(), body.answer_hash)
    if correct:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$inc": {"game_wins": 1}},
        )
    return {"correct": correct}


@api.get("/game/leaderboard")
async def game_leaderboard():
    top = await db.users.find({"game_wins": {"$gt": 0}}, {"_id": 0, "name": 1, "game_wins": 1, "avatar_emoji": 1}).sort("game_wins", -1).limit(10).to_list(10)
    return top


# =====================
# Stripe Subscriptions
# =====================
class CheckoutIn(BaseModel):
    plan: Literal["premium", "pro"]
    origin_url: str  # Frontend origin to redirect back to


async def get_stripe_price_id(plan: str) -> str:
    doc = await db.settings.find_one({"key": "stripe_prices"}, {"_id": 0})
    if not doc:
        # Try bootstrapping now
        await bootstrap_stripe_catalog()
        doc = await db.settings.find_one({"key": "stripe_prices"}, {"_id": 0})
    catalog = doc.get("value", {}) if doc else {}
    info = catalog.get(plan)
    if not info or not info.get("price_id"):
        raise HTTPException(status_code=500, detail=f"Stripe price for {plan} not configured")
    return info["price_id"]


@api.get("/stripe/config")
async def stripe_config():
    return {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "configured": bool(STRIPE_SECRET_KEY),
    }


@api.post("/stripe/create-checkout-session")
async def create_checkout(body: CheckoutIn, user: dict = Depends(get_current_user)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe no configurado")
    if user.get("is_guest"):
        raise HTTPException(status_code=400, detail="Crea una cuenta antes de suscribirte")
    price_id = await get_stripe_price_id(body.plan)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/premium?session_id={{CHECKOUT_SESSION_ID}}&status=success"
    cancel_url = f"{origin}/premium?status=cancel"
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user["email"],
            client_reference_id=user["user_id"],
            subscription_data={"metadata": {"app_user_id": user["user_id"], "plan": body.plan}},
            metadata={"app_user_id": user["user_id"], "plan": body.plan},
            allow_promotion_codes=True,
        )
    except Exception as e:
        logger.exception("Stripe checkout error")
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)[:200]}")
    # Save payment intent record
    await db.payments.insert_one({
        "session_id": session.id,
        "user_id": user["user_id"],
        "email": user["email"],
        "plan": body.plan,
        "status": "pending",
        "created_at": utcnow(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


@api.get("/stripe/session-status")
async def stripe_session_status(session_id: str, user: dict = Depends(get_current_user)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe no configurado")
    try:
        s = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)[:120]}")
    plan = (s.metadata or {}).get("plan") if hasattr(s, "metadata") else None
    paid = s.payment_status == "paid"
    if paid and plan and (s.metadata.get("app_user_id") == user["user_id"]):
        # Upgrade as a fallback (webhook should also do this)
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"plan": plan}})
        await db.payments.update_one({"session_id": session_id}, {"$set": {"status": "paid", "completed_at": utcnow()}})
    return {"status": s.status, "payment_status": s.payment_status, "plan": plan, "paid": paid}


@api.post("/support/tickets/{tid}/request-human")
async def request_human(tid: str, user: dict = Depends(get_current_user)):
    t = await db.support_tickets.find_one({"ticket_id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if t["user_id"] != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.support_tickets.update_one({"ticket_id": tid}, {"$set": {"bot_handling": False, "updated_at": utcnow()}})
    notice = "✋ Has solicitado hablar con un agente. RASC te responderá pronto. 🛡️"
    msg = {
        "ticket_message_id": f"tm_{uuid.uuid4().hex[:10]}",
        "ticket_id": tid,
        "sender_role": "bot",
        "sender_id": "bot",
        "sender_name": "Bot RAX AI",
        "message": notice,
        "created_at": utcnow(),
    }
    await db.support_messages.insert_one(dict(msg))
    return {"ok": True, "bot_handling": False}


@api.post("/stripe/cancel-subscription")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    if user.get("plan") in (None, "free"):
        raise HTTPException(status_code=400, detail="No tienes una suscripción activa")
    sub_id = user.get("stripe_subscription_id")
    refund_info = {"refunded": False, "amount_usd": 0.0}

    if sub_id:
        try:
            stripe.Subscription.cancel(sub_id)
        except Exception as e:
            logger.warning(f"Subscription cancel error: {e}")
        try:
            invoices = stripe.Invoice.list(subscription=sub_id, limit=1)
            if invoices.data:
                latest = invoices.data[0]
                pi = latest.get("payment_intent")
                ch = latest.get("charge")
                if pi:
                    refund = stripe.Refund.create(payment_intent=pi)
                    refund_info = {"refunded": True, "amount_usd": (refund.amount or 0) / 100.0, "refund_id": refund.id}
                elif ch:
                    refund = stripe.Refund.create(charge=ch)
                    refund_info = {"refunded": True, "amount_usd": (refund.amount or 0) / 100.0, "refund_id": refund.id}
        except Exception as e:
            logger.warning(f"Refund error: {e}")
            refund_info = {"refunded": False, "error": str(e)[:200]}

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"plan": "free"}, "$unset": {"stripe_subscription_id": ""}},
    )

    await db.cancellations.insert_one({
        "cancellation_id": f"can_{uuid.uuid4().hex[:10]}",
        "user_id": user["user_id"],
        "email": user["email"],
        "previous_plan": user.get("plan"),
        "subscription_id": sub_id,
        "refund_info": refund_info,
        "created_at": utcnow(),
    })

    return {
        "ok": True,
        "previous_plan": user.get("plan"),
        "new_plan": "free",
        "refund": refund_info,
        "message": "Suscripción cancelada. Si había un cobro reciente, el reembolso aparecerá en 5-10 días hábiles.",
    }


@api.get("/admin/cancellations")
async def admin_cancellations(_: dict = Depends(require_admin)):
    items = await db.cancellations.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [
        {**c, "created_at": iso(c["created_at"]) if isinstance(c.get("created_at"), datetime) else c.get("created_at")}
        for c in items
    ]


@api.get("/stripe/payments")
async def admin_payments(_: dict = Depends(require_admin)):
    payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    paid = [p for p in payments if p.get("status") == "paid"]
    total_paid = 0.0
    for p in paid:
        total_paid += PLAN_PRICES.get(p.get("plan", "free"), 0)
    return {
        "payments": [
            {**p, "created_at": iso(p["created_at"]) if isinstance(p.get("created_at"), datetime) else p.get("created_at"),
             "completed_at": iso(p["completed_at"]) if isinstance(p.get("completed_at"), datetime) else p.get("completed_at")}
            for p in payments
        ],
        "total_paid_count": len(paid),
        "lifetime_revenue_usd": round(total_paid, 2),
    }


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    event = None
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=sig, secret=STRIPE_WEBHOOK_SECRET)
        else:
            # No signature secret configured yet - parse trusted payload (configure in production)
            import json as _json
            event = _json.loads(payload.decode("utf-8"))
            logger.warning("Stripe webhook received without signature verification")
    except Exception as e:
        logger.error(f"Webhook construct error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")

    etype = event.get("type") if isinstance(event, dict) else event["type"]
    data_object = (event.get("data", {}).get("object") if isinstance(event, dict) else event["data"]["object"]) or {}

    if etype == "checkout.session.completed":
        meta = data_object.get("metadata") or {}
        app_user_id = meta.get("app_user_id")
        plan = meta.get("plan")
        if app_user_id and plan in ("premium", "pro"):
            await db.users.update_one(
                {"user_id": app_user_id},
                {"$set": {
                    "plan": plan,
                    "stripe_customer_id": data_object.get("customer"),
                    "stripe_subscription_id": data_object.get("subscription"),
                }},
            )
            await db.payments.update_one(
                {"session_id": data_object.get("id")},
                {"$set": {"status": "paid", "completed_at": utcnow()}},
                upsert=False,
            )
            logger.info("User %s upgraded to %s via Stripe", app_user_id, plan)
    elif etype == "customer.subscription.deleted":
        meta = data_object.get("metadata") or {}
        app_user_id = meta.get("app_user_id")
        if app_user_id:
            await db.users.update_one({"user_id": app_user_id}, {"$set": {"plan": "free"}})
            logger.info("User %s subscription canceled - reverted to free", app_user_id)
    elif etype == "invoice.payment_succeeded":
        # Renewal - ensure plan is still set
        sub_id = data_object.get("subscription")
        if sub_id:
            try:
                sub = stripe.Subscription.retrieve(sub_id)
                meta = sub.metadata or {}
                app_user_id = meta.get("app_user_id")
                plan = meta.get("plan")
                if app_user_id and plan:
                    await db.users.update_one({"user_id": app_user_id}, {"$set": {"plan": plan}})
            except Exception as e:
                logger.warning(f"Subscription retrieve failed: {e}")

    return {"received": True}


# ============================================================
# 💎 RevenueCat — Apple In-App Purchases (iOS)
# Web/Android keep using Stripe via the endpoints above.
# - POST /api/revenuecat/sync     → authenticated user reports their new plan after a purchase
# - POST /api/revenuecat/webhook  → RevenueCat server-to-server notifications (no JWT auth, uses Bearer secret)
# ============================================================
REVENUECAT_WEBHOOK_SECRET = os.getenv("REVENUECAT_WEBHOOK_SECRET", "")


class RevenueCatSyncIn(BaseModel):
    app_user_id: str
    plan: Literal["free", "premium", "pro"]
    entitlements: Optional[List[str]] = None


def _derive_plan_from_entitlements(entitlements: Any) -> str:
    """Given the entitlements payload from RevenueCat, return our internal plan name."""
    keys: List[str] = []
    if isinstance(entitlements, dict):
        active = entitlements.get("active") if "active" in entitlements else entitlements
        if isinstance(active, dict):
            keys = list(active.keys())
        elif isinstance(active, list):
            keys = list(active)
    elif isinstance(entitlements, list):
        keys = list(entitlements)
    keys_lower = [str(k).lower() for k in keys]
    if "pro" in keys_lower:
        return "pro"
    if "premium" in keys_lower:
        return "premium"
    return "free"


def _plan_from_product_id(product_id: Optional[str]) -> Optional[str]:
    """Fallback: map App Store product_id → internal plan."""
    if not product_id:
        return None
    pid = product_id.lower()
    if "pro" in pid:
        return "pro"
    if "premium" in pid:
        return "premium"
    return None


@api.post("/revenuecat/sync")
async def revenuecat_sync(body: RevenueCatSyncIn, user: dict = Depends(get_current_user)):
    """Client-driven sync: called by the iOS app after a successful purchase/restore.
    The authenticated user can only update their OWN plan (security check).
    """
    if body.app_user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="app_user_id does not match the authenticated user")

    new_plan = body.plan
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"plan": new_plan, "iap_provider": "revenuecat", "iap_updated_at": utcnow()}},
    )
    try:
        await db.revenuecat_events.insert_one({
            "event_id": f"sync_{uuid.uuid4().hex[:12]}",
            "source": "client_sync",
            "user_id": user["user_id"],
            "plan": new_plan,
            "entitlements": body.entitlements or [],
            "created_at": utcnow(),
        })
    except Exception:
        pass
    logger.info(f"RevenueCat sync - user={user['user_id']} -> plan={new_plan}")
    return {"status": "ok", "plan": new_plan}


@app.post("/api/revenuecat/webhook", include_in_schema=False)
async def revenuecat_webhook(request: Request):
    """RevenueCat server-to-server webhook.
    Configure in RevenueCat Dashboard -> Project settings -> Integrations -> Webhooks:
        URL:    https://<your-backend>/api/revenuecat/webhook
        Header: Authorization: Bearer <REVENUECAT_WEBHOOK_SECRET>
    """
    if not REVENUECAT_WEBHOOK_SECRET:
        logger.error("RevenueCat webhook hit but REVENUECAT_WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    expected = f"Bearer {REVENUECAT_WEBHOOK_SECRET}"
    if auth_header.strip() != expected.strip():
        logger.warning("RevenueCat webhook: invalid Authorization header")
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event") or {}
    event_type = (event.get("type") or "UNKNOWN").upper()
    app_user_id = event.get("app_user_id") or event.get("original_app_user_id")
    aliases = event.get("aliases") or []
    product_id = event.get("product_id")

    candidates = [c for c in [app_user_id, *aliases] if c]

    entitlements = event.get("entitlement_ids") or event.get("entitlements") or {}
    new_plan = _derive_plan_from_entitlements(entitlements)

    downgrade_events = {"CANCELLATION", "EXPIRATION", "SUBSCRIPTION_PAUSED", "REFUND"}
    upgrade_events = {"INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE", "UNCANCELLATION", "NON_RENEWING_PURCHASE"}

    if new_plan == "free" and event_type in upgrade_events:
        guessed = _plan_from_product_id(product_id)
        if guessed:
            new_plan = guessed

    if event_type in downgrade_events:
        new_plan = "free"

    try:
        await db.revenuecat_events.insert_one({
            "event_id": event.get("id") or f"rc_{uuid.uuid4().hex[:12]}",
            "source": "webhook",
            "event_type": event_type,
            "app_user_id": app_user_id,
            "aliases": aliases,
            "product_id": product_id,
            "derived_plan": new_plan,
            "raw": event,
            "created_at": utcnow(),
        })
    except Exception as e:
        logger.warning(f"Failed to persist RC event: {e}")

    updated = 0
    for uid in candidates:
        res = await db.users.update_one(
            {"user_id": uid},
            {"$set": {"plan": new_plan, "iap_provider": "revenuecat", "iap_updated_at": utcnow()}},
        )
        updated += res.modified_count
        if res.matched_count > 0:
            break

    logger.info(
        f"RevenueCat webhook - event={event_type} user={app_user_id} product={product_id} -> plan={new_plan} (updated={updated})"
    )

    if event_type == "TEST":
        return {"status": "ok", "note": "Test webhook received successfully"}

    return {"status": "ok", "plan": new_plan, "event_type": event_type, "updated": updated}




@api.get("/stripe/payments")
async def admin_payments(_: dict = Depends(require_admin)):
    payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    paid = [p for p in payments if p.get("status") == "paid"]
    total_paid = 0.0
    for p in paid:
        total_paid += PLAN_PRICES.get(p.get("plan", "free"), 0)
    return {
        "payments": [
            {**p, "created_at": iso(p["created_at"]) if isinstance(p.get("created_at"), datetime) else p.get("created_at"),
             "completed_at": iso(p["completed_at"]) if isinstance(p.get("completed_at"), datetime) else p.get("completed_at")}
            for p in payments
        ],
        "total_paid_count": len(paid),
        "lifetime_revenue_usd": round(total_paid, 2),
    }


app.include_router(api)


# ============================================================
# NEW FEATURES: Cámara Mágica, Diario Inteligente, Roast, Personal Shopper
# ============================================================
new_features = APIRouter(prefix="/api")
# Daily-reset feature quotas (free=3/day, premium=30/day, pro=unlimited per feature)
FEATURE_DAILY_LIMITS = {"free": 3, "premium": 30, "pro": 99999}


async def check_feature_quota(user: dict, feature: str):
    """Generic daily-reset quota for new features (lens, roast, journal, shopper)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key_date = f"{feature}_date"
    key_used = f"{feature}_today"
    last_date = user.get(key_date)
    used = user.get(key_used, 0) if last_date == today else 0
    limit = FEATURE_DAILY_LIMITS.get(user.get("plan", "free"), 3)
    if used >= limit:
        raise HTTPException(status_code=402, detail=f"Límite diario de {limit} alcanzado para {feature}. Mejora tu plan.")
    return today, used


async def bump_feature_quota(user_id: str, feature: str, today: str, used: int):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {f"{feature}_date": today, f"{feature}_today": used + 1}},
    )


# ---------- 📸 Cámara Mágica (AR Lens) ----------
class LensIn(BaseModel):
    image_base64: str
    locale: str = "es"


@new_features.post("/lens/scan")
async def lens_scan(body: LensIn, user: dict = Depends(get_current_user)):
    today, used = await check_feature_quota(user, "lens")
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="Imagen requerida")
    lang_names = {"es": "Spanish", "en": "English", "hi": "Hindi", "zh": "Chinese", "ru": "Russian"}
    lang = lang_names.get((body.locale or "es").lower().split("-")[0], "Spanish")
    system = (
        f"Eres RAX Lens, el escáner mágico de objetos del mundo. Cuando recibas una imagen, identifica al objeto "
        f"principal y devuelve información estructurada en {lang}. SIEMPRE responde en formato Markdown con estas secciones (omite las que no apliquen):\n\n"
        "## 🔍 ¿Qué es?\n[Nombre del objeto en una línea]\n\n"
        "## 📖 Descripción\n[2-3 oraciones explicando]\n\n"
        "## 💰 Precio estimado\n[rango USD]\n\n"
        "## 🌍 Cómo se llama en otros idiomas\n- 🇺🇸 English: ...\n- 🇪🇸 Español: ...\n- 🇫🇷 Français: ...\n- 🇨🇳 中文: ...\n- 🇯🇵 日本語: ...\n\n"
        "## 💡 Datos curiosos\n- ...\n- ...\n\n"
        "## ✅ Recomendaciones / Cuidados / Cómo usarlo\n[según aplique]\n\n"
        "Si es comida, agrega recetas. Si es planta, cuidados. Si es ropa/marca, dónde comprarla. Si es animal, info de la especie."
    )
    b64 = body.image_base64.split(",")[-1] if "," in body.image_base64 else body.image_base64
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"lens_{user['user_id']}", system_message=system)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    msg = UserMessage(text="Analiza esta imagen como RAX Lens.", file_contents=[ImageContent(image_base64=b64)])
    try:
        result = await chat.send_message(msg)
    except Exception as e:
        logger.error(f"Lens error: {e}")
        raise HTTPException(status_code=500, detail="Error al analizar imagen")
    await bump_feature_quota(user["user_id"], "lens", today, used)
    return {"result": result, "used_today": used + 1, "limit": FEATURE_DAILY_LIMITS.get(user.get("plan", "free"), 3)}


# ---------- 🔥 Modo Roast ----------
class RoastIn(BaseModel):
    image_base64: str
    intensity: Literal["suave", "medio", "brutal"] = "medio"
    locale: str = "es"


@new_features.post("/roast")
async def roast_generate(body: RoastIn, user: dict = Depends(get_current_user)):
    today, used = await check_feature_quota(user, "roast")
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="Imagen requerida")
    lang_names = {"es": "Spanish", "en": "English", "hi": "Hindi", "zh": "Chinese", "ru": "Russian"}
    lang = lang_names.get((body.locale or "es").lower().split("-")[0], "Spanish")
    intensity_map = {
        "suave": "humor amable y bromas tipo papá, sin ofender",
        "medio": "humor más mordaz pero respetuoso, tipo amigo cercano roasteándote",
        "brutal": "humor brutal pero ingenioso, sin discriminar por raza/género/religión",
    }
    system = (
        f"Eres RAX Roast Master, el comediante más ingenioso del mundo. Cuando recibas una foto de una persona, "
        f"escribe un ROAST gracioso, original y CREATIVO en {lang}. Nivel: {intensity_map.get(body.intensity, 'medio')}. "
        "REGLAS: 5-7 líneas máximo, debe ser GRACIOSO, observa detalles (ropa, pose, fondo, expresión), usa metáforas creativas, "
        "termina con un cumplido sarcástico que sea casi un halago. Si es una foto sin persona, roastea el objeto/escena. "
        "NUNCA insultos sobre peso, raza, género, orientación, religión o discapacidad. Solo cosas circunstanciales. "
        "Usa emojis con gracia (1-2 máximo)."
    )
    b64 = body.image_base64.split(",")[-1] if "," in body.image_base64 else body.image_base64
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"roast_{user['user_id']}", system_message=system)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    msg = UserMessage(text=f"Roastea esta imagen con intensidad {body.intensity}.", file_contents=[ImageContent(image_base64=b64)])
    try:
        result = await chat.send_message(msg)
    except Exception as e:
        logger.error(f"Roast error: {e}")
        raise HTTPException(status_code=500, detail="Error generando roast")
    await bump_feature_quota(user["user_id"], "roast", today, used)
    return {"roast": result, "intensity": body.intensity, "used_today": used + 1, "limit": FEATURE_DAILY_LIMITS.get(user.get("plan", "free"), 3)}


# ---------- 🌙 Diario Inteligente ----------
class JournalEntryIn(BaseModel):
    content: str
    mood: Literal["feliz", "triste", "ansioso", "neutral", "motivado", "enojado", "agradecido"] = "neutral"
    locale: str = "es"


@new_features.post("/journal/entry")
async def journal_add(body: JournalEntryIn, user: dict = Depends(get_current_user)):
    if not body.content or len(body.content.strip()) < 3:
        raise HTTPException(status_code=400, detail="Escribe al menos 3 caracteres")
    entry_id = f"journ_{uuid.uuid4().hex[:14]}"
    now = utcnow()
    today = now.strftime("%Y-%m-%d")
    # Generate AI insight on this entry
    lang_names = {"es": "Spanish", "en": "English", "hi": "Hindi", "zh": "Chinese", "ru": "Russian"}
    lang = lang_names.get((body.locale or "es").lower().split("-")[0], "Spanish")
    system = (
        f"Eres RAX, el mejor amigo IA del usuario. Te acaba de compartir una entrada de su diario personal. "
        f"Responde en {lang} con: una reflexión empática (2-3 oraciones), 1 pregunta poderosa para profundizar, "
        f"y 1 acción concreta que pueda tomar hoy. Tono cálido, cercano, no robótico. Máximo 5-6 líneas total."
    )
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"journal_{user['user_id']}", system_message=system)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        insight = await chat.send_message(UserMessage(text=f"Estado de ánimo: {body.mood}\nEntrada: {body.content}"))
    except Exception:
        insight = "Gracias por compartir. Sigue escribiendo, te ayuda a procesar y crecer. 💙"
    doc = {
        "entry_id": entry_id,
        "user_id": user["user_id"],
        "content": body.content.strip(),
        "mood": body.mood,
        "ai_insight": insight,
        "date": today,
        "created_at": now,
    }
    await db.journal_entries.insert_one(doc)
    return {**doc, "_id": str(doc.get("_id", "")), "created_at": iso(now)}


@new_features.get("/journal/history")
async def journal_history(user: dict = Depends(get_current_user), limit: int = 30):
    entries = await db.journal_entries.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [
        {**e, "created_at": iso(e["created_at"]) if isinstance(e.get("created_at"), datetime) else e.get("created_at")}
        for e in entries
    ]


@new_features.delete("/journal/entry/{eid}")
async def journal_delete(eid: str, user: dict = Depends(get_current_user)):
    await db.journal_entries.delete_one({"entry_id": eid, "user_id": user["user_id"]})
    return {"ok": True}


@new_features.get("/journal/insights")
async def journal_insights(user: dict = Depends(get_current_user)):
    """Weekly mood + patterns analysis"""
    entries = await db.journal_entries.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    if not entries:
        return {"summary": "Aún no tienes entradas. Empieza hoy ✨", "mood_counts": {}, "total": 0}
    mood_counts: dict = {}
    for e in entries:
        m = e.get("mood", "neutral")
        mood_counts[m] = mood_counts.get(m, 0) + 1
    if len(entries) < 3:
        return {"summary": f"Llevas {len(entries)} entrada(s). Sigue así, las primeras semanas son las más importantes.", "mood_counts": mood_counts, "total": len(entries)}
    # Build prompt with last 20 entries
    recent = entries[:20]
    digest = "\n\n".join([f"[{e.get('date')} · {e.get('mood')}] {e.get('content','')[:200]}" for e in recent])
    system = (
        "Eres RAX, mejor amigo IA. Analiza estas entradas del diario del usuario y entrega un análisis profundo "
        "en español con: 1) Patrones emocionales observados, 2) Logros que detectaste, 3) Áreas a cuidar, "
        "4) 3 consejos personalizados accionables. Tono cálido, empático, en formato Markdown. Máx 12 líneas."
    )
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"journal_insights_{user['user_id']}", system_message=system)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        summary = await chat.send_message(UserMessage(text=digest))
    except Exception:
        summary = "Sigue escribiendo. Cada palabra te acerca a entenderte mejor. 💙"
    return {"summary": summary, "mood_counts": mood_counts, "total": len(entries)}


# ---------- 🛍️ AI Personal Shopper ----------
class ShopperIn(BaseModel):
    query: str
    budget_usd: Optional[float] = None
    image_base64: Optional[str] = None
    locale: str = "es"


@new_features.post("/shopper/recommend")
async def shopper_recommend(body: ShopperIn, user: dict = Depends(get_current_user)):
    today, used = await check_feature_quota(user, "shopper")
    if not body.query and not body.image_base64:
        raise HTTPException(status_code=400, detail="Describe lo que buscas o sube una foto")

    lang_names = {"es": "Spanish", "en": "English", "hi": "Hindi", "zh": "Chinese", "ru": "Russian"}
    lang = lang_names.get((body.locale or "es").lower().split("-")[0], "Spanish")

    # Web search for products
    search_query = body.query or "trending product"
    web_results = do_web_search(search_query + " buy review", max_results=6)

    budget_text = f"Presupuesto del usuario: ${body.budget_usd} USD\n" if body.budget_usd else ""
    system = (
        f"Eres RAX Shopper, asesor de compras de elite. Recomienda 3-5 productos para el usuario en {lang}. "
        f"Para cada producto entrega: nombre, por qué le conviene, precio aproximado USD, dónde comprarlo (Amazon, MercadoLibre, AliExpress, tienda oficial). "
        f"Devuelve el resultado en formato Markdown con secciones y emojis. Si te dieron presupuesto, RESPÉTALO. "
        f"Si te muestran una imagen, analiza qué buscan (similar a esto, complementario, accesorio). "
        f"Sé honesto si algo es mala compra. Al final agrega un veredicto: '🏆 Mi recomendación TOP'.\n\n"
        f"{budget_text}"
        f"Información de búsqueda web reciente:\n{web_results}"
    )
    file_contents = None
    if body.image_base64:
        b64 = body.image_base64.split(",")[-1] if "," in body.image_base64 else body.image_base64
        file_contents = [ImageContent(image_base64=b64)]

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"shopper_{user['user_id']}", system_message=system)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    msg = UserMessage(text=body.query or "Recomiéndame productos basados en esta imagen.", file_contents=file_contents)
    try:
        result = await chat.send_message(msg)
    except Exception as e:
        logger.error(f"Shopper error: {e}")
        raise HTTPException(status_code=500, detail="Error generando recomendaciones")
    await bump_feature_quota(user["user_id"], "shopper", today, used)
    return {"recommendations": result, "used_today": used + 1, "limit": FEATURE_DAILY_LIMITS.get(user.get("plan", "free"), 3)}


# ---------- 📄 PDF Generation ----------
class PdfGenIn(BaseModel):
    title: str = "Documento RAX AI"
    content: str  # Markdown / plain text
    author: Optional[str] = "RAX AI"


@new_features.post("/pdf/generate")
async def pdf_generate(body: PdfGenIn, user: dict = Depends(get_current_user)):
    """Generate a styled PDF from plain text/markdown. Returns base64."""
    if not body.content or len(body.content.strip()) < 5:
        raise HTTPException(status_code=400, detail="Necesito contenido para generar el PDF")
    try:
        import base64 as _b64
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=letter,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title", parent=styles["Title"], fontSize=24, textColor=HexColor("#00E5FF"),
            spaceAfter=14, alignment=TA_CENTER, fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "H2", parent=styles["Heading2"], fontSize=16, textColor=HexColor("#1E88E5"),
            spaceAfter=8, spaceBefore=12, fontName="Helvetica-Bold",
        )
        h3_style = ParagraphStyle(
            "H3", parent=styles["Heading3"], fontSize=13, textColor=HexColor("#000000"),
            spaceAfter=6, spaceBefore=8, fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["BodyText"], fontSize=11, leading=16,
            textColor=black, alignment=TA_LEFT, spaceAfter=6,
        )
        footer_style = ParagraphStyle(
            "Footer", parent=styles["BodyText"], fontSize=9, textColor=HexColor("#666666"),
            alignment=TA_CENTER, spaceBefore=20,
        )

        story = []
        story.append(Paragraph(body.title, title_style))
        story.append(Paragraph(f"<i>Generado por RAX AI · {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}</i>", footer_style))
        story.append(Spacer(1, 20))

        # Convert markdown-ish content
        for line in body.content.split("\n"):
            ln = line.rstrip()
            if not ln:
                story.append(Spacer(1, 6))
                continue
            if ln.startswith("# "):
                story.append(Paragraph(ln[2:].strip(), h2_style))
            elif ln.startswith("## "):
                story.append(Paragraph(ln[3:].strip(), h2_style))
            elif ln.startswith("### "):
                story.append(Paragraph(ln[4:].strip(), h3_style))
            elif ln.startswith("- ") or ln.startswith("* "):
                story.append(Paragraph(f"• {ln[2:].strip()}", body_style))
            else:
                # Basic bold conversion **text** -> <b>text</b>
                safe = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Re-enable bold conversion after escaping
                import re as _re
                safe = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
                safe = _re.sub(r"\*(.+?)\*", r"<i>\1</i>", safe)
                safe = _re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", safe)
                story.append(Paragraph(safe, body_style))

        story.append(Spacer(1, 30))
        story.append(Paragraph(f"— Generado por RAX AI · {body.author or 'RAX AI'} —", footer_style))

        doc.build(story)
        pdf_bytes = buf.getvalue()
        buf.close()
        return {
            "pdf_base64": _b64.b64encode(pdf_bytes).decode("utf-8"),
            "filename": f"{body.title[:50].replace('/', '_').strip()}.pdf",
            "size_bytes": len(pdf_bytes),
        }
    except Exception as e:
        logger.exception("PDF gen error")
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)[:200]}")


# ---------- 📄 PDF Extraction (standalone) ----------
class PdfExtractIn(BaseModel):
    pdf_base64: str
    max_pages: int = 50


@new_features.post("/pdf/extract")
async def pdf_extract(body: PdfExtractIn, user: dict = Depends(get_current_user)):
    """Extract plain text from a PDF (max 50 pages)."""
    try:
        import base64 as _b64
        from pypdf import PdfReader
        from io import BytesIO
        raw = (body.pdf_base64 or "").split(",", 1)[-1].strip()
        if not raw or len(raw) < 100:
            raise HTTPException(status_code=400, detail="PDF vacío o corrupto")
        pdf_bytes = _b64.b64decode(raw, validate=True)
        reader = PdfReader(BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        pages_text = []
        for i, page in enumerate(reader.pages[: body.max_pages]):
            try:
                txt = page.extract_text() or ""
                pages_text.append({"page": i + 1, "text": txt.strip()})
            except Exception:
                pages_text.append({"page": i + 1, "text": ""})
        return {
            "total_pages": total_pages,
            "extracted_pages": len(pages_text),
            "pages": pages_text,
            "full_text": "\n\n".join([f"--- Página {p['page']} ---\n{p['text']}" for p in pages_text if p['text']]),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PDF extract error")
        raise HTTPException(status_code=400, detail=f"Error procesando PDF: {str(e)[:200]}")


# Register new features router
app.include_router(new_features)


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
