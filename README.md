# Showing Your Hand

A Slay the Spire 2 companion powered by **Jev through OpenRouter**. It shows one recommended action inside the game and refreshes as you play. You keep control of the game.

## Quick start

You need **Python 3.9 or newer**, a Steam installation of **Slay the Spire 2**, and your own **OpenRouter API key with credits**. Close STS2 during setup.

```sh
git clone https://github.com/Ch1nZ/showing-your-hand.git
cd showing-your-hand
python manage.py setup
python manage.py start
```

Use `python3` on macOS/Linux if `python` is unavailable; on Windows, `py -3` also works. This repository is currently private, so cloning requires repository access.

`setup` finds your Steam libraries, prompts for your API key without displaying it, creates a local Python environment, downloads a project-local .NET SDK, builds against your installed game, and installs the bridge mod. Nothing needs to be installed with pip, Homebrew, or an administrator-level package manager. You need write access to your game's mods folder; if your Steam library restricts that access, use a user-writable Steam library.

**Launch STS2 normally through Steam and enable the bridge in its mod settings.** Accept the game's mod-loading prompt if shown and restart the game if it requests it. Keep the companion running while you play. The recommendation appears at the top of the game window.

After the initial setup, just run `python manage.py start` and open the game from Steam. Either can start first. Ctrl-C stops only the companion; it does not close the game. Optional launchers: `Start Showing Your Hand.command` on macOS and `Start Showing Your Hand.cmd` on Windows.

Optional companion panel: [localhost:18765](http://127.0.0.1:18765), with Pause, Resume, and Retry. Closing the browser does not pause recommendations while the in-game overlay is connected.

## Steam detection

Setup reads Steam's `libraryfolders.vdf` and the STS2 application manifest, including libraries on other drives. Windows detection also checks Steam's current-user registry entry. macOS, Windows and Linux layout detection is implemented. For nonstandard installations or multiple detected copies, select the game explicitly:

```sh
python manage.py setup --game-dir "/path/to/steamapps/common/Slay the Spire 2"
```

`STS2_GAME_DIR` overrides game detection, and `STEAM_DIR` supplies an additional Steam root. Do not select a saves folder. On macOS you may also select `SlayTheSpire2.app`.

The original Steam game is used directly. Production does not copy the game, disable Steam, modify launch options, or redirect saves. The game controls its own modded profile behavior; this tool does not copy or migrate existing saves.

## Your key

Setup stores your key in the Git-ignored `.env.local` file; on macOS/Linux its permissions are limited to your user. It is never included in browser responses or sent to the game mod.

For a noninteractive installation, copy `.env.example` to `.env.local` and fill in `OPENROUTER_API_KEY` first. Alternatively, provide that environment variable to the process. `OPENROUTER_MODEL` defaults to `typesafe/jev-1.13`. To replace a saved key, edit `.env.local`; to add a missing key interactively, run `python manage.py configure`.

Each player supplies their own key. No key is bundled with the repository. Only game context and action candidates are sent to OpenRouter.

## Updates, checks and removal

```sh
python manage.py doctor
# After pulling an update or updating STS2, quit the game and rebuild:
python manage.py setup
# Remove only this project's bridge files:
python manage.py uninstall
```

Startup checks the bridge hashes and the game assembly used for the build. A game update requires a rebuild; incompatible game API changes may require a repository update too. Setup refuses to overwrite another installation's STS2_MCP files and rolls back its writes if installation fails. Keep the repository's `.cache/production-install.json` receipt for updates and removal.

Only the bridge DLL and manifest are installed in the game's `mods` directory. The source, SDK, Python environment, key and build caches remain inside the repository folder. No autostart service is registered. Run only one STS2 instance: the bridge uses port 15526 and the companion uses 18765.

## Recommendation behavior

- Reads live state four times per second and waits for 0.5 seconds of unchanged state before deciding.
- Uses OpenRouter's dedicated Decisions API, not chat completions.
- Sends one request per unchanged decision, at least two seconds apart, with a limit of 120 requests per companion session. Failed requests require explicit Retry. A sole available action needs no model request.
- Clears recommendations on observed state changes, disconnect, or pause. Results for an old state are discarded.
- Builds candidates for combat, card rewards, maps, shops, events, campfires, treasure and common selection prompts. Unknown screens and targeting types require manual input.
- Includes the permanent deck, hand and unordered draw-pile contents. Hidden draw order and future random outcomes are not supplied.

The bridge accepts only health and single-player state reads. It rejects control requests, does not play cards, and does not automatically open shops or chests. Jev selects from the available candidates; this is a direct model policy, not a combat simulator or a claim of optimal play.

## Development and validation

```sh
python -m unittest discover -s tests -v
# Compile against an installed game without installing or requesting a key:
python manage.py setup --build-only
```

The SDK is downloaded using Microsoft's official installer into `.tools/dotnet`. Build caches stay in `.cache`. There are no Python package dependencies.

**Verified:** 18 local regression tests, Steam discovery on this Mac, and compilation against the actual installed STS2 v0.107.1 with zero warnings/errors. Real Jev calls and the in-game overlay were previously verified in an isolated copy of that build. Windows/Linux discovery and installation logic have fixture tests and a CI matrix; native Steam-connected gameplay on those platforms has not been tested. Full production gameplay on the original Steam installation remains to be validated. Multiplayer and every character/mechanic are not yet covered.

The optional macOS-only isolated development environment is separate from the normal setup:

```sh
bash scripts/setup-isolated.sh
bash scripts/play.sh
```

It uses a copied game, disposable saves, disabled Steam and restricted network access. Its temporary Application Support symlink is removed on launcher exit. Production setup never creates this copy. Saved local test snapshots in `artifacts/` are not shipped; `scripts/live-check.py` requires such a snapshot and makes one billed request.

## Code and attribution

- `manage.py`, `spire/setup.py`, `spire/steam.py`: portable setup, Steam discovery and lifecycle.
- `spire/decisions.py`: candidate generation and the Jev request contract.
- `spire/clients.py`, `spire/engine.py`: OpenRouter connection, polling, request limits and stale-result rejection.
- `spire/server.py`, `spire/web/`: local service and companion panel.
- `mod/STS2Bridge/`: state reader and in-game overlay.

The bridge derives from [STS2MCP](https://github.com/Gennadiyev/STS2MCP), revision `55e064850a68f3b4cde7e5fd525bf9b2dec4e885`, under its included MIT license. See `mod/STS2Bridge/UPSTREAM.md`. Game binaries and saves are never distributed.

[OpenRouter Decisions API reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request) · [Microsoft SDK installer documentation](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-install-script)
