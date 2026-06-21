#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${LOG_DIR:-$ROOT/runtime/logs}"
PID_DIR="${PID_DIR:-$ROOT/runtime/pids}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-5173}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:$API_PORT/api/v1}"

mkdir -p "$LOG_DIR" "$PID_DIR"

bash "$ROOT/scripts/start-infra.sh"

echo "[Wiki AI RAG] Starting API in background..."
(
  cd "$ROOT"
  API_HOST="$API_HOST" API_PORT="$API_PORT" bash scripts/start-api.sh
) > "$LOG_DIR/api.log" 2>&1 &
echo $! > "$PID_DIR/api.pid"

echo "[Wiki AI RAG] Starting web UI in background..."
(
  cd "$ROOT"
  WEB_HOST="$WEB_HOST" WEB_PORT="$WEB_PORT" VITE_API_BASE_URL="$VITE_API_BASE_URL" bash scripts/start-web.sh
) > "$LOG_DIR/web.log" 2>&1 &
echo $! > "$PID_DIR/web.pid"

echo "[Wiki AI RAG] API: http://127.0.0.1:$API_PORT/api/v1/health"
echo "[Wiki AI RAG] Web: http://127.0.0.1:$WEB_PORT"
echo "[Wiki AI RAG] Logs: $LOG_DIR"
echo "[Wiki AI RAG] PIDs: $PID_DIR"
