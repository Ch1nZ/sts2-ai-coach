#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DOTNET_ROOT="$PROJECT_DIR/.tools/dotnet"
export DOTNET_CLI_HOME="$PROJECT_DIR/.cache/dotnet-home"
export NUGET_PACKAGES="$PROJECT_DIR/.cache/nuget"
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_NOLOGO=1
export DOTNET_GENERATE_ASPNET_CERTIFICATE=false
export TMPDIR="$PROJECT_DIR/.cache/tmp"
mkdir -p "$TMPDIR" "$DOTNET_CLI_HOME" "$NUGET_PACKAGES"
