<div align="center">

# 🚀 RAX AI

### La Inteligencia que Piensa Contigo

**Una app de IA multi-modal full-stack (mobile + web) — chat, imágenes, voz, análisis de fotos/PDF, herramientas creativas, juego y mucho más.**

Creada por **SARANGO CABRERA · R A S C** · 2026

[![Made with Expo](https://img.shields.io/badge/Expo-SDK%2054-000020?logo=expo)](https://expo.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb)](https://mongodb.com/atlas)
[![Stripe](https://img.shields.io/badge/Stripe-Live-635BFF?logo=stripe)](https://stripe.com)

</div>

---

## 📦 ¿Qué hay en este repo?

```
rax-ai/
├── backend/                      # FastAPI (Python 3.11)
│   ├── server.py                 # API principal — 60+ endpoints
│   ├── requirements.txt          # Dependencias Python
│   ├── render.yaml               # Blueprint despliegue Render
│   ├── Procfile                  # Comando arranque gunicorn
│   ├── runtime.txt               # Python 3.11.9
│   ├── .env.example              # Plantilla variables (copiar a .env)
│   └── README.md                 # Docs técnicas del backend
│
├── frontend/                     # Expo React Native (iOS, Android, Web)
│   ├── app/                      # Rutas (file-based routing)
│   │   ├── (tabs)/               # 5 tabs principales
│   │   ├── chat/[id].tsx         # Hilo de chat con foto/PDF/cámara
│   │   ├── lens.tsx              # Cámara Mágica (AR Lens)
│   │   ├── roast.tsx             # Modo Roast
│   │   ├── journal.tsx           # Diario Inteligente
│   │   ├── shopper.tsx           # Personal Shopper IA
│   │   ├── admin.tsx             # Panel administrador (RASC)
│   │   ├── premium.tsx           # Suscripciones Stripe
│   │   ├── support.tsx           # Tickets de soporte
│   │   └── settings.tsx          # Config (idiomas, perfil, password)
│   ├── src/                      # Código compartido
│   │   ├── api.ts                # Cliente HTTP (axios)
│   │   ├── auth.tsx              # AuthContext (JWT)
│   │   ├── i18n.tsx              # 5 idiomas (ES/EN/HI/ZH/RU)
│   │   ├── theme.ts              # Colores, spacing
│   │   └── utils/                # Helpers (storage, etc.)
│   ├── app.json                  # Config Expo (bundle ID, permisos)
│   ├── eas.json                  # Config EAS Build
│   ├── package.json              # Dependencias JS
│   └── .env.example              # Plantilla URL del backend
│
├── DEPLOY_GUIDE.md               # ⭐ Guía paso a paso despliegue Render
├── APP_STORE_GUIDE.md            # ⭐ Guía paso a paso App Store + Play
└── .gitignore                    # Protege .env y secretos
```

---

## ✨ Features

### 🧠 IA Avanzada (Claude 4.5 Sonnet vía Emergent LLM Key)
- 💬 Chat en tiempo real con memoria, multi-idioma
- 📸 **Análisis de imágenes** — sube foto de tarea/recibo/objeto → respuesta inteligente
- 📄 **PDF** — sube PDF y la IA lo lee completo (hasta 50 páginas)
- 📝 **Genera PDFs** — pide "hazme un PDF de X" y se descarga al instante
- 🌐 **Internet en tiempo real** — DuckDuckGo + Open-Meteo para noticias, clima, precios

### 🎨 Generación de contenido
- 🖼️ Imágenes con Gemini Nano Banana (realista, anime, futurista, etc.)
- 🎙️ Voz: STT (Whisper) + TTS con 4 voces (Thalia, Jennifer, Alexander, Steven)
- ✍️ Herramientas de creador: captions TikTok, posts FB, ideas virales

### 🌟 Studio Mágico (4 features exclusivas)
- 📸 **Cámara Mágica** — escanea cualquier objeto → identifica + precio + traducciones
- 🌙 **Diario Inteligente** — entradas con análisis emocional + insights semanales
- 🔥 **Modo Roast** — 3 niveles, súper viral
- 🛍️ **Personal Shopper** — recomendaciones con presupuesto + web search
- 🎮 Mini-juego anti-estrés (word scramble)

### 💳 Suscripciones
- **Free**: 30 msgs/día, 5 imágenes/día, 10 fotos chat
- **Premium $5.99/mes**: 200 msgs/día, 50 imágenes, 40 fotos
- **Pro $15.99/mes**: ILIMITADO
- Pagos en vivo con **Stripe** (web) — para iOS se usa **Apple IAP** vía RevenueCat

### 🌐 Multi-idioma
- 🇪🇸 Español · 🇺🇸 English · 🇮🇳 हिन्दी · 🇨🇳 中文 · 🇷🇺 Русский
- Auto-detección + switch manual en Configuración

### 🔐 Auth
- Email/Password (bcrypt + JWT)
- Google OAuth (vía Emergent session)
- Cuenta de invitado (acceso instantáneo)
- *Apple/Facebook login: requieren build nativo, pendiente*

### 👑 Panel de Administrador
- Email: `rascsarango12345@gmail.com`
- Métricas de ingresos, usuarios, tickets de soporte
- Cambio de tema, gestión de suscripciones, refunds inmediatos

---

## 🛠️ Stack Técnico

| Capa | Tecnología |
|---|---|
| **Frontend** | Expo SDK 54, React Native, expo-router, TypeScript |
| **Backend** | FastAPI (Python 3.11), Motor (MongoDB async), JWT, gunicorn |
| **DB** | MongoDB Atlas (M0 free tier) |
| **IA** | Claude 4.5 Sonnet + Gemini Nano Banana + OpenAI TTS/Whisper (Emergent LLM Key) |
| **Pagos** | Stripe Live API (web), Apple IAP via RevenueCat (iOS) |
| **Hosting** | Render.com (backend), MongoDB Atlas, Expo EAS Build (móvil) |
| **PDF** | pypdf (lectura), reportlab (generación) |
| **Búsqueda web** | duckduckgo-search, Open-Meteo (clima) |

---

## 🚀 Despliegue Rápido

### Quiero correrlo local (dev)
```bash
# Backend
cd backend
cp .env.example .env  # luego pega tus llaves
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Frontend (nueva terminal)
cd frontend
cp .env.example .env  # pon EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
yarn install
yarn start
```

### Quiero subirlo a producción
👉 Lee **`DEPLOY_GUIDE.md`** — guía completa Render + MongoDB Atlas + Stripe webhook (~45 min)

### Quiero publicarlo en App Store / Google Play
👉 Lee **`APP_STORE_GUIDE.md`** — guía completa EAS Build + Apple Developer + Apple IAP (~2 horas)

---

## 🔑 Variables de entorno requeridas

**Backend** (`backend/.env`):
```env
MONGO_URL=mongodb+srv://...           # MongoDB Atlas
DB_NAME=raxai_database
EMERGENT_LLM_KEY=sk-emergent-...      # Universal key (Claude + Gemini + OpenAI)
JWT_SECRET=string-random-largo-min-32-chars
STRIPE_SECRET_KEY=sk_live_...         # Stripe Dashboard
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...       # Después de crear el webhook
```

**Frontend** (`frontend/.env`):
```env
EXPO_PUBLIC_BACKEND_URL=https://tu-backend.onrender.com
```

⚠️ Los archivos `.env` están en `.gitignore` — **NUNCA** los subas al repo.

---

## 📞 Soporte

Email: **rascsarango12345@gmail.com**

Hecho con ❤️ por **R A S C** — SARANGO CABRERA · 2026

---

## 📄 Licencia

Código propietario — © 2026 RASC. Todos los derechos reservados.
