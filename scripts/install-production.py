"""Install/remove only our two mod files in the real macOS Steam game."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GAME = Path.home() / 'Library/Application Support/Steam/steamapps/common/Slay the Spire 2'
FILES = {'STS2_MCP.dll': ROOT / 'artifacts/production/STS2_MCP.dll',
         'STS2_MCP.json': ROOT / 'mod/STS2Bridge/mod_manifest.json'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME)
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    game = args.game_dir.expanduser().resolve()
    executable = game / 'SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2'
    if not executable.is_file():
        raise SystemExit('Slay the Spire 2 was not found at the specified Steam path.')
    processes = subprocess.check_output(['ps', '-axo', 'command='], text=True)
    if any(line.startswith(str(executable)) for line in processes.splitlines()):
        raise SystemExit('Quit the Steam game before installing or removing the mod.')
    mods = executable.parent / 'mods'
    receipt_path = ROOT / '.cache/production-install.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if receipt and receipt.get('game_dir') != str(game):
        raise SystemExit('An installation is already recorded at another path. Remove that installation first.')
    owned = receipt.get('files', {})
    # Preflight all files before changing either. Never overwrite another mod.
    for name, source in FILES.items():
        dest = mods / name
        if dest.is_symlink():
            raise SystemExit('Refusing to modify a symlink in the mods folder.')
        if dest.exists() and (name not in owned or digest(dest) != owned[name]):
            raise SystemExit('An existing or externally modified STS2_MCP file is present. It was left untouched.')
        if not args.uninstall and not source.is_file():
            raise SystemExit('Build the production bridge first with scripts/install-production.sh.')
    if args.uninstall:
        for name in owned:
            if name in FILES:
                (mods / name).unlink(missing_ok=True)
        receipt_path.unlink(missing_ok=True)
        print('Removed this project’s production mod files. Saves and other mods were not changed.')
        return
    mods.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, source in FILES.items():
        shutil.copy2(source, mods / name)
        hashes[name] = digest(mods / name)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps({'game_dir': str(game), 'files': hashes}, indent=2))
    print('Production bridge installed. Launch the game through Steam and enable the mod in game settings.')


if __name__ == '__main__':
    main()
