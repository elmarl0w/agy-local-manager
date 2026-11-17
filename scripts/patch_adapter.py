#!/usr/bin/env python3
"""Guarded modifications for free-antigravity-cli@1.1.5; no global npm edits."""
from pathlib import Path
import subprocess
import sys


def swap(src, old, new, label):
    if old in src:
        if src.count(old) != 1:
            raise ValueError(f'{label}: multiple matches; upstream drift')
        return src.replace(old, new, 1)
    if new in src:
        return src
    raise ValueError(f'{label}: upstream layout changed; refusing unsafe patch')


def patch_text(src):
    src = swap(src, "    write_file: {\n        primaryKey: 'AbsolutePath',", "    write_file: {\n        primaryKey: 'Path',", 'write_file primary')
    src = swap(src, "    read_file: {\n        primaryKey: 'AbsolutePath',", "    read_file: {\n        primaryKey: 'Path',", 'read_file primary')
    old = """    const config = TOOL_PARAM_NORMALIZATION[name];
    if (!config) {
        return applyUniversalPathFallback(args);
    }
    const normalized = {};"""
    new = """    const config = TOOL_PARAM_NORMALIZATION[name];
    if (!config) {
        return applyUniversalPathFallback(args);
    }
    args = { ...args };
    if (name === 'run_command' && 'ToolSummary' in args) {
        if (!('toolSummary' in args)) args.toolSummary = args.ToolSummary;
        delete args.ToolSummary;
    }
    const normalized = {};"""
    src = swap(src, old, new, 'toolSummary')
    old = """    return normalized;
}
function applyUniversalPathFallback(args)"""
    new = """    if (name === 'write_file' || name === 'read_file') {
        if (!normalized.Path && normalized.AbsolutePath) normalized.Path = normalized.AbsolutePath;
        delete normalized.AbsolutePath;
    }
    return normalized;
}
function applyUniversalPathFallback(args)"""
    if "if (name === 'write_file' || name === 'read_file')" not in src:
        src = swap(src, old, new, 'Path cleanup')
    # Disable command re-routing to missing/unsafe native tools in agy 1.5.x.
    # Keep all ordinary shell commands as run_command, using the permission system.
    start = 'function translateToolCallToNative(name, args) {'
    end = '/**\n * Formats native file tool outputs'
    if src.count(start) != 1 or src.count(end) != 1:
        raise ValueError('translateToolCallToNative boundaries changed upstream')
    begin = src.index(start)
    finish = src.index(end, begin)
    replacement = """function translateToolCallToNative(name, args) {
    if (name === 'run_command') {
        const safeArgs = { ...(args || {}) };
        delete safeArgs.Cwd;
        delete safeArgs.cwd;
        return { name, args: safeArgs };
    }
    return { name, args };
}
"""
    src = src[:begin] + replacement + src[finish:]
    # The tool might bypass translation. Strip unsupported Cwd after normalization as well.
    find = "    if (name === 'write_file' || name === 'read_file') {"
    if src.count(find) != 1:
        raise ValueError('normalization cleanup boundary changed upstream')
    if 'delete normalized.Cwd;' not in src:
        src = src.replace(find, "    if (name === 'run_command') {\n        delete normalized.Cwd;\n        delete normalized.cwd;\n    }\n" + find, 1)
    return src


def patch_proxy_text(src):
    old = 'const REQUEST_TIMEOUT_MS = model.timeout || 120000;'
    new = 'const REQUEST_TIMEOUT_MS = model.timeout || 600000;'
    return swap(src, old, new, 'custom model request timeout')


def checked_write(p, patched):
    original = p.read_text()
    if patched == original:
        return False
    backup = p.with_name(p.name + '.orig')
    if not backup.exists():
        backup.write_text(original)
    tmp = p.with_name(p.stem + '.new.js')
    try:
        tmp.write_text(patched)
        subprocess.run(['node', '--check', str(tmp)], check=True)
        tmp.replace(p)
    finally:
        tmp.unlink(missing_ok=True)
    return True


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: patch_adapter.py <isolated adapter directory>')
    base = Path(sys.argv[1])
    pkg = base / 'package.json'
    import json
    if json.loads(pkg.read_text()).get('version') != '1.1.5':
        raise SystemExit('Unsupported adapter version; only 1.1.5 is tested')
    p = base / 'dist/proxy/translators/utils.js'
    proxy = base / 'dist/proxy.js'
    # Validate both transformations before writing either file.
    patched_utils = patch_text(p.read_text())
    patched_proxy = patch_proxy_text(proxy.read_text())
    changed_utils = checked_write(p, patched_utils)
    changed_proxy = checked_write(proxy, patched_proxy)
    print('[OK] Adapter compatibility and timeout patches ' + ('applied' if changed_utils or changed_proxy else 'already present'))


if __name__ == '__main__':
    main()
