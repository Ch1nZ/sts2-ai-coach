#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import json,socket,hashlib
from pathlib import Path
receipt=Path('.cache/production-install.json')
if not receipt.exists():
    raise SystemExit('First run: bash scripts/install-production.sh. Then enable the mod in the Steam game.')
data=json.loads(receipt.read_text())
mods=Path(data['game_dir'])/'SlayTheSpire2.app/Contents/MacOS/mods'
for name,expected in data['files'].items():
    p=mods/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Production mod files changed or are missing. Rebuild/reinstall before playing.')
with socket.socket() as s:
    if s.connect_ex(('127.0.0.1',18765))==0:
        raise SystemExit('The companion is already running: http://127.0.0.1:18765')
PY
echo 'Companion ready. Launch Slay the Spire 2 normally through Steam.'
echo 'Keep this window open while playing. Ctrl-C stops the companion without closing your game.'
exec .venv/bin/python -m spire.server
