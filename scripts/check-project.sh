#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[Wiki AI RAG] Running backend checks..."
cd "$ROOT/apps/api"
.venv/bin/python -m compileall src tests
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests

echo "[Wiki AI RAG] Running frontend checks..."
cd "$ROOT/apps/web"
npm run lint
npm run build
npm audit

echo "[Wiki AI RAG] All checks passed."
