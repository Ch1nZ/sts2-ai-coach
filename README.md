# Showing Your Hand

A local Slay the Spire 2 companion. Play the game yourself; Jev recommends one next action through OpenRouter. No explanations, chat, or automatic gameplay.

## Run on this Mac

For the existing local installation, the isolated environment and key are already configured. For a fresh clone, run `bash scripts/setup.sh`, then copy `.env.example` to `.env.local`, fill in your OpenRouter key and run `chmod 600 .env.local`.

Double-click **Start Showing Your Hand.command** in this folder, or use:

```sh
cd /path/to/showing-your-hand
bash scripts/play.sh
```

This starts the recommendation service and the separate game copy. The recommendation appears at the top of the game. Continue the disposable run or start a new one normally. Your Steam save is not used. The first graphical launch may take time to compile shaders.

Optional companion panel: http://127.0.0.1:18765 — includes Pause, Resume and Retry. Closing the browser does not pause if the game overlay is still connected. Quit the game to stop a session launched with `play.sh`; Ctrl-C also stops it.

When running development processes separately:

```sh
bash scripts/start.sh
# In another terminal:
bash scripts/launch-isolated.sh
```

Use `--headless` with `launch-isolated.sh` for state-reader tests. It does not start a run automatically.

## Setup and secrets

`bash scripts/setup.sh` prepares local Python/.NET environments and the separate game copy on this Mac. It uses no global package installation or shell profile edits. The script targets this Mac's Steam path and v0.107.1; this is not yet a cross-platform installer.

The key is in `.env.local`, permission `600`, excluded from Git. Do not paste it into source files. `.env.example` lists supported settings. The default model is `typesafe/jev-1.13`. Only the backend reads the key; neither the browser nor the mod receives it. Game snapshots and candidate actions are sent to OpenRouter when a decision is needed.

## Behavior

- Reads game state four times per second; waits for 0.5 seconds of unchanged state before deciding.
- Uses OpenRouter's `POST https://openrouter.ai/api/alpha/decisions` with typed choice questions, not chat completions.
- Sends one request per unchanged decision state, with at least two seconds between requests and at most 120 requests per service session. Retry is explicit after a failed call. A sole available action needs no model request.
- Clears recommendations when a state change is observed, on disconnect, and when paused. Responses from a previous state are discarded.
- Builds candidates for combat, card rewards, maps, shops, events, campfires, treasure, and ordinary selection prompts. Unknown screens/targeting types wait for manual input. Combat recommendations include potions and ending the turn.
- Supplies the permanent deck, current hand and unordered draw-pile contents. Never treats the draw-pile list as the hidden draw order.
- The local model choice is constrained to supplied candidates. This is a direct Jev policy, not a combat simulator or a demonstrated optimal strategy.

## Components

| Location | Purpose |
|---|---|
| `spire/decisions.py` | Candidate generation and decision contract |
| `spire/clients.py` | Local state reader, local secret loading, OpenRouter client |
| `spire/engine.py` | Polling, stable-state checks, stale-result rejection and request limits |
| `spire/server.py`, `spire/web/` | Local service and compact companion panel |
| `mod/STS2Bridge/` | Modified STS2MCP reader and in-game recommendation display |
| `scripts/` | Local setup, build, run and integration checks |
| `tests/` | Offline decision and concurrency regression checks |

The bridge accepts only `GET /` and `GET /api/v1/singleplayer`. All control requests return 405. State queries no longer open shops or chests; they tell the player to open them. The upstream test client remains in `scripts/probe_state.py` for historical testing, but its action requests are rejected by this build.

## Isolation

Source, Python environment, SDK, dependency caches, game copy and disposable saves live in this project. The game runs under a macOS sandbox that prevents writes outside this workspace and disables non-local network connections. Steam is disabled for the copied game; the normal Steam installation is untouched. A temporary uniquely named Application Support symlink points to the disposable saves while running and is removed on exit. The recommendation service can reach OpenRouter independently of the game's network restriction.

The app is a local development prototype, not a full virtual machine. Standard operating-system process bookkeeping still occurs. If forcibly killing the launcher prevents cleanup, remove only the `ShowingYourHand-STS2-Dev` symlink after verifying the copied game has stopped.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
bash scripts/build-bridge.sh
.venv/bin/python scripts/live-check.py artifacts/state-combat-before.json
```

The last command makes one billed OpenRouter request. Never rebuild/copy the mod while the isolated game is running; quit first.

Validated on STS2 v0.107.1: bridge builds with no warnings/errors; live combat state includes the 10-card deck; OpenRouter returned a valid action using `typesafe/jev-1.13-20260917`; both the connected companion panel and the in-game overlay visibly displayed `Play Bash → Nibbit (enemy 1)`. Offline tests cover stale responses, paused requests, deduplication, budgets, targeting and unavailable actions. Broader mechanics, other characters, multiplayer, future patches, and normal Steam-connected play are not yet validated.

## Upstream

The bridge is based on [STS2MCP](https://github.com/Gennadiyev/STS2MCP), revision `55e064850a68f3b4cde7e5fd525bf9b2dec4e885`, under the included MIT license. See `mod/STS2Bridge/UPSTREAM.md`. The original investigation is in `TEST-RESULTS.md`.

OpenRouter's [Decisions API reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request) defines the request/response contract. This endpoint is in alpha.
