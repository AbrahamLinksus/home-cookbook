#!/usr/bin/env bash
# Fast gates before each commit. Installed as the pre-commit hook by scripts/install-hooks.sh.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src
uv run lint-imports
staged=$(git diff --cached --name-only --diff-filter=ACM | grep -v -e '^uv.lock$' -e '^.secrets.baseline$' || true)
if [ -n "$staged" ]; then echo "$staged" | xargs uv run detect-secrets-hook --baseline .secrets.baseline; fi
