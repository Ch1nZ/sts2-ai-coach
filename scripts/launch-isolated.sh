#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_DIR"
TEST_LINK="$HOME/Library/Application Support/ShowingYourHand-STS2-Dev"
if [ -e "$TEST_LINK" ] || [ -L "$TEST_LINK" ]; then
  echo 'Test save-folder link already exists; inspect it before starting another test.' >&2
  exit 1
fi
ln -s "$PROJECT_DIR/.runtime/userdata" "$TEST_LINK"
GAME_PID=''
cleanup() {
  if [ -n "$GAME_PID" ]; then
    kill -KILL "$GAME_PID" 2>/dev/null || true
    wait "$GAME_PID" 2>/dev/null || true
  fi
  if [ -L "$TEST_LINK" ] && [ "$(readlink "$TEST_LINK")" = "$PROJECT_DIR/.runtime/userdata" ]; then
    unlink "$TEST_LINK"
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
DISPLAY_ARGS=(--windowed --resolution 1440x900)
if [ "${1:-}" = "--headless" ]; then DISPLAY_ARGS=(--headless); fi
sandbox-exec -f "$PROJECT_DIR/.runtime/test.sb" \
  "$PROJECT_DIR/.runtime/SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2" \
  "${DISPLAY_ARGS[@]}" --max-fps 30 --force-steam=off \
  --log-file "$PROJECT_DIR/artifacts/mod-runtime.log" \
  > "$PROJECT_DIR/artifacts/mod-console.log" 2>&1 &
GAME_PID=$!
wait "$GAME_PID"
