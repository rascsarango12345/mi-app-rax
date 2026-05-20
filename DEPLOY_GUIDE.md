# 🚀 GUÍA DE DESPLIEGUE — RAX AI Backend a Producción

> **Objetivo:** Pasar tu backend de Emergent a Render.com + MongoDB Atlas + Webhook de Stripe configurado.
> **Tiempo total:** ~45 minutos
> **Costo mensual:** $0 (free tier) o ~$7/mes (recomendado para producción real)

---

## 📋 ARCHIVOS YA PREPARADOS PARA TI

Tu carpeta `/app/backend/` ya tiene listo:
- ✅ `render.yaml` — blueprint para Render (deploy con 1 click)
- ✅ `Procfile` — comando de arranque con gunicorn
- ✅ `runtime.txt` — versión de Python (3.11.9)
- ✅ `requirements.txt` — con `stripe`, `duckduckgo-search`, `gunicorn` agregados
- ✅ `.env.example` — plantilla de variables
- ✅ `README.md` — instrucciones técnicas
- ✅ `/api/health` — endpoint health check para Render
- ✅ `.gitignore` (en raíz `/app/`) — para no subir secrets a GitHub

---

## 🟦 PASO 1 — MongoDB Atlas (10 min)

MongoDB Atlas ofrece un cluster M0 **gratis** (512 MB, suficiente para empezar).

1. Crea cuenta en **https://www.mongodb.com/cloud/atlas/register**
2. **Build a Database** → **M0 FREE** → Region: cualquiera cerca de US-West (donde estará Render)
3. Cluster name: `raxai-cluster`
4. **Database Access** → Add New Database User:
   - Username: `raxai`
   - Password: genera uno seguro (guárdalo)
   - Built-in role: **Atlas admin**
5. **Network Access** → Add IP Address → **Allow Access from Anywhere** (`0.0.0.0/0`)
   - ⚠️ Esto está bien porque la app valida con auth + password, pero si quieres más seguridad, después añade solo las IPs de Render
6. **Database** → Connect → **Drivers** → Python → copia el connection string:
   ```
   mongodb+srv://raxai:<password>@raxai-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
7. ✅ **Reemplaza `<password>` con la contraseña real** y guarda este string — lo usarás en Paso 3

---

## 🟨 PASO 2 — Subir Código a GitHub (10 min)

Render necesita un repo de GitHub para deployar.

1. Crea cuenta en **https://github.com** si no tienes
2. **New repository** → Name: `rax-ai` → **Private** → Create
3. En tu computadora local (necesitas tener git instalado):
   ```bash
   # Descarga tu código de Emergent (ZIP) o clónalo
   cd ruta/donde/tengas/rax-ai

   # Inicializa git
   git init
   git add .
   git commit -m "Initial commit - RAX AI v1.0"

   # Conecta con GitHub (cambia tu usuario)
   git remote add origin https://github.com/TU_USUARIO/rax-ai.git
   git branch -M main
   git push -u origin main
   ```

4. ⚠️ **VERIFICA que `.env` NO se subió** (debe estar ignorado por `.gitignore`):
   ```bash
   git ls-files | grep .env
   ```
   Si aparece `backend/.env` algún resultado, ROTA inmediatamente todas tus llaves porque están públicas en GitHub.

---

## 🟧 PASO 3 — Render Web Service (15 min)

1. Crea cuenta en **https://render.com** (puedes loguearte con GitHub)
2. **New +** → **Blueprint**
3. Connect your GitHub account → selecciona el repo `rax-ai`
4. Render detectará `backend/render.yaml` automáticamente y propondrá crear el servicio `raxai-backend`
5. **Apply** → Render empezará a buildear

### Configurar variables de entorno
Mientras buildea, ve al servicio creado → **Environment** y pega estos valores:

| Variable | Valor | Notas |
|---|---|---|
| `MONGO_URL` | `mongodb+srv://raxai:TU_PASS@raxai-cluster.xxx.mongodb.net/?retryWrites=true&w=majority` | Del Paso 1 |
| `DB_NAME` | `raxai_database` | Ya viene |
| `EMERGENT_LLM_KEY` | `sk-emergent-87e368c67C65613825` | Tu llave actual |
| `JWT_SECRET` | (Render lo genera automático) | Ya configurado |
| `STRIPE_SECRET_KEY` | `sk_live_51TXiOHEW5rZXRvtsYr2aOBAZ4ncNFlL4...` | Tu llave nueva rotada |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_51TXiOHEW5rZXRvtsaKwvV7frAuS2...` | Tu llave pública |
| `STRIPE_WEBHOOK_SECRET` | (Pendiente — Paso 5) | Se obtiene después |

6. **Manual Deploy** → Deploy → espera ~5 min
7. Cuando esté `Live`, Render te dará una URL como:
   ```
   https://raxai-backend.onrender.com
   ```
8. **Verifica que funciona:**
   - Abre en navegador: `https://raxai-backend.onrender.com/api/health`
   - Deberías ver: `{"status":"healthy","db":"ok","version":"1.0.0","service":"rax-ai-backend"}`
   - ✅ Si ves esto, el backend está vivo y conectado a MongoDB Atlas

---

## 🟩 PASO 4 — Apuntar la App al Backend de Producción

Edita `/app/frontend/eas.json`:

```json
{
  "build": {
    "production": {
      "autoIncrement": true,
      "env": {
        "EXPO_PUBLIC_BACKEND_URL": "https://raxai-backend.onrender.com"
      }
    }
  }
}
```

Cuando hagas `eas build --profile production`, la app móvil usará el backend de Render.

---

## 🟪 PASO 5 — Configurar el Webhook de Stripe (10 min)

Esta es la parte D — el webhook es CRÍTICO para que se actualicen los estados de suscripciones (renovaciones, cancelaciones, pagos fallidos).

1. Ve a **https://dashboard.stripe.com/webhooks**
2. **Add endpoint**
3. **Endpoint URL:**
   ```
   https://raxai-backend.onrender.com/api/stripe/webhook
   ```
4. **Description:** `RAX AI Production Webhook`
5. **Listen to:** Events on your account
6. **Select events to listen to** → marca estos 7 eventos críticos:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`
   - ✅ `charge.refunded`
7. **Add endpoint** → se crea
8. **Click en el endpoint recién creado** → **Reveal** el **Signing secret** (empieza con `whsec_...`)
9. Copia ese `whsec_...`
10. Vuelve a **Render** → tu servicio `raxai-backend` → **Environment** → edita:
    - `STRIPE_WEBHOOK_SECRET` = `whsec_xxxxxxxxxxxxx` (el que copiaste)
11. **Save Changes** → Render reiniciará el servicio (~30 seg)

### Probar que el webhook funciona
1. En la página del webhook en Stripe → **Send test webhook**
2. Selecciona `checkout.session.completed` → **Send test webhook**
3. Verás respuesta:
   - ✅ `200 OK` = webhook funciona perfecto
   - ❌ `400/500` = revisa los logs de Render

---

## 🟥 PASO 6 — Verificación Final End-to-End

Prueba que toda la cadena funciona:

```bash
# 1. Backend vivo
curl https://raxai-backend.onrender.com/api/health
# → {"status":"healthy","db":"ok",...}

# 2. Stripe config funciona
curl https://raxai-backend.onrender.com/api/stripe/config
# → {"premium":{...},"pro":{...}}

# 3. Crear cuenta admin en producción
curl -X POST https://raxai-backend.onrender.com/api/admin/seed-admin \
  -H "Content-Type: application/json"
# → ok
```

Luego intenta loguearte desde la app móvil apuntando al backend nuevo y suscríbete con una tarjeta de prueba.

---

## ⚠️ NOTAS IMPORTANTES SOBRE COSTOS

| Componente | Free Tier | Recomendado para producción |
|---|---|---|
| **MongoDB Atlas** | M0 (512 MB) gratis para siempre | Suficiente hasta ~5K usuarios. Después M10 = $9/mes |
| **Render Free** | Web service duerme después de 15 min sin tráfico (cold start ~30 seg) | **Starter $7/mes** = siempre activo, no duerme |
| **Total mes 1** | $0 | $7 |
| **Total mes 12+ (con tracción)** | $0-7 | $16-50 |

📌 **Mi recomendación:** Empieza con Render Free para validar. Cuando tengas 50+ usuarios activos, sube a Starter $7/mes (el cold start de 30 seg molesta a usuarios).

---

## 🆘 PROBLEMAS COMUNES

### "Build failed" en Render
- Revisa los logs → casi siempre es un paquete que falta en `requirements.txt`
- Solución: agrégalo y haz `git push` → Render redeploya automático

### "Cannot connect to MongoDB"
- Verifica que en Atlas → Network Access tengas `0.0.0.0/0`
- Verifica que el password en el `MONGO_URL` esté URL-encoded si tiene caracteres especiales

### "Stripe webhook returns 401"
- Esto es PORQUE NO tienes el `STRIPE_WEBHOOK_SECRET` configurado. Completa el Paso 5.

### "App móvil muestra error de conexión"
- Verifica que `EXPO_PUBLIC_BACKEND_URL` en `eas.json` apunte al URL correcto
- Rebuildea: `eas build --profile production`

---

## 🎯 SIGUIENTE PASO DESPUÉS DE DESPLEGAR

Cuando tengas el backend en producción funcionando:
1. **Build móvil con EAS** → `eas build --platform ios --profile production`
2. **Subir a TestFlight** → invita a 5-10 amigos a probar
3. **Submit to App Store** → review de Apple (1-7 días)

Ver `/app/APP_STORE_GUIDE.md` para los siguientes pasos.

---

## 🤝 ¿NECESITAS AYUDA?

Hazme saber en qué paso te atoraste y te guío específicamente. Por ejemplo:
- "Atlas no me deja crear el cluster"
- "Render me da error en el build"
- "El webhook devuelve 400"
- "No sé cómo subir a GitHub desde mi Mac"

¡Vamos! 🚀
