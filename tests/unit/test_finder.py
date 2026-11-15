"""RecipeFinder against a real SQLite file and a fake clock (T-07, S-08, S-10)."""

from typing import Any

import pytest

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.models import Ingredient, RecipeDraft, SearchBy
from cookbook.services.finder import RecipeFinder
from cookbook.services.keeper import RecipeKeeper


def _draft(title: str, *names: str) -> RecipeDraft:
    ingredients = tuple(Ingredient("1", "cup", n) for n in names) or (Ingredient("1", "cup", "x"),)
    return RecipeDraft(title, 4, ingredients, ("Mix",))


@pytest.fixture
def keeper(settings: Settings, clock: Any) -> RecipeKeeper:
    repo = SqliteRecipeRepository(settings.db_path)
    repo.init_schema()
    return RecipeKeeper(repo, clock, undo_seconds=10)


@pytest.fixture
def finder(settings: Settings) -> RecipeFinder:
    return RecipeFinder(SqliteRecipeRepository(settings.db_path))


def _titles(finder: RecipeFinder, query: str, by: SearchBy = SearchBy.NAME) -> list[str]:
    return [r.title for r in finder.search(query, by)]


@pytest.fixture
def seeded(keeper: RecipeKeeper) -> RecipeKeeper:
    keeper.create(_draft("Grandma's Apple Pie", "flour", "apples"))
    keeper.create(_draft("Shepherd's Pie", "potatoes"))
    keeper.create(_draft("Lemon Cake", "lemons", "3 eggs"))
    keeper.create(_draft("Crème Brûlée", "cream"))
    keeper.create(_draft("Buttermilk Pancakes", "buttermilk", "eggs"))
    keeper.create(_draft("Aunt May's Scones", "buttermilk"))
    keeper.create(_draft("Ratatouille", "1 eggplant"))
    return keeper


def test_pie_lists_both_pies_not_lemon_cake(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert _titles(finder, "pie") == ["Grandma's Apple Pie", "Shepherd's Pie"]


@pytest.mark.parametrize(
    ("query", "title"),
    [
        ("shepherds", "Shepherd's Pie"),
        ("creme", "Crème Brûlée"),
        ("APP", "Grandma's Apple Pie"),
    ],
)
def test_forgiving_name_matching_s08(
    seeded: RecipeKeeper, finder: RecipeFinder, query: str, title: str
) -> None:
    assert _titles(finder, query) == [title]


def test_buttermilk_by_ingredient_lists_exactly_two(
    seeded: RecipeKeeper, finder: RecipeFinder
) -> None:
    assert _titles(finder, "buttermilk", SearchBy.INGREDIENT) == [
        "Aunt May's Scones",
        "Buttermilk Pancakes",
    ]


def test_egg_matches_eggs_and_eggplant_s08(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert _titles(finder, "egg", SearchBy.INGREDIENT) == [
        "Buttermilk Pancakes",
        "Lemon Cake",
        "Ratatouille",
    ]


def test_units_and_amounts_are_not_searched(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert _titles(finder, "cup", SearchBy.INGREDIENT) == []
    assert _titles(finder, "4", SearchBy.INGREDIENT) == []


def test_ingredient_search_does_not_match_title(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert _titles(finder, "pie", SearchBy.INGREDIENT) == []


def test_name_search_does_not_match_ingredients(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert _titles(finder, "buttermilk") == ["Buttermilk Pancakes"]


def test_no_match_returns_empty_s10(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert _titles(finder, "soup") == []


def test_blank_query_returns_everything(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    assert len(_titles(finder, "")) == 7
    assert len(_titles(finder, "   ")) == 7


def test_recipes_in_undo_window_never_appear(seeded: RecipeKeeper, finder: RecipeFinder) -> None:
    lemon = next(r for r in seeded.list_recipes() if r.title == "Lemon Cake")
    seeded.delete(lemon.id)

    assert "Lemon Cake" not in _titles(finder, "")
    assert _titles(finder, "lemon") == []
    assert _titles(finder, "lemons", SearchBy.INGREDIENT) == []


def test_results_favourites_first_then_az(
    keeper: RecipeKeeper, finder: RecipeFinder, settings: Settings
) -> None:
    for title in ("Zucchini Pie", "Apple Pie", "Meat Pie", "Berry Pie"):
        keeper.create(_draft(title))
    repo = SqliteRecipeRepository(settings.db_path)
    ids = {r.title: r.id for r in keeper.list_recipes()}
    repo.set_favourite(ids["Zucchini Pie"], True)

    assert _titles(finder, "pie") == ["Zucchini Pie", "Apple Pie", "Berry Pie", "Meat Pie"]
