#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -gt 0 ]; then exec python3 manage.py setup --game-dir "$1"; fi
exec python3 manage.py setup
