#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT/apps/web"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-5173}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
export VITE_API_BASE_URL

echo "[Wiki AI RAG] Building web UI..."
cd "$WEB_DIR"
npm run build

echo "[Wiki AI RAG] Starting web preview on http://$WEB_HOST:$WEB_PORT"
echo "[Wiki AI RAG] API base URL: $VITE_API_BASE_URL"
exec npm run preview -- --host "$WEB_HOST" --port "$WEB_PORT"
