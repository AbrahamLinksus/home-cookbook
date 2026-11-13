"""SQLite implementation of RecipeRepository (LLD §2.1, §2.5). The only module that runs SQL."""

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cookbook.adapters.schema import CONNECTION_PRAGMAS, MIGRATIONS
from cookbook.domain.errors import DuplicateTitle
from cookbook.domain.models import Ingredient, NewRecipe, Recipe, RecipeDraft
from cookbook.domain.rules import title_key

_COLUMNS = (
    "id, title, servings, ingredients_json, steps_json, favourite, version,"
    " created_at, updated_at, deleted_at"
)


def _to_text(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _from_text(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _ingredients_json(draft: RecipeDraft) -> str:
    rows = [{"amount": i.amount, "unit": i.unit, "name": i.name} for i in draft.ingredients]
    return json.dumps(rows, ensure_ascii=False)


def _to_recipe(row: sqlite3.Row) -> Recipe:
    return Recipe(
        id=row["id"],
        title=row["title"],
        servings=row["servings"],
        ingredients=tuple(
            Ingredient(i["amount"], i["unit"], i["name"])
            for i in json.loads(row["ingredients_json"])
        ),
        steps=tuple(json.loads(row["steps_json"])),
        favourite=bool(row["favourite"]),
        version=row["version"],
        created_at=_from_text(row["created_at"]),
        updated_at=_from_text(row["updated_at"]),
        deleted_at=_from_text(row["deleted_at"]) if row["deleted_at"] else None,
    )


def _fetch(conn: sqlite3.Connection, recipe_id: int, include_deleted: bool = True) -> Recipe | None:
    sql = f"SELECT {_COLUMNS} FROM recipe WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    row = conn.execute(sql, (recipe_id,)).fetchone()
    return _to_recipe(row) if row else None


def _duplicate(
    conn: sqlite3.Connection, title: str, error: sqlite3.IntegrityError
) -> DuplicateTitle:
    """DuplicateTitle for a live-title clash; any other integrity failure is re-raised (§2.5)."""
    if error.sqlite_errorcode != sqlite3.SQLITE_CONSTRAINT_UNIQUE:
        raise error
    row = conn.execute(
        "SELECT title FROM recipe WHERE title_key = ? AND deleted_at IS NULL", (title_key(title),)
    ).fetchone()
    if row is None:
        raise error
    return DuplicateTitle(row["title"])


def _insert(conn: sqlite3.Connection, new: NewRecipe) -> int:
    draft = new.draft
    try:
        cursor = conn.execute(
            "INSERT INTO recipe (title, title_key, servings, ingredients_json, steps_json,"
            " favourite, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                draft.title,
                title_key(draft.title),
                draft.servings,
                _ingredients_json(draft),
                json.dumps(list(draft.steps), ensure_ascii=False),
                int(new.favourite),
                _to_text(new.created_at),
                _to_text(new.updated_at),
            ),
        )
    except sqlite3.IntegrityError as error:
        raise _duplicate(conn, draft.title, error) from error
    if cursor.lastrowid is None:  # pragma: no cover - sqlite always sets it after INSERT
        raise RuntimeError("insert returned no row id")
    return cursor.lastrowid


class SqliteRecipeRepository:
    def __init__(self, db_path: Path) -> None:
        self._path = db_path

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, timeout=5)
        try:
            conn.row_factory = sqlite3.Row
            for pragma in CONNECTION_PRAGMAS:
                conn.execute(pragma)
            with conn:
                yield conn
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Create or migrate the data file; OSError when it cannot be opened or migrated."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._transaction() as conn:
                current = conn.execute("PRAGMA user_version").fetchone()[0]
                for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
                    # One transaction per migration, so a crash never leaves it half applied.
                    conn.executescript(f"BEGIN; {script}; PRAGMA user_version = {number}; COMMIT;")
        except sqlite3.OperationalError as error:
            raise OSError(f"cannot use the data file {self._path}: {error}") from error

    def list_live(self) -> list[Recipe]:
        with self._transaction() as conn:
            rows = conn.execute(f"SELECT {_COLUMNS} FROM recipe WHERE deleted_at IS NULL")
            return [_to_recipe(row) for row in rows.fetchall()]

    def get(self, recipe_id: int, *, include_deleted: bool = False) -> Recipe | None:
        with self._transaction() as conn:
            return _fetch(conn, recipe_id, include_deleted)

    def live_title_keys(self) -> set[str]:
        with self._transaction() as conn:
            rows = conn.execute("SELECT title_key FROM recipe WHERE deleted_at IS NULL")
            return {row["title_key"] for row in rows.fetchall()}

    def add(self, new: NewRecipe) -> Recipe:
        with self._transaction() as conn:
            recipe = _fetch(conn, _insert(conn, new))
        if recipe is None:  # pragma: no cover - row was just inserted
            raise RuntimeError("inserted recipe vanished")
        return recipe

    def add_many(self, items: Sequence[NewRecipe]) -> None:
        with self._transaction() as conn:
            for item in items:
                _insert(conn, item)

    def update_if_version(
        self, recipe_id: int, draft: RecipeDraft, base_version: int, now: datetime
    ) -> Recipe | None:
        params: tuple[Any, ...] = (
            draft.title,
            title_key(draft.title),
            draft.servings,
            _ingredients_json(draft),
            json.dumps(list(draft.steps), ensure_ascii=False),
            _to_text(now),
            recipe_id,
            base_version,
        )
        with self._transaction() as conn:
            try:
                cursor = conn.execute(
                    "UPDATE recipe SET title = ?, title_key = ?, servings = ?,"
                    " ingredients_json = ?, steps_json = ?, updated_at = ?, version = version + 1"
                    " WHERE id = ? AND version = ? AND deleted_at IS NULL",
                    params,
                )
            except sqlite3.IntegrityError as error:
                raise _duplicate(conn, draft.title, error) from error
            return _fetch(conn, recipe_id) if cursor.rowcount else None

    def set_favourite(self, recipe_id: int, favourite: bool) -> bool:
        with self._transaction() as conn:
            cursor = conn.execute(
                "UPDATE recipe SET favourite = ? WHERE id = ? AND deleted_at IS NULL",
                (int(favourite), recipe_id),
            )
            return cursor.rowcount > 0

    def mark_deleted(self, recipe_id: int, now: datetime) -> Recipe | None:
        with self._transaction() as conn:
            conn.execute(
                "DELETE FROM recipe WHERE deleted_at IS NOT NULL AND id != ?", (recipe_id,)
            )
            cursor = conn.execute(
                "UPDATE recipe SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (_to_text(now), recipe_id),
            )
            return _fetch(conn, recipe_id) if cursor.rowcount else None

    def unmark_deleted(self, recipe_id: int, title: str) -> Recipe | None:
        with self._transaction() as conn:
            try:
                cursor = conn.execute(
                    "UPDATE recipe SET deleted_at = NULL, title = ?, title_key = ?"
                    " WHERE id = ? AND deleted_at IS NOT NULL",
                    (title, title_key(title), recipe_id),
                )
            except sqlite3.IntegrityError as error:
                raise _duplicate(conn, title, error) from error
            return _fetch(conn, recipe_id) if cursor.rowcount else None

    def purge_deleted_before(self, cutoff: datetime) -> int:
        with self._transaction() as conn:
            pending = conn.execute(
                "SELECT id, deleted_at FROM recipe WHERE deleted_at IS NOT NULL"
            ).fetchall()
            expired = [(r["id"],) for r in pending if _from_text(r["deleted_at"]) < cutoff]
            conn.executemany("DELETE FROM recipe WHERE id = ?", expired)
            return len(expired)
