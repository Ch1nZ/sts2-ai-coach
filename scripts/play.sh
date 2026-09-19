#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
APP_PID=''
cleanup() {
  if [ -n "$APP_PID" ]; then
    kill -TERM "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT
.venv/bin/python - <<'PY'
import socket
for port in (18765, 15526):
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            raise SystemExit('Showing Your Hand or its game bridge is already running. Use the existing session.')
PY
.venv/bin/python -m spire.server > artifacts/app.log 2>&1 &
APP_PID=$!
bash scripts/launch-isolated.sh
