# 🚀 GUÍA COMPLETA: Publicar RAX AI en App Store y Google Play

> **App Lista:** RAX AI v1.0.0 | Bundle ID: `com.sarangocabrera.raxai`

---

## 📋 RESUMEN DE LO QUE NECESITAS

| Concepto | Costo | Tiempo |
|---|---|---|
| Apple Developer Program | **$99 USD/año** | 24-48 hrs aprobación |
| Google Play Developer | **$25 USD (pago único)** | 1-2 días |
| Expo EAS Build (cloud) | **Gratis hasta 30 builds/mes** | ~30 min por build |
| Backend en producción (Render/Railway) | **$5-7 USD/mes** | 30 min setup |
| **TOTAL primer año** | **~$130 USD** | ~1 semana de trabajo |

---

## 🟦 PASO 1 — CREAR CUENTAS DE DESARROLLADOR

### Apple Developer (App Store)
1. Ve a **https://developer.apple.com/programs/enroll/**
2. Inicia sesión con tu Apple ID
3. Si vas a vender como persona individual: selecciona "Individual" ($99/año)
4. Si tienes una empresa registrada (R A S C): selecciona "Organization" — requiere DUNS Number gratis
5. Paga los $99 USD
6. ⏳ Espera 24-48 horas para activación

### Google Play Developer
1. Ve a **https://play.google.com/console/signup**
2. Paga los $25 USD (1 sola vez)
3. Completa tu perfil de desarrollador
4. ✅ Activación inmediata

---

## 🟨 PASO 2 — DESPLEGAR EL BACKEND EN PRODUCCIÓN

Tu backend actual corre en este entorno de Emergent. Para producción necesitas un host estable:

### Opción A: Render.com (recomendado, fácil)
1. Crea cuenta en **https://render.com**
2. New → Web Service → Conectar tu GitHub
3. Sube el código del backend a un repo de GitHub primero
4. Selecciona tu repo, branch `main`, root `/backend`
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
7. Agrega Environment Variables (las que están en `/app/backend/.env`):
   - `MONGO_URL` → usa MongoDB Atlas (gratis) en https://www.mongodb.com/atlas
   - `EMERGENT_LLM_KEY`
   - `STRIPE_SECRET_KEY` ⚠️ ROTA TU LLAVE PRIMERO
   - `STRIPE_WEBHOOK_SECRET`
   - `JWT_SECRET` (genera uno nuevo random largo)
8. Plan: Starter $7/mes (siempre activo) o Free (sleeps después de 15 min)
9. Render te dará una URL: `https://raxai-backend.onrender.com`

### Opción B: Railway.app (alternativa)
Similar a Render pero a veces más rápido. **$5/mes** después de los primeros $5 de crédito.

---

## 🟧 PASO 3 — ACTUALIZAR LA APP CON LA URL DE PRODUCCIÓN

Edita `/app/frontend/eas.json`:
```json
"production": {
  "env": {
    "EXPO_PUBLIC_BACKEND_URL": "https://raxai-backend.onrender.com"
  }
}
```

---

## 🟪 PASO 4 — GENERAR ICONOS Y SCREENSHOTS

### Iconos requeridos (ya tienes en /app/frontend/assets/images/):
- `icon.png` → 1024x1024 (App Store)
- `adaptive-icon.png` → 1024x1024 (Android)
- `splash-icon.png` → 200x200 (splash screen)

📌 **Recomendación:** usa **https://icon.kitchen** o **https://www.canva.com** para generar todos los tamaños desde tu logo. Diseño sugerido: fondo negro con la letra "R" en neón azul/verde.

### Screenshots requeridos para App Store:
- iPhone 6.7" (iPhone 15 Pro Max): **1290 x 2796 px** — 3 a 10 imágenes
- iPhone 6.5" (iPhone 11 Pro Max): **1242 x 2688 px** — 3 a 10 imágenes
- iPad Pro 12.9": **2048 x 2732 px** (opcional pero recomendado)

📌 **Sugerencia:** captura las pantallas más impresionantes:
1. Splash screen "RAX AI · La Inteligencia que Piensa Contigo"
2. Chat con respuesta de Claude
3. Imagen generada
4. Estudio Mágico (los 5 cards de gradientes)
5. Cámara Mágica con un objeto escaneado
6. Modo Roast con foto
7. Diario Inteligente
8. Premium tiers

Para crear screenshots bonitos: **https://app.previewed.app** o **https://screenshots.pro**

---

## 🟥 PASO 5 — INSTALAR EAS CLI Y BUILDEAR

En tu computadora (Mac/PC/Linux):

```bash
# Instalar EAS CLI
npm install -g eas-cli

# Login en Expo
eas login

# En la carpeta del proyecto
cd /ruta/a/rax-ai/frontend

# Configurar EAS (la primera vez)
eas build:configure

# Build iOS
eas build --platform ios --profile production

# Build Android
eas build --platform android --profile production
```

⏳ Cada build tarda 15-30 minutos en la nube de Expo. Recibirás un link al `.ipa` (iOS) y `.aab` (Android).

---

## 🍎 PASO 6 — SUBIR A APP STORE (iOS)

### A. Crear listing en App Store Connect
1. Ve a **https://appstoreconnect.apple.com**
2. My Apps → "+" → New App
3. Selecciona:
   - Platform: iOS
   - Name: **RAX AI**
   - Primary Language: Spanish (Mexico) o English
   - Bundle ID: `com.sarangocabrera.raxai` (el que pusiste en `app.json`)
   - SKU: `raxai-001`
4. Click "Create"

### B. Completar la información de la app
- **App Icon**: sube el icon.png 1024x1024
- **Screenshots**: sube las que generaste
- **Description**: Te dejo un texto sugerido abajo ⬇️
- **Keywords**: chatgpt, ia, inteligencia artificial, español, imágenes, voz, rax, ai chat
- **Support URL**: `https://raxai.com/support` (puedes crear una landing simple)
- **Privacy Policy URL**: `https://raxai.com/privacy` (requerida — abajo te explico)
- **Category**: Productivity (primary) + Lifestyle (secondary)
- **Age Rating**: completa el cuestionario (será 12+ por contenido de IA)
- **Price**: Free (con compras dentro de la app)

### C. Compras dentro de la app (In-App Purchases)
⚠️ **MUY IMPORTANTE**: Si tu app tiene suscripciones, Apple **OBLIGA** a usar su sistema de pagos in-app (NO Stripe en iOS — se rechaza). Hay dos rutas:

**Ruta 1 (recomendada para empezar):** Marcar la app como "no comercia con bienes/servicios digitales". Las suscripciones se gestionan SOLO en tu web `raxai.com`, y la app dice "Suscríbete en raxai.com". Es lo que hacen Netflix, Spotify free, etc. Apple lo permite.

**Ruta 2 (más ingresos pero +30% comisión):** Implementar StoreKit / RevenueCat para in-app purchases. Apple se queda 30% el primer año, 15% después. Esta opción es para fase 2.

### D. Subir el build
- En la carpeta del proyecto: `eas submit --platform ios --profile production`
- O súbelo manualmente con Transporter (app de Mac) usando el .ipa
- Espera 5-15 min para procesamiento
- Selecciona el build en App Store Connect → "Add for Review"
- Llena "What's New": "Versión inicial de RAX AI - tu IA personal."
- **Submit for Review**

### E. Review de Apple
- ⏳ Tarda 1-7 días (promedio 24h en 2026)
- ⚠️ Razones comunes de rechazo:
  - Funciones que no funcionan en review (asegúrate de que el guest login funciona)
  - Faltan iconos o screenshots
  - Privacy Policy no accesible
  - Stripe directo (usar Ruta 1 arriba)
  - Demo account no provisto → en notas, dale a Apple: `Email: rascsarango12345@gmail.com / Pass: <tu password>`

---

## 🤖 PASO 7 — SUBIR A GOOGLE PLAY (Android)

1. Ve a **https://play.google.com/console**
2. Create App → Name: RAX AI → Default language: Spanish
3. Free / Paid: Free
4. Completar las 4 secciones obligatorias:
   - **App content**: Privacy Policy URL, Ads (yes/no), Target audience, Data safety
   - **Main store listing**: iconos, screenshots, descripción
   - **App releases**: Production → New release → sube el .aab
5. Submit
6. ⏳ Review: 1-3 días (más rápido que Apple)

---

## 📄 PASO 8 — PÁGINA DE PRIVACIDAD Y TÉRMINOS (OBLIGATORIO)

Necesitas hospedar 2 URLs públicas. Opciones:

### Opción A: Usar el dominio raxai.com
- Compra el dominio en Namecheap ($10/año)
- Crea una landing simple en Vercel (gratis) con páginas:
  - `/privacy` → política de privacidad
  - `/terms` → términos de uso

### Opción B: Usar GitHub Pages (gratis)
- Crea repo `raxai-legal` en GitHub
- Sube `privacy.html` y `terms.html`
- Activa GitHub Pages → URLs serán `https://sarangocabrera.github.io/raxai-legal/privacy`

📌 **Te dejo plantilla de Privacy Policy genérica abajo** ⬇️ (sólo cambia datos personales).

---

## ✍️ TEXTO SUGERIDO PARA EL LISTING

**Title:** RAX AI · Asistente Inteligente

**Subtitle (iOS):** Tu IA personal en español

**Description (4000 chars max):**
```
🚀 RAX AI es la inteligencia artificial más avanzada y rápida del mercado en español.

✨ TODO LO QUE PUEDES HACER CON RAX AI:

🗣️ CHAT INTELIGENTE
Conversaciones naturales con memoria. La IA recuerda todo de ti.

🎨 GENERACIÓN DE IMÁGENES
Crea imágenes realistas, anime, futuristas con una sola descripción.

🎙️ VOZ COMPLETA
Transcripción de voz + 4 voces premium (2 masculinas, 2 femeninas).

📸 CÁMARA MÁGICA
Apunta a cualquier cosa y descubre qué es. Plantas, comida, ropa, animales.

🌙 DIARIO INTELIGENTE
Escribe cómo te sientes. RAX recuerda y te da insights personalizados.

🔥 MODO ROAST
Roastéate o roastea a tus amigos con humor inteligente.

🛍️ PERSONAL SHOPPER
Te encuentra los mejores productos al mejor precio.

✍️ HERRAMIENTAS DE CREADOR
Captions para TikTok, posts para Facebook, ideas virales.

🎮 MINI-JUEGO
Word scramble para relajar tu mente.

🌐 5 IDIOMAS
Español, English, हिन्दी, 中文, Русский

💎 PLANES
• Gratis: chat ilimitado limitado, 5 imágenes/día
• Premium ($5.99/mes): más generaciones, prioridad
• Pro ($15.99/mes): TODO ilimitado

🔒 PRIVACIDAD
Tus datos son tuyos. No vendemos info personal.

Hecho con ❤️ por SARANGO CABRERA — R A S C
```

---

## 📋 PLANTILLA DE PRIVACY POLICY (cópiala y adapta)

```
PRIVACY POLICY FOR RAX AI

Last updated: 19 May 2026
Operator: SARANGO CABRERA (R A S C)
Contact: rascsarango12345@gmail.com

1. INFORMATION WE COLLECT
- Account info: name, email, password (encrypted)
- Chat content (stored to provide service)
- Device info: OS, language, timezone
- Usage statistics (anonymized)

2. HOW WE USE IT
- Provide AI services (Claude, Gemini, OpenAI APIs)
- Process payments (Stripe — see their privacy policy)
- Improve the service (aggregated, anonymous)

3. WHAT WE DO NOT DO
- We do not sell your data.
- We do not show ads inside the app.
- We do not use your content to train external models.

4. YOUR RIGHTS
- Delete your account anytime in Settings.
- Request data export by emailing us.
- GDPR / CCPA compliant.

5. CHILDREN
RAX AI is for users 12+. We do not knowingly collect data from kids under 12.

6. CONTACT
Email: rascsarango12345@gmail.com
```

---

## ⚠️ ANTES DE PUBLICAR — CHECKLIST CRÍTICO

- [ ] Rotar la API key de Stripe (la que compartiste antes)
- [ ] Backend desplegado en Render/Railway con URL pública
- [ ] MongoDB Atlas configurado y conectado
- [ ] Variable `EXPO_PUBLIC_BACKEND_URL` apunta al backend de producción
- [ ] Probar la app en TestFlight (iOS) o Internal Testing (Android) con usuarios reales
- [ ] Privacy Policy y Terms hospedados con URL pública
- [ ] Demo account (`rascsarango12345@gmail.com`) funciona para reviewers de Apple
- [ ] Eliminar cualquier "console.log" con datos sensibles
- [ ] Probar el flujo guest login (Apple exige que funcione sin crear cuenta)
- [ ] Iconos y splash screen finales (no los de Expo default)
- [ ] Si vas a vender suscripciones: redirigir a tu web fuera de la app iOS

---

## 🆘 ¿NECESITAS AYUDA EN ALGÚN PASO?

Hazme saber en qué paso estás y te guío específicamente:
- "Necesito ayuda con Render"
- "Hazme la página de privacy/terms"
- "Genérame los textos del listing"
- "Diseña los screenshots de App Store"

🚀 **¡Buena suerte con RAX AI!**
