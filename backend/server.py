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
ADMIN_EMAILS = {"admin@raxai.com", "alex@alexsarango.com"}

# OpenAI client uses Emergent key (Whisper/TTS via Emergent gateway)
os.environ["OPENAI_API_KEY"] = EMERGENT_LLM_KEY
openai_client = OpenAI(api_key=EMERGENT_LLM_KEY, base_url="https://integrations.emergentagent.com/llm")

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
    plan: str = "free"
    is_admin: bool = False
    is_blocked: bool = False
    is_guest: bool = False
    created_at: str
    messages_used: int = 0
    images_used: int = 0


class ChatSendIn(BaseModel):
    conversation_id: Optional[str] = None
    text: str
    language: str = "es"
    image_base64: Optional[str] = None  # optional image attachment


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
    "free": {"messages": 30, "images": 5},
    "premium": {"messages": 500, "images": 100},
    "pro": {"messages": 99999, "images": 99999},
}


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
        plan=u.get("plan", "free"),
        is_admin=u.get("is_admin", False) or (u["email"] in ADMIN_EMAILS),
        is_blocked=u.get("is_blocked", False),
        is_guest=u.get("is_guest", False),
        created_at=iso(u.get("created_at", utcnow())) if isinstance(u.get("created_at"), datetime) else (u.get("created_at") or iso(utcnow())),
        messages_used=u.get("messages_used", 0),
        images_used=u.get("images_used", 0),
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
    logger.info("RAX AI backend ready")


# =====================
# Auth endpoints
# =====================
@api.get("/")
async def root():
    return {"app": "RAX AI", "by": "AlexSarango", "status": "online"}


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


# =====================
# Conversations & Chat
# =====================
SYSTEM_PROMPT = (
    "Eres RAX AI, una inteligencia artificial conversacional avanzada creada por AlexSarango. "
    "Tu lema es 'La Inteligencia que Piensa Contigo'. "
    "Respondes en el idioma del usuario (español o inglés). Eres rápida, precisa, creativa y profesional. "
    "Puedes ayudar con ideas, traducciones, contenido, código, análisis y tareas complejas. "
    "Sé natural, cercana y útil. Usa emojis con moderación cuando aporten claridad."
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

    # Build LlmChat
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=cid, system_message=SYSTEM_PROMPT)
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
    # estimated revenue
    revenue = premium * 9.99 + pro * 19.99
    return {
        "total_users": total_users,
        "total_messages": total_msgs,
        "total_images": total_imgs,
        "blocked_users": blocked,
        "premium_users": premium,
        "pro_users": pro,
        "estimated_revenue_usd": round(revenue, 2),
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
    """Idempotent admin seeding. Safe to call multiple times."""
    email = "admin@raxai.com"
    password = "RaxAI2026!"
    existing = await db.users.find_one({"email": email})
    if existing:
        # update password to ensure consistency
        await db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": hash_password(password), "is_admin": True, "is_blocked": False}},
        )
        return {"ok": True, "seeded": False, "email": email}
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": "Admin RAX",
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


app.include_router(api)


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
