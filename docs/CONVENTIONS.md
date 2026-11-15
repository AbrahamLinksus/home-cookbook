# CONVENTIONS — Home Cookbook

> Written by the Architect with the LLD and approved by the owner. Every coder reads this
> before every task; the Tester enforces section 6 automatically, and the Reviewer
> enforces sections 2–5. Module details live in `docs/LLD.md` (referenced as `LLD §n`).

## 1. Stack-specific style
- Python 3.12 only (`~=3.12.0`, uv-managed). PEP 8 via ruff (`target-version = "py312"`, line length 100); type hints on every function; `mypy --strict` clean.
- No Pydantic: I/O boundaries are checked by plain functions in `cookbook.domain.rules` (`parse_draft`) and `services/backup/formats.py` (`from_document`); domain types are `@dataclass(frozen=True, slots=True)`.
- Datetimes are timezone-aware UTC inside the app, ISO 8601 with `Z` in the DB and export file. Get "now" only from the injected `Clock`, never `datetime.now()` in domain/services.
- `sqlite3` may be imported only in `src/cookbook/adapters/**` (ruff `TID251` banned-api with a per-file ignore for that folder).
- Flask: blueprints in `web/pages.py` (HTML) and `web/api.py` (JSON); views stay thin (parse → one service call → render/JSON). Get services with `cookbook.web.services()`.
- Templates (Jinja2): autoescape on (default); never `|safe` on recipe text; embed data with `|tojson`. Every interactive element has the `data-testid` named in LLD §7.1.
- JavaScript: plain ES modules (`type="module"`), no build, no Node, no external libraries; `const`/`let`, `async/await`, all HTTP through `static/js/api.js` (one exception: `list.js` fetches the HTML list fragment `/recipes/_list` with raw `fetch`, because it needs text and an `AbortSignal`, which `api.js` does not offer; LLD §7.2). Pure logic (scaler) has no DOM access. JSDoc type comments on exported functions.
- CSS: one file `static/css/app.css`, mobile-first (390 px base, no horizontal scroll), one `@media (min-width: 768px)` desktop layer; touch targets ≥ 44 px.

## 2. Layering (dependencies point inward only)
```
cookbook.app        →  cookbook.web        →  cookbook.services       →  cookbook.domain
(composition root,     (Flask routes, guard,  (keeper, finder, backup:   (dataclasses, rules,
 config, serving)       error mapping, texts)  business logic, no I/O     errors, Protocols;
                                               except through ports)      stdlib only)
                        cookbook.adapters  →  cookbook.domain
                        (SQLite repository, system clock: all I/O here)
templates + static JS  →  HTTP contracts in LLD §3.2, §4.2, §5.2 only
```
- Routes never import `cookbook.adapters`; they reach storage only through services.
- Services and adapters never import each other, Flask, Werkzeug or waitress; services use `RecipeRepository` and `Clock` from `domain.ports`.
- Domain imports nothing from the other layers and does no I/O.
- Only `cookbook.app.factory.create_app` constructs adapters and services.
- Front end: page JS (`list.js`, `view.js`, `edit.js`, `menu.js`) → shared modules (`api.js`, `undo.js`, `favourite.js`, `scaler.js`); shared modules never import page JS. Browser texts come only from `uiText(key)` (LLD §6.4).
- Enforced by the import-linter contracts in LLD §0.3.

## 3. SOLID: what it means in this project

| Principle | Rule here |
|---|---|
| **S**ingle responsibility | One reason to change per module: keeper (one recipe's rules), finder (search), backup (file format), repository (SQL), web (HTTP). No SQL in services, no business rules in routes or templates. |
| **O**pen/closed | Export format changes are new `UPGRADES[n]` steps, never edits to old ones (LLD §5.3). New error kinds are new exception classes plus one row in `web/errors.py`. |
| **L**iskov substitution | Any `RecipeRepository` (SQLite, or the in-memory fake in tests) honours LLD §2.1 exactly, including `DuplicateTitle` on clashes and all-or-nothing `add_many`. |
| **I**nterface segregation | Two small Protocols only: `RecipeRepository`, `Clock`. |
| **D**ependency inversion | Services receive repo/clock/settings in their constructors; Flask reaches them via `app.extensions["cookbook"]`. Wiring happens only in `create_app`. |

**Where to abstract:** only the two ports above (storage, time). Everything else is plain functions and concrete classes; no interface with one implementation and no planned second.

## 4. Limits
- Function ≤ 40 lines; cyclomatic complexity ≤ 10; parameters ≤ 5 (use a dataclass beyond that).
- File ≤ 300 lines; class ≤ 200 lines. Same limits for JS files and functions (Reviewer checks; no JS linter).
- No commented-out code, no `print` (use `logging`; `serve.py` banner goes through the logger too), no `console.log` left in JS, no TODOs without a task ID.

## 5. Errors, logging, config, tests
- Errors: domain exceptions from `cookbook.domain.errors` only; mapped to HTTP status and message only in `web/errors.py` (LLD §6.3); user-facing texts only in `web/messages.py` (LLD §6.4) or the templates.
- Logging: stdlib `logging`, `key=value` format; log recipe ids, never titles or recipe text.
- Config: only `cookbook.app.config.Settings.from_env()` reads the environment (LLD §0.5); no magic numbers elsewhere (undo grace and size limits are named constants).
- Tests: Arrange-Act-Assert, one behaviour per test, names `test_<unit>_<condition>_<expected>`.
  - `tests/unit/`: domain rules, formats, services with an in-memory `RecipeRepository` fake and a fixed `Clock`.
  - `tests/integration/`: Flask test client on `create_app(Settings(db_path=tmp_path/...), clock=FakeClock)`; SQLite repository on a temp file.
  - `tests/e2e/`: pytest-playwright against a live server started in a thread (`werkzeug.serving.make_server("127.0.0.1", 0, app)`) on a temp DB, phone viewport 390×844 plus one desktop run; scaler tested via `page.evaluate("window.cookbookScaler…")`. One e2e test per acceptance criterion tagged `(S-xx)`. Shared fixtures live in `tests/e2e/conftest.py` (`live_url`, `seed`, `start_app`); put new shared helpers there, not copies per file.
  - Definition-of-done e2e (A-33): the `start_app(name)` fixture runs the real app as `timeout -k 5 300 uv run --no-sync cookbook` on a temp `COOKBOOK_DB` and a free `COOKBOOK_PORT`, waits for the banner, drives the printed LAN URL, and always stops it (skips if the machine has no LAN address). This server is a subprocess, so it adds no coverage. Screenshots go to `tmp_path`, or to the folder in `COOKBOOK_TEST_SHOTS` (e.g. `.results/T-10`) when evidence is wanted.
  - `tests/fixtures/exports/v<n>-*.json`: frozen export samples; never edited once added (LLD §5.3).
  - Never patch deep inside code; fake through the two ports.

## 6. Environment, commands and automated checks
### 6.1 Environment
| Item | Value |
|---|---|
| OS | Arch Linux (home computer); system Python 3.14 is **not** used |
| Python | 3.12 via uv (`uv python install 3.12`; `.python-version` = `3.12`) |
| Dependencies | `pyproject.toml` + `uv.lock` (exact pins); dev tools in the `dev` dependency group |
| Browser for tests | Playwright's own Chromium headless shell: `uv run playwright install chromium --only-shell` (no system Chromium, no `install-deps` on Arch) |
| Data file | `COOKBOOK_DB` (default `~/.local/share/home-cookbook/cookbook.db`); tests always use `tmp_path` |
| Secrets | none; `.env` is git-ignored if ever used, keys documented in `.env.example` |

### 6.2 Commands
| Purpose | Command (from the project root) |
|---|---|
| Install / update env | `uv sync` |
| Run the app | `uv run cookbook` → open the printed `http://<lan-ip>:8765` on phone/laptop |
| Run on another port | `COOKBOOK_PORT=9000 uv run cookbook` |
| All checks (Tester) | `scripts/check.sh` |
| All checks except coverage (coders, debugger) | `CHECK_NO_COVERAGE=1 scripts/check.sh` |
| Fast tests only | `uv run pytest -q tests/unit tests/integration` |
| End-to-end only | `uv run pytest -q tests/e2e` |
Never leave the app running after a task: start background servers with `timeout`.

### 6.3 Automated checks (`scripts/check.sh` must pass; Tester runs it on every task)
Coders and the debugger run `CHECK_NO_COVERAGE=1 scripts/check.sh` (every check except the coverage
threshold, since tests are the Tester's job); the Tester runs the full script and owns coverage.

| Check | Command (Python; there is no TypeScript and no JS toolchain) |
|---|---|
| Lint + format | `uv run ruff check .` + `uv run ruff format --check .` (rules: E,F,W,I,N,UP,B,SIM,C90,PL,RUF,TID; `TID251` bans `sqlite3` outside `src/cookbook/adapters/`) |
| Types | `uv run mypy --strict src` |
| Complexity / size | ruff `C901` (max 10), `PLR0913` (max 5 args), `PLR0915`; `uv run radon cc -n C -s src` (script fails if it prints anything) |
| Layer rules | `uv run lint-imports` (contracts in LLD §0.3) |
| Tests + coverage | `uv run pytest --cov=cookbook --cov-fail-under=80` (unit + integration + e2e; e2e server runs in-process so it counts); with `CHECK_NO_COVERAGE=1`: `uv run pytest` |
| Secrets in code | `uv run detect-secrets-hook --baseline .secrets.baseline` over all tracked files |
| JavaScript | No linter (no Node). Covered by Playwright e2e tests and the Reviewer against section 4 limits |
