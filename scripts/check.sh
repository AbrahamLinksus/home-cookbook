#!/usr/bin/env bash
# All automated checks (docs/CONVENTIONS.md section 6). Exits non-zero if any gate fails.
# CHECK_NO_COVERAGE=1 relaxes only the coverage threshold.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
step() { echo; echo "== $1"; shift; "$@" || { echo "FAILED: $*"; fail=1; }; }

radon_gate() {
  local out
  out=$(uv run radon cc -n C -s src) || return 1
  if [ -n "$out" ]; then echo "$out"; return 1; fi
}

pytest_gate() {
  if [ "${CHECK_NO_COVERAGE:-0}" = "1" ]; then
    uv run pytest -q; local rc=$?
    if [ "$rc" -eq 5 ]; then echo "no tests collected (accepted: CHECK_NO_COVERAGE=1)"; return 0; fi
    return "$rc"
  fi
  uv run pytest -q --cov=cookbook --cov-fail-under=80
}

secrets_gate() {
  local files
  files=$(git ls-files --cached --others --exclude-standard | grep -v -e '^uv.lock$' -e '^.secrets.baseline$' || true)
  if [ -z "$files" ]; then return 0; fi
  echo "$files" | xargs uv run detect-secrets-hook --baseline .secrets.baseline
}

step "ruff check" uv run ruff check .
step "ruff format --check" uv run ruff format --check .
step "mypy --strict" uv run mypy --strict src
step "radon complexity" radon_gate
step "import-linter" uv run lint-imports
step "pytest" pytest_gate
step "detect-secrets" secrets_gate

echo
if [ "$fail" -ne 0 ]; then echo "CHECK FAILED"; exit 1; fi
echo "CHECK OK"
