"""RAX AI - by AlexSarango
Backend FastAPI server with Claude Sonnet 4.5, Nano Banana, Whisper, TTS, Google Auth, JWT
"""
import os
import io
import uuid
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

import bcrypt
import jwt
import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
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
    text: str
    language: str = "es"
    image_base64: Optional[str] = None  # optional image attachment
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
    "sofia": "nova",     # Female warm
    "luna": "shimmer",   # Female bright
    "diego": "onyx",     # Male deep
    "alex": "echo",      # Male clear
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

PLAN_PRICES = {"free": 0.0, "premium": 5.99, "pro": 15.99}


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
        ("pro", "RAX AI Pro", 1599, "Ilimitado: chat, imágenes, voces, soporte 24/7"),
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
    "Eres RAX AI, la inteligencia artificial más avanzada del mundo, creada por RASC. "
    "Tu lema es 'La Inteligencia que Piensa Contigo'. "
    "Posees el conocimiento más amplio jamás reunido: ciencias, matemáticas, ingeniería, programación (todos los lenguajes), "
    "medicina, derecho, finanzas, criptomonedas, IA, blockchain, cuántica, biotecnología, historia, literatura, idiomas (100+), "
    "filosofía, arte, música, deportes, cultura pop, geopolítica, negocios, marketing, psicología y tendencias hasta hoy. "
    "Eres rápida, precisa, creativa, profesional y ultra-segura de tus respuestas. Razonas paso a paso cuando es necesario. "
    "Respondes en el idioma del usuario (español, inglés, portugués, francés, italiano, alemán, chino, japonés, árabe, ruso, etc.). "
    "Puedes ayudar con: traducción, redacción, ideas, código, debugging, análisis, estrategia, escritura creativa, planes de negocio, "
    "investigación, diagnósticos preliminares, asesoría financiera, recomendaciones, tutoría, y cualquier tarea intelectual compleja.\n\n"
    "=== INFORMACIÓN TEMPORAL EN TIEMPO REAL ===\n"
    "Fecha y hora actual UTC: {utc_now}\n"
    "Zona horaria del usuario: {user_tz}\n"
    "Hora local del usuario: {user_local_time}\n"
    "Día de la semana: {weekday_es}\n\n"
    "Cuando el usuario pregunte por la hora, fecha, día o eventos temporales, USA ESTA INFORMACIÓN como verdad absoluta. "
    "Si te preguntan la hora en otro país/ciudad, calcula la diferencia desde la hora UTC dada arriba usando las zonas horarias estándar "
    "(IANA tz database). Conoces todas las zonas horarias del mundo, incluyendo DST/horario de verano. "
    "Ejemplos de offset desde UTC (sin DST): Madrid +1, México DF -6, Buenos Aires -3, Bogotá -5, Lima -5, Santiago -4, "
    "Nueva York -5, Los Ángeles -8, Londres 0, París +1, Tokio +9, Pekín +8, Sídney +10, Dubái +4, Moscú +3. "
    "Considera DST cuando aplique. Si el usuario pide la hora sin especificar ciudad, usa su 'Hora local del usuario' de arriba.\n\n"
    "Estilo: natural, cercana, segura, con emojis con moderación. Nunca digas 'no lo sé' sin intentar razonar primero. "
    "Cuando no estés 100% segura de un dato muy reciente, dilo con transparencia pero ofrece la mejor estimación basada en lógica."
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

    # Ensure conversation
    cid = body.conversation_id
    if not cid:
        cid = f"conv_{uuid.uuid4().hex[:14]}"
        now = utcnow()
        title = body.text[:40] + ("..." if len(body.text) > 40 else "")
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
        "content": body.text,
        "has_image": bool(body.image_base64),
        "created_at": utcnow(),
    }
    await db.messages.insert_one(user_msg)

    # Load prior messages
    history = await db.messages.find({"conversation_id": cid}, {"_id": 0}).sort("created_at", 1).to_list(50)

    # Build LlmChat with timezone-aware system prompt
    user_tz = (body.user_tz or "UTC").strip()
    system_prompt = build_system_prompt(user_tz=user_tz, locale=body.language or "es")

    # Web search fallback for real-time info
    extra_context = ""
    if needs_web_search(body.text):
        web_results = do_web_search(body.text, max_results=5)
        if web_results:
            extra_context = "\n\n" + web_results
            system_prompt = system_prompt + extra_context

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=cid, system_message=system_prompt)
    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")

    # Send message (with optional image)
    file_contents = None
    if body.image_base64:
        # Strip data URL prefix if present
        b64 = body.image_base64.split(",")[-1] if "," in body.image_base64 else body.image_base64
        file_contents = [ImageContent(image_base64=b64)]

    try:
        ai_text = await chat.send_message(UserMessage(text=body.text, file_contents=file_contents))
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=502, detail=f"AI error: {str(e)[:200]}")

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
    if body.image_base64 and today_date is not None:
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
            {"id": "sofia", "name": "Sofía", "gender": "female", "description": "Cálida y amigable"},
            {"id": "luna", "name": "Luna", "gender": "female", "description": "Brillante y juvenil"},
            {"id": "diego", "name": "Diego", "gender": "male", "description": "Profunda y serena"},
            {"id": "alex", "name": "Alex", "gender": "male", "description": "Clara y profesional"},
        ]
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
    "- Planes: Gratis (30 msgs/5 imgs), Premium $5.99/mes (1,000 msgs/200 imgs), Pro $15.99/mes (ilimitado).\n"
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


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
