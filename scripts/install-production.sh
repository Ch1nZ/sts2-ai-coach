#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_DIR"
GAME_DIR="${1:-$HOME/Library/Application Support/Steam/steamapps/common/Slay the Spire 2}"
"$DOTNET_ROOT/dotnet" build "$PROJECT_DIR/mod/STS2Bridge/STS2_MCP.csproj" \
  -c Release -o "$PROJECT_DIR/artifacts/production" "-p:STS2GameDir=$GAME_DIR" -p:NuGetAudit=false
.venv/bin/python scripts/install-production.py --game-dir "$GAME_DIR"
