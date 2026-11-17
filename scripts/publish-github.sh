#!/usr/bin/env bash
set -Eeuo pipefail
if ! command -v gh >/dev/null 2>&1; then
  echo 'GitHub CLI (gh) is missing. On Arch: sudo pacman -S github-cli' >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo 'Sign in first: gh auth login' >&2
  exit 1
fi
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
if [[ ! -d .git ]]; then
  git init -b main
fi
# Never stage user's runtime data. Only allowlisted files are committed.
git add README.md CONTRIBUTING.md .gitignore .github/workflows/ci.yml \
    docs/INSTALL.ru.md docs/ARCHITECTURE.ru.md docs/TROUBLESHOOTING.ru.md \
    agy_manager.py install.sh uninstall.sh scripts/patch_adapter.py \
    scripts/publish-github.sh tests/test_adapter_patch.py tests/test_manager.py
if ! git diff --cached --quiet; then
  git commit -m 'Initial experimental local Antigravity Ollama manager'
fi
if git remote get-url origin >/dev/null 2>&1; then
  echo 'Existing origin detected; no new repository created.'
  echo 'Review: git remote -v; then git push -u origin main'
  exit 0
fi
# Default PRIVATE because upstream project integrates with an authenticated CLI.
name="${1:-agy-local-manager}"
gh repo create "$name" --private --source=. --remote=origin --push
echo 'Private GitHub repository created and pushed. Review it before making it public.'
