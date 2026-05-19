# RAX AI - PRD

**By AlexSarango** · "La Inteligencia que Piensa Contigo"

## Vision
Modern ChatGPT-style AI assistant with chat, image generation, voice, content tools, and premium tiers. Mobile (iOS/Android) + Web via Expo.

## Status: MVP v1.0 ✅ (22/22 backend tests passed)

## Features Implemented
### Authentication
- Email/password (JWT, bcrypt)
- Google OAuth (Emergent-managed)
- Guest mode
- Admin auto-detection by allowlist (admin@raxai.com, alex@alexsarango.com)

### AI Chat (Claude Sonnet 4.5)
- Multi-turn conversations with memory (LlmChat per session)
- Spanish/English support
- Conversation list + history persistence
- System prompt: "Eres RAX AI..."

### Image Generation (Gemini Nano Banana 2.5)
- 6 styles: realista, anime, futurista, gamer, caricatura, cinematico
- Base64 storage, quota-tracked

### Voice
- 4 voices (OpenAI TTS-1):
  - Sofía (nova) — female warm
  - Luna (shimmer) — female bright
  - Diego (onyx) — male deep
  - Alex (echo) — male clear
- Whisper-1 STT with mic recording (expo-av)

### Content Creator
- TikTok captions, Facebook posts, YouTube titles
- Viral ideas, scripts, logo ideas, business ideas

### File Analysis
- Image + document analysis via Claude vision

### Premium Tiers
- Free: 30 msgs/5 imgs day
- Premium ($9.99): 500 msgs/100 imgs
- Pro ($19.99): unlimited
- Apple Pay/Google Pay/Stripe/PayPal will activate at publish

### Admin Panel
- Users list (block/unblock, change plan)
- Stats: total users/msgs/imgs, premium/pro count, estimated revenue
- Idempotent seed endpoint

## Tech Stack
- Frontend: Expo React Native (SDK 54), expo-router, expo-av, reanimated
- Backend: FastAPI + Motor (MongoDB)
- LLMs: emergentintegrations (Claude Sonnet 4.5 + Nano Banana + Whisper + TTS)
- Storage: MongoDB
- Auth: JWT HS256

## Endpoints (all /api prefixed)
- `/auth/*`: register, login, guest, google/session, me
- `/conversations*`, `/chat/send`
- `/images/generate`, `/images`
- `/voice/tts`, `/voice/transcribe`, `/voice/voices`
- `/content/generate`
- `/files/analyze`
- `/admin/*`: users, stats, users/{id}/plan, users/{id}/block, seed-admin

## Future Roadmap
- Video generation (Sora 2)
- Music generation
- Voice cloning
- AI Avatars
- Prompts marketplace
- Stripe/Apple Pay/Google Pay integration at publish
