# DECISIONS — home-cookbook

## Tier 1 — decided by the owner
| ID | Date | Decision | Chosen | Means for you · if wrong | Alternatives | Task |
|---|---|---|---|---|---|---|
| D-01 | 2026-11-13 | Where the code lives | Local only (no GitHub) | Nothing leaves this computer · can move to GitHub later with two commands | Private / Public GitHub | plan |
| D-02 | 2026-11-13 | Restore from export | App loads the export file back in | Real restore after a wipe · adds an import feature | Readable copy only | plan |
| D-03 | 2026-11-13 | Delete behaviour | Gone at once, Undo for ~10 s | A mistaken tap is recoverable for 10 s, not after | Confirm then gone; 30-day bin | plan |
| D-04 | 2026-11-13 | Phone access | Only at home, computer on | Phone and laptop always agree · no offline use | Must work anywhere | plan |
| D-05 | 2026-11-13 | Scaled amounts | Kitchen-friendly rounding, same unit | ½ cup, 1½ eggs · not exact decimals | Exact numbers | plan |
| D-06 | 2026-11-13 | Import into a non-empty app | Add, keep existing, skip same title | An import never erases recipes | Replace all; ask each time | plan |
| D-07 | 2026-11-13 | Home Wi-Fi access | Anyone on home Wi-Fi, no password | Anyone at home can change or delete recipes | One simple password | plan |
| D-08 | 2026-11-13 | Photos | None | Simpler screens, small export file | One photo per recipe | plan |
| D-09 | 2026-11-13 | Deadline | None | Everything in the first version | A set date | plan |
| D-10 | 2026-11-13 | Duplicate recipe names | Not allowed; saving asks for another name | Backups never silently drop a recipe | Allowed with import variants | plan |
| D-11 | 2026-11-13 | Two devices edit one recipe | Warn the second save (reload theirs / keep yours) | No silent lost edits | Last save wins; keep both as copy | plan |
| D-12 | 2026-11-13 | Old backup files | Always load in later versions | Any export ever made stays restorable | Recent only; no promise | plan |
| D-13 | 2026-11-13 | Spec | Approved (with D-10..D-12 folded in) | — | — | plan |
| D-14 | 2026-11-13 | Overall design (HLD) | Approved | — | — | plan |
| D-15 | 2026-11-13 | Build team | backend-coder, frontend-coder, tester, reviewer, debugger, docs; no optional helpers (devops, git-pr declined) | No auto-start on boot / pre-commit automation from devops | Add devops, git-pr | plan |
| D-16 | 2026-11-13 | Server | Small Python website (Flask) | Switching later = 2–3 day rewrite of web layer | FastAPI | plan |
| D-17 | 2026-11-13 | Storage | Crash-safe SQLite file at ~/.local/share/home-cookbook/cookbook.db | ≈1 day to change; export carries data | Plain JSON file | plan |
| D-18 | 2026-11-13 | Screens | Server-rendered pages + small vanilla JS | 3–4 day rewrite to change | JS framework + build step | plan |
| D-19 | 2026-11-13 | Start & reach | Home network on port 8765, refuse non-home visitors and cross-site changes; no auto-start | Minutes to change port | Localhost only | plan |
| D-20 | 2026-11-13 | Export format | Readable JSON with format version; upgrades never removed; newer-version files refused | Locked at M2; changes add an upgrade step | Compact binary | plan |
| D-21 | 2026-11-13 | Gap G-9: edit of a recipe deleted elsewhere | Keep typing; ask Save as new / Discard | ≈1 h to change | Refuse, typing lost | plan |
| D-22 | 2026-11-13 | Amount input (G-4) | One number in any common form; no ranges | ≈1 day + format step to add ranges | Allow ranges | plan |
| D-23 | 2026-11-13 | Scaled grams/millilitres (G-5) | Whole numbers (84 g); other units keep ¼ ⅓ ½ ⅔ ¾ — spec change to F-3 | ≈1 h to change | Fractions (84⅓ g) | plan |
| D-24 | 2026-11-13 | Search matching (G-8) | Forgiving: part of a word, ignore case/accents/apostrophes | ≈1 h to change | Whole words | plan |
| D-25 | 2026-11-13 | Toolkit | Python 3.12 via uv; pytest + Playwright 1.65.1 (fallback 1.49.1); ruff, mypy strict, import-linter, radon; 80% coverage; detect-secrets; no JS linter | Minutes–1 h each to change | Each item shown separately | plan |
| D-26 | 2026-11-13 | LLD, conventions, packages | Approved (with D-23 folded in) | — | — | plan |
| D-27 | 2026-11-13 | Install plan | Approved: uv Python 3.12 .venv, pinned packages, check.sh, plain git pre-commit hook, Playwright Chromium shell to ~/.cache | Undo: delete .venv and generated files | Edit / Cancel | plan |
| D-28 | 2026-11-13 | Playwright version | 1.49.1 (the LLD fallback) | Fast e2e teardown; 1.65.1 hung ~30s on browser.close() here · if wrong: re-pin and re-test, ~15 min | 1.65.1 with slow teardown | plan |
| D-29 | 2026-11-13 | Environment | Approved: Python 3.12 + pinned packages, Playwright 1.49.1, check.sh 7 gates, pre-commit hook | Undo: delete .venv and generated files | Request changes | plan |
| D-30 | 2026-11-13 | G-6 import over an existing title | Keep skipping; the import result names each skipped recipe and says "to restore one, delete it first, then import again" | Folds into T-04 · if wrong: add a replace picker later (~1 task) | Offer to replace · leave as is | plan |
| D-31 | 2026-11-13 | Plan | Approved: 10 tasks in 3 milestones | Build starts with T-01 | Request changes | plan |
| D-32 | 2026-11-13 | Guard vs DNS rebinding (review M-1) | Answer only when Host is an IP literal, localhost or *.local; else 403 | Malicious sites can't reach the app via the family's browser · open the app by IP or .local name; router names like desktop.lan get 403 | Accept the risk | T-01 |
| D-33 | 2026-11-13 | "1,000" amounts (review m-6) | A comma followed by exactly 3 digits is refused as unclear; "0,5", "2,25" still work (refines D-22) | No silent 1,000→1 · if wrong: ~15 min to change | Treat as thousands · keep as is | T-01 |
| D-34 | 2026-11-13 | Review minors in shared code | Fix m-1, m-2, m-3, m-7, m-9 in T-01 | One extra fix round | Fix 4 · log all | T-01 |
| D-35 | 2026-11-13 | Settings via .env | Reword .env.example: settings are environment variables in front of the command; no .env loading | No new package · if wrong: add python-dotenv (~15 min) | Add python-dotenv | M1-docs |
| D-36 | 2026-11-13 | Milestone M1 | Approved: as-built LLD + README; continue M2 in a fresh session | — | Continue here · request changes | M1-docs |
| D-37 | 2026-11-14 | Import: rename past 200 chars vs SPEC F-6 | Accept as built: refuse the whole file (A-13); log a follow-up for a clearer message than "not an export" | Only hand-edited files hit it · if wrong: shorten instead (~1 small task) | Shorten the title · clearer message only | M2-docs |
| D-38 | 2026-11-14 | Export timestamp precision (format v1 locked) | Whole seconds; "every field identical" holds to the second (LLD §5.5) | No format change · full precision later needs format v2 | Full precision now | M2-docs |
| D-39 | 2026-11-14 | Milestone M2 | Approved: as-built LLD + README; continue M3 in a fresh session | — | Continue here · request changes | M2-docs |

## Tier 2 — decided by agents (overrule any time)
| ID | Date | Decision | Chosen | Agent | Task |
|---|---|---|---|---|---|
| A-01 | 2026-11-13 | Where scaling runs | In the browser; never changes the saved recipe | planner | plan |
| A-02 | 2026-11-13 | Search | LLD picks where it runs; no search index | planner | plan |
| A-03 | 2026-11-13 | Undo window | Owned by the home computer, not the screen | planner | plan |
| A-04 | 2026-11-13 | Export format | Format version from day one; upgrade steps never removed | planner | plan |
| A-05 | 2026-11-13 | Undo after the title was re-saved elsewhere ("Save as new") | Undo never refused; restored as "Lemon Cake (2)" | architect | plan |
| A-06 | 2026-11-13 | Unit kind (g/ml vs other) | Decided only in the browser; "milliliter" spelling counts | architect | plan |
| A-07 | 2026-11-13 | Amount display before scaling | Shown unrounded until servings change | architect | plan |
| A-08 | 2026-11-13 | Save-as-new form | Stays in new-recipe mode | architect | plan |
| A-09 | 2026-11-13 | Leave-page prompt | Browser built-in confirm (LLD §7.4); wireframe custom dialog superseded; LLD §6.4 is the sole source of UI text | architect | plan |
| A-10 | 2026-11-14 | Where /export is mounted | From web/api.py via bp.record_once, outside /api; factory.py untouched | backend-coder | T-03 |
| A-11 | 2026-11-14 | Export dates | File name uses the home computer's local date; timestamps inside are UTC "…Z" | backend-coder | T-03 |
| A-12 | 2026-11-14 | Import: missing `favourite` / dates | favourite defaults false; missing dates default to the import time | backend-coder | T-04 |
| A-13 | 2026-11-14 | Import: rename past 200 chars | Refuse the whole file (nothing written) rather than truncate | debugger | T-04 |
| A-14 | 2026-11-14 | Import result display | menu.js stores the message in sessionStorage and reloads, so the list refreshes and the message stays | frontend-coder | T-04 |
