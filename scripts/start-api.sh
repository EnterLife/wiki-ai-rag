#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"

if [ ! -x "$API_DIR/.venv/bin/python" ]; then
  echo "[Wiki AI RAG] Backend venv is missing. Run scripts/setup-api-venv.sh first."
  exit 1
fi

echo "[Wiki AI RAG] Starting API on http://$API_HOST:$API_PORT"
cd "$API_DIR"
exec .venv/bin/python -m uvicorn wiki_ai_rag_api.main:app --host "$API_HOST" --port "$API_PORT"
