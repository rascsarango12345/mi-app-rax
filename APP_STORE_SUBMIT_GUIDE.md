# 🚀 RAX AI — GUÍA COMPLETA PASO 2 → 11

> **Tu PASO 1 (Save to GitHub + Render env vars) ya está listo.**
> Esta guía es del **PASO 2 al PASO 11 (Submit for Review)**.

---

## 📦 Assets que ya están listos en tu repo

| Archivo | Ubicación | Para qué sirve |
|---------|-----------|----------------|
| `frontend/assets/images/icon.png` | App Icon — **REEMPLÁZALO con tu ícono propio** antes del build | Apple lo pide 1024×1024 PNG, sin transparencia |
| `appstore_screenshots/EN_*.png` × 6 | Screenshots en **inglés** (1290×2796) | App Store screenshots iPhone 6.7"/6.9" |
| `appstore_screenshots/ES_*.png` × 6 | Screenshots en **español** (1290×2796) | Localización para App Store |
| `RAX_AI_Screenshots_EN.zip` | ZIP con los 6 EN | Sube fácil de tu Mac |
| `RAX_AI_Screenshots_ES.zip` | ZIP con los 6 ES | Sube fácil de tu Mac |
| `RAX_AI_Screenshots_ALL.zip` | ZIP con los 12 (EN + ES) | Todo en uno |

**⚠️ IMPORTANTE:** Antes de hacer `eas build`, reemplaza `frontend/assets/images/icon.png` con tu ícono 1024×1024 PNG (sin transparencia ni canal alpha). Si no lo haces, el build usará el ícono placeholder.

---

# PASO 2 — Instalar EAS CLI (3 min)

Abre Terminal en tu Mac (`Cmd+Space` → "Terminal") y ejecuta:

```bash
# 1) Instala Node.js (si no lo tienes): https://nodejs.org → versión LTS
# 2) Instala EAS CLI globalmente:
npm install -g eas-cli

# 3) Verifica:
eas --version
# Debe mostrar algo tipo: eas-cli/15.x.x

# 4) Instala también el CLI de expo (opcional pero útil):
npm install -g expo
```

✅ **Si ves un error de permisos**, anteponé `sudo`: `sudo npm install -g eas-cli`

---

# PASO 3 — Clonar el repo a tu Mac (2 min)

```bash
# Ve al directorio donde quieras tener el proyecto
cd ~/Documents

# Clona tu repo (reemplaza TU_USUARIO con el tuyo de GitHub)
git clone https://github.com/TU_USUARIO/raxai.git
cd raxai/frontend

# Instala las dependencias
yarn install
# Si no tienes yarn: corepack enable && yarn install
# O usa npm: npm install --legacy-peer-deps
```

**📥 Aquí REEMPLAZA el ícono:**
```bash
# Pon tu propio ícono (1024×1024 PNG sin transparencia) en:
# raxai/frontend/assets/images/icon.png
# Y opcionalmente también en:
# raxai/frontend/assets/images/adaptive-icon.png  (igual)
# raxai/frontend/assets/images/splash-icon.png    (versión cuadrada igual)
```

---

# PASO 4 — Login en Expo + Configurar EAS (3 min)

```bash
# Asegúrate de estar en raxai/frontend
cd ~/Documents/raxai/frontend

# Login con tu cuenta de Expo (si no tienes: créala en https://expo.dev/signup)
eas login
# Te pregunta email + password

# Configura el proyecto (ya está pre-configurado, esto solo valida)
eas build:configure
# Si te pregunta plataforma → elige iOS
# Si te pregunta bundle ID → confirma com.sarangocabrera.raxai
```

---

# PASO 5 — Conectar Apple Developer (3 min)

```bash
# Asegúrate de estar en raxai/frontend
eas credentials

# Selecciones:
# - Platform: iOS
# - Build profile: production
# - What do you want to do? → "Set up a new credential"
#
# Te pedirá:
#   Apple ID:       rascsarango12345@gmail.com   (tu email)
#   Password:       (tu contraseña Apple)
#   2FA code:       (lo recibirás en tu iPhone)
#
# EAS automáticamente:
#   ✓ Crea el App ID en developer.apple.com (si no existe)
#   ✓ Genera el Distribution Certificate
#   ✓ Crea el Provisioning Profile
#   ✓ Lo guarda todo en la cloud
```

> 💡 **Si te dice "App ID already exists for com.sarangocabrera.raxai"** → elige **"Use existing"**.

Cuando termine sales con `Ctrl+C` (o salir del menú).

---

# PASO 6 — Construir el Build de Producción iOS ⏳ (15-25 min)

```bash
# Ejecutar el build
eas build --platform ios --profile production

# Te confirma versión y bundle ID — escribe "y"
# Te dice "Build in progress, ETA: 15 minutes..."
# Te da un link tipo: https://expo.dev/accounts/.../builds/abc123
```

📺 **Mientras esperas:**
- Abre el link en el navegador para ver el progreso en vivo
- Toma agua, estira las piernas

Cuando termine verás: `✓ Build finished`. El `.ipa` queda en la cloud de EAS.

---

# PASO 7 — Submit a TestFlight (5 min)

Primero necesitas un **App-Specific Password** de Apple. Es UNA SOLA VEZ:

1. Ve a 👉 https://appleid.apple.com → sign in con tu Apple ID.
2. Sección **"Sign-In and Security"** → click **"App-Specific Passwords"** → **"+ Generate Password"**.
3. Nombre: `EAS Submit RAX AI`. Apple te dará una contraseña tipo `abcd-efgh-ijkl-mnop`. **Cópiala**.

Ahora en Terminal:

```bash
eas submit --platform ios --profile production --latest

# Te pedirá confirmar:
#   Apple ID: rascsarango12345@gmail.com
#   App-specific password: pega la que copiaste arriba
#   App Store Connect App ID: 6771876490
#   Team ID: 764PWN3V94
```

> ⏳ **Después de submit, Apple tarda 5-30 min** en procesar el build. Te llegará un email **"Your build is now available for testing"**.

---

# PASO 8 — Probar en TestFlight con tu iPhone (10 min)

1. **Instala TestFlight** en tu iPhone (gratis en App Store).
2. Abre TestFlight → login con tu Apple ID.
3. Espera 5-30 min hasta ver **"RAX AI"** en la lista (Internal Testing).
4. Click **Install** → abre RAX AI.

### 🧪 Pruebas obligatorias antes de submit a Apple:

- [ ] Te puedes registrar con email/password
- [ ] Te puedes loguear con Google
- [ ] Continue as Guest funciona
- [ ] Mandar un mensaje al chat → RAX responde
- [ ] **Memoria del chat:** dile tu nombre, después pregúntale "¿cómo me llamo?" → debe recordar
- [ ] Generar una imagen
- [ ] Pantalla **Voice** → graba 2 seg, debes escuchar respuesta clara del altavoz principal
- [ ] Pantalla **Studio** → todas las tarjetas abren bien
- [ ] **Cambiar idioma**: Profile → Settings → cambia a English → toda la app debe estar en inglés (incluyendo Términos y Privacidad)
- [ ] Pantalla **Premium** → tap "Subscribe to Premium" → se abre el modal de Apple

### 💎 Para probar **suscripciones SIN cobrar** (Sandbox Tester):

1. En App Store Connect → **Users and Access** → **Sandbox Testers** → **"+"**.
2. Crea un usuario fake (puede ser un email cualquiera, ej: `test+sandbox@raxai.app`, password fácil).
3. En tu iPhone: **Settings (gear icon) → App Store → scroll down → "Sandbox Account" → Sign In** con ese email.
4. Vuelve a RAX AI → Premium → Subscribe → no te cobra dinero real.

---

# PASO 9 — Llenar Metadata en App Store Connect (30 min)

Ve a 👉 https://appstoreconnect.apple.com → tu app **RAX AI** → **"1.0.0 Prepare for Submission"**.

## 9.1 — Información de la App
- **Name:** `RAX AI`
- **Subtitle:** `AI assistant. Smarter. Faster.`
- **Primary Language:** elige uno (recomiendo **English (US)** — luego añades Spanish como localización)
- **Category Primary:** `Productivity`
- **Category Secondary:** `Utilities`
- **Content Rights:** ✅ "Does not use third-party content"

## 9.2 — Pricing & Availability
- **Price:** `Free`
- **Availability:** Marca **all countries** (o los que quieras)

## 9.3 — Privacy
- **Privacy Policy URL:** `https://raxai-backendd.onrender.com/api/legal/privacy`
- **App Privacy** — click **"Get Started"**, llena el cuestionario así:
  - **Do you collect data from this app?** → Yes
  - Marca estas categorías:
    - ✅ **Contact Info** → Email Address, Name
    - ✅ **User Content** → Photos or Videos, Audio Data, Other User Content (chat messages)
    - ✅ **Identifiers** → User ID
    - ✅ **Usage Data** → Product Interaction
    - ✅ **Diagnostics** → Crash Data
  - Para cada categoría marca:
    - **Linked to user?** Yes
    - **Used for tracking?** ❌ No
    - **Purposes:** App Functionality + Analytics

## 9.4 — Versión 1.0.0 — Localizaciones

### A) English (US) — Primary
- **Promotional Text** (170 chars):
  > "Your AI assistant for chat, images, voice, photos & PDFs. Powered by Claude, GPT, Gemini. 5 languages. Try free today."

- **Description** (4000 chars) — copia desde `/app/APP_STORE_DESCRIPTION_EN.md` o usa esto:
  ```
  RAX AI is your all-in-one futuristic AI assistant.

  ✨ FEATURES
  • Real-time AI Chat with memory — powered by Claude
  • Image Generation — realistic, anime, futuristic (Gemini Nano Banana)
  • Voice Conversation — talk with 4 unique AI personalities
  • PDF & Document Analysis
  • Photo Analysis — capture or upload
  • Web Search for live information
  • Mini-Game — destress with word scrambles

  🎨 STUDIO TOOLS
  • Magic Lens — object recognition
  • Smart Journal — AI mood tracking
  • Roast Mode — playful AI roasts
  • AI Personal Shopper

  🌍 MULTILINGUAL — Spanish, English, Hindi, Chinese, Russian.

  💎 PLANS
  • Free — basic daily quota
  • Premium ($5.99/mo) — 1,000 messages, 200 images, 40 photos/day
  • Pro ($9.99/mo) — Unlimited everything

  🔒 PRIVACY FIRST — No ads. No data selling.

  Terms: https://raxai-backendd.onrender.com/api/legal/terms
  Privacy: https://raxai-backendd.onrender.com/api/legal/privacy
  ```

- **Keywords** (100 chars):
  > `ai,chatbot,gpt,claude,assistant,voice,image,creator,study,help,translator,journal,roast,futuristic`

- **Support URL:** `https://raxai-backendd.onrender.com/api/legal/privacy`
- **Marketing URL:** déjalo vacío

- **Screenshots:** Sube los 6 **EN_*.png** desde `appstore_screenshots/`.

### B) Spanish (Mexico) — Localización adicional

1. Click **"+ Add Language"** → elige **Spanish (Mexico)**.
2. Llena:
   - **Name:** `RAX AI`
   - **Subtitle:** `Asistente IA. Más inteligente. Más rápido.`
   - **Description:**
     ```
     RAX AI es tu asistente IA todo-en-uno.

     ✨ FUNCIONES
     • Chat IA en tiempo real con memoria — potenciado por Claude
     • Generación de imágenes — realista, anime, futurista (Gemini Nano Banana)
     • Conversación por voz — habla con 4 personalidades AI
     • Análisis de PDFs y documentos
     • Análisis de fotos — captura o sube
     • Búsqueda web en vivo
     • Mini-juego de palabras

     🎨 HERRAMIENTAS STUDIO
     • Lente Mágica — reconocimiento de objetos
     • Diario Inteligente — estado de ánimo con IA
     • Modo Roast — bromas divertidas
     • Personal Shopper IA

     🌍 MULTI-IDIOMA — Español, English, Hindi, Chinese, Russian.

     💎 PLANES
     • Gratis — cuota básica diaria
     • Premium ($5.99/mes) — 1,000 mensajes, 200 imágenes, 40 fotos/día
     • Pro ($9.99/mes) — Ilimitado todo

     🔒 PRIVACIDAD PRIMERO — Sin anuncios. No vendemos datos.

     Términos: https://raxai-backendd.onrender.com/api/legal/terms?lang=es
     Privacidad: https://raxai-backendd.onrender.com/api/legal/privacy?lang=es
     ```
   - **Keywords:** `ia,chatbot,gpt,claude,asistente,voz,imagen,creador,estudio,traductor,diario`
   - **Screenshots:** Sube los 6 **ES_*.png** desde `appstore_screenshots/`.

## 9.5 — Build
Click **"+ Build"** → selecciona el build que subiste con `eas submit` (aparece como 1.0.0 (1)).

> Si no aparece → espera 10-30 min después del `eas submit`.

## 9.6 — App Review Information
- **Sign-In Required:** ✅ Yes
- **Demo Account:**
  - **Username:** `apple_review@raxai.app`
  - **Password:** `RaxReview2026!`
  - ⚠️ **CRÍTICO**: Antes de submit, regístrate con ESE EMAIL en la app desde TestFlight, así Apple lo puede usar.
- **Notes:**
  > "Use the demo account above OR tap 'Continue as Guest' for limited free access. The Voice tab needs microphone permission. Subscriptions are via Apple In-App Purchases (RevenueCat). Privacy: https://raxai-backendd.onrender.com/api/legal/privacy ; Terms: https://raxai-backendd.onrender.com/api/legal/terms"
- **Contact Information:** tu email + teléfono

## 9.7 — Version Release
- ✅ "Automatically release this version" (cuando Apple aprueba, sale al store automáticamente).

---

# PASO 10 — Llenar Metadata de Cada Suscripción (15 min)

Ve a **In-App Purchases and Subscriptions** → click cada producto:

## 🅰️ `raxai_premium_monthly`
- **Reference Name:** `Premium Monthly`
- **Subscription Display Name:** `Premium`
- **Description (English):** `1,000 messages, 200 image generations, and 40 chat photos per day. Renews monthly.`
- **Description (Spanish):** `1,000 mensajes, 200 imágenes y 40 fotos de chat por día. Se renueva mensualmente.`
- **Promotional Image (1024×1024):** sube `frontend/assets/images/icon.png` (tu ícono)
- **Review Information:**
  - **Screenshot:** sube `appstore_screenshots/EN_05_premium.png`
  - **Review Notes:** `Premium subscription. Test using a Sandbox Tester after logging in. The Premium tab in the app shows this product.`
- **Status:** ✅ Submit for Review with App

## 🅱️ `raxai_pro_monthly1`
- Igual que arriba pero:
- **Reference Name:** `Pro Monthly`
- **Display Name:** `Pro`
- **Description (EN):** `Unlimited messages, image generations, photos, and priority responses. Renews monthly.`
- **Description (ES):** `Mensajes, imágenes y fotos ilimitados. Renovación mensual.`
- **Screenshot:** el mismo `EN_05_premium.png`.

---

# PASO 11 — Submit for Review 🚀

1. Vuelve a la página principal de tu versión 1.0.0.
2. Verifica que TODO esté en verde ✅
3. Click el botón naranja **"Add for Review"** arriba a la derecha.
4. Apple te preguntará:
   - **Export Compliance:** ¿usa cifrado no exento? → **No**
   - **Advertising Identifier (IDFA):** ¿la app la usa? → **No**
   - **Content Rights:** ¿tienes los derechos del contenido? → **Yes**
5. Click **Submit**.

🎉 **¡Ya está! Espera 24-48 horas (a veces hasta 7 días).**

---

## 🐛 Errores comunes de Apple y cómo arreglarlos

| Error | Causa | Solución |
|-------|-------|----------|
| **Guideline 2.1 — App crashes on launch** | Falta una env var en Render o un asset | Revisa logs en Render. Asegúrate de tener `REVENUECAT_WEBHOOK_SECRET` añadido. |
| **Guideline 5.1.1 — Privacy Policy URL not working** | Render no terminó de deploy o falta el endpoint | Abre https://raxai-backendd.onrender.com/api/legal/privacy en navegador antes de submit. |
| **Guideline 3.1.1 — In-App Purchase products not found** | Productos en estado "Missing Metadata" | Llena descripción + screenshot de cada IAP product. Marca "Submit with App". |
| **Guideline 4.0 — Design** | Screenshots con marketing exagerado | Usa los EN_*.png REALES que generamos — son screenshots de tu app actual. |
| **Demo account doesn't work** | No registraste `apple_review@raxai.app` | Hazlo desde TestFlight ANTES de submit. |
| **Missing screenshot for IAP** | IAP product sin screenshot | Sube `EN_05_premium.png` a cada IAP. |

---

## 🔄 Para versiones futuras (1.0.1, 1.0.2, etc.)

```bash
cd ~/Documents/raxai/frontend

# El buildNumber se incrementa automáticamente (autoIncrement en eas.json)
# Si cambiaste la versión visible, edita app.json: "version": "1.0.1"

eas build --platform ios --profile production
eas submit --platform ios --latest

# Luego en App Store Connect crea una nueva versión 1.0.1 y repite los pasos 9-11.
```

---

## ✅ Checklist final ANTES de "Submit for Review"

- [ ] PASO 1: Save to GitHub hecho + `REVENUECAT_WEBHOOK_SECRET` añadido en Render
- [ ] Mi ícono propio reemplaza `frontend/assets/images/icon.png` (1024×1024 PNG sin alpha)
- [ ] `eas build` exitoso (versión 1.0.0 build 1)
- [ ] Build subido a TestFlight con `eas submit`
- [ ] Probé en TestFlight en mi iPhone real → todo funciona
- [ ] Cambié idioma a inglés → toda la app + Terms/Privacy están en inglés
- [ ] Sandbox Tester probó una suscripción Premium con éxito
- [ ] Webhook de RevenueCat configurado y test enviado (200 OK)
- [ ] 6 screenshots EN subidos a la versión English
- [ ] 6 screenshots ES subidos a la versión Spanish
- [ ] Descripción + Keywords + Privacy URL llenos para EN y ES
- [ ] Privacy questionnaire completado
- [ ] App Review Information con demo account funcional
- [ ] IAP products `raxai_premium_monthly` y `raxai_pro_monthly1` con metadata + screenshot
- [ ] Click "Add for Review" → "Submit"

---

🚀 **¡Vamos! Empieza por el PASO 2.**

Cualquier error o pantalla rara, mándame screenshot y te ayudo en segundos.
