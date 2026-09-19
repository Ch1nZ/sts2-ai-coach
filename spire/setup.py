"""Clone-to-run setup for Windows, macOS and Linux; writes tools only inside the repo."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import urllib.request
import venv
from .clients import ROOT, config
from .steam import discover, layout

SDK = '9.0.318'
RECEIPT = ROOT / '.cache/production-install.json'
FILES = ('STS2_MCP.dll', 'STS2_MCP.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_env():
    env = os.environ.copy()
    for key, suffix in {'DOTNET_ROOT': '.tools/dotnet', 'DOTNET_CLI_HOME': '.cache/dotnet-home',
                        'NUGET_PACKAGES': '.cache/nuget', 'TMPDIR': '.cache/tmp',
                        'TMP': '.cache/tmp', 'TEMP': '.cache/tmp'}.items():
        path = ROOT / suffix; path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',
               DOTNET_GENERATE_ASPNET_CERTIFICATE='false', DOTNET_NOLOGO='1')
    return env


def python_path():
    return ROOT / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')


def sdk(env):
    binary = ROOT / ('.tools/dotnet/dotnet.exe' if os.name == 'nt' else '.tools/dotnet/dotnet')
    if binary.exists():
        return binary
    suffix = 'ps1' if os.name == 'nt' else 'sh'
    script = ROOT / f'.tools/dotnet-install.{suffix}'
    print('Downloading the project-local .NET SDK…', flush=True)
    with urllib.request.urlopen('https://dot.net/v1/dotnet-install.' + suffix, timeout=60) as response:
        script.write_bytes(response.read())
    if os.name == 'nt':
        command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
                   '-Version', SDK, '-InstallDir', str(binary.parent), '-NoPath']
    else:
        command = ['bash', str(script), '--version', SDK, '--install-dir', str(binary.parent), '--no-path']
    subprocess.run(command, env=env, check=True)
    return binary


def build(game):
    env = local_env()
    binary = sdk(env)
    output = ROOT / 'artifacts/production'
    subprocess.run([str(binary), 'build', str(ROOT / 'mod/STS2Bridge/STS2_MCP.csproj'),
                    '-c', 'Release', '-o', str(output), '-p:NuGetAudit=false',
                    '-p:STS2GameDataDir=' + str(game['data_dir'])], env=env, check=True, cwd=ROOT)
    shutil.copy2(ROOT / 'mod/STS2Bridge/mod_manifest.json', output / FILES[1])
    return output


def ensure_stopped(game):
    if os.name == 'nt':
        raw = subprocess.check_output(['powershell', '-NoProfile', '-Command',
            'Get-CimInstance Win32_Process | Select-Object -ExpandProperty ExecutablePath | ConvertTo-Json'], text=True)
        paths = json.loads(raw or '[]')
        if isinstance(paths, str): paths = [paths]
        running = any(p and os.path.normcase(p) == os.path.normcase(str(game['executable'])) for p in paths or [])
    else:
        lines = subprocess.check_output(['ps', '-axo', 'command='], text=True).splitlines()
        running = any(line.strip().startswith(str(game['executable'])) for line in lines)
    if running:
        raise ValueError('Quit STS2 before installing or removing the bridge.')


def install(game, output, receipt_path=RECEIPT, uninstall=False):
    """Preflight ownership, then rollback both files if any write fails."""
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if receipt and receipt.get('game_dir') != str(game['game_dir']):
        raise ValueError('A different installation is recorded. Uninstall it before changing paths.')
    mods = game['mods_dir']
    if mods.is_symlink():
        raise ValueError('The mods directory is a symlink; select a normal game installation.')
    owned = receipt.get('files', {})
    for name in FILES:
        dest = mods / name
        if dest.is_symlink() or (dest.exists() and (name not in owned or digest(dest) != owned[name])):
            raise ValueError('Existing STS2_MCP files belong to another installation or were changed. They were left untouched.')
        if not uninstall and not (output / name).is_file():
            raise ValueError('Build output is incomplete.')
    previous = {name: (mods / name).read_bytes() if (mods / name).exists() else None for name in FILES}
    old_receipt = receipt_path.read_bytes() if receipt_path.exists() else None
    mods.mkdir(parents=True, exist_ok=True)
    try:
        for name in FILES:
            dest = mods / name
            if uninstall:
                if name in owned: dest.unlink(missing_ok=True)
            else:
                dest.write_bytes((output / name).read_bytes())
        if uninstall:
            receipt_path.unlink(missing_ok=True)
        else:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(json.dumps({'game_dir': str(game['game_dir']),
                'game_assembly_sha256': digest(game['data_dir'] / 'sts2.dll'),
                'files': {name: digest(mods / name) for name in FILES}}, indent=2))
    except Exception:
        for name, contents in previous.items():
            dest = mods / name
            if contents is None: dest.unlink(missing_ok=True)
            else: dest.write_bytes(contents)
        if old_receipt is None: receipt_path.unlink(missing_ok=True)
        else: receipt_path.write_bytes(old_receipt)
        raise


def configure_key():
    if config()[0]:
        print('OpenRouter key is configured (value hidden).')
        return
    if not sys.stdin.isatty():
        raise ValueError('Set OPENROUTER_API_KEY or fill in .env.local, then run setup again. No key is accepted as a command-line argument.')
    key = getpass.getpass('OpenRouter API key (hidden): ').strip()
    if not key or any(c.isspace() for c in key):
        raise ValueError('A non-empty API key without whitespace is required.')
    path = ROOT / '.env.local'
    lines = path.read_text().splitlines() if path.exists() else []
    lines = [line for line in lines if not line.strip().startswith('OPENROUTER_API_KEY=')]
    lines.append('OPENROUTER_API_KEY=' + key)
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as file: file.write('\n'.join(lines) + '\n')
    if os.name != 'nt': path.chmod(0o600)


def installed_game():
    if not RECEIPT.is_file():
        raise ValueError('Run python manage.py setup first.')
    receipt = json.loads(RECEIPT.read_text())
    game = layout(receipt['game_dir'])
    for name in FILES:
        path = game['mods_dir'] / name
        if not path.is_file() or digest(path) != receipt['files'].get(name):
            raise ValueError('Bridge files changed or are missing. Run setup again.')
    if receipt.get('game_assembly_sha256') != digest(game['data_dir'] / 'sts2.dll'):
        raise ValueError('The game has changed since the bridge was built. Quit it and run setup again.')
    return game


def main():
    parser = argparse.ArgumentParser(description='Set up and run STS2 AI Coach with your Steam game.')
    parser.add_argument('command', choices=['setup', 'start', 'doctor', 'configure', 'uninstall'])
    parser.add_argument('--game-dir', help='Override automatic Steam-library discovery')
    parser.add_argument('--build-only', action='store_true', help='Setup only: compile without installing or prompting for a key')
    args = parser.parse_args()
    try:
        if args.command == 'setup':
            game = discover(args.game_dir)
            print('Found STS2:', game['game_dir'], flush=True)
            if not args.build_only:
                ensure_stopped(game)
                configure_key()
            if not python_path().exists():
                venv.EnvBuilder(with_pip=False).create(ROOT / '.venv')
            output = build(game)
            if args.build_only:
                print('Build complete. No Steam files were changed.')
            else:
                install(game, output)
                print('Setup complete. Enable the mod in STS2 settings, then run: python manage.py start')
        elif args.command == 'configure':
            configure_key()
        elif args.command == 'doctor':
            game = discover(args.game_dir)
            print('Game:', game['game_dir'])
            print('OpenRouter key:', 'configured' if config()[0] else 'missing')
            print('Local Python environment:', 'ready' if python_path().exists() else 'missing')
            installed_game()
            print('Bridge installed and matches this game version.')
        elif args.command == 'uninstall':
            if not RECEIPT.exists():
                print('No installation is recorded. Nothing changed.')
                return
            game = layout(json.loads(RECEIPT.read_text())['game_dir'])
            ensure_stopped(game)
            install(game, None, uninstall=True)
            print('Bridge removed. Saves and other mods were not changed.')
        else:
            installed_game()
            if not config()[0]: raise ValueError('Run python manage.py configure to add your OpenRouter key.')
            if not python_path().exists(): raise ValueError('Local environment missing. Run setup again.')
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', 18765)) == 0:
                    raise ValueError('The companion is already running at http://127.0.0.1:18765.')
            print('Launch STS2 normally through Steam. Ctrl-C stops only the companion.', flush=True)
            os.chdir(ROOT)
            os.execv(str(python_path()), [str(python_path()), '-m', 'spire.server'])
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
