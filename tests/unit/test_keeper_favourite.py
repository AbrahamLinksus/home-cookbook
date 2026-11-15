"""RecipeKeeper.set_favourite: idempotent, keeps version, survives edit and undo (T-08)."""

from typing import Any

import pytest

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.errors import DeletedElsewhere
from cookbook.domain.models import Ingredient, RecipeDraft
from cookbook.services.keeper import RecipeKeeper


def _draft(title: str = "Lemon Cake") -> RecipeDraft:
    return RecipeDraft(title, 6, (Ingredient("2", "cups", "flour"),), ("Mix",))


@pytest.fixture
def keeper(settings: Settings, clock: Any) -> RecipeKeeper:
    repo = SqliteRecipeRepository(settings.db_path)
    repo.init_schema()
    return RecipeKeeper(repo, clock, undo_seconds=10)


def test_set_is_idempotent_and_keeps_version(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())

    keeper.set_favourite(recipe.id, True)
    keeper.set_favourite(recipe.id, True)

    saved = keeper.get(recipe.id)
    assert saved.favourite is True
    assert saved.version == recipe.version
    keeper.set_favourite(recipe.id, False)
    assert keeper.get(recipe.id).favourite is False


def test_update_keeps_star_set_meanwhile(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())
    keeper.set_favourite(recipe.id, True)

    saved = keeper.update(recipe.id, _draft(), recipe.version)

    assert saved.favourite is True


def test_undo_keeps_star(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())
    keeper.set_favourite(recipe.id, True)
    keeper.delete(recipe.id)

    restored, _ = keeper.restore(recipe.id)

    assert restored.favourite is True


def test_deleted_or_missing_recipe_is_gone(keeper: RecipeKeeper) -> None:
    recipe = keeper.create(_draft())
    keeper.delete(recipe.id)

    with pytest.raises(DeletedElsewhere):
        keeper.set_favourite(recipe.id, True)
    with pytest.raises(DeletedElsewhere):
        keeper.set_favourite(999, True)
