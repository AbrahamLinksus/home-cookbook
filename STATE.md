# STATE — home-cookbook

> Source of truth for resuming. Updated after every task.

| Field | Value |
|---|---|
| Problem | A private recipe box on the home computer, used from phone and laptop: save family recipes, search by name or ingredient, scale servings, favourites on top, export everything to a file |
| Repo | local (/home/Jake/recipe-test/home-cookbook.git) |
| Local folder | /home/Jake/recipe-test/home-cookbook (worktrees in /home/Jake/recipe-test/home-cookbook-wt/; start sessions in /home/Jake/recipe-test) |
| Status | Active |
| Stage | 7 Build |
| Owner mode | builder: plain words, technical detail collapsed |
| Size | medium · signals: backend, database, deployment (home Wi-Fi) · 9 stories · full track |
| Milestone | M1 · First recipe end to end |
| Next step | T-02 Add a recipe and read it on the phone |
| Started | 2026-11-13 07:50 +05:30 (cost.py --since) · Budget 0 (no cap) |
| Last updated | 2026-11-13 |

## Config
| Field | Value |
|---|---|
| Owner | Jake Roberts (from git config) |
| GitHub owner | — (local repo; gh login expired) |
| Approval mode | every-task (default) |
| Cost mode | quality (default) |
| Visuals | installed (plugin venv on Python 3.12 via uv; 3.14 can't build greenlet for playwright 1.49.1) |

## Team
| Agent | Model | Why on this project |
|---|---|---|
| backend-coder | Sonnet | Home server, recipe keeper, finder, backup |
| frontend-coder | Sonnet | Screens and servings scaler |
| tester | Sonnet | Checks each feature against acceptance criteria |
| reviewer | Opus | Read-only review before each result card |
| debugger | Opus | Fixes failing checks |
| docs | Haiku | README / how to start and use |

## Open work
- Tasks in progress live on `wip/*` branches (see `taskgit.sh list`); their step states are in each branch's TASK_PROGRESS.md.

## Open decisions (waiting for the owner)
- none

## How to run
- Setup: `uv sync`, then `uv run playwright install --only-shell chromium`, then `scripts/install-hooks.sh`.
- Full check: `scripts/check.sh` (`CHECK_NO_COVERAGE=1` only for the empty skeleton).
- Tests: `uv run pytest` · browser smoke: `uv run python -I scripts/smoke_playwright.py`.
- Python 3.12 via uv (`.python-version`); Playwright 1.49.1 (D-28).

## Known minors
| Task | Where | Fix | Size |
|---|---|---|---|
| T-01 | domain/amounts.py:24 | Move UnclearAmountError into domain/errors.py (CONVENTIONS §5) (n-1) | S |
| T-01 | adapters/sqlite_repo.py:124 | Catch sqlite3.DatabaseError ("file is not a database") → one-line start-up message (n-2) | S |
| T-01 | web/guard.py:29 | Test trailing-dot / missing Host (403); optionally strip trailing dot (n-3) | S |
| T-01 | docs/LLD.md §6.5, §6.4 | Add D-32 Host rule and `unclear_amount` code — M1 as-built sync (n-4) | S |
| T-01 | static/js/api.js | uiText() returns "" for an unknown key (n-5) | S |
| T-01 | various | Earlier review minors m-4, m-5, m-8, m-10, m-11, m-12, rest of m-9 — see T-01 review notes | S–M |

## Context additions
| Role | Also read | Why (from gap report) |
|---|---|---|
| planner, tester | docs/scenarios.md | Acceptance criteria link usage scenarios S-xx (planner gap report, stage 6) |

## Notes for the next session
- Repo is local-only. To move to GitHub later: `git remote set-url origin <url> && git push -u origin --all`.
- Shared files (STATE/DECISIONS) on wip/plan: edit them only after a step's `done`, then `taskgit checkpoint` before the next agent starts — a step's scope check reverts them otherwise.
- planner can't write docs/*.mmd; the Orchestrator copies .results/hld/hld.mmd → docs/hld-dataflow.mmd and renders it.
- Run capture.py with ~/.cache/dev-team-setup/venv/bin/python (it has playwright + PIL); the project venv and system python lack one or the other.
