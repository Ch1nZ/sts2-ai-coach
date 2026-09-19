"""Discover Steam libraries via libraryfolders.vdf and the game's app manifest."""
import os
from pathlib import Path
import platform
import re

APP_ID = '2868840'


def pairs(text):
    # Steam's quoted key/value format: preserve Unicode and decode only VDF escapes.
    return [(a.replace('\\\\', '\\').replace('\\"', '"'),
             b.replace('\\\\', '\\').replace('\\"', '"'))
            for a, b in re.findall(r'"((?:\\.|[^"\\])*)"\s*"((?:\\.|[^"\\])*)"', text)]


def steam_roots(system=None, home=None):
    system = system or platform.system()
    home = home or Path.home()
    roots = []
    if os.environ.get('STEAM_DIR'):
        roots.append(Path(os.environ['STEAM_DIR']).expanduser())
    if system == 'Darwin':
        roots.append(home / 'Library/Application Support/Steam')
    elif system == 'Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
                roots.append(Path(winreg.QueryValueEx(key, 'SteamPath')[0]))
        except (ImportError, OSError):
            pass
        for key in ('ProgramFiles(x86)', 'ProgramFiles'):
            if os.environ.get(key):
                roots.append(Path(os.environ[key]) / 'Steam')
    else:
        roots += [home / '.local/share/Steam', home / '.steam/steam',
                  home / '.steam/root', home / '.var/app/com.valvesoftware.Steam/.local/share/Steam']
    return list(dict.fromkeys(roots))


def library_paths(roots):
    libraries = list(roots)
    for root in roots:
        for config in (root / 'steamapps/libraryfolders.vdf', root / 'config/libraryfolders.vdf'):
            if config.is_file():
                for key, value in pairs(config.read_text(encoding='utf-8-sig')):
                    if key == 'path' or (key.isdigit() and (':' in value or value.startswith('/'))):
                        libraries.append(Path(value))
    return list(dict.fromkeys(p.resolve() for p in libraries))


def layout(game, system=None, machine=None):
    system, machine = system or platform.system(), machine or platform.machine()
    game = Path(game).expanduser().resolve()
    if game.suffix == '.app':
        game = game.parent
    if system == 'Darwin':
        base = game / 'SlayTheSpire2.app/Contents'
        binary = base / 'MacOS/Slay the Spire 2'
        arch = 'arm64' if machine.lower() in ('arm64', 'aarch64') else 'x86_64'
        data = base / f'Resources/data_sts2_macos_{arch}'
    else:
        names = ('SlayTheSpire2.exe', 'Slay the Spire 2.exe', 'sts2.exe') if system == 'Windows' else (
            'SlayTheSpire2', 'Slay the Spire 2', 'sts2')
        binary = next((game / n for n in names if (game / n).is_file()), game / names[0])
        suffix = 'windows_x86_64' if system == 'Windows' else 'linuxbsd_x86_64'
        data = game / ('data_sts2_' + suffix)
    if not binary.is_file() or not all((data / name).is_file() for name in ('sts2.dll', 'GodotSharp.dll', '0Harmony.dll')):
        raise ValueError(f'No supported STS2 installation at {game}. Select the folder containing the game from Steam → Manage → Browse local files.')
    return {'game_dir': game, 'executable': binary, 'data_dir': data, 'mods_dir': binary.parent / 'mods'}


def discover(override=None, roots=None):
    override = override or os.environ.get('STS2_GAME_DIR')
    if override:
        return layout(override)
    matches = []
    for library in library_paths(steam_roots() if roots is None else roots):
        manifest = library / f'steamapps/appmanifest_{APP_ID}.acf'
        if manifest.is_file():
            values = dict(pairs(manifest.read_text(encoding='utf-8-sig')))
            name = values.get('installdir')
            if name and Path(name).name == name:
                try:
                    found = layout(library / 'steamapps/common' / name)
                    if found not in matches:
                        matches.append(found)
                except ValueError:
                    continue
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError('Multiple STS2 installations found. Select one with --game-dir.')
    raise ValueError('STS2 was not found. Install it through Steam or pass --game-dir "/path/to/Slay the Spire 2".')
