"""RecipeKeeper.delete / restore against a real SQLite file and a fake clock (T-05, S-04)."""

from datetime import UTC, datetime
from typing import Any

import pytest

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.errors import RecipeNotFound, UndoExpired
from cookbook.domain.models import Ingredient, Recipe, RecipeDraft
from cookbook.services.keeper import RecipeKeeper


def _draft(title: str = "Lemon Cake") -> RecipeDraft:
    return RecipeDraft(title, 6, (Ingredient("2", "cups", "flour"),), ("Mix", "Bake"))


@pytest.fixture
def keeper(settings: Settings, clock: Any) -> RecipeKeeper:
    repo = SqliteRecipeRepository(settings.db_path)
    repo.init_schema()
    return RecipeKeeper(repo, clock, undo_seconds=10)


def _titles(keeper: RecipeKeeper) -> list[str]:
    return [r.title for r in keeper.list_recipes()]


def test_delete_hides_recipe_from_list_and_get(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())

    deleted = keeper.delete(recipe.id)

    assert deleted.title == "Lemon Cake"
    assert _titles(keeper) == []
    with pytest.raises(RecipeNotFound):
        keeper.get(recipe.id)


def test_delete_unknown_raises_not_found(keeper: RecipeKeeper) -> None:
    with pytest.raises(RecipeNotFound):
        keeper.delete(42)


def test_restore_within_window_brings_back_every_field(keeper: RecipeKeeper, clock: Any) -> None:
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)
    clock.advance(9)

    restored, renamed = keeper.restore(recipe.id)

    assert renamed is None
    assert restored.draft() == _draft()
    assert restored.id == recipe.id
    assert restored.created_at == recipe.created_at
    assert _titles(keeper) == ["Lemon Cake"]


def test_restore_at_edge_of_grace_works_and_just_after_is_refused(
    keeper: RecipeKeeper, clock: Any
) -> None:
    a = keeper.create(_draft("Lemon Cake"))
    keeper.delete(a.id)
    clock.advance(12)
    assert keeper.restore(a.id)[0].title == "Lemon Cake"
    keeper.delete(a.id)
    clock.advance(12.001)

    with pytest.raises(UndoExpired) as caught:
        keeper.restore(a.id)

    assert caught.value.title == "Lemon Cake"


def test_expired_recipe_never_returns_to_list(keeper: RecipeKeeper, clock: Any) -> None:
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)
    clock.advance(30)

    with pytest.raises(UndoExpired):
        keeper.restore(recipe.id)

    assert _titles(keeper) == []
    with pytest.raises(UndoExpired):  # purged: still refused (the browser supplies the title)
        keeper.restore(recipe.id)


def test_restore_unknown_id_is_expired(keeper: RecipeKeeper) -> None:
    with pytest.raises(UndoExpired):
        keeper.restore(99)


def test_restore_of_live_recipe_is_a_no_op(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())
    restored, renamed = keeper.restore(recipe.id)
    assert (restored.id, renamed) == (recipe.id, None)


def test_second_delete_makes_first_final(keeper: RecipeKeeper, clock: Any) -> None:
    first = keeper.create(_draft("Lemon Cake"))
    second = keeper.create(_draft("Soup"))
    keeper.delete(first.id)
    clock.advance(1)
    keeper.delete(second.id)

    with pytest.raises(UndoExpired):
        keeper.restore(first.id)
    assert keeper.restore(second.id)[0].title == "Soup"
    assert _titles(keeper) == ["Soup"]


def test_restore_renames_when_title_reused_during_window(keeper: RecipeKeeper) -> None:
    old = keeper.create(_draft("Lemon Cake"))
    keeper.delete(old.id)
    new = keeper.create(_draft("Lemon Cake"))

    restored, renamed = keeper.restore(old.id)

    assert renamed == "Lemon Cake (2)"
    assert restored.title == "Lemon Cake (2)"
    assert sorted(_titles(keeper)) == ["Lemon Cake", "Lemon Cake (2)"]
    assert keeper.get(new.id).title == "Lemon Cake"


def test_restore_rename_skips_taken_suffix(keeper: RecipeKeeper) -> None:
    old = keeper.create(_draft("Lemon Cake"))
    keeper.delete(old.id)
    keeper.create(_draft("Lemon Cake"))
    keeper.create(_draft("Lemon Cake (2)"))

    _, renamed = keeper.restore(old.id)

    assert renamed == "Lemon Cake (3)"


class _OtherDeviceUndoesFirst(SqliteRecipeRepository):
    """Another device's Undo lands between this restore's read and its write."""

    def unmark_deleted(self, recipe_id: int, title: str) -> Recipe | None:
        super().unmark_deleted(recipe_id, title)
        return super().unmark_deleted(recipe_id, title)


def test_restore_when_other_device_undid_first_returns_live_recipe(
    settings: Settings, clock: Any
) -> None:
    repo = _OtherDeviceUndoesFirst(settings.db_path)
    repo.init_schema()
    keeper = RecipeKeeper(repo, clock, undo_seconds=10)
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)

    restored, renamed = keeper.restore(recipe.id)

    assert (restored.id, restored.title, renamed) == (recipe.id, "Lemon Cake", None)
    assert _titles(keeper) == ["Lemon Cake"]


class _PurgedBeforeWrite(SqliteRecipeRepository):
    """The row is purged between this restore's read and its write."""

    def unmark_deleted(self, recipe_id: int, title: str) -> Recipe | None:
        self.purge_deleted_before(datetime.max.replace(tzinfo=UTC))
        return super().unmark_deleted(recipe_id, title)


def test_restore_when_row_purged_before_write_is_expired(settings: Settings, clock: Any) -> None:
    repo = _PurgedBeforeWrite(settings.db_path)
    repo.init_schema()
    keeper = RecipeKeeper(repo, clock, undo_seconds=10)
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)

    with pytest.raises(UndoExpired) as caught:
        keeper.restore(recipe.id)

    assert caught.value.title == "Lemon Cake"
