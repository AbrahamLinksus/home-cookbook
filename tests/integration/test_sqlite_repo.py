"""SqliteRecipeRepository on a temp file (LLD §2)."""

import sqlite3  # noqa: TID251 (reads PRAGMA user_version directly)
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.domain.errors import DuplicateTitle
from cookbook.domain.models import Ingredient, NewRecipe, RecipeDraft
from cookbook.domain.rules import title_key

START = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)

NewRecipeFactory = Callable[..., NewRecipe]


@pytest.fixture
def repo(tmp_path: Path) -> SqliteRecipeRepository:
    repository = SqliteRecipeRepository(tmp_path / "nested" / "cookbook.db")
    repository.init_schema()
    return repository


def test_init_schema_sets_user_version_and_is_repeatable(tmp_path: Path) -> None:
    path = tmp_path / "cookbook.db"
    repository = SqliteRecipeRepository(path)
    repository.init_schema()
    repository.init_schema()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_add_get_keeps_every_field_and_order(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    new = new_recipe("Crème Brûlée", favourite=True)

    added = repo.add(new)
    loaded = repo.get(added.id)

    assert loaded == added
    assert loaded is not None
    assert loaded.draft() == new.draft
    assert [i.name for i in loaded.ingredients] == ["flour", "salt, to taste", "cinnamon"]
    assert loaded.ingredients[1].amount is None
    assert loaded.steps == ("Mix", "Preheat oven to 200°C", "Bake")
    assert (loaded.favourite, loaded.version, loaded.deleted_at) == (True, 1, None)
    assert (loaded.created_at, loaded.updated_at) == (START, START)


def test_add_same_title_key_raises_duplicate_title(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    repo.add(new_recipe("Pancakes"))
    with pytest.raises(DuplicateTitle) as caught:
        repo.add(new_recipe(" pancakes "))
    assert caught.value.existing_title == "Pancakes"


def test_add_many_with_one_clash_writes_nothing(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    repo.add(new_recipe("Pancakes"))
    batch = [new_recipe("Soup"), new_recipe("PANCAKES"), new_recipe("Stew")]

    with pytest.raises(DuplicateTitle):
        repo.add_many(batch)

    assert repo.live_title_keys() == {title_key("Pancakes")}


def test_add_many_without_clash_writes_all(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    repo.add_many([new_recipe("Soup"), new_recipe("Stew")])
    assert [r.title for r in repo.list_live()] == ["Soup", "Stew"]


def test_update_if_version_bumps_version_and_refuses_stale_base(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    added = repo.add(new_recipe("Soup"))
    draft = RecipeDraft("Soup 2", 2, (Ingredient("1", "", "leek"),), ("Boil",))
    later = START + timedelta(minutes=5)

    updated = repo.update_if_version(added.id, draft, 1, later)
    stale = repo.update_if_version(added.id, draft, 1, later)

    assert updated is not None
    assert (updated.version, updated.title, updated.updated_at) == (2, "Soup 2", later)
    assert updated.created_at == START
    assert stale is None


def test_set_favourite_keeps_version(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    added = repo.add(new_recipe("Soup"))
    assert repo.set_favourite(added.id, True) is True
    loaded = repo.get(added.id)
    assert loaded is not None
    assert (loaded.favourite, loaded.version) == (True, 1)
    assert repo.set_favourite(999, True) is False


def test_mark_deleted_hides_frees_title_and_purges_earlier_pending(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    first = repo.add(new_recipe("Soup"))
    second = repo.add(new_recipe("Stew"))

    repo.mark_deleted(first.id, START)
    repo.mark_deleted(second.id, START)

    assert repo.list_live() == []
    assert repo.get(first.id, include_deleted=True) is None
    pending = repo.get(second.id, include_deleted=True)
    assert pending is not None
    assert pending.deleted_at == START
    repo.add(new_recipe("Stew"))


def test_unmark_deleted_restores_with_given_title(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    gone = repo.add(new_recipe("Soup"))
    repo.mark_deleted(gone.id, START)
    restored = repo.unmark_deleted(gone.id, "Soup (2)")
    assert restored is not None
    assert (restored.title, restored.deleted_at) == ("Soup (2)", None)


def test_purge_deleted_before_removes_only_old_pending(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    gone = repo.add(new_recipe("Soup"))
    repo.mark_deleted(gone.id, START)

    assert repo.purge_deleted_before(START - timedelta(seconds=1)) == 0
    assert repo.purge_deleted_before(START + timedelta(seconds=1)) == 1
    assert repo.get(gone.id, include_deleted=True) is None


def test_add_other_integrity_failure_is_not_a_duplicate_title(
    repo: SqliteRecipeRepository, new_recipe: NewRecipeFactory
) -> None:
    good = new_recipe("Soup")
    bad = NewRecipe(replace(good.draft, servings=0), False, START, START)

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        repo.add(bad)


def test_init_schema_failed_migration_leaves_nothing_behind(tmp_path: Path) -> None:
    path = tmp_path / "cookbook.db"
    with sqlite3.connect(path) as conn:  # clashes with migration 1's second statement
        conn.execute("CREATE TABLE other (x)")
        conn.execute("CREATE INDEX recipe_title_live ON other (x)")

    with pytest.raises(OSError, match="cannot use the data file"):
        SqliteRecipeRepository(path).init_schema()

    with sqlite3.connect(path) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE name = 'recipe'").fetchall()
        assert (tables, conn.execute("PRAGMA user_version").fetchone()[0]) == ([], 0)


def test_init_schema_unwritable_folder_raises_os_error(tmp_path: Path) -> None:
    folder = tmp_path / "locked"
    folder.mkdir(mode=0o555)
    try:
        with pytest.raises(OSError, match="cannot use the data file"):
            SqliteRecipeRepository(folder / "cookbook.db").init_schema()
    finally:
        folder.chmod(0o755)
