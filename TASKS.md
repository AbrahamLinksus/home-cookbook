# TASKS — home-cookbook

Status: Backlog → In progress → Review → Needs you → Done

A task is one user-visible feature slice end to end (data, logic, UI, tests), never one layer.
Only the first task may be a foundation task (the app starts and shows its first screen; shared
helpers). Caps by size: small 8, medium 15, large 30; an extra task carries `Why separate:`.

Every task needs `Owner:`, `Depends on:` (real data or interface dependencies only, never a
preferred order; `—` for none) and `Files:` (paths or globs it will create or change): the build
schedules from them (`taskgraph.py`), running tasks with no dependency and no shared files at
the same time.

`Context:` lists exactly what the task's agents need to read: spec stories, LLD sections
(by number) and file globs. The Orchestrator builds every brief's `Read:` field from it.

Owner `backend-coder → frontend-coder` means both coders work the slice in that order: backend-coder
writes the Python under `src/cookbook/` (not templates/static), then frontend-coder writes
`templates/` and `static/` against the routes just built (scopes in `.devteam/scopes.json`).
Test files listed under `Files:` are written by the tester. Paths are relative to the project root.

## M1 · First recipe end to end (data model locked)

### T-01 · Foundation: the app starts on the home network and shows the empty recipe list
- Owner: backend-coder → frontend-coder
- Depends on: —
- Files: pyproject.toml (`[project.scripts] cookbook` entry only, if missing), src/cookbook/__main__.py, src/cookbook/app/*, src/cookbook/domain/*, src/cookbook/adapters/*, src/cookbook/services/__init__.py, src/cookbook/services/keeper.py, src/cookbook/services/finder.py, src/cookbook/services/backup/__init__.py, src/cookbook/services/backup/service.py, src/cookbook/web/__init__.py, src/cookbook/web/guard.py, src/cookbook/web/errors.py, src/cookbook/web/messages.py, src/cookbook/web/pages.py, src/cookbook/templates/base.html, src/cookbook/templates/error.html, src/cookbook/templates/list.html, src/cookbook/templates/_list_items.html, src/cookbook/static/css/app.css, src/cookbook/static/js/api.js, src/cookbook/static/js/undo.js, src/cookbook/static/js/menu.js, tests/conftest.py, tests/unit/test_domain_*.py, tests/integration/test_sqlite_repo.py, tests/integration/test_guard.py, tests/integration/test_serve.py, tests/e2e/conftest.py, tests/e2e/test_start.py
- Context: SPEC US-01, US-02 · LLD §0, §1, §2, §6, §7.1, §7.2 · files: pyproject.toml, scripts/check.sh, docs/wireframes/*.html
- Notes: builds every shared module in LLD §0.7 in full (all of domain §1, adapters §2, app, web shared parts, base/error templates, api.js, undo.js). `RecipeKeeper`, `RecipeFinder`, `BackupService` exist with their §3.1/§4.1/§5.1 constructors so `Services` is complete; only `RecipeKeeper.list_recipes` has behaviour (it feeds `GET /`). `app.css` covers all three screens from the wireframes, mobile 390 px plus the 768 px desktop layer, so feature tasks need no CSS. `menu.js` is an empty module until T-04.
- Status: Done
- Acceptance criteria:
  - [x] `timeout 10 uv run cookbook` with `COOKBOOK_DB` in a temp folder logs "Home Cookbook is running. On your phone or laptop open: http://<lan-ip>:8765 …", creates the data file (`PRAGMA user_version` = 1) and stops cleanly; `COOKBOOK_PORT=abc` exits with code 2 and a one-line message
  - [x] `GET /` on an empty app at 390×844 shows "No recipes yet" with an "Add recipe" button and the header menu ("Export all recipes", "Import recipes"), with no sideways scroll; screenshots at 390 and 1280 wide in `.results/T-01/` (S-10)
  - [x] A request from a non-home address (e.g. `REMOTE_ADDR=8.8.8.8` in the test client) gets 403 "Home Cookbook only answers inside the home"; a POST with `Origin: http://evil.example` gets 403; requests from 192.168.x.x and 127.0.0.1 are served
  - [x] Domain unit tests: `parse_amount` accepts "2", "2.5", "0,5", "1/2", "1 1/2" (= 3/2), "½", "1 ½" and refuses "2-3", "2 to 3", "0", "abc"; `display_amount("2.5")` = "2½" and `("1 1/2")` = "1½"; `title_key(" pancakes ") == title_key("Pancakes")`; `normalise("Shepherd's Crème")` = "shepherds creme" (S-01, S-08)
  - [x] SQLite repository integration tests: add/get keeps every field and order; a second live recipe with the same title key raises `DuplicateTitle`; `add_many` with one clash writes nothing; `CHECK_NO_COVERAGE=1 scripts/check.sh` passes, including `lint-imports`
- Result: ✅ 5/5 criteria · 134 tests · coverage 86% · 1 debug round (review M-1 DNS rebinding fixed, D-32..D-34) · commit 474be37

### T-02 · Add a recipe and read it on the phone
- Owner: backend-coder → frontend-coder
- Depends on: T-01
- Files: src/cookbook/services/keeper.py, src/cookbook/web/api.py, src/cookbook/web/pages.py, src/cookbook/templates/edit.html, src/cookbook/templates/view.html, src/cookbook/templates/_list_items.html, src/cookbook/static/js/edit.js, tests/unit/test_keeper_create.py, tests/integration/test_api_create.py, tests/e2e/test_add_recipe.py
- Context: SPEC US-01, US-02 · LLD §1.1, §1.2, §1.4, §3.1, §3.2, §6.3, §6.4, §7.3, §7.4 · files: src/cookbook/domain/*, src/cookbook/services/keeper.py, src/cookbook/web/*.py, src/cookbook/templates/*, src/cookbook/static/js/api.js, docs/wireframes/recipe-edit.html, docs/wireframes/recipe-view.html
- Notes: covers `create`, `get`, `POST /api/recipes`, `GET /recipes/new`, `GET /recipes/<id>` (read view with `IngredientLine` incl. `data-num/den/unit/text`, ready for scaling in T-09). Editing an existing recipe is T-06.
- Status: Backlog
- Acceptance criteria:
  - [ ] Adding "Grandma's Apple Pie" (8 servings; "2 cups flour", "1 cup butter", "6 apples", "¾ cup sugar", "1 tsp cinnamon", "salt, to taste" with no amount; 5 steps starting "Preheat oven to 200°C") opens it in read view; the list shows "Grandma's Apple Pie · 8 servings"; reopening shows exactly what was typed
  - [ ] Saving " pancakes " while "Pancakes" exists keeps the form open with "You already have a recipe called 'Pancakes'. Please choose another name, e.g. 'Pancakes (Gran's)'" under the title and saves nothing; saving as "Pancakes (Gran's)" works (S-07)
  - [ ] Amounts typed "2", "2.5", "1/2", "1 1/2", "½" save and show as "2", "2½", "½", "1½", "½"; "2-3" keeps the form open with "Enter one amount, e.g. 2 or 2½" under that amount; a blank title or servings 0 keeps the form open with the message beside the field and focus on it (S-01)
  - [ ] Ingredient and step rows can be added, removed and moved up/down; an ingredient added last and moved up to line 6 is saved and shown at line 6 (S-09); leaving the new form after typing asks "Discard changes?"
  - [ ] The read view of a 38-ingredient, 22-step recipe (one step 900 words) at 390×844 has no sideways scroll (US-02, S-09); screenshots of edit and view at 390 and 1280 in `.results/T-02/`
- Result:

## M2 · Backup format locked

### T-03 · Export all recipes to one file
- Owner: backend-coder
- Depends on: T-01
- Files: src/cookbook/services/backup/service.py, src/cookbook/services/backup/formats.py, src/cookbook/web/api.py, tests/unit/test_backup_export.py, tests/integration/test_export.py
- Context: SPEC US-08 · LLD §5.1, §5.2, §5.3, §5.5, §6.3 · files: src/cookbook/domain/*, src/cookbook/services/backup/*, src/cookbook/web/api.py, src/cookbook/templates/base.html
- Notes: the "Export all recipes" link already exists in `base.html` (T-01); this task makes `GET /export` answer it.
- Status: Backlog
- Acceptance criteria:
  - [ ] With 42 recipes, tapping "Export all recipes" downloads one file `cookbook-<home computer's date>.json` holding all 42 with title, servings, favourite, ingredients in order (amount as typed, `null` when none), steps in order, created_at and updated_at
  - [ ] The file matches LLD §5.3: `"format": "home-cookbook-export"`, `"format_version": 1`, `app_version`, `exported_at`, `recipe_count` equal to the number of recipes; UTF-8, indented 2, with "Crème Brûlée" and "200°C" readable as typed when opened in a text viewer (S-12)
  - [ ] An empty app exports a valid file with `"recipe_count": 0` and an empty recipe list (S-10)
  - [ ] A recipe waiting out its undo window is not exported (unit test with the in-memory repository fake and a fixed Clock)
- Result:

### T-04 · Load an export file back in (any version, all or nothing)
- Owner: backend-coder → frontend-coder
- Depends on: T-03
- Files: src/cookbook/services/backup/service.py, src/cookbook/services/backup/formats.py, src/cookbook/web/api.py, src/cookbook/static/js/menu.js, tests/fixtures/exports/v1-*.json, tests/unit/test_backup_import.py, tests/integration/test_import.py, tests/e2e/test_backup_round_trip.py
- Context: SPEC US-08, US-09, F-6 · scenarios S-05 · LLD §5, §6.3, §6.4, §7.1 · files: src/cookbook/domain/*, src/cookbook/services/backup/*, src/cookbook/web/api.py, src/cookbook/templates/base.html, src/cookbook/static/js/api.js, src/cookbook/static/js/menu.js
- Status: Backlog
- Acceptance criteria:
  - [ ] Export 42 recipes, import the file into an empty app: the menu shows "Imported 42 recipes", the list shows all 42 (favourites on top), and exporting again gives every recipe with every field identical (only `exported_at` differs)
  - [ ] The same file imported into an app already holding "Lemon Cake" and "shepherd's pie" shows "Imported 40 recipes · skipped 2 with the same title" and leaves those two unchanged
  - [ ] That import result names each skipped recipe ("Lemon Cake", "Shepherd's Pie") and says "To restore one, delete it first, then import again"; deleting "Lemon Cake" (after its Undo window) and importing the same file again brings back the file's "Lemon Cake" with every field as exported and skips only "Shepherd's Pie" (S-05, D-30)
  - [ ] A file holding two recipes titled "Pancakes" imports both, the second as "Pancakes (2)", and the message says "renamed 1 with a repeated title" (S-07)
  - [ ] `holiday.jpg`, an export with a missing bracket halfway through, and one whose `recipe_count` is wrong each show "This file isn't a Home Cookbook export; nothing was changed" with the recipe count unchanged; a file with `format_version` 2 shows "This file was made by a newer version of Home Cookbook. Update the app to load it; nothing was changed" (S-11)
  - [ ] A frozen fixture `tests/fixtures/exports/v1-*.json` (favourites, a no-amount ingredient, accents, fraction and decimal amounts) imports with every field checked, and one test imports every file in `tests/fixtures/exports/` so later versions keep loading it (S-06)
- Result:

## M3 · Ready at home (before deploy)

### T-05 · Delete a recipe with a 10-second Undo
- Owner: backend-coder → frontend-coder
- Depends on: T-02
- Files: src/cookbook/services/keeper.py, src/cookbook/web/api.py, src/cookbook/templates/view.html, src/cookbook/static/js/view.js, tests/unit/test_keeper_delete.py, tests/integration/test_api_delete.py, tests/e2e/test_delete_undo.py
- Context: SPEC US-03 · LLD §2.1, §3.1, §3.2, §3.4, §3.5, §6.3, §6.4, §7.1, §7.3 · files: src/cookbook/services/keeper.py, src/cookbook/web/api.py, src/cookbook/templates/view.html, src/cookbook/static/js/undo.js, src/cookbook/static/js/view.js, docs/wireframes/recipe-list.html, docs/wireframes/recipe-view.html
- Status: Backlog
- Acceptance criteria:
  - [ ] Tapping "Delete" on "Lemon Cake" returns to the list at once without it and without an "Are you sure?" question; the bar shows "'Lemon Cake' deleted · Undo"; tapping "Undo" within 10 seconds brings it back with every field unchanged
  - [ ] Opening another recipe during the window keeps the bar showing until the window ends; after the window (fake clock) Undo is refused with "Too late to undo; 'Lemon Cake' is gone" and the recipe never comes back in the list (S-04)
  - [ ] Deleting a second recipe while the bar shows makes the first delete final and shows the bar for the second
  - [ ] If a new "Lemon Cake" is saved during the window, Undo restores the old one as "Lemon Cake (2)" and the bar says "'Lemon Cake' is back as 'Lemon Cake (2)' because another recipe now has its name"
- Result:

### T-06 · Edit a recipe safely from two devices
- Owner: backend-coder → frontend-coder
- Depends on: T-02, T-05
- Files: src/cookbook/services/keeper.py, src/cookbook/web/api.py, src/cookbook/web/pages.py, src/cookbook/templates/edit.html, src/cookbook/templates/view.html, src/cookbook/static/js/edit.js, tests/unit/test_keeper_update.py, tests/integration/test_api_update.py, tests/e2e/test_edit_two_devices.py
- Context: SPEC US-01, US-03 · LLD §2.1, §3.1, §3.2, §3.4, §3.5, §6.3, §6.4, §7.4 · files: src/cookbook/services/keeper.py, src/cookbook/web/*.py, src/cookbook/templates/edit.html, src/cookbook/templates/view.html, src/cookbook/static/js/edit.js, docs/wireframes/recipe-edit.html
- Status: Backlog
- Acceptance criteria:
  - [ ] Editing "2 cups flour" to "2½ cups flour" and saving shows "2½ cups flour" in read view; saving with the recipe's own title works; renaming it to another recipe's title shows the same-title message under the title
  - [ ] Two browser contexts: the laptop opens "Lemon Cake" in edit, the phone changes 220°C to 180°C and saves; the laptop's Save shows "This recipe changed on another device"; "Reload theirs" opens the read view with 180°C (laptop typing dropped); repeating with "Keep mine" saves the laptop's version (S-03)
  - [ ] The phone deletes "Lemon Cake" while the laptop edits it; the laptop's Save keeps all typing and shows "This recipe was deleted on another device"; "Save as new" saves the typed version as "Lemon Cake" and opens it; "Discard my changes" goes to the list and "Lemon Cake" stays deleted; nothing is saved before a choice (S-03)
  - [ ] If the phone taps Undo before the laptop saves, the laptop's Save works as normal
  - [ ] Cancel or leaving with unsaved changes asks "Discard changes?"; no prompt after a successful save or after "Reload theirs"
- Result:

### T-07 · Search by name or by ingredient
- Owner: backend-coder → frontend-coder
- Depends on: T-02
- Files: src/cookbook/services/finder.py, src/cookbook/web/pages.py, src/cookbook/templates/list.html, src/cookbook/templates/_list_items.html, src/cookbook/static/js/list.js, tests/unit/test_finder.py, tests/integration/test_search.py, tests/e2e/test_search.py
- Context: SPEC US-04, US-05 · LLD §1.4, §4, §7.2 · files: src/cookbook/domain/search.py, src/cookbook/services/finder.py, src/cookbook/web/pages.py, src/cookbook/templates/list.html, src/cookbook/templates/_list_items.html, docs/wireframes/recipe-list.html
- Status: Backlog
- Acceptance criteria:
  - [ ] By name, typing "pie" lists "Grandma's Apple Pie" and "Shepherd's Pie" and not "Lemon Cake"; the list narrows while typing, without pressing Enter
  - [ ] By name, "shepherds" finds "Shepherd's Pie", "creme" finds "Crème Brûlée", "APP" finds "Grandma's Apple Pie" (S-08)
  - [ ] By ingredient, "buttermilk" lists exactly "Buttermilk Pancakes" and "Aunt May's Scones"; "egg" finds recipes with "3 eggs" and with "1 eggplant"; units and amounts are not searched (S-08)
  - [ ] "soup" with no match shows "No recipes match 'soup'" with "Clear search", which brings back the full list (S-10); recipes waiting out their undo window never appear in results (unit test)
  - [ ] Results keep favourites first, then A–Z; with 500 recipes a search answer arrives in under 1 second (integration timing)
- Result:

### T-08 · Favourites on top
- Owner: backend-coder → frontend-coder
- Depends on: T-05, T-06, T-07
- Files: src/cookbook/services/keeper.py, src/cookbook/web/api.py, src/cookbook/templates/_list_items.html, src/cookbook/templates/view.html, src/cookbook/static/js/list.js, src/cookbook/static/js/view.js, tests/unit/test_keeper_favourite.py, tests/integration/test_api_favourite.py, tests/e2e/test_favourites.py
- Context: SPEC US-07, US-03 · LLD §2.1, §3.1, §3.2, §3.5, §7.2, §7.3 · files: src/cookbook/services/keeper.py, src/cookbook/web/api.py, src/cookbook/templates/_list_items.html, src/cookbook/templates/view.html, src/cookbook/static/js/list.js, src/cookbook/static/js/view.js, docs/wireframes/recipe-list.html, docs/wireframes/recipe-view.html
- Notes: depends on T-07 (list refresh via `/recipes/_list`), T-06 (starring must not trigger the changed-elsewhere warning) and T-05 (Undo keeps the star).
- Status: Backlog
- Acceptance criteria:
  - [ ] Starring "Sunday Roast Chicken" in the list moves it to the top, above "Aunt May's Scones"; favourites first, then A–Z within each group; unstarring returns it to its A–Z place
  - [ ] Starring from the read view shows in the list, survives a reload and is seen from a second browser context
  - [ ] Starring "Lemon Cake" on the phone while the laptop edits it: the laptop's Save goes through with no warning and the star is kept; after a real conflict both "Reload theirs" and "Keep mine" keep the current star
  - [ ] Deleting a starred recipe and tapping "Undo" brings it back starred
- Result:

### T-09 · Scale a recipe to a different number of servings
- Owner: frontend-coder
- Depends on: T-02
- Files: src/cookbook/static/js/scaler.js, src/cookbook/static/js/view.js, src/cookbook/templates/view.html, tests/e2e/test_scaler.py, tests/e2e/test_scale_view.py
- Context: SPEC US-06 · LLD §7.3, §8 · files: src/cookbook/templates/view.html, src/cookbook/static/js/*.js, docs/wireframes/recipe-view.html
- Status: Backlog
- Acceptance criteria:
  - [ ] "Grandma's Apple Pie" 8 → 4 shows "1 cup flour", "½ cup butter", "3 apples", "⅓ cup sugar", "½ tsp cinnamon", "salt, to taste" and "Scaled from 8 servings · Reset"; Reset shows 8 servings and the amounts as saved
  - [ ] "Buttermilk Pancakes" 4 → 6 shows "4½ eggs", "½ cup sugar"; "Oat Cookies" 24 → 36 shows "1½ cups oats", "1½ eggs" (S-13)
  - [ ] "Aunt May's Scones" 3 → 1 shows "84 g flour", "50 ml buttermilk", "⅔ tbsp sugar"; 62.5 g rounds to "63 g"; amounts that would round to 0 show "1 g", "½" egg or "¼ tsp", never 0 (S-02)
  - [ ] Servings 0, -1 or "abc" are refused and the input resets; after scaling, reloading the page shows the saved servings and amounts unchanged
  - [ ] `window.cookbookScaler` tests cover every check row in LLD §8.5
- Result:

### T-10 · Whole cookbook on phone and laptop at home
- Owner: frontend-coder
- Depends on: T-04, T-06, T-08, T-09
- Files: src/cookbook/static/css/app.css, src/cookbook/templates/*.html (layout fixes only), tests/e2e/test_definition_of_done.py
- Context: SPEC US-01..US-09 (§12 Definition of done) · LLD §0.6, §6.5, §7 · files: src/cookbook/templates/*, src/cookbook/static/css/app.css, docs/wireframes/*.html
- Notes: the M3 checkpoint. The owner's real-network check (phone on the home Wi-Fi) happens at the M3 card; this task proves the same journey automatically and fixes layout gaps found across the finished screens.
- Status: Backlog
- Acceptance criteria:
  - [ ] Started with `timeout … uv run cookbook` on a temp data file, the app answers at the printed LAN address (not only 127.0.0.1) from a 390×844 phone context and a 1280×800 laptop context
  - [ ] One e2e journey runs SPEC §12: add "Grandma's Apple Pie" on the phone and see it on the laptop; "pie" by name and "buttermilk" by ingredient; 8 → 4 servings shows "½ cup", saved recipe unchanged; a starred recipe on top; delete then Undo; export, fresh app, import brings every recipe back
  - [ ] All three screens have no sideways scroll at 390 px, use the desktop layout at 1280 px, and every button is at least 44 px tall; screenshots of list, view and edit at both sizes in `.results/T-10/`
  - [ ] Full `scripts/check.sh` passes, including 80% coverage
- Result:
