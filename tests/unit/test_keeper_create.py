"""RecipeKeeper.create / get against a real SQLite file and a fixed clock (T-02)."""

import pytest

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.errors import DuplicateTitle, RecipeNotFound
from cookbook.domain.models import Ingredient, RecipeDraft
from cookbook.domain.ports import Clock
from cookbook.services.keeper import RecipeKeeper


def _draft(title: str = "Pancakes") -> RecipeDraft:
    return RecipeDraft(title, 8, (Ingredient("2", "cups", "flour"),), ("Mix", "Bake"))


@pytest.fixture
def keeper(settings: Settings, clock: Clock) -> RecipeKeeper:
    repo = SqliteRecipeRepository(settings.db_path)
    repo.init_schema()
    return RecipeKeeper(repo, clock, undo_seconds=10)


def test_create_returns_recipe_stamped_with_clock_and_version_one(
    keeper: RecipeKeeper, clock: Clock
) -> None:
    recipe = keeper.create(_draft())

    assert recipe.version == 1
    assert recipe.created_at == recipe.updated_at == clock.now()
    assert not recipe.favourite
    assert keeper.get(recipe.id).draft() == _draft()


def test_create_same_title_in_other_spelling_raises_duplicate_with_existing_title(
    keeper: RecipeKeeper,
) -> None:
    keeper.create(_draft("Pancakes"))

    with pytest.raises(DuplicateTitle) as caught:
        keeper.create(_draft("pancakes"))

    assert caught.value.existing_title == "Pancakes"
    assert len(keeper.list_recipes()) == 1


def test_get_unknown_id_raises_not_found(keeper: RecipeKeeper) -> None:
    with pytest.raises(RecipeNotFound):
        keeper.get(999)
