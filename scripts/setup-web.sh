#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT/apps/web"

echo "[Wiki AI RAG] Installing frontend dependencies..."
cd "$WEB_DIR"
npm install

echo "[Wiki AI RAG] Frontend dependencies are ready."
