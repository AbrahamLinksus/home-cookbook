"""title_key, parse_draft, list_order, free_title (LLD §1.1, §1.2)."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from cookbook.domain.errors import InvalidRecipe
from cookbook.domain.models import Ingredient, Recipe
from cookbook.domain.rules import free_title, list_order, parse_draft, title_key

NOW = datetime(2026, 11, 13, tzinfo=UTC)


def _recipe(recipe_id: int, title: str, *, favourite: bool = False) -> Recipe:
    return Recipe(recipe_id, title, 2, (), (), favourite, 1, NOW, NOW, None)


def _raw(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Pie",
        "servings": "8",
        "ingredients": [{"amount": "2", "unit": "cups", "name": "flour"}],
        "steps": ["Bake"],
    }
    return base | changes


def test_title_key_ignores_case_and_edge_spaces() -> None:
    assert title_key(" pancakes ") == title_key("Pancakes")


def test_free_title_taken_title_gets_first_free_number() -> None:
    taken = {title_key("Pancakes"), title_key("Pancakes (2)")}
    assert free_title("pancakes", taken) == "pancakes (3)"


def test_free_title_free_title_is_unchanged() -> None:
    assert free_title("Soup", {title_key("Pancakes")}) == "Soup"


def test_list_order_favourites_first_then_alphabetical() -> None:
    recipes = [_recipe(1, "banana"), _recipe(2, "Apple"), _recipe(3, "Zucchini", favourite=True)]
    assert [r.title for r in list_order(recipes)] == ["Zucchini", "Apple", "banana"]


def test_parse_draft_valid_input_keeps_order_and_drops_blank_rows() -> None:
    raw = _raw(
        ingredients=[
            {"amount": "", "unit": "", "name": ""},
            {"amount": "", "unit": "", "name": "salt, to taste"},
            {"amount": " 1 1/2 ", "unit": "cup", "name": "sugar"},
        ],
        steps=["One", "  ", "Two"],
    )
    draft = parse_draft(raw)
    assert draft.ingredients == (
        Ingredient(None, "", "salt, to taste"),
        Ingredient("1 1/2", "cup", "sugar"),
    )
    assert draft.steps == ("One", "Two")
    assert draft.servings == 8


@pytest.mark.parametrize(
    ("changes", "key", "code"),
    [
        ({"title": "  "}, "title", "required"),
        ({"title": "x" * 201}, "title", "too_long"),
        ({"servings": "0"}, "servings", "not_whole"),
        ({"servings": ""}, "servings", "required"),
        ({"servings": "2.5"}, "servings", "not_whole"),
        ({"servings": True}, "servings", "not_whole"),
        ({"servings": "9" * 5000}, "servings", "not_whole"),
        ({"servings": "1001"}, "servings", "not_whole"),
        (
            {"ingredients": [{"amount": "1,000", "unit": "ml", "name": "milk"}]},
            "ingredients.0.amount",
            "unclear_amount",
        ),
        (
            {"ingredients": [{"amount": "2-3", "unit": "", "name": "eggs"}]},
            "ingredients.0.amount",
            "bad_amount",
        ),
        (
            {"ingredients": [{"amount": "2", "unit": "", "name": ""}]},
            "ingredients.0.name",
            "required",
        ),
        ({"steps": ["ok", "y" * 10_001]}, "steps.1", "too_long"),
    ],
)
def test_parse_draft_bad_field_is_reported(changes: dict[str, object], key: str, code: str) -> None:
    with pytest.raises(InvalidRecipe) as caught:
        parse_draft(_raw(**changes))
    assert caught.value.fields[key] == code


def test_parse_draft_reports_every_problem_at_once() -> None:
    with pytest.raises(InvalidRecipe) as caught:
        parse_draft({"title": "", "servings": 0})
    assert set(caught.value.fields) == {"title", "servings"}


def test_parse_draft_accepts_integer_servings() -> None:
    parse: Callable[[dict[str, object]], object] = parse_draft
    assert parse(_raw(servings=3)) is not None


def test_parse_draft_servings_with_leading_zeros_is_accepted() -> None:
    assert parse_draft(_raw(servings="0004")).servings == 4
