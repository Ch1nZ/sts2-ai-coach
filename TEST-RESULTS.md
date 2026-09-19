# Slay the Spire 2 integration test

Tested on 2026-09-19 on this Apple Silicon Mac.

**Result: STS2MCP builds and reads live combat state with the installed v0.107.1 game.**

## Evidence

- Upstream: https://github.com/Gennadiyev/STS2MCP
- Revision: `55e064850a68f3b4cde7e5fd525bf9b2dec4e885` (v0.4.0).
- Built from source with workspace-local .NET SDK 9.0.318: zero errors and zero warnings.
- Health endpoint returned `status: ok`.
- Read main menu, character selection, map, and combat state.
- Started a disposable Ironclad run; captured five cards, 3 energy, 80 HP, Burning Blood, and a Nibbit with 44 HP intending 12 attack damage.
- Played one Defend solely to verify live updates. Next snapshot showed energy 3 → 2, block 0 → 5, hand count 5 → 4, discard count 0 → 1.
- All 517 original save/config files matched their pre-test SHA-256 hashes. No files were added or removed in the original save directory.

Snapshots and logs are under `artifacts/`, including `state-menu.json`, `state-event.json` (map state), `state-combat-before.json`, `state-combat-after.json`, `build.log`, and `save-integrity-result.json`.

## Isolation

- Source: `vendor/STS2MCP`; upstream MIT license retained there.
- SDK: `.tools/dotnet`; build caches: `.cache`; outputs: `artifacts/mod`.
- Separate copy of the locally owned game: `.runtime/SlayTheSpire2.app`. No changes to the original Steam installation.
- Disposable settings and saves: `.runtime/userdata`. The copied game's `override.cfg` selects a unique user-data name. A temporary symlink in Application Support points that unique name into this workspace; the link was removed after testing.
- macOS sandbox policy denies file writes outside the workspace (except `/dev/null`) and network access except localhost. Steam initialization is explicitly disabled with the game's `--force-steam=off` option. The copied Steam native libraries were also renamed to prevent accidental Steam initialization if this option regresses.
- No Homebrew installs, shell profile edits, global Python packages, global dotnet tool installation, or background service registration.
- Test process stopped and temporary link removed at completion. Standard OS process bookkeeping and the SDK installer's temporary download are not a full virtual-machine environment.

## Repeat locally

Run `bash scripts/build.sh` to rebuild. Run `bash scripts/launch-isolated.sh` to start the disposable headless game; stop with Ctrl-C. In another terminal run `python3 scripts/probe_state.py` to save its state. Paths in the launch environment are specific to this workspace and Mac.

The upstream mod still contains action endpoints. `probe_state.py --action` is an explicit test harness, used only on the disposable game. The recommendation product should disable these endpoints. No Jev integration or recommendation UI has been implemented yet.

## Scope

This validates build compatibility and live state extraction in a headless, Steam-disabled copy of the actual installed game. It does not yet validate normal Steam-connected play, graphical overlay behavior, every card or screen, multiplayer, or compatibility with future game updates. No screenshot/OCR was used. A small state adapter remains necessary before sending input to Jev.
