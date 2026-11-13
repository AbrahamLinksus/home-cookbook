#!/usr/bin/env bash
# Install the tracked pre-commit hook (the hooks folder is not versioned). Run once per clone.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
hooks=$(git rev-parse --git-path hooks)
mkdir -p "$hooks"
ln -sf "$root/scripts/pre-commit-hook.sh" "$hooks/pre-commit"
chmod +x "$root/scripts/pre-commit-hook.sh"
echo "installed $hooks/pre-commit"
