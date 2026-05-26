# 🚀 RAX AI — App Store Submission Guide

**Status:** Listo para subir. Esta es la guía paso a paso para llegar a la App Store.

---

## 📦 Assets generados (ya en el repo)

| Asset | Ubicación | Resolución | Estado |
|-------|-----------|------------|--------|
| App Icon | `/app/frontend/assets/images/icon.png` | 1024 × 1024 | ✅ Listo |
| Adaptive Icon (Android) | `/app/frontend/assets/images/adaptive-icon.png` | 1024 × 1024 | ✅ Listo |
| Splash | `/app/frontend/assets/images/splash-icon.png` | 1024 × 1024 | ✅ Listo |
| Favicon (Web) | `/app/frontend/assets/images/favicon.png` | 1024 × 1024 | ✅ Listo |
| App Store Screenshots × 6 | `/app/appstore_screenshots/*.png` | 1290 × 2796 (iPhone 6.7") | ✅ Listos |
| ZIP descargable | `/app/RAX_AI_AppStore_Assets.zip` | — | ✅ Listo |

Las screenshots son:
1. `01_login.png` — Pantalla de login
2. `02_home.png` — Lista de conversaciones
3. `03_studio.png` — Studio (herramientas exclusivas)
4. `04_voice.png` — Conversación por voz
5. `05_premium.png` — Planes de suscripción
6. `06_profile.png` — Perfil de usuario

---

## 🎯 PASOS PARA SUBIR LA APP A LA APP STORE

### ⚙️ PASO 1 — Pushear los cambios a GitHub (2 min)

1. En Emergent click **"Save to GitHub"** (arriba a la derecha).
2. Render hará redeploy automático del backend.
3. **Importante:** en Render → Environment → añade la variable:
   ```
   REVENUECAT_WEBHOOK_SECRET = kcHgaiBPYYh_Cu82RE1zUqCIOnemAK-EKRf9WyVSCvo
   ```
4. Verifica los endpoints legales en producción:
   - https://raxai-backendd.onrender.com/api/legal/privacy
   - https://raxai-backendd.onrender.com/api/legal/terms

---

### 💻 PASO 2 — Instalar EAS CLI en tu Mac (3 min)

Abre la app **Terminal** en tu Mac (Cmd+Espacio → "Terminal") y ejecuta:

```bash
# 1. Instala Node.js si no lo tienes (https://nodejs.org)
# 2. Instala EAS CLI:
npm install -g eas-cli

# 3. Verifica:
eas --version
```

---

### 📥 PASO 3 — Clonar el repo y entrar al proyecto (2 min)

```bash
cd ~/Documents
git clone https://github.com/TU_USUARIO/raxai.git
cd raxai/frontend

# Instala dependencias
yarn install
# o si usas npm:
# npm install
```

---

### 🔐 PASO 4 — Login en Expo y configurar EAS (3 min)

```bash
# Login con tu cuenta de Expo (crea una en expo.dev si no tienes)
eas login

# Configura el proyecto (ya está pre-configurado pero corre esto para validar)
eas build:configure

# Cuando pregunte qué plataforma → elige iOS
# Cuando pregunte el bundle ID → confirma com.sarangocabrera.raxai
```

---

### 🔑 PASO 5 — Conectar tu Apple Developer Account (3 min)

```bash
# Asegúrate que estás en frontend/
eas credentials

# Te preguntará:
# - Plataforma: iOS
# - Profile: production
# - Te pedirá tu Apple ID y password (acepta el 2FA en tu iPhone)
# - EAS automáticamente:
#     • Crea el App ID en developer.apple.com
#     • Genera el certificado de distribución
#     • Crea el provisioning profile
#     • Lo guarda todo en la cloud de EAS
```

---

### 🏗 PASO 6 — Construir la app (15-25 min ⏳)

```bash
eas build --platform ios --profile production

# Te dirá: "Build queued — ETA: 15 min"
# Esperas mientras EAS construye en sus servidores Mac
# Cuando termine te dará un link al .ipa (ej: https://expo.dev/.../builds/...)
```

> ⚠️ **Primera vez:** EAS te puede pedir crear el App en App Store Connect. Si tu app ID `6771876490` ya existe, dile que **"reuse"**.

---

### 📤 PASO 7 — Subir a TestFlight (5 min)

```bash
# Submit automático a App Store Connect (TestFlight)
eas submit --platform ios --profile production --latest

# Te pedirá confirmar:
# - Apple ID: rascsarango12345@gmail.com
# - App-specific password (genera una en appleid.apple.com → Sign-In and Security → App-Specific Passwords)
# - ASC App ID: 6771876490

# Cuando termine, Apple tarda 5-30 min en procesar el build en TestFlight.
```

---

### 📱 PASO 8 — Probar en TestFlight ANTES de submission (10 min)

1. Abre **TestFlight** en tu iPhone (descárgala del App Store si no la tienes).
2. Login con tu Apple ID.
3. Espera 5-30 min hasta ver "RAX AI" disponible para Internal Testing.
4. Click **Install** → abre la app.
5. **PRUEBA TODO**: login, chat, imagen, voz (¡el fix de iOS!), suscripción RevenueCat sandbox.

> 💡 **Para probar suscripciones SIN cobrar:** crea un Sandbox Tester en App Store Connect → Users and Access → Sandbox Testers → "+ New". Luego en tu iPhone → Settings → App Store → Sandbox Account → login con ese email. Las compras NO se cobrarán.

---

### 📝 PASO 9 — Llenar metadata en App Store Connect (30 min)

Ve a https://appstoreconnect.apple.com → tu app **RAX AI** → "1.0.0 Prepare for Submission".

#### 9.1 — App Information
- **Name:** `RAX AI`
- **Subtitle:** `AI assistant. Smarter. Faster.`
- **Primary Language:** Spanish (Mexico) o English (US)
- **Bundle ID:** com.sarangocabrera.raxai
- **Category (Primary):** Productivity
- **Category (Secondary):** Utilities
- **Content Rights:** ✅ "Does not use third-party content" (a menos que uses imágenes de terceros)

#### 9.2 — Pricing and Availability
- **Price:** Free
- **Availability:** All countries (o los que quieras)

#### 9.3 — Privacy
- **Privacy Policy URL:** `https://raxai-backendd.onrender.com/api/legal/privacy`
- En "App Privacy" llena el formulario:
  - Contact Info: ✅ Email Address, ✅ Name
  - Identifiers: ✅ User ID
  - Usage Data: ✅ Product Interaction
  - Audio Data: ✅ Voice
  - Photos: ✅ Photos
  - Files and Docs: ✅ Documents
  - **NONE for tracking** (you don't sell data, no ads)

#### 9.4 — Version Information (1.0.0)
- **Promotional Text (170 chars):**
  > "Your AI assistant for chat, images, voice, photos & PDFs. Spanish, English, Hindi, Chinese & Russian. Powered by Claude, GPT, Gemini. Try free today."

- **Description (4000 chars):** copia y pega esto:

```
RAX AI is your all-in-one futuristic AI assistant — chat, voice, image generation, file analysis, and creator tools, all in one stunning neon-themed app.

✨ FEATURES
• Real-time AI Chat with memory — powered by Claude
• Image Generation — realistic, anime, futuristic styles (Gemini Nano Banana)
• Voice Conversation — talk naturally with 4 unique AI personalities (Thalia, Jennifer, Alexander, Steven)
• PDF & Document Analysis — upload any PDF and get instant summaries, Q&A
• Photo Analysis — capture or upload to identify objects, translate text, get insights
• Web Search — RAX AI fetches live information for fresh answers
• Mini-Game — destress with word scrambles between conversations

🎨 EXCLUSIVE STUDIO TOOLS
• Magic Lens — AR-style object recognition
• Smart Journal — AI-powered daily journaling with mood tracking
• Roast Mode — playful AI roasts of your photos
• AI Personal Shopper — instant product recommendations

🌍 MULTILINGUAL
Spanish, English, Hindi, Chinese, Russian. Switch anytime.

💎 PREMIUM PLANS
• Free — basic daily quota
• Premium ($5.99/mo) — 1000 messages, 200 images, 40 photos per day
• Pro ($9.99/mo) — Unlimited everything + priority responses

🔒 PRIVACY FIRST
No ads. No data selling. Your conversations are encrypted. Delete them anytime.

⚙️ ABOUT
RAX AI is made by RASC (Sarango Cabrera). Built with the world's best AI models — Anthropic Claude, OpenAI Whisper & TTS, and Google Gemini.

By using RAX AI you agree to our Terms of Service and Privacy Policy:
• Terms: https://raxai-backendd.onrender.com/api/legal/terms
• Privacy: https://raxai-backendd.onrender.com/api/legal/privacy
```

- **Keywords (100 chars):**
  > `ai,chatbot,gpt,claude,assistant,voice,image,creator,study,help,translator,journal,roast,futuristic`

- **Support URL:** `https://raxai-backendd.onrender.com/api/legal/privacy` (o tu email)
- **Marketing URL:** (opcional, déjalo vacío)

#### 9.5 — Build
Click **"+ Build"** → selecciona el build que subiste con `eas submit` (aparece después de procesar).

#### 9.6 — App Review Information
- **Sign-In Required:** ✅ Yes
- **Demo Account:** crea uno fácil:
  - **Username:** `apple_review@raxai.app`
  - **Password:** `RaxReview2026!`
  - Regístralo desde la app antes de submission.
- **Notes:**
  > "Please use the demo account above to access all features. Tap 'Continue as Guest' for limited free access. The Voice tab requires microphone permission. Image generation uses Gemini Nano Banana. Subscriptions are handled via Apple In-App Purchases."
- **Contact Information:** tu email + teléfono

#### 9.7 — Version Release
- ✅ "Automatically release this version" — (Apple suelta tu app apenas se aprueba)
  - O escoge "Manually release" si quieres timing exacto.

#### 9.8 — Screenshots
- **iPhone 6.7":** sube los 6 screenshots de `/app/appstore_screenshots/`
- **iPhone 6.9" (Pro Max):** Apple ahora pide 6.9". Sube los mismos — App Store los acepta porque tienen la misma proporción.
- **iPad:** opcional. Si quieres soporte iPad, hay que generar screenshots de 2048x2732. Por ahora desactiva "supportsTablet" en `app.json` si no las tienes.

---

### 💰 PASO 10 — Llenar Subscription Metadata (15 min)

Ve a **In-App Purchases and Subscriptions** → cada producto:

#### 10.1 — `raxai_premium_monthly`
- **Reference Name:** Premium Monthly
- **Subscription Display Name:** `Premium`
- **Description:** `1000 messages, 200 image generations, and 40 chat photos per day. Renews monthly.`
- **Promotional Image (1024x1024):** sube `/app/frontend/assets/images/icon.png`
- **Review Information:**
  - Screenshot: sube `/app/appstore_screenshots/05_premium.png`
  - Review Notes: `Premium subscription. Test via Sandbox tester after logging in with the demo account.`
- **Status:** Submit for Review with App

#### 10.2 — `raxai_pro_monthly1`
- **Reference Name:** Pro Monthly
- **Subscription Display Name:** `Pro`
- **Description:** `Unlimited messages, image generations, photos, and priority responses. Renews monthly.`
- Demás campos iguales.

---

### 🚦 PASO 11 — Submit for Review

1. Una vez todo verde, click **"Add for Review"** arriba a la derecha.
2. Te preguntará si exportas data → tu app no exporta cifrado custom → marca "No".
3. Submit ✅

> ⏳ **Tiempo de revisión típico:** 24-48 horas. Algunas veces hasta 7 días.
> 
> Si Apple rechaza, lee el motivo y arréglalo. Volver a submit es rápido.

---

## 🐛 Si Apple te rechaza, errores más comunes:

| Error | Solución |
|-------|----------|
| "Missing Privacy Policy" | Verifica que `/api/legal/privacy` cargue en producción. |
| "Crashes on launch" | Suele ser una key faltante en Render. Revisa env vars. |
| "Subscription metadata missing" | Llena screenshots + descripción en cada IAP product. |
| "Demo account no funciona" | Asegúrate de haberte registrado **antes** de submit. |
| "Uses non-public API" | El SDK de RevenueCat es público — no debería pasar. |
| "Won't pass review with Stripe" | ✅ Ya está arreglado — iOS usa RevenueCat ahora. |

---

## 📊 Comando rápido para subir versiones futuras

Cuando hagas cambios y quieras subir una nueva versión:

```bash
cd ~/Documents/raxai/frontend

# Sube el build number en app.json manualmente o deja que EAS lo haga
# (autoIncrement: true ya está en eas.json)

eas build --platform ios --profile production
eas submit --platform ios --latest
```

---

## ✅ Checklist final antes de submit

- [ ] Backend re-deployed en Render con `REVENUECAT_WEBHOOK_SECRET`
- [ ] Privacy y Terms cargan en URL de producción
- [ ] EAS build exitoso (versión 1.0.0 build 1)
- [ ] Build subido a TestFlight y probado en iPhone real
- [ ] Login con demo account funciona
- [ ] Chat, Voice, Imagen, Premium screen funcionan
- [ ] Suscripción se completa en Sandbox tester
- [ ] Webhook de RevenueCat configurado y verificado
- [ ] Screenshots subidas (6 imágenes 6.7")
- [ ] Description + Keywords llenas en App Store Connect
- [ ] Privacy questionnaire respondida
- [ ] Reviewer notes con demo account
- [ ] IAP products tienen metadata + review screenshot

---

🎉 **¡Estás listo! Empieza por el PASO 1 (Save to GitHub) y vamos avanzando.**

Si te trabas en cualquier paso, mándame screenshot y te ayudo en segundos.
