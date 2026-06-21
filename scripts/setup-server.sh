#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[Wiki AI RAG] Preparing server runtime..."
bash "$ROOT/scripts/setup-api-venv.sh"
bash "$ROOT/scripts/setup-web.sh"

echo "[Wiki AI RAG] Server runtime is ready."
echo "Next: copy infra/.env.example to .env, edit it, then run scripts/start-server.sh"
