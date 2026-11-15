"""RecipeKeeper.update: conflict token, deleted-elsewhere, titles (T-06, S-03)."""

from typing import Any

import pytest

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.errors import ChangedElsewhere, DeletedElsewhere, DuplicateTitle
from cookbook.domain.models import Ingredient, RecipeDraft
from cookbook.services.keeper import RecipeKeeper


def _draft(title: str = "Lemon Cake", amount: str = "2") -> RecipeDraft:
    return RecipeDraft(title, 6, (Ingredient(amount, "cups", "flour"),), ("Mix",))


@pytest.fixture
def keeper(settings: Settings, clock: Any) -> RecipeKeeper:
    repo = SqliteRecipeRepository(settings.db_path)
    repo.init_schema()
    return RecipeKeeper(repo, clock, undo_seconds=10)


def test_update_saves_and_bumps_version_and_keeps_own_title(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())

    saved = keeper.update(recipe.id, _draft(amount="2½"), recipe.version)

    assert saved.version == recipe.version + 1
    assert keeper.get(recipe.id).ingredients[0].amount == "2½"


def test_stale_version_is_changed_elsewhere_then_keep_mine_works(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())
    keeper.update(recipe.id, _draft(amount="3"), recipe.version)

    with pytest.raises(ChangedElsewhere) as info:
        keeper.update(recipe.id, _draft(amount="4"), recipe.version)

    keeper.update(recipe.id, _draft(amount="4"), info.value.current_version)
    assert keeper.get(recipe.id).ingredients[0].amount == "4"


def test_deleted_recipe_is_deleted_elsewhere_until_undone(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)

    with pytest.raises(DeletedElsewhere):
        keeper.update(recipe.id, _draft(amount="4"), recipe.version)

    keeper.restore(recipe.id)
    keeper.update(recipe.id, _draft(amount="4"), recipe.version)


def test_missing_recipe_is_deleted_elsewhere(keeper: RecipeKeeper) -> None:
    with pytest.raises(DeletedElsewhere):
        keeper.update(999, _draft(), 1)


def test_other_recipes_title_is_duplicate(keeper: RecipeKeeper) -> None:
    keeper.create(_draft("Pancakes"))
    recipe = keeper.create(_draft())

    with pytest.raises(DuplicateTitle):
        keeper.update(recipe.id, _draft(" pancakes "), recipe.version)


def test_update_after_undo_window_is_deleted_elsewhere(keeper: RecipeKeeper, clock: Any) -> None:
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)
    clock.advance(13)

    with pytest.raises(DeletedElsewhere):
        keeper.update(recipe.id, _draft(amount="4"), recipe.version)


def test_deleted_check_comes_before_version_and_title(keeper: RecipeKeeper) -> None:
    keeper.create(_draft("Pancakes"))
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)

    with pytest.raises(DeletedElsewhere):
        keeper.update(recipe.id, _draft("Pancakes"), recipe.version + 5)


def test_failed_update_changes_nothing(keeper: RecipeKeeper) -> None:
    keeper.create(_draft("Pancakes"))
    recipe = keeper.create(_draft())

    with pytest.raises(DuplicateTitle):
        keeper.update(recipe.id, _draft("Pancakes", "9"), recipe.version)

    assert keeper.get(recipe.id).ingredients[0].amount == "2"
    assert keeper.get(recipe.id).version == recipe.version
