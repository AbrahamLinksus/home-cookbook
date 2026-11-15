# Codebase walkthrough — Home Cookbook

> A guided tour so the owner can understand, own and explain this code. Written at handover
> by the architect. Each section starts in plain words; the file-by-file detail is folded
> under "Technical detail". The big picture is in `docs/ARCHITECTURE.md`.

## 1. Read these first (in order)

In plain words: start where the app starts, then read the recipe rules, then one service, then the two web files, then the browser side. About 15 short files cover everything that matters.

1. `pyproject.toml`: the `[project.scripts]` line `cookbook = "cookbook.app.serve:main"` is what `uv run cookbook` runs; the import-linter contracts at the bottom are the layer rules.
2. `src/cookbook/app/serve.py`: `main()` and `_serve()`, the start-up order and the address banner.
3. `src/cookbook/app/factory.py`: `create_app()`, the one place where every part is built and connected.
4. `src/cookbook/domain/models.py`: what a recipe is (`Recipe`, `RecipeDraft`, `Ingredient`).
5. `src/cookbook/domain/rules.py`: `parse_draft()` (every validation rule), `title_key()` (the same-title rule), `free_title()`, `list_order()`.
6. `src/cookbook/domain/ports.py`: the two interfaces, `RecipeRepository` and `Clock`, that services use instead of touching the database or the system clock.
7. `src/cookbook/services/keeper.py`: `RecipeKeeper`, the heart of the app (create, edit with version check, star, delete, undo).
8. `src/cookbook/adapters/sqlite_repo.py`: `SqliteRecipeRepository`, the only code that runs SQL.
9. `src/cookbook/web/api.py` and `src/cookbook/web/pages.py`: every URL the browser can call.
10. `src/cookbook/web/errors.py`: the `BUILDERS` table that turns each named error into an answer.
11. `src/cookbook/web/messages.py`: every text a person sees, in one file.
12. `src/cookbook/templates/base.html`: the page frame, the menu, the undo bar, and how texts reach the browser (`data-texts`).
13. `src/cookbook/static/js/api.js`: `api()` and `uiText()`, used by every other script.
14. `src/cookbook/static/js/edit.js`: the biggest script; the edit form and the conflict dialog.
15. `tests/conftest.py`: `FakeClock` and the `app` / `client` fixtures every server test starts from.

## 2. Follow one request end to end

Trace: **adding a new recipe**, from tapping "+ Add recipe" to seeing the saved recipe.

In plain words: the list links to an empty form; the form is filled by JavaScript; Save sends the typed recipe as JSON; the server checks it, saves it in one database write, and answers with the new recipe's number; the browser then opens the recipe page.

<details>
<summary>Technical detail: file by file, with the line where each hand-off happens</summary>

**Opening the form**
1. `src/cookbook/templates/list.html` line 3: the `add-recipe` link goes to `/recipes/new`.
2. `src/cookbook/web/guard.py` line 45, `check_request()`: runs before every request (registered in `src/cookbook/app/factory.py` line 38). It refuses non-home addresses or host names with a plain-text 403.
3. `src/cookbook/web/pages.py` line 84, `new_recipe()`: renders `edit.html` with `form_data(None)` (line 38: blank title, 4 servings, no rows) and `version=None`.
4. `src/cookbook/templates/edit.html` line 74: the form data is embedded as JSON in `<script id="form-data">`; line 77 loads `edit.js`.
5. `src/cookbook/static/js/edit.js` line 245: `fill(...)` reads that JSON and adds one empty ingredient row and one empty step row; line 246 remembers the starting state, so leaving with changes asks "Discard changes?".

**Saving**
6. `edit.js` lines 258–261: the form's submit handler calls `save()` (line 168), which allows one request at a time, then `sendAndHandle()` (line 178).
7. `edit.js` line 143, `sendRecipe()`: with no recipe id, line 147 calls `api("POST", "/api/recipes", { recipe: readForm() })`. `readForm()` (line 45) sends every row, blank rows too, so error keys match row positions.
8. `src/cookbook/static/js/api.js` line 22, `api()`: sets JSON headers and calls `fetch` (line 31); it never throws; a network failure becomes status 0 with the `network` text.
9. `src/cookbook/web/guard.py` line 49: a write from another website (wrong `Origin`) is refused here.
10. `src/cookbook/web/api.py` line 36, `create_recipe()`: `_recipe_in()` (line 17) returns 400 unless the body holds a `recipe` object; then `parse_draft(...)` and `services().keeper.create(...)`.
11. `src/cookbook/domain/rules.py` line 36, `parse_draft()`: checks title, servings, ingredients and steps, collecting every problem; raises `InvalidRecipe(fields)` if any.
12. `src/cookbook/web/__init__.py` line 19, `services()`: fetches the services that `create_app` stored in `app.extensions["cookbook"]` (`factory.py` lines 33–37).
13. `src/cookbook/services/keeper.py` line 44, `RecipeKeeper.create()`: stamps `created_at`/`updated_at` from the injected clock, `favourite=False`, and calls `repo.add(...)`.
14. `src/cookbook/adapters/sqlite_repo.py` line 141, `add()`: opens a connection with the safety pragmas (`_transaction`, line 103), `_insert()` (line 75) writes the row with `version = 1`. If the unique title index fires, `_duplicate()` (line 61) turns it into `DuplicateTitle(existing_title)`.
15. Back in `api.py` line 38: answer `201 {"id", "version"}`.

**If something is wrong**
16. `src/cookbook/web/errors.py` line 83, `_handle_cookbook_error()`: looks up the error in `BUILDERS` (line 53) and `_answer()` (line 73) returns JSON for `/api/` paths: 422 `invalid` with a text per field, or 409 `duplicate_title`.
17. `edit.js` line 150, `refusedSave()`: shows each message beside its field (`showFieldErrors`, line 93) and focuses the first.

**Showing the result**
18. `edit.js` lines 183–184: on 201 it goes to `/recipes/<id>`.
19. `src/cookbook/web/pages.py` line 89, `view_recipe()`: `keeper.get(id)` and `ingredient_line()` (line 25) for each ingredient, giving the kitchen-style text (`display_amount`) and the exact fraction for the scaler.
20. `src/cookbook/templates/view.html` line 53 loads `view.js`, which wires the servings stepper (using `scaler.js`), the star and Delete.

</details>

## 3. How the layers fit

In plain words: the code is in layers, like rooms that only open inward. The recipe rules (domain) know nothing about websites or databases. The services use the rules and ask for storage through an interface. The web layer only talks to services. One start-up file connects them all, and an automatic check fails if anyone breaks these rules.

<details>
<summary>Technical detail</summary>

| Folder | Layer | May import |
|---|---|---|
| `src/cookbook/app/` | Start-up and composition root | everything |
| `src/cookbook/web/` | HTTP: routes, guard, error mapping, texts | services, domain (never adapters) |
| `src/cookbook/services/` | Use cases: keeper, finder, backup | domain only (ports, rules) |
| `src/cookbook/adapters/` | I/O: SQLite, system clock | domain only |
| `src/cookbook/domain/` | Pure rules and types | stdlib only |
| `src/cookbook/templates/`, `src/cookbook/static/` | Screens | only the HTTP contracts |

- Direction: `app` → `web` → `services` → `domain`, and `adapters` → `domain`. Services and adapters never import each other; nothing below `web` imports Flask, Werkzeug or waitress.
- Enforced by three import-linter contracts in `pyproject.toml` (run by `uv run lint-imports`) and by ruff's `TID251` rule, which bans `sqlite3` outside `src/cookbook/adapters/`.
- Composition root: `create_app()` in `src/cookbook/app/factory.py` builds `SqliteRecipeRepository`, `SystemClock` (or the clock passed in), `RecipeKeeper`, `RecipeFinder`, `BackupService`, and stores them as `Services` (`src/cookbook/web/__init__.py`) in `app.extensions["cookbook"]`. Routes reach them with `services()`.
- Browser side: page scripts (`list.js`, `view.js`, `edit.js`, `menu.js`) use shared modules (`api.js`, `undo.js`, `favourite.js`, `scaler.js`), never the other way round. Texts come from `uiText(key)`, filled from `messages.UI_TEXTS` via `base.html`.

</details>

## 4. How to extend it

In plain words: each kind of change has one obvious place to go and an existing example to copy.

| I want to… | Touch these files | Pattern to copy |
|---|---|---|
| add an endpoint | `src/cookbook/web/api.py` (route), a method on a service in `src/cookbook/services/`, a test in `tests/integration/` | `set_favourite` route → `RecipeKeeper.set_favourite` → `tests/integration/test_api_favourite.py` |
| add a screen | a template extending `src/cookbook/templates/base.html`, a route in `src/cookbook/web/pages.py`, a page script in `src/cookbook/static/js/`, styles in `src/cookbook/static/css/app.css`, an e2e test in `tests/e2e/` | `view.html` + `view_recipe()` + `view.js` |
| swap a provider (e.g. DB) | a new class in `src/cookbook/adapters/` implementing `RecipeRepository` from `src/cookbook/domain/ports.py`; change the one line in `create_app()` that builds the repository | `SqliteRecipeRepository`; for time, `SystemClock` and the test `FakeClock` in `tests/conftest.py` |
| add a new kind of error | a class in `src/cookbook/domain/errors.py`, one row in `BUILDERS` in `src/cookbook/web/errors.py`, its text in `src/cookbook/web/messages.py` | `DeletedElsewhere` and its `_simple(410, ...)` row |
| add a text the browser shows | one entry in `UI_TEXTS` in `src/cookbook/web/messages.py`, then `uiText("key")` in the script | `favourite_failed` used in `favourite.js` |
| change the export file | raise `CURRENT_FORMAT_VERSION`, add an `UPGRADES[n]` step in `src/cookbook/services/backup/formats.py`, add a frozen `tests/fixtures/exports/v<n>-*.json`; never edit old steps or fixtures | `test_every_fixture_imports_with_every_field` in `tests/unit/test_backup_import.py` |
| change the database table | append a new entry to `MIGRATIONS` in `src/cookbook/adapters/schema.py`; never edit a released one | the first entry of `MIGRATIONS` |
| add a setting | a field in `Settings` and a line in `Settings.from_env()` in `src/cookbook/app/config.py`, plus `.env.example` and the README "Settings" table | `COOKBOOK_UNDO_SECONDS` |

## 5. Tests

In plain words: there are three kinds of automatic tests: quick checks of the rules, checks of the web answers without a browser, and real-browser tests at phone size. `scripts/check.sh` runs them all (516 tests at handover). No test touches your real recipe file; each uses a temporary one.

<details>
<summary>Technical detail</summary>

- `tests/unit/`: domain rules, amounts, search, export/import format, and the services. Time is faked with `FakeClock` (`tests/conftest.py`), whose `advance(seconds)` moves time on for undo-window tests. Keeper and finder tests use a real `SqliteRecipeRepository` on a temp file; the backup tests use small in-memory fakes (`MemoryRepo` in `test_backup_export.py`, `Repo` in `test_backup_import.py`).
- `tests/integration/`: the Flask test client from the `client` fixture, built by `create_app(settings, clock=clock)` on `tmp_path`; one file per area (`test_api_create.py`, `test_guard.py`, `test_import.py`, `test_serve.py`, `test_sqlite_repo.py`, …).
- `tests/e2e/`: Playwright (Chromium headless shell) at 390×844, plus 1280×800 in `test_layout_at_home.py`. Fixtures in `tests/e2e/conftest.py`: `live_url` (the app in a background thread on a temp file), `seed` (adds a recipe through the API), `start_app` (the real `uv run cookbook` as a subprocess, used by `test_definition_of_done.py` and `test_layout_at_home.py`; skipped when the machine has no LAN address). The scaler is tested directly through `window.cookbookScaler` in `test_scaler.py`.
- `tests/fixtures/exports/v1-basic.json`: frozen export sample that every future version must still import.
- How fakes are injected: only through the two ports. `create_app(settings, clock=FakeClock())` swaps the clock; services take any `RecipeRepository` in their constructor. Nothing is patched inside the code.

Commands (from the project folder):
- Everything, with coverage: `scripts/check.sh`
- All tests: `uv run pytest`
- Quick tests only: `uv run pytest -q tests/unit tests/integration`
- Browser tests only: `uv run pytest -q tests/e2e` (one time first: `uv run playwright install --only-shell chromium`)
- One test: `uv run pytest tests/unit/test_keeper_create.py::test_get_unknown_id_raises_not_found`
- Save browser screenshots: `COOKBOOK_TEST_SHOTS=.results/shots uv run pytest -q tests/e2e`

</details>

## 6. Talking points

**Three interesting design decisions and their trade-offs**
- **A version number guards every edit.** Each recipe carries `version`; a save says which version it started from, and the database write only happens `WHERE id = ? AND version = ?` (`update_if_version` in `src/cookbook/adapters/sqlite_repo.py`). Two devices can never silently overwrite each other. Trade-off: saving an unchanged form still counts as a change, and starring is deliberately kept out of the version so it never triggers the warning.
- **The home computer owns the undo window.** Delete only marks the row (`deleted_at`); it is hidden everywhere at once and removed for good later (`purge_deleted_before`, or the next delete). So Undo works even if the phone locks, and the bar follows you across pages via `sessionStorage` in `undo.js`. Trade-off: only one delete can be undone at a time.
- **Every backup file loads forever.** The export carries `format_version`; each future change adds a pure `UPGRADES[n]` step and a frozen sample file, and old steps are never edited (`src/cookbook/services/backup/formats.py`). Trade-off: a little more care for every format change, in return for never stranding an old backup.

**One problem hit during the build and how it was solved**
- The newest Playwright (1.65.1) hung about 30 seconds every time it closed the browser on this machine, which would have made the browser tests painfully slow. The team pinned 1.49.1 instead (D-28), and the quick smoke script `scripts/smoke_playwright.py` now fails if closing the browser takes 5 seconds or more. Another: the review found that a malicious website could reach the app through a family member's browser with a DNS trick, so the guard now also checks the host name (only IPs, `localhost` and `.local` names; D-32, `_is_home_host` in `src/cookbook/web/guard.py`).

**What to do next with more time**
- Push the code to GitHub so the ready-made CI workflow (`.github/workflows/ci.yml`) runs on every change; today the remote is a local bare repository.
- Start the app automatically when the home computer boots (left out on purpose, D-15).
- Small fixes from `STATE.md` "Known minors": JSON answers for refused `/api/` requests so a blocked import shows the right message, a clearer message for the 200-character rename case (D-37), and a single database read per search keystroke.
