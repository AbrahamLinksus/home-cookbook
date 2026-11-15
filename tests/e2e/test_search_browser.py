"""Search in the browser (US-04, S-08, S-10)."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Browser, Page, expect

PHONE = {"width": 390, "height": 844}


@pytest.fixture
def make_recipe(live_url: str, browser: Browser) -> Iterator[Callable[..., int]]:
    ctx = browser.new_context()

    def make(title: str, *ingredients: str) -> int:
        items = [{"amount": "1", "unit": "cup", "name": n} for n in ingredients]
        recipe = {"title": title, "servings": 4, "ingredients": items, "steps": ["Mix"]}
        response = ctx.request.post(f"{live_url}/api/recipes", data={"recipe": recipe})
        assert response.ok, response.text()
        return int(response.json()["id"])

    yield make
    ctx.close()


@pytest.fixture
def page(live_url: str, browser: Browser, make_recipe: Callable[..., int]) -> Iterator[Page]:
    make_recipe("Grandma's Apple Pie", "flour")
    make_recipe("Shepherd's Pie", "potatoes")
    make_recipe("Lemon Cake", "lemons")
    make_recipe("Crème Brûlée", "cream")
    make_recipe("Buttermilk Pancakes", "buttermilk", "eggs")
    make_recipe("Aunt May's Scones", "buttermilk")
    make_recipe("Ratatouille", "eggplant")
    p = browser.new_page(viewport=PHONE)
    p.goto(live_url)
    yield p
    p.close()


def _titles(page: Page) -> object:
    return page.get_by_test_id("recipe-row").locator(".row-title")


def test_typing_narrows_list_without_enter(page: Page) -> None:
    expect(page.get_by_test_id("recipe-row")).to_have_count(7)

    page.get_by_test_id("search-input").press_sequentially("pie")

    expect(_titles(page)).to_have_text(["Grandma's Apple Pie", "Shepherd's Pie"])
    expect(page.get_by_text("Lemon Cake")).to_have_count(0)


@pytest.mark.parametrize(
    ("query", "title"),
    [("shepherds", "Shepherd's Pie"), ("creme", "Crème Brûlée"), ("APP", "Grandma's Apple Pie")],
)
def test_forgiving_name_search(page: Page, query: str, title: str) -> None:
    page.get_by_test_id("search-input").fill(query)

    expect(_titles(page)).to_have_text([title])


def test_by_ingredient_buttermilk_and_egg(page: Page) -> None:
    page.get_by_test_id("search-by-ingredient").check()
    page.get_by_test_id("search-input").fill("buttermilk")
    expect(_titles(page)).to_have_text(["Aunt May's Scones", "Buttermilk Pancakes"])

    page.get_by_test_id("search-input").fill("egg")
    expect(_titles(page)).to_have_text(["Buttermilk Pancakes", "Ratatouille"])

    page.get_by_test_id("search-input").fill("cup")
    expect(page.get_by_test_id("no-matches")).to_contain_text("No recipes match 'cup'")


def test_no_match_and_clear_search_restores_list(page: Page, live_url: str) -> None:
    page.get_by_test_id("search-input").fill("soup")

    expect(page.get_by_test_id("no-matches")).to_contain_text("No recipes match 'soup'")
    page.get_by_test_id("clear-search").click()

    page.wait_for_url(f"{live_url}/")
    expect(page.get_by_test_id("recipe-row")).to_have_count(7)
    expect(page.get_by_test_id("search-input")).to_have_value("")


def test_no_js_form_path_filters_via_get(page: Page, live_url: str) -> None:
    page.goto(f"{live_url}/?q=lemon&by=name")

    expect(_titles(page)).to_have_text(["Lemon Cake"])
    expect(page.get_by_test_id("search-input")).to_have_value("lemon")


def test_failed_fragment_request_shows_search_failed_note(page: Page) -> None:
    page.route("**/recipes/_list*", lambda route: route.abort())

    page.get_by_test_id("search-input").fill("pie")

    expect(page.get_by_role("alert")).to_have_text("Could not search. Please try again")
