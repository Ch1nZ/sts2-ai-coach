#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_DIR"
mkdir -p .tools .runtime artifacts
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
if [ ! -x "$DOTNET_ROOT/dotnet" ]; then
  curl -fsSL https://dot.net/v1/dotnet-install.sh -o .tools/dotnet-install.sh
  bash .tools/dotnet-install.sh --version 9.0.318 --install-dir "$DOTNET_ROOT" --no-path
fi
if [ ! -d .runtime/SlayTheSpire2.app ]; then
  cp -cR "$HOME/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.app" .runtime/SlayTheSpire2.app
fi
.venv/bin/python - <<'PY'
from pathlib import Path
import json
root=Path.cwd()
user=root/'.runtime/userdata'
user.mkdir(parents=True,exist_ok=True)
name='ShowingYourHand-STS2-Dev'
cfg='[application]\nconfig/use_custom_user_dir=true\nconfig/custom_user_dir_name="'+name+'"\n'
for folder in ['MacOS','Resources']:
    (root/'.runtime/SlayTheSpire2.app/Contents'/folder/'override.cfg').write_text(cfg)
for p in (root/'.runtime/SlayTheSpire2.app/Contents/Resources').glob('data_*/libsteam_api.dylib'):
    p.rename(p.with_suffix('.dylib.disabled-for-isolated-test'))
settings=user/'default/1/settings.save'
if not settings.exists():
    settings.parent.mkdir(parents=True,exist_ok=True)
    settings.write_text(json.dumps({'schema_version':5,'mod_settings':{'mods_enabled':True,'mod_list':[]}}))
(root/'.runtime/SlayTheSpire2.app/Contents/MacOS/mods').mkdir(exist_ok=True)
(root/'.runtime/test.sb').write_text('(version 1)\n(allow default)\n(deny file-write*)\n(allow file-write* (subpath "'+str(root)+'") (literal "/dev/null"))\n(deny network*)\n(allow network-inbound (local ip "localhost:*"))\n(allow network-outbound (remote ip "localhost:*"))\n')
PY
bash scripts/build-bridge.sh
