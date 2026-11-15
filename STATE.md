# STATE — home-cookbook

> Source of truth for resuming. Updated after every task.

| Field | Value |
|---|---|
| Problem | A private recipe box on the home computer, used from phone and laptop: save family recipes, search by name or ingredient, scale servings, favourites on top, export everything to a file |
| Repo | local (/home/Jake/recipe-test/home-cookbook.git) |
| Local folder | /home/Jake/recipe-test/home-cookbook (worktrees in /home/Jake/recipe-test/home-cookbook-wt/; start sessions in /home/Jake/recipe-test) |
| Status | Active |
| Stage | 8 Handover (all build tasks done) |
| Owner mode | builder: plain words, technical detail collapsed |
| Size | medium · signals: backend, database, deployment (home Wi-Fi) · 9 stories · full track |
| Milestone | All milestones done (M1: 393b7c7 · M2: d4421d2 · M3: 015a51b) |
| Next step | Handover task `handover`: devops CI running scripts/check.sh → architect ARCHITECTURE.md + WALKTHROUGH.md → docs README how to run/test/extend → reviewer checks every named path/command. Start with `/setup-project resume home-cookbook` in a fresh chat (from /home/Jake/recipe-test). Owner still to try the app on the phone over home Wi-Fi (http://192.168.1.16:8765 on this machine) |
| Started | 2026-11-13 07:50 +05:30 (cost.py --since) · Budget 0 (no cap) |
| Last updated | 2026-11-15 |

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
| T-01 | static/js/api.js | uiText() returns "" for an unknown key (n-5) | S |
| T-01 | adapters (import rows) | Non-object ingredient rows are silently dropped (m-4) | S |
| T-01 | domain | `\d` regexes match Unicode digits; use [0-9] (m-5) | S |
| T-01 | app/serve.py | Banner shows the LAN IP even when bound to 127.0.0.1 (m-8) | S |
| T-01 | static/js/undo.js | Guard corrupt sessionStorage JSON; ignore a double-tapped Undo (m-9 rest) | S |
| T-01 | tests/integration/test_guard.py | Add a `::ffff:8.8.8.8` test (m-10) | S |
| T-01 | web/guard.py, web/errors.py | Teredo/NAT64 addresses; 403 on /api is plain text, not JSON (m-11) | S |
| T-01 | web/errors.py, app | Keep HTTPException headers; name the 3600 constant (m-12; init_schema-before-bind already done per M1 LLD sync) | S |
| T-02 | static/js/edit.js:131-150 | Keep focus after move-to-end and Remove (m-4) | S |
| T-02 | static/css/app.css:129 | Merge the second @media (min-width: 768px) block (m-5) | S |
| T-02 | templates/edit.html, view.html | Move inline styles to app.css; give the favourite star a text alternative (m-6) | S |
| T-02 | tests/e2e | Tag e2e tests with (S-xx); add a 1280-wide e2e run (m-7) | S |
| T-02 | tests (pages) | test_form_data_blank_and_filled covers only the blank form (m-8) | S |
| T-02 | static/js/edit.js:103-107 | Several unknown 422 keys stack notes under the title (n-9) | S |
| T-02 | tests/integration/test_serve.py | readline without timeout; add a direct regression test for the start-up race; "stopped" logged when stopped before serving (race-fix review) | S |
| T-03 | tests/unit/test_backup_export.py | Partial in-memory repo fake with type: ignore; make it honour the full Protocol (m1) | S |
| T-03 | tests/unit/test_backup_export.py | Undo-window test only proves list_live is called; assert the pending recipe is absent from the file (m2) | S |
| T-03 | tests (export filename) | Filename test repeats the implementation's date expression; use a fixed Clock with a known local date (m3) | S |
| T-03 | tests/integration/test_export.py | Tests check several behaviours each; one name claims "order" but doesn't check it (m4) | S |
| T-04 | web/guard.py or web/messages.py, static/js/menu.js | A guard 403 on import shows "Could not reach the home computer"; return JSON for /api/ 403s (ties to T-01 m-11) or add UI_TEXTS["import_failed"] (m-4r) | S |
| T-04 | tests (backup import) | Split multi-behaviour tests, tighten names, tag e2e with S-xx (m-7) | S |
| T-04 | services/backup/service.py | A title repeated in the file that the app already holds is listed twice under "skipped" (m-8; follows LLD invariant) | S |
| T-04 | tests/unit/test_backup_import.py | Every-fixture test only picks up files named v*-*.json (nit) | S |
| T-04 | services/backup/formats.py, web/messages.py | A file needing a rename past 200 chars is refused as "not an export"; give it a clearer message (D-37) | S |
| T-05 | services/backup or web/errors.py | API 410 text for a purged recipe reads "'' is gone" (no screen shows it) (nit) | S |
| T-07 | web/pages.py:67-69 | Reads every recipe twice per keystroke (total_live + search) (m2) | S |
| T-07 | static/js/list.js | Query built twice; URL can briefly show a newer query than the list (m3) | S |
| T-07 | web/pages.py | No length cap on q (m5) | S |
| T-07 | tests (search) | "Units and amounts not searched" barely tested for amounts (m6) | S |
| T-09 | static/js/scaler.js | Plural/singular gaps: "smoothies"→"smoothy", "halves"→"halve", "Tomatoes"→"tomato" loses capital (n1) | S |
| T-09 | static/js/view.js | MAX_SERVINGS repeats rules.py's limit; pass it from the template (n2) | S |
| T-09 | tests/e2e (scaler) | No desktop-width run; some old test names (m8) | S |
| T-06 | static/js/edit.js | Dialog test id stays "deleted-dialog" after a 410, so a later to_be_hidden() on "conflict-dialog" passes vacuously (m6) | S |
| T-06 | tests/unit/test_keeper_update.py | Unit tests use real SQLite, not the in-memory fake; _lost_race untested (m3) | S |
| T-06 | static/css/app.css | A disabled Save has no disabled look (n3, predates T-06) | S |
| T-08 | templates/_list_items.html:9, view.html:14 | Star aria-labels hard-coded, copying UI_TEXTS; take them from the template context (m1) | S |
| T-08 | static/js/favourite.js | showMessage never clears menu-message; a failure note stays after a later success (m2) | S |
| T-08 | tests/e2e/test_favourites.py | No S-xx tag; 361 lines (over 300); fixtures copied from test_edit_two_devices.py, move to conftest (m3) | S |
| T-08 | static/js/favourite.js | paintStar JSDoc lacks @param types (m4) | S |
| T-10 | tests/e2e/conftest.py | start_app retry fires on any "cannot start", not only a taken port (n1) | S |
| T-10 | tests/e2e | Star helper duplicated across e2e files (n3) | S |

## Context additions
| Role | Also read | Why (from gap report) |
|---|---|---|
| reviewer | src/cookbook/web/messages.py, static/js/api.js, app/factory.py | UI-text and security questions need them (T-02 gap) |
| reviewer | src/cookbook/templates/base.html, src/cookbook/domain/rules.py, src/cookbook/adapters/sqlite_repo.py | Verifying links and repository behaviour needs them (T-03 gap) |
| debugger | tests/e2e/conftest.py | UI fixes need the e2e fixtures (T-02 gap) |
| debugger | src/cookbook/static/js/api.js, src/cookbook/web/errors.py | UI-text and error-mapping fixes need them (T-04 gap) |
| planner, tester | docs/scenarios.md | Acceptance criteria link usage scenarios S-xx (planner gap report, stage 6) |
| reviewer | src/cookbook/static/css/app.css, src/cookbook/domain/rules.py | Touch-target sizes and servings limits need them (T-09 gap) |
| reviewer | src/cookbook/services/keeper.py, src/cookbook/static/js/edit.js, src/cookbook/templates/edit.html | Edit/conflict reviews need them in full (T-06 gap) |

## Notes for the next session
- LLD is 422 lines after the M2 sync (400-line guide); trimming further would cut real content.
- taskgit approve prints "approved: <hash>" then exits 1 from a `pwd` error after the worktree is removed; the merge and push succeed — verify with git log / ls-remote.
- Repo is local-only. To move to GitHub later: `git remote set-url origin <url> && git push -u origin --all`.
- Shared files (STATE/DECISIONS) on wip/plan: edit them only after a step's `done`, then `taskgit checkpoint` before the next agent starts — a step's scope check reverts them otherwise.
- planner can't write docs/*.mmd; the Orchestrator copies .results/hld/hld.mmd → docs/hld-dataflow.mmd and renders it.
- capture.py `term` images can't draw accented letters (font); use `md` rendering for text with accents.
- Briefs that pass a fixed commit message to git-pr must include the `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` line (c4dd6b9 has a Haiku trailer, 51f2768 none; left as is, no history rewrite).
- git-pr runs on Haiku and applies its own Co-Authored-By trailer even when the brief gives Opus (c4dd6b9 and d4421d2 say Haiku, 51f2768 none). Not rewritten.
- Checkpoint after EVERY step before spawning the next agent: `scope` reverts uncommitted files outside the new agent's scope (the first M2 README pass was lost this way).
- Docs agents have no shell: the Orchestrator renders README/LLD images with capture.py `md`.
- Run capture.py with ~/.cache/dev-team-setup/venv/bin/python (it has playwright + PIL); the project venv and system python lack one or the other.
- Debugger and coders cannot run git (scope hook). When a sync conflicts, the Orchestrator runs `git merge --no-commit origin/main` in the worktree, takes main's TASKS/STATE/DECISIONS, sends only the conflicted code file to the debugger, then commits the merge and pushes the wip branch.
- Record agent IDs in TASK_PROGRESS.md only after the next `scope` + before `checkpoint`; an uncommitted edit there is reverted by the next agent's scope check.
- M3 docs: the docs agent has no shell; the Orchestrator regenerated README screenshots with `COOKBOOK_TEST_SHOTS=<dir> uv run pytest tests/e2e/test_layout_at_home.py --no-cov` and copied them into docs/images/.
