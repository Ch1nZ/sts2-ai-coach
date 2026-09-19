#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
"$DOTNET_ROOT/dotnet" build "$PROJECT_DIR/mod/STS2Bridge/STS2_MCP.csproj" -c Release -o "$PROJECT_DIR/artifacts/bridge" "-p:STS2GameDir=$PROJECT_DIR/.runtime" -p:NuGetAudit=false
cp "$PROJECT_DIR/artifacts/bridge/STS2_MCP.dll" "$PROJECT_DIR/.runtime/SlayTheSpire2.app/Contents/MacOS/mods/STS2_MCP.dll"
cp "$PROJECT_DIR/mod/STS2Bridge/mod_manifest.json" "$PROJECT_DIR/.runtime/SlayTheSpire2.app/Contents/MacOS/mods/STS2_MCP.json"
