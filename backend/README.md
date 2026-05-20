# RAX AI Backend

FastAPI backend for RAX AI mobile/web app.

## Stack
- Python 3.11+ · FastAPI · MongoDB (Motor) · JWT auth
- Integrations: Anthropic Claude 4.5, Google Gemini Nano Banana, OpenAI TTS/Whisper (via Emergent LLM key), Stripe Live, DuckDuckGo Search

## Local dev
```bash
cp .env.example .env  # then fill values
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

## Production deploy on Render
1. Push this repo to GitHub
2. Render → New → Blueprint → connect repo → it reads `render.yaml`
3. Set the `sync: false` env vars manually (see `.env.example`)
4. Deploy → Render gives you a URL like `https://raxai-backend.onrender.com`
5. Add that URL to `EXPO_PUBLIC_BACKEND_URL` in your Expo `eas.json` production env
6. Setup Stripe webhook → POST to `https://raxai-backend.onrender.com/api/stripe/webhook`

## Health check
`GET /api/health` → `{status, db, version, service}`

## API surface
`/api/auth/*`, `/api/chat/*`, `/api/image/*`, `/api/voice/*`, `/api/lens/scan`, `/api/journal/*`, `/api/roast`, `/api/shopper/recommend`, `/api/stripe/*`, `/api/admin/*`, `/api/support/*`, `/api/game/*`.
