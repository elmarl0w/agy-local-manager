#!/usr/bin/env bash
set -Eeuo pipefail
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/agy-local-manager"
WRAPPER="$HOME/.local/bin/agy"
if [[ -f "$WRAPPER" ]] && grep -q 'agy-local-manager/app/agy_manager.py' "$WRAPPER"; then
  rm -- "$WRAPPER"
fi
if [[ -d "$DATA" ]]; then
  echo "This removes ONLY the user-space manager directory: $DATA"
  read -r -p 'Type REMOVE to confirm: ' answer
  [[ "$answer" == REMOVE ]] || exit 1
  rm -rf -- "$DATA"
fi
echo 'Manager removed. AUR package, Ollama, Gemma and ~/.free-antigravity/ were not touched.'
