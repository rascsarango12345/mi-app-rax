#!/bin/bash
# ============================================================
# RAX AI - Script de configuración rápida después de clonar
# ============================================================
# Uso: bash setup.sh

set -e

echo "🚀 RAX AI - Setup automático"
echo ""

# Verificar dependencias
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 no instalado."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js no instalado. Descarga de https://nodejs.org"; exit 1; }
command -v yarn >/dev/null 2>&1 || npm install -g yarn

echo "📦 Instalando backend (Python)..."
cd backend
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Backend: copiamos .env.example → .env. Edítalo con tus llaves antes de arrancar."
fi
python3 -m pip install -r requirements.txt --quiet
echo "✅ Backend listo"
cd ..

echo ""
echo "📱 Instalando frontend (Expo)..."
cd frontend
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Frontend: copiamos .env.example → .env. Edita EXPO_PUBLIC_BACKEND_URL."
fi
yarn install --silent
echo "✅ Frontend listo"
cd ..

echo ""
echo "🎉 Todo listo. Próximos pasos:"
echo ""
echo "   1. Edita backend/.env con tus llaves (MongoDB, Stripe, Emergent)"
echo "   2. Edita frontend/.env con la URL de tu backend"
echo ""
echo "   3. En 2 terminales separadas:"
echo "        cd backend && uvicorn server:app --reload --port 8001"
echo "        cd frontend && yarn start"
echo ""
echo "   📚 Para producción lee DEPLOY_GUIDE.md"
echo "   📱 Para App Store lee APP_STORE_GUIDE.md"
