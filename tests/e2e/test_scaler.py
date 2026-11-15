"""window.cookbookScaler checks (LLD 8.5) run in the browser."""

from collections.abc import Iterator
from typing import Any

import pytest
from playwright.sync_api import Browser, Page

RECIPE = {"title": "Probe", "servings": 4, "ingredients": [], "steps": ["Mix"]}


@pytest.fixture
def page(browser: Browser, live_url: str) -> Iterator[Page]:
    ctx = browser.new_context()
    rid = ctx.request.post(f"{live_url}/api/recipes", data={"recipe": RECIPE}).json()["id"]
    pg = ctx.new_page()
    pg.goto(f"{live_url}/recipes/{rid}")
    pg.wait_for_function("window.cookbookScaler !== undefined")
    yield pg
    ctx.close()


def call(page: Page, fn: str, *args: Any) -> Any:
    return page.evaluate(f"(a) => window.cookbookScaler.{fn}(...a)", list(args))


def shown(page: Page, *scale_args: int | str) -> str:
    result = call(page, "scale", *scale_args)
    return str(call(page, "formatAmount", result))


def test_exposes_the_five_functions(page: Page) -> None:
    keys = page.evaluate("Object.keys(window.cookbookScaler).sort()")
    assert keys == ["formatAmount", "kindFor", "nameFor", "scale", "unitFor"]


@pytest.mark.parametrize(
    ("unit", "kind"),
    [
        ("g", "metric"),
        ("Gram", "metric"),
        (" GRAMS ", "metric"),
        ("ml", "metric"),
        ("millilitre", "metric"),
        ("Milliliters", "metric"),
        ("", "counted"),
        ("   ", "counted"),
        (None, "counted"),
        ("kg", "fraction"),
        ("l", "fraction"),
        ("cup", "fraction"),
        ("tsp", "fraction"),
    ],
)
def test_kind_for(page: Page, unit: str | None, kind: str) -> None:
    assert call(page, "kindFor", unit) == kind


@pytest.mark.parametrize(
    "case",
    [
        (3, 4, 8, 4, "fraction", "⅓"),  # 3/8 -> 1/3
        (3, 1, 4, 6, "counted", "4½"),
        (1, 3, 4, 6, "fraction", "½"),
        (2, 1, 8, 4, "fraction", "1"),
        (253, 1, 3, 1, "metric", "84"),
        (150, 1, 3, 1, "metric", "50"),
        (2, 1, 3, 1, "fraction", "⅔"),
        (125, 1, 8, 4, "metric", "63"),  # 62.5 tie goes up
        (1, 1, 2, 1, "counted", "½"),
        (1, 8, 3, 1, "fraction", "¼"),  # rounds to 0 -> smallest step
        (1, 1, 3, 1, "metric", "1"),  # 0 -> 1 g
        (1, 1, 3, 1, "counted", "½"),
        (1, 1, 100, 1, "counted", "½"),
        (1, 1, 100, 1, "fraction", "¼"),
        (1, 1, 100, 1, "metric", "1"),
        (7, 8, 1, 1, "fraction", "1"),  # carry 7/8 -> 1
        (9, 8, 1, 1, "fraction", "1¼"),  # 1/8 ties 0 / ¼ -> larger
        (1, 1, 24, 36, "fraction", "1½"),
        (1, 1, 24, 36, "counted", "1½"),
        (3, 1, 1, 1, "fraction", "3"),
        (1, 4, 1, 3, "counted", "1"),  # 3/4 -> 1 (nearer 1 than ½)
        (1, 2, 1, 1, "counted", "½"),
        (1, 1, 4, 1, "counted", "½"),  # 1/4 is a tie 0 / 1/2 -> larger
        (1, 1, 2, 3, "metric", "2"),  # 1.5 g tie -> 2
    ],
)
def test_scale_and_format(page: Page, case: tuple[int, int, int, int, str, str]) -> None:
    *scale_args, text = case
    assert shown(page, *scale_args) == text


def test_scale_never_shows_zero(page: Page) -> None:
    for kind in ("metric", "counted", "fraction"):
        text = shown(page, 1, 1000, 1, 1, kind)
        assert text not in ("", "0")


def test_scale_result_shape(page: Page) -> None:
    assert call(page, "scale", 3, 2, 1, 1, "fraction") == {"whole": 1, "frac": "½"}
    assert call(page, "scale", 1, 1, 100, 1, "metric") == {"whole": 1, "frac": ""}


def test_format_amount(page: Page) -> None:
    assert call(page, "formatAmount", {"whole": 1, "frac": "½"}) == "1½"
    assert call(page, "formatAmount", {"whole": 0, "frac": "½"}) == "½"
    assert call(page, "formatAmount", {"whole": 3, "frac": ""}) == "3"
    assert call(page, "formatAmount", {"whole": 84, "frac": ""}) == "84"


@pytest.mark.parametrize(
    "case",
    [
        ("cup", 2, "", "cups"),
        ("cups", 1, "", "cup"),
        ("cup", 1, "½", "cups"),
        ("cups", 0, "½", "cup"),
        ("cups", 0, "¼", "cup"),
        ("tbsp", 2, "", "tbsp"),  # unknown units unchanged
        ("Tbsp", 1, "", "Tbsp"),
        ("kg", 3, "", "kg"),
        ("gram", 5, "", "grams"),
        ("grams", 1, "", "gram"),
        ("pinch", 2, "", "pinches"),
        ("clove", 3, "", "cloves"),
        ("g", 84, "", "g"),
    ],
)
def test_unit_for(page: Page, case: tuple[str, int, str, str]) -> None:
    unit, whole, frac, expected = case
    assert call(page, "unitFor", unit, {"whole": whole, "frac": frac}) == expected


@pytest.mark.parametrize(
    "case",
    [
        ("egg", "", 2, "", "eggs"),
        ("egg", "", 1, "½", "eggs"),
        ("egg", "", 1, "", "egg"),  # exactly 1 stays singular
        ("egg", "", 0, "½", "egg"),  # at most a half stays singular
        ("egg", "", 0, "¼", "egg"),
        ("berry", "", 3, "", "berries"),
        ("cherry", "", 2, "", "cherries"),
        ("day", "", 2, "", "days"),  # vowel + y just takes s
        ("peach", "", 2, "", "peaches"),
        ("box", "", 2, "", "boxes"),
        ("dish", "", 2, "", "dishes"),
        ("buzz", "", 2, "", "buzzes"),
        ("tomato", "", 3, "", "tomatoes"),
        ("potato", "", 3, "", "potatoes"),
        ("loaf", "", 2, "", "loaves"),
        ("leaf", "", 2, "", "leaves"),
        ("mango", "", 2, "", "mangoes"),
        ("apples", "", 3, "", "apples"),  # already ends in s
        ("molasses", "", 3, "", "molasses"),
        ("red apple", "", 3, "", "red apples"),  # last word only
        ("large egg", "", 2, "", "large eggs"),
        ("salt, to taste", "", 3, "", "salt, to taste"),
        ("eggs (large)", "", 3, "", "eggs (large)"),
        ("egg (large)", "", 3, "", "egg (large)"),
        ("cup of flour", "", 3, "", "cup of flour"),
        ("salt to taste", "", 3, "", "salt to taste"),
        ("milk for glaze", "", 3, "", "milk for glaze"),
        ("salt or pepper", "", 3, "", "salt or pepper"),
        ("salt and pepper", "", 3, "", "salt and pepper"),
        ("flour", "cups", 3, "", "flour"),  # has a unit: not a counted item
        ("egg", "kg", 3, "", "egg"),
        ("egg", "g", 3, "", "egg"),
        ("", "", 3, "", ""),
    ],
)
def test_name_for(page: Page, case: tuple[str, str, int, str, str]) -> None:
    name, unit, whole, frac, expected = case
    assert call(page, "nameFor", name, unit, {"whole": whole, "frac": frac}) == expected


@pytest.mark.parametrize(
    "case",
    [
        ("eggs", "", 1, "", "egg"),
        ("eggs", "", 0, "½", "egg"),
        ("apples", "", 1, "", "apple"),
        ("red apples", "", 1, "", "red apple"),
        ("tomatoes", "", 1, "", "tomato"),
        ("potatoes", "", 0, "½", "potato"),
        ("berries", "", 1, "", "berry"),
        ("loaves", "", 1, "", "loaf"),
        ("leaves", "", 1, "", "leaf"),
        ("peaches", "", 1, "", "peach"),
        ("boxes", "", 1, "", "box"),
        ("radishes", "", 1, "", "radish"),
        ("glasses", "", 1, "", "glass"),
        ("cookies", "", 1, "", "cookie"),
        ("Eggs", "", 1, "", "Egg"),
        ("egg", "", 1, "", "egg"),  # already singular
        ("glass", "", 1, "", "glass"),
        ("molasses", "", 1, "", "molasses"),
        ("hummus", "", 1, "", "hummus"),
        ("couscous", "", 1, "", "couscous"),
        ("eggs (large)", "", 1, "", "eggs (large)"),
        ("eggs, beaten", "", 1, "", "eggs, beaten"),
        ("eggs for glaze", "", 1, "", "eggs for glaze"),
        ("eggs", "cups", 1, "", "eggs"),  # has a unit: not a counted item
        ("eggs", "", 1, "½", "eggs"),
    ],
)
def test_name_for_one_or_less_singular(page: Page, case: tuple[str, str, int, str, str]) -> None:
    name, unit, whole, frac, expected = case
    assert call(page, "nameFor", name, unit, {"whole": whole, "frac": frac}) == expected


@pytest.mark.parametrize(
    "case",
    [
        ("clove garlic", 3, "cloves garlic"),
        ("cloves garlic", 1, "clove garlic"),
        ("sprig thyme", 2, "sprigs thyme"),
        ("head lettuce", 2, "heads lettuce"),
        ("slice bread", 2, "slices bread"),
        ("pinches saffron", 1, "pinch saffron"),
        ("fish", 2, "fish"),
        ("garlic", 2, "garlic"),
        ("sheep", 2, "sheep"),
        ("rice", 2, "rice"),
        ("chilli", 2, "chillies"),
        ("cress", 2, "cress"),  # names ending in s are left as they are
        ("glass", 2, "glass"),
    ],
)
def test_name_for_count_words_and_invariants(page: Page, case: tuple[str, int, str]) -> None:
    name, whole, expected = case
    assert call(page, "nameFor", name, "", {"whole": whole, "frac": ""}) == expected
