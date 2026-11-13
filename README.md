# Home Cookbook

Home Cookbook is a private recipe box for your family's recipes. It runs on your own computer at home, and you open it in a browser on your phone or laptop while you are on the home Wi-Fi. There are no accounts, no cloud and no sharing: the recipes never leave the house.

**Status:** Milestone 1 is done. You can add a recipe and read it on the phone. Export, delete, edit, search, favourites and scaling are still to come (see "Not yet").

## Start it

One time, in the project folder (you need [uv](https://docs.astral.sh/uv/) installed; uv fetches Python 3.12 for you):

```bash
uv sync
```

Every time you want the cookbook running:

```bash
uv run cookbook
```

It prints a line like this (the addresses shown are placeholders; yours are printed by the app):

```
Home Cookbook is running. On your phone or laptop open: http://<lan-ip>:8765 (or http://<computer-name>.local:8765)
```

- **On the computer:** open `http://localhost:8765`.
- **On the phone:** the phone must be on the home Wi-Fi. Open the address from the printed line, `http://<lan-ip>:8765`. The `.local` name also works on networks that support it; if it does not open, use the IP.
- Names your router gives a device (for example `desktop.lan`) are refused on purpose. The app only answers to IP addresses, `localhost` and `.local` names.
- **To stop:** press Ctrl+C in the terminal.
- If it prints `Home Cookbook cannot start: ...` and exits, the reason follows (for example the port is already in use, or a setting is wrong).

## What works now

- **Add a recipe:** title, servings, ingredients (amount, unit and name; an ingredient can have no amount, like "salt, to taste") and numbered steps. Tap Save and the recipe opens for reading.
- **Read it on the phone:** the recipe page fits a phone screen without sideways scrolling.
- **Checks when you save:**
  - A title that is already used is refused, with "You already have a recipe called 'Pancakes'. Please choose another name". Nothing is saved until you change it. Titles that differ only in capitals, or in spaces at the start or end, count as the same.
  - Amounts can be whole numbers, decimals, fractions (`1/2`, `1 1/2`) or fraction characters (`½`). They are shown kitchen-style, so `1 1/2` appears as `1½`.
  - A range such as `2-3` is refused: "Enter one amount, e.g. 2 or 2½".
  - A blank title, or servings of 0, keeps the form open with a message by that field.

## Not yet

- Export all recipes to one file, and load that file back in (Milestone 2)
- Delete a recipe, with a 10-second Undo (Milestone 3)
- Edit a recipe safely when the phone and laptop both change it (Milestone 3)
- Search by name or by ingredient (Milestone 3)
- Favourites shown at the top of the list (Milestone 3)
- Scale a recipe to a different number of servings (Milestone 3)

## Settings

Settings are environment variables. The app reads them from the shell; it does not read the `.env` file. Put them in front of the command:

```bash
COOKBOOK_PORT=8800 uv run cookbook
```

| Variable | Default | What it does |
|---|---|---|
| `COOKBOOK_PORT` | `8765` | The port the phone and laptop use. A whole number from 1 to 65535. The address the app prints changes with it. |
| `COOKBOOK_DB` | `~/.local/share/home-cookbook/cookbook.db` | Where the recipes are stored. Leave it unset for the default. |

## Where the data lives

All recipes are in one file, `cookbook.db`, in `~/.local/share/home-cookbook/` (or in `$XDG_DATA_HOME/home-cookbook/` if that variable is set). The app creates the folder and file the first time it starts. The file is kept outside the project folder, so reinstalling or updating the code does not touch your recipes.

Until export arrives (Milestone 2), this file is the only copy. To back it up by hand, stop the app and copy `cookbook.db`. If `cookbook.db-wal` or `cookbook.db-shm` sits next to it, copy those too.

## Checks

<details>
<summary>How to run the checks (for the owner or a developer)</summary>

- Full check (lint, format, types, complexity, layer rules, tests with 80% coverage, secrets scan): `scripts/check.sh`. It ends with `CHECK OK` or `CHECK FAILED`.
- Tests only: `uv run pytest`
- One time, for the browser tests: `uv run playwright install --only-shell chromium`
- One time after cloning: `scripts/install-hooks.sh`
- Quick browser smoke script: `uv run python -I scripts/smoke_playwright.py`

</details>

## For developers

<details>
<summary>Architecture and project layout</summary>

- **Stack:** Python 3.12, Flask with Jinja pages, the waitress server, SQLite (standard library), plain JavaScript. No build step and no Node.
- **Layers:** `domain` holds the recipe rules (no input or output). `services` holds the keeper (add and read), finder (search, Milestone 3) and backup (Milestone 2). `adapters` holds the SQLite storage. `web` holds the pages, the JSON endpoints and the request guard, and `app` starts everything. The import-linter check enforces these rules.
- **Start-up order:** settings from the environment, then the stop-signal handler, then the data file (created or migrated), then the port is bound, then the address banner is printed, then the server runs.
- **Request guard:** only private or loopback addresses are served. The Host name must be an IP, `localhost` or a `.local` name. Cross-site writes are refused.
- **Layout:**
  - `src/cookbook/app/`: start-up, settings, app factory
  - `src/cookbook/domain/`: recipe rules, amounts, search rules
  - `src/cookbook/adapters/`: SQLite storage
  - `src/cookbook/services/`: keeper, finder, backup
  - `src/cookbook/web/`: pages, API, guard, error pages
  - `src/cookbook/templates/` and `src/cookbook/static/`: HTML, CSS and JavaScript
  - `tests/`: unit, integration and end-to-end tests
  - `docs/`: `SPEC.md` (what it does, user stories) and `LLD.md` (how it is built, section 0 covers start-up and settings)
  - `.env.example`: the settings with their defaults
- **Dependencies:** `uv.lock` pins the exact versions. Install with `uv sync`.

</details>
