# Research — Home Cookbook (Stage 4)

Date: 2026-11-13. Versions are the latest stable on PyPI / npm on this date (registry JSON pages). Recommendations are input for the owner's Tier 1 decisions, not decisions.
"Unverified" = I could not confirm it from a source; the LLD or env-setup should check it with one command before relying on it.

Project facts used (HLD, SPEC §6, §9, §10): one user, ~500 recipes (~30 ingredients, ~20 steps each), phone + laptop on home Wi-Fi, Arch Linux, Python 3.14 system / 3.12 via uv, no cost, no stack preference stated, scaling runs in the browser (HLD assumption), 3 mobile-first screens, 10 s undo owned by the server.

## 1. Server stack

| | A. Flask 3.1.3 (+ Werkzeug 3.1.9, Jinja2) | B. FastAPI 0.162.5 + uvicorn 0.54.0 | C. Django 6.1.3 |
|---|---|---|---|
| Python | >=3.9; no 3.14 classifier, pure Python, no compiled parts | >=3.10; 3.14 classifier yes (both) | >=3.12; 3.14 classifier yes |
| Licence | BSD-3 | MIT | BSD-3 |
| Maintenance | Active (3.1.3 released 2026-02-19, Pallets) | Very active (frequent releases) | Active, major release line |
| Install footprint | Small: 6 pure-Python deps (blinker, click, itsdangerous, jinja2, markupsafe, werkzeug) | Medium-large: starlette, pydantic (compiled Rust core), anyio, typing-inspection, annotated-doc, **opentelemetry-api** now a core dep; templates/forms need extras (`standard`: jinja2, python-multipart, httpx, uvicorn[standard]...) | Medium: asgiref, sqlparse; but big framework (ORM, admin, auth, migrations) mostly unused here |
| Fit | Server-rendered pages + a few JSON endpoints; sync code matches sqlite3; fewest concepts | Strong for JSON APIs / typed models; async adds nothing for one user; HTML forms need extra pieces | Over-sized: its ORM/migrations would fight a hand-owned export format |
| Known issues | Dev server (Werkzeug) is documented as not for production; needs a small WSGI server (see below) | Pydantic is compiled; wheels for 3.14 exist per classifier (wheel presence not individually checked) | None for 3.14; heavy for the job |
| greenlet | none | none | none |

Serving Flask on the home network (WSGI server, same decision):
| | Werkzeug dev server | waitress 3.0.2 | gunicorn |
|---|---|---|---|
| Notes | Built in, zero install, `host=0.0.0.0`; Flask docs say not for production | Pure Python, cross-platform, BSD-like ZPL; last release 2024-11-16, no 3.14 classifier (probably works; unverified) | Mature; Unix only, pre-fork, extra moving part |

Sources: https://pypi.org/pypi/flask/json · https://pypi.org/pypi/werkzeug/json · https://pypi.org/pypi/fastapi/json · https://pypi.org/pypi/uvicorn/json · https://pypi.org/pypi/django/json · https://pypi.org/pypi/waitress/json

**Recommendation: A, Flask + Jinja2.** Fewest moving parts, tiny pure-Python install, no greenlet or compiled packages, runs unchanged on 3.14 or 3.12. Serve with waitress (one extra pure-Python package, one command) rather than the dev server; if waitress misbehaves on 3.14, fall back to Werkzeug's server, which is acceptable for one user on a home LAN with the "no password" decision already made. Pin Python 3.12 via uv if any dependency misbehaves on 3.14. No Node needed at runtime.

## 2. Data store (one file, ~500 recipes, safe writes, per-recipe version)

| | A. SQLite via stdlib `sqlite3` | B. One JSON file, atomic replace (write temp, fsync, `os.replace`) | C. SQLAlchemy 2.1.8 on SQLite |
|---|---|---|---|
| Maintenance | Part of Python (stdlib); SQLite is extremely stable | Stdlib only | Active; requires Python >=3.11; 3.14 classifier yes |
| Install footprint | None | None | One package (core dep: typing-extensions only); **greenlet is needed only with the `asyncio` extra**, not for sync use |
| Power-loss safety | Atomic transactions. With `journal_mode=WAL` + `synchronous=FULL` it is fully ACID (consistent and durable). `NORMAL` in WAL stays consistent but may lose the last commit; in default rollback mode `NORMAL` has a tiny corruption chance on old filesystems | Safe only if the code does the fsync + rename dance correctly (own code to get right); whole file rewritten per save (500 recipes is well under 1-2 MB, fast enough) | Same as A (it sits on sqlite3) |
| All-or-nothing import | One transaction | Build whole new file, replace | One transaction |
| Per-recipe version | `version INTEGER` column; save = `UPDATE ... WHERE id=? AND version=?`, 0 rows changed means "changed on another device" (atomic, race-free even with two requests at once) | Check in code under a lock; single-process only | Same as A, plus ORM version feature |
| Search ~500 recipes | `LIKE` / load all and filter in Python; both well under 1 s | Load all, filter | Same as A |
| Quirks | WAL leaves `-wal` and `-shm` side files while running; copy/backup the db only through SQLite's backup API or after a clean close. The "one file" is true at rest | Hand-rolled durability is the usual source of bugs | Extra layer to learn for ~2 tables |

Sources: https://www.sqlite.org/pragma.html#pragma_synchronous · https://pypi.org/pypi/sqlalchemy/json

**Recommendation: A, stdlib `sqlite3`** with `PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;`, an integer `version` per recipe bumped on every content change (not on star), and a nullable `deleted_at` column for the undo window. Zero dependencies, and the corruption-on-power-loss requirement is met by a documented setting rather than hand-written code. Store ingredients and steps as JSON text in the recipe row (ordered lists, ~500 rows) to keep the schema to one table; the LLD can choose. Export format stays a separate, versioned JSON file independent of the db layout. SQLAlchemy adds a layer with no benefit here.

## 3. Front end

| | A. Server-rendered pages + small vanilla JS (no build) | B. Server-rendered + htmx 2.0.11 and/or Alpine 3.17.5 | C. SPA (Preact 11.2.0 / Svelte 5.57.3 + Vite) |
|---|---|---|---|
| Maintenance | n/a (browser built-ins) | htmx 2.x supported "indefinitely"; htmx 4.0.0 released 2026-08-28 but npm "latest" is still 2.0.11 until early 2027. Alpine active, MIT | Active |
| Licence | n/a | htmx 0BSD; Alpine MIT | MIT |
| Install footprint | None; one small .js file served by Flask | One file each (vendored or CDN-free copy since no internet is assumed at home use); no runtime deps except Alpine's bundled reactivity | Needs Node + build tool + `node_modules`; separate JSON API and build step in deploy |
| Instant scaling (F-3) | ~30 lines JS reading amounts from data attributes | Alpine makes it declarative; htmx would add a server round trip (wrong tool) | Natural |
| 10 s undo bar | `setTimeout` plus a POST to undo; the server owns the real window (HLD) | Same | Same |
| Live search narrowing | `fetch` on input or client-side filter of the ~500 titles (fast either way) | htmx `hx-trigger="input"` does it with no JS written | Natural |
| Fit for 3 screens | Best: least to learn and to break | Good; adds a dependency for small gain; htmx 2 vs 4 version choice to manage | Over-sized; duplicates validation and routing; heavier to test |
| Known issues | None | htmx 4 changes (fetch, opt-in inheritance) mean pin 2.x deliberately | Build tooling churn; Vitest 5 needs Node ^22.12 |

Sources: https://registry.npmjs.org/htmx.org/latest · https://registry.npmjs.org/alpinejs/latest · https://registry.npmjs.org/preact/latest · https://registry.npmjs.org/svelte/latest · https://four.htmx.org/announcements/2026-08-28-htmx-4.0.0-is-released · https://www.infoq.com/news/2026/09/htmx-4-released/

**Recommendation: A, Jinja2 server-rendered pages with a few small vanilla JS files** (scaler, undo bar, search filter, servings stepper). No build step, no Node needed in the running app, one language on the server. If the LLD finds the JS growing past ~200 lines, add Alpine (single file) before considering a SPA. A SPA is not justified by three screens.

## 4. Kitchen fraction rounding

Required rule (SPEC F-3): round to nearest of 0, ¼, ⅓, ½, ⅔, ¾, 1 within each whole; unit-less counts to nearest ½; never 0 (shows ¼); unit unchanged. Runs in the browser (HLD assumption), so a JS implementation is needed; the browser is the only place it must exist.

| | A. fraction.js 5.3.4 (npm) | B. Python `fractions.Fraction` (stdlib) | C. Own code (~40 lines JS) |
|---|---|---|---|
| Maintenance | MIT, no runtime deps, no deprecation; last publish about 2025-08 (inferred) | Stdlib | Ours |
| Footprint | One package plus bundling/vendoring | None | None |
| Does the job? | Exact rational arithmetic and string output, but no "snap to ¼ ⅓ ½ ⅔ ¾" rule and no unicode glyphs; you still write the snapping | Server-side only, so would put the scaler in the wrong module or duplicate it | Directly implements the rule: pick nearest from a fixed candidate list, whole part separate, glyph map |
| Risks | New dependency for a trivial piece | Two implementations to keep equal | Edge cases to test: exact ties, e.g. 0.375 (nearest ⅓ is correct, matches SPEC 8→4 example), 0.125 (rounds up to ¼ via never-zero rule), whole-number carry (1.9 → 2), float error (scale with integer/rational arithmetic or tolerance) |

Sources: https://registry.npmjs.org/fraction.js/latest · https://docs.python.org/3/library/fractions.html

**Recommendation: C, own code.** The rule is a fixed list of 7 candidates, so a library gives only arithmetic the code does not need. Keep it a pure function with a table-driven test (all SPEC §5 examples plus tie cases). The owner should settle exact ties (e.g. 0.625 is halfway between ½ and ⅔: choose round-up or nearest) in the LLD; the SPEC does not say.

## 5. Test runner + browser end-to-end

| | A. pytest 9.2.0 + Playwright for Python 1.65.1 + pytest-playwright 0.10.0 | B. @playwright/test 1.65.0 (Node) + Node built-in `node:test` or Vitest 5.1.0 for JS | C. Selenium / Cypress |
|---|---|---|---|
| Maintenance | pytest, Playwright: very active (Apache-2.0 / MIT) | Active; Apache-2.0 | Not researched (no reason found to prefer them) |
| Python 3.14 | pytest and Playwright carry the 3.14 classifier. **Playwright requires greenlet (>=3.1.1,<4)**; current greenlet 3.5.6 has the 3.14 classifier; I did not confirm a prebuilt Linux cp314 wheel (without one it would compile from source, needing a C compiler). Check with `uv pip install --only-binary :all: greenlet` | No Python involved | n/a |
| Footprint | Python packages plus browser download (hundreds of MB) | Node >=20 (Vitest: ^22.12), `node_modules`, browser download | Heavy |
| Arch Linux | Playwright does not officially support Arch; maintainers say they do not test on it. `playwright install` may report "generic-linux" unsupported or fail on bundled-browser libraries. Workaround reported by users: install Chromium with pacman and launch with `executable_path="/usr/bin/chromium"` (needs a Chromium version close to the one Playwright expects). Anecdotal (forum/gist), not official | Same Arch caveat | n/a |
| Phone-width checks | Built-in device emulation (e.g. viewport 390 x 844, touch, mobile user agent) in Chromium; screenshots via the same API | Same | Possible, clunkier |
| Fit | Same language and runner as the server tests; one `check` command; fixtures start the Flask app on a temp database | Second language/toolchain just for tests; JS scaler tests natural | |

Sources: https://pypi.org/pypi/pytest/json · https://pypi.org/pypi/playwright/json · https://pypi.org/pypi/pytest-playwright/json · https://pypi.org/pypi/greenlet/json · https://registry.npmjs.org/@playwright/test/latest · https://registry.npmjs.org/vitest/latest · https://github.com/microsoft/playwright/issues/11122 · https://gist.github.com/mewset/44d4b5f21d3d00587a50190aa85cb692

**Recommendation: A, pytest + Playwright for Python (pytest-playwright), using the system Chromium on Arch** and a 390-wide emulated phone. Test the JS scaler through Playwright (call the page's function) so Node is not required; if Node is present anyway, `node --test` (built in) is a no-install option for pure-function tests. env-setup must verify, before the LLD commits: (1) greenlet installs on 3.14 without compiling, else use Python 3.12 via uv for the project; (2) Playwright can drive the system Chromium. pytest-asyncio is not needed (sync Flask app).

## Overall risks to check early
1. greenlet wheel on 3.14 (Playwright only). Fallback: project on Python 3.12 via uv.
2. Playwright on Arch needs system Chromium, not its bundled download (anecdotal).
3. waitress has no 3.14 classifier and no release since 2024-11; fallback is Werkzeug's server.
4. WAL mode creates side files; backups must use SQLite's backup or a clean close (export file is the owner's real backup anyway).

## Plain-word summary for the owner
1. The app will be a small Python website that runs on your home computer and nothing else, with no paid or online services.
2. Recipes will live in one database file that survives a power cut, and each recipe carries a counter so a stale save is caught.
3. The three screens will be ordinary web pages with a little extra code for the instant scaling and the 10-second undo, with no heavy framework.
4. The "½ cup instead of 0.375 cup" rounding is short enough to write ourselves, so we add no extra package.
5. Phone-size screens will be checked automatically with a browser robot; on your Arch computer it may need the browser you already have installed, which we will test first.
