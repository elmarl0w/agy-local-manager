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
    old = "return { name: 'write_file', args: { AbsolutePath: absPath, Content: content, Append: cmd.includes('>>') } };"
    new = "return { name: 'write_file', args: { Path: absPath, Content: content, Append: cmd.includes('>>') } };"
    src = swap(src, old, new, 'redirect')
    return src


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: patch_adapter.py <isolated adapter directory>')
    base = Path(sys.argv[1])
    pkg = base / 'package.json'
    import json
    if json.loads(pkg.read_text()).get('version') != '1.1.5':
        raise SystemExit('Unsupported adapter version; only 1.1.5 is tested')
    p = base / 'dist/proxy/translators/utils.js'
    original = p.read_text()
    patched = patch_text(original)
    if patched == original:
        print('[OK] Adapter was already patched'); return
    backup = p.with_suffix('.js.orig')
    if not backup.exists():
        backup.write_text(original)
    tmp = p.with_suffix('.js.new')
    tmp.write_text(patched)
    subprocess.run(['node', '--check', str(tmp)], check=True)
    tmp.replace(p)
    print('[OK] Adapter tool parameter compatibility patch applied')


if __name__ == '__main__':
    main()
