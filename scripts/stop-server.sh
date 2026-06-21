#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${PID_DIR:-$ROOT/runtime/pids}"

for name in api web; do
  pid_file="$PID_DIR/$name.pid"
  if [ -f "$pid_file" ]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "[Wiki AI RAG] Stopping $name ($pid)..."
      kill "$pid"
    fi
    rm -f "$pid_file"
  fi
done

echo "[Wiki AI RAG] Application processes stopped."
