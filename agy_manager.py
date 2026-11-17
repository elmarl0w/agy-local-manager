#!/usr/bin/env python3
"""User-space launcher and health checks for the experimental Antigravity/Ollama stack."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import shutil
import subprocess
import sys

HOME = Path.home()
DATA = Path(os.environ.get('XDG_DATA_HOME', str(HOME / '.local/share'))) / 'agy-local-manager'
APP = DATA / 'app'
STATE = DATA / 'state'
BIN = DATA / 'bin' / 'agy-upstream'
NPM = DATA / 'npm'
ADAPTER = NPM / 'node_modules/free-antigravity-cli'
PATCHER = DATA / 'eligibility-patcher'
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', str(HOME / '.config'))) / 'agy-local-manager/config.json'
MODEL_FILE = HOME / '.free-antigravity/models.json'


def cmd(argv, *, check=True, capture=True, env=None, timeout=180):
    return subprocess.run(argv, check=check, text=True, capture_output=capture, env=env, timeout=timeout)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def settings():
    if not CONFIG.is_file():
        return {}
    return json.loads(CONFIG.read_text())


def source_binary():
    configured = settings().get('system_agy')
    candidates = [configured, '/usr/bin/agy', '/usr/local/bin/agy']
    for raw in candidates:
        if raw and Path(raw).is_file() and os.access(raw, os.X_OK):
            return Path(raw)
    # Avoid calling `which agy`, which would resolve our own wrapper.
    raise RuntimeError('System agy not found. Install antigravity-cli via paru, or set system_agy in config.json.')


def run_patcher(action, *, capture=True):
    script = PATCHER / 'manager.py'
    if not script.is_file():
        raise RuntimeError('Eligibility patcher missing: run `agy repair` after installation.')
    return cmd([sys.executable, str(script), '--path-cli', str(BIN), *action], capture=capture)


def ensure_binary(*, verbose=True):
    source = source_binary()
    BIN.parent.mkdir(parents=True, exist_ok=True)
    current_source_sha = sha(source)
    marker = STATE / 'source.sha256'
    recorded = marker.read_text().strip() if marker.exists() else ''
    if BIN.is_file() and recorded == current_source_sha:
        return False
    if is_running():
        raise RuntimeError('Update detected, but a prior agy-upstream process still runs; close it before repair.')
    staging = BIN.with_suffix('.new')
    shutil.copy2(source, staging)
    os.chmod(staging, 0o755)
    staging.replace(BIN)
    STATE.mkdir(parents=True, exist_ok=True)
    marker.write_text(current_source_sha + '\n')
    if verbose:
        print(f'[agy-local] User copy synchronized with {source}')
    return True


def is_running():
    # Linux /proc check, no signals or process termination.
    proc = Path('/proc')
    if not proc.exists() or not BIN.exists():
        return False
    target = os.path.realpath(BIN)
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            if os.path.realpath(entry / 'exe') == target:
                return True
        except (OSError, PermissionError):
            continue
    return False


def patch_status():
    r = run_patcher(['status'], capture=True)
    output = r.stdout + r.stderr
    # Only extract the CLI subsection: the IDE/manager may be missing normally.
    section = output.split('=== Antigravity CLI (cli) ===', 1)[-1].split('=== Antigravity Manager', 1)[0]
    if 'status: patched' in section:
        return 'patched'
    if 'status: unpatched' in section:
        return 'unpatched'
    raise RuntimeError('Unrecognized patcher status. Run patcher status manually; refuse to guess:\n' + section[:1200])


def ensure_patch(*, verbose=True):
    status = patch_status()
    if status == 'patched':
        return
    if is_running():
        raise RuntimeError('Cannot patch a running agy. Close CLI first.')
    if verbose:
        print('[agy-local] Applying compatibility patch to USER COPY only')
    result = run_patcher(['patch', 'cli'])
    if patch_status() != 'patched':
        raise RuntimeError('Patch was not confirmed. Output:\n' + (result.stdout + result.stderr)[-2000:])


def ensure_local_adapter():
    js = ADAPTER / 'dist/proxy/translators/utils.js'
    cli = ADAPTER / 'dist/cli.js'
    if not js.is_file() or not cli.is_file():
        raise RuntimeError('Adapter missing. Run `agy repair` (requires npm)')
    # Validate patched behavior without changing files at launch.
    script = '''const u=require(process.argv[1]);const r=u.normalizeToolArgs('run_command',{CommandLine:'pwd',ToolSummary:'test'});const f=u.normalizeToolArgs('write_file',{AbsolutePath:'/tmp/test.txt',Content:'x'});const rd=u.normalizeToolArgs('read_file',{AbsolutePath:'/tmp/test.txt'});if(r.toolSummary!=='test'||'ToolSummary' in r||f.Path!=='/tmp/test.txt'||'AbsolutePath' in f||rd.Path!=='/tmp/test.txt'||'AbsolutePath' in rd)process.exit(2);'''
    script += """const cmds=['ls -la','cat file.txt','grep hello index.js'];for(const c of cmds){const x=u.translateToolCallToNative('run_command',{CommandLine:c,Cwd:'/tmp',toolSummary:'test'});if(x.name!=='run_command'||x.args.CommandLine!==c||'Cwd' in x.args)process.exit(3);}const n=u.normalizeToolArgs('run_command',{CommandLine:'pwd',Cwd:'/tmp',ToolSummary:'test'});if('Cwd' in n||'cwd' in n)process.exit(4);"""
    result = cmd(['node', '-e', script, str(js)], check=False)
    if result.returncode != 0:
        raise RuntimeError('Adapter tool schema checks failed. Run `agy repair`.')
    proxy = ADAPTER / 'dist/proxy.js'
    if 'const REQUEST_TIMEOUT_MS = model.timeout || 600000;' not in proxy.read_text():
        raise RuntimeError('Adapter timeout patch missing. Run `agy repair`.')
    return cli


def proxy_port_busy():
    """Return True if the adapter default loopback port already accepts TCP connections."""
    try:
        with socket.create_connection(('127.0.0.1', 50998), timeout=0.3):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def model_status():
    try:
        response = cmd(['curl', '-fsS', '--max-time', '3', 'http://127.0.0.1:11434/api/tags'])
        data = json.loads(response.stdout)
        available = [x.get('name') for x in data.get('models', [])]
        return available
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def doctor():
    problems = 0
    try:
        original = source_binary()
        print('[OK] system agy:', original)
        if BIN.is_file():
            print('[OK] user copy:', BIN)
            print('[INFO] eligibility status:', patch_status() if (PATCHER / 'manager.py').is_file() else 'patcher missing')
        else:
            print('[WARN] user copy missing'); problems += 1
    except Exception as e:
        print('[FAIL] agy:', e); problems += 1
    try:
        print('[OK] adapter entry:', ensure_local_adapter())
    except Exception as e:
        print('[FAIL] adapter:', e); problems += 1
    names = model_status()
    if names is None:
        print('[WARN] Ollama API unavailable on 127.0.0.1:11434'); problems += 1
    else:
        print('[OK] Ollama API; models:', len(names))
        for name in names:
            if 'gemma' in (name or '').lower():
                print('     ', name)
    if proxy_port_busy():
        print('[WARN] Port 50998 is already in use. Close the old proxy before launching agy.')
    else:
        print('[OK] Proxy port 50998 is available')
    print('[INFO] adapter model config:', 'present' if MODEL_FILE.is_file() else 'missing; run `agy models add`')
    print('[INFO] current versions:', 'adapter=1.1.5 pinned; CLI changes checked on start')
    return 0 if not problems else 1


def repair():
    if is_running():
        raise RuntimeError('Close Antigravity before repair (the binary is busy).')
    # First reinstall locked adapter to local folder, then apply deterministic tool schema patch.
    if shutil.which('npm') is None:
        raise RuntimeError('npm not installed')
    print('[agy-local] Installing isolated adapter 1.1.5…')
    cmd(['npm', 'install', '--no-audit', '--no-fund', '--prefix', str(NPM), 'free-antigravity-cli@1.1.5'], capture=False, timeout=300)
    patch_script = APP / 'scripts/patch_adapter.py'
    cmd([sys.executable, str(patch_script), str(ADAPTER)], capture=False)
    if not (PATCHER / 'manager.py').is_file():
        if shutil.which('git') is None:
            raise RuntimeError('git not installed')
        print('[agy-local] Cloning third-party patch manager; inspect before trusting…')
        cmd(['git', 'clone', '--depth', '1', 'https://github.com/QNIX-Dev/eligibility-antigravity-patcher.git', str(PATCHER)], capture=False, timeout=180)
    ensure_binary()
    ensure_patch()
    ensure_local_adapter()
    print('[OK] Repair completed. Check `agy doctor` and run `agy`.')


def launch(args):
    verbose = '--verbose' in args or '--debug' in args
    if proxy_port_busy():
        raise RuntimeError("Port 50998 is already in use. Close the old Antigravity/proxy instance; inspect with: ss -ltnp 'sport = :50998'. Refusing dynamic-port fallback.")
    ensure_binary(verbose=verbose)
    ensure_patch(verbose=verbose)
    cli = ensure_local_adapter()
    names = model_status()
    if names is None:
        print('[WARN] Ollama is not responding. Start it with `sudo systemctl start ollama`.', file=sys.stderr)
    env = os.environ.copy()
    env['AGY_BIN'] = str(BIN)
    # No --debug by default: older proxy versions may print OAuth tokens in HTTP headers.
    # Filter only known, informational startup strings. Never silence stderr wholesale.
    node_args = ['node']
    if not verbose:
        node_args += ['--require', str(APP / 'scripts/quiet_startup.cjs')]
    node_args += [str(cli), *args]
    os.execvpe('node', node_args, env)


def main():
    # Leading diagnostic flags belong to the adapter, not to our subcommand parser.
    if len(sys.argv) > 1 and sys.argv[1] in ('--verbose', '--debug'):
        launch(sys.argv[1:])
        return 0
    parser = argparse.ArgumentParser(prog='agy', description='Isolated Antigravity + Ollama local launcher')
    parser.add_argument('action', nargs='?', default='launch', help='doctor | repair | setup-model | version | launch; other args pass through')
    parser.add_argument('rest', nargs=argparse.REMAINDER)
    ns = parser.parse_args()
    if ns.action == 'doctor':
        return doctor()
    if ns.action == 'repair':
        repair(); return 0
    if ns.action == 'version':
        print('agy-local-manager 0.1.3'); return 0
    if ns.action == 'setup-model':
        ensure_binary(); ensure_patch()
        cli = ensure_local_adapter()
        env = os.environ.copy(); env['AGY_BIN'] = str(BIN)
        return subprocess.call(['node', str(cli), 'models', 'add'], env=env)
    passthrough = ([] if ns.action == 'launch' else [ns.action]) + ns.rest
    launch(passthrough)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print('[agy-local] ERROR:', exc, file=sys.stderr)
        print('[agy-local] Try `agy doctor` and `agy repair` (close active agy processes first).', file=sys.stderr)
        sys.exit(1)
