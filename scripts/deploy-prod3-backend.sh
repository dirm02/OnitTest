#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/onittest-abc-energy"
REPO_URL="https://github.com/dirm02/OnitTest.git"

if [ ! -d "${APP_DIR}/.git" ]; then
  rm -rf "${APP_DIR}"
  git clone "${REPO_URL}" "${APP_DIR}"
else
  git -C "${APP_DIR}" fetch origin main
  git -C "${APP_DIR}" reset --hard origin/main
fi

cd "${APP_DIR}"

cat > backend/.env <<'ENVEOF'
PROJECT_NAME=onit_test
DEBUG=true
ENVIRONMENT=local
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=onit_test
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
API_KEY=change-me-in-production
GOOGLE_API_KEY=
AI_MODEL=gemini-2.5-flash
CORS_ORIGINS=["https://dirm02-onittest-abc-energy.netlify.app","http://52.165.83.50:8000"]
ENVEOF

docker rm -f onit_test_db onit_test_backend >/dev/null 2>&1 || true
docker compose -f docker-compose.azure.yml down --remove-orphans
docker compose -f docker-compose.azure.yml up -d --build db app
docker compose -f docker-compose.azure.yml ps
