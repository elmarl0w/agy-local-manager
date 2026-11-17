#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/agy-local-manager"
DEST="$DATA/app"
USER_BIN="$HOME/.local/bin"

for dependency in python3 node npm git curl; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing dependency: $dependency" >&2
    echo 'On Arch: sudo pacman -S python nodejs npm git curl' >&2
    exit 1
  fi
done
if [[ ! -x /usr/bin/agy && ! -x /usr/local/bin/agy ]]; then
  echo 'Missing system Antigravity CLI; on Arch install with: paru -S antigravity-cli' >&2
  exit 1
fi

mkdir -p "$DEST/scripts" "$USER_BIN" "$DATA/state"
if [[ -e "$USER_BIN/agy" ]] && ! grep -q 'agy-local-manager/app/agy_manager.py' "$USER_BIN/agy" 2>/dev/null; then
  echo "Refusing to overwrite an existing custom wrapper: $USER_BIN/agy" >&2
  echo 'Move it manually to a backup before installing.' >&2
  exit 1
fi
install -m 755 "$ROOT/agy_manager.py" "$DEST/agy_manager.py"
install -m 755 "$ROOT/scripts/patch_adapter.py" "$DEST/scripts/patch_adapter.py"
install -m 644 "$ROOT/scripts/quiet_startup.cjs" "$DEST/scripts/quiet_startup.cjs"
# Put a shell wrapper ahead of /usr/bin/agy. This is NOT a modification to system binary.
cat > "$USER_BIN/agy" <<'EOF'
#!/usr/bin/env bash
exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/agy-local-manager/app/agy_manager.py" "$@"
EOF
chmod 755 "$USER_BIN/agy"

# The wrapper must be first in PATH. zsh usually reads ~/.zshrc for interactive terminals.
if ! grep -Fqx 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.zshrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
fi
export PATH="$USER_BIN:$PATH"

echo 'User-level wrapper installed. Installing dependencies and repairing in isolation…'
python3 "$DEST/agy_manager.py" repair
printf '\nDONE. Open a new terminal and run:\n  command -v agy\n  agy doctor\n  agy setup-model  # only on first setup\n  agy\n'
