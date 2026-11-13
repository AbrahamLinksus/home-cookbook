"""SQLite schema and forward-only migrations keyed by PRAGMA user_version (LLD §2.3).

Released migrations are never edited; a schema change appends a new entry.
"""

from typing import Final

CONNECTION_PRAGMAS: Final = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=FULL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
)

MIGRATIONS: Final[tuple[str, ...]] = (
    """
    CREATE TABLE recipe (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        title_key TEXT NOT NULL,
        servings INTEGER NOT NULL CHECK (servings >= 1),
        ingredients_json TEXT NOT NULL,
        steps_json TEXT NOT NULL,
        favourite INTEGER NOT NULL DEFAULT 0 CHECK (favourite IN (0, 1)),
        version INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        deleted_at TEXT
    );
    CREATE UNIQUE INDEX recipe_title_live ON recipe (title_key) WHERE deleted_at IS NULL;
    """,
)
