#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[Wiki AI RAG] Starting PostgreSQL and Qdrant..."
cd "$ROOT"
docker compose -f infra/docker-compose.yml up -d postgres qdrant

echo "[Wiki AI RAG] Infrastructure started."
echo "Qdrant dashboard: http://localhost:6333/dashboard"
