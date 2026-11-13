"""normalise and matches (LLD §1.4, S-08)."""

from datetime import UTC, datetime

import pytest

from cookbook.domain.models import Ingredient, Recipe, SearchBy
from cookbook.domain.search import matches, normalise

NOW = datetime(2026, 11, 13, tzinfo=UTC)


def _recipe(title: str, *names: str) -> Recipe:
    ingredients = tuple(Ingredient(None, "", name) for name in names)
    return Recipe(1, title, 2, ingredients, (), False, 1, NOW, NOW, None)


def test_normalise_drops_accents_apostrophes_and_case() -> None:
    assert normalise("Shepherd's Crème") == "shepherds creme"


def test_normalise_collapses_spaces_and_curly_apostrophes() -> None:
    assert normalise("  Gran’s   Pie ") == "grans pie"  # noqa: RUF001


@pytest.mark.parametrize("query", ["pie", "APP", "shepherds", "app pie", ""])
def test_matches_name_forgiving(query: str) -> None:
    recipe = _recipe("Shepherd's Apple Pie")
    assert matches(recipe, query, SearchBy.NAME) is True


def test_matches_name_unrelated_word_is_false() -> None:
    assert matches(_recipe("Lemon Cake"), "pie", SearchBy.NAME) is False


def test_matches_ingredient_looks_at_ingredient_names_only() -> None:
    recipe = _recipe("Pancakes", "buttermilk", "eggs")
    assert matches(recipe, "buttermilk", SearchBy.INGREDIENT) is True
    assert matches(recipe, "pancakes", SearchBy.INGREDIENT) is False


def test_matches_ingredient_words_must_share_one_ingredient() -> None:
    recipe = _recipe("Cake", "butter", "milk")
    assert matches(recipe, "butter milk", SearchBy.INGREDIENT) is False
