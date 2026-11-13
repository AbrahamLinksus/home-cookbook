"""Add a recipe and read it on the phone (US-01, US-02, S-01, S-07, S-09)."""

import json

import pytest
from playwright.sync_api import Browser, Locator, Page, Route, expect

from cookbook.web import messages

PHONE = {"width": 390, "height": 844}
INGREDIENTS = [
    ("2", "cups", "flour"),
    ("1", "cup", "butter"),
    ("6", "", "apples"),
    ("¾", "cup", "sugar"),
    ("1", "tsp", "cinnamon"),
    ("", "", "salt, to taste"),
]
STEPS = [
    "Preheat oven to 200°C.",
    "Rub the butter into the flour.",
    "Slice the apples.",
    "Fill the dish.",
    "Bake 45 minutes.",
]


def open_new(browser: Browser, live_url: str, viewport: dict[str, int] = PHONE) -> Page:
    page = browser.new_page(viewport=viewport)
    page.goto(f"{live_url}/recipes/new")
    return page


def ingredient(page: Page, index: int) -> Locator:
    return page.get_by_test_id("ingredient-row").nth(index)


def fill_ingredient(page: Page, index: int, amount: str, unit: str, name: str) -> None:
    while page.get_by_test_id("ingredient-row").count() <= index:
        page.get_by_test_id("add-ingredient").click()
    row = ingredient(page, index)
    row.get_by_label("Amount").fill(amount)
    row.get_by_label("Unit").fill(unit)
    row.get_by_label("Name").fill(name)


def fill_step(page: Page, index: int, text: str) -> None:
    while page.get_by_test_id("step-row").count() <= index:
        page.get_by_test_id("add-step").click()
    page.get_by_test_id("step-row").nth(index).get_by_label("Step", exact=True).fill(text)


def fill_recipe(page: Page, title: str, servings: str = "4") -> None:
    page.get_by_label("Title").fill(title)
    page.get_by_label("Servings").fill(servings)
    fill_ingredient(page, 0, "2", "cups", "flour")
    fill_step(page, 0, "Mix.")


def test_add_apple_pie_opens_read_view_and_list_shows_it(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    page.get_by_label("Title").fill("Grandma's Apple Pie")
    page.get_by_label("Servings").fill("8")
    for i, row in enumerate(INGREDIENTS):
        fill_ingredient(page, i, *row)
    for i, text in enumerate(STEPS):
        fill_step(page, i, text)

    page.get_by_test_id("save").click()

    page.wait_for_url("**/recipes/1")
    lines = page.get_by_test_id("ingredient-line")
    expect(lines).to_have_text(
        [
            "2 cups flour",
            "1 cup butter",
            "6 apples",
            "¾ cup sugar",
            "1 tsp cinnamon",
            "salt, to taste",
        ]
    )
    expect(page.get_by_test_id("step").first).to_have_text("Preheat oven to 200°C.")
    page.goto(live_url)
    expect(page.get_by_test_id("recipe-row")).to_contain_text("Grandma's Apple Pie")
    expect(page.get_by_test_id("recipe-row")).to_contain_text("8 servings")
    page.close()


def test_duplicate_title_keeps_form_open_then_new_name_saves(
    browser: Browser, live_url: str
) -> None:
    first = open_new(browser, live_url)
    fill_recipe(first, "Pancakes")
    first.get_by_test_id("save").click()
    first.wait_for_url("**/recipes/1")
    page = open_new(browser, live_url)
    fill_recipe(page, " pancakes ")

    page.get_by_test_id("save").click()

    expect(page.get_by_test_id("title-error")).to_have_text(
        "You already have a recipe called 'Pancakes'. "
        "Please choose another name, e.g. 'Pancakes (Gran's)'"
    )
    assert page.url.endswith("/recipes/new")
    page.get_by_label("Title").fill("Pancakes (Gran's)")
    page.get_by_test_id("save").click()
    page.wait_for_url("**/recipes/2")
    first.close()
    page.close()


def test_amounts_are_saved_in_kitchen_form(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    fill_recipe(page, "Amounts")
    typed = ["2", "2.5", "1/2", "1 1/2", "½"]
    for i, amount in enumerate(typed):
        fill_ingredient(page, i, amount, "", f"item{i}")

    page.get_by_test_id("save").click()

    page.wait_for_url("**/recipes/1")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(
        ["2 item0", "2½ item1", "½ item2", "1½ item3", "½ item4"]
    )
    page.close()


def test_range_amount_is_refused_under_that_amount(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    fill_recipe(page, "Omelette")
    fill_ingredient(page, 0, "2-3", "", "eggs")

    page.get_by_test_id("save").click()

    error = ingredient(page, 0).get_by_text("Enter one amount, e.g. 2 or 2½")
    expect(error).to_be_visible()
    expect(ingredient(page, 0).get_by_label("Amount")).to_be_focused()
    assert page.url.endswith("/recipes/new")
    page.close()


def test_blank_title_and_zero_servings_show_messages_and_focus(
    browser: Browser, live_url: str
) -> None:
    page = open_new(browser, live_url)
    page.get_by_label("Servings").fill("0")

    page.get_by_test_id("save").click()

    expect(page.get_by_test_id("title-error")).to_be_visible()
    expect(page.get_by_label("Title")).to_be_focused()
    expect(page.get_by_text("Use a whole number of 1 or more")).to_be_visible()
    assert page.url.endswith("/recipes/new")
    page.close()


def test_added_ingredient_moved_up_to_line_six_is_saved_at_line_six(
    browser: Browser, live_url: str
) -> None:
    page = open_new(browser, live_url)
    page.get_by_label("Title").fill("Order")
    for i, row in enumerate(INGREDIENTS):
        fill_ingredient(page, i, *row)
    fill_ingredient(page, 6, "9", "", "last")
    fill_step(page, 0, "Mix.")

    ingredient(page, 6).get_by_test_id("ingredient-up").click()
    page.get_by_test_id("save").click()

    page.wait_for_url("**/recipes/1")
    expect(page.get_by_test_id("ingredient-line").nth(5)).to_have_text("9 last")
    expect(page.get_by_test_id("ingredient-line").nth(6)).to_have_text("salt, to taste")
    page.close()


def test_rows_can_be_removed_and_steps_moved(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    fill_recipe(page, "Rows")
    fill_step(page, 1, "Second")
    fill_step(page, 2, "Third")

    page.get_by_test_id("step-row").nth(2).get_by_test_id("step-up").click()
    page.get_by_test_id("step-row").nth(0).get_by_test_id("step-remove").click()

    expect(page.get_by_test_id("step-row")).to_have_count(2)
    expect(page.get_by_test_id("step-row").first.get_by_label("Step", exact=True)).to_have_value(
        "Third"
    )
    page.close()


def test_cancel_after_typing_asks_discard_changes(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    asked: list[str] = []
    page.on("dialog", lambda d: (asked.append(d.message), d.dismiss()))
    page.get_by_label("Title").fill("Half typed")

    page.get_by_test_id("cancel").click()

    assert asked == ["Discard changes?"]
    assert page.url.endswith("/recipes/new")
    page.close()


def test_cancel_confirm_text_comes_from_messages_ui_texts(
    browser: Browser, live_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(messages.UI_TEXTS, "discard_changes", "Changed in messages.py?")
    page = open_new(browser, live_url)
    asked: list[str] = []
    page.on("dialog", lambda d: (asked.append(d.message), d.dismiss()))
    page.get_by_label("Title").fill("Half typed")

    page.get_by_test_id("cancel").click()

    assert asked == ["Changed in messages.py?"]
    page.close()


def _answer(page: Page, status: int, body: dict[str, object]) -> None:
    def fulfill(route: Route) -> None:
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    page.route("**/api/recipes", fulfill)


@pytest.mark.parametrize(
    ("key", "button"), [("ingredients", "add-ingredient"), ("steps", "add-step")]
)
def test_list_level_error_shows_under_its_add_button_and_keeps_typing(
    browser: Browser, live_url: str, key: str, button: str
) -> None:
    page = open_new(browser, live_url)
    fill_recipe(page, "Too many rows")
    too_long = messages.FIELD_MESSAGES["too_long"]
    _answer(page, 422, {"error": "invalid", "message": "", "fields": {key: too_long}})

    page.get_by_test_id("save").click()

    expect(page.get_by_test_id(f"{key}-error")).to_have_text(too_long)
    expect(page.get_by_test_id(button)).to_be_focused()
    expect(page.get_by_label("Title")).to_have_value("Too many rows")
    page.close()


def test_save_stays_disabled_after_201_until_the_page_changes(
    browser: Browser, live_url: str
) -> None:
    page = open_new(browser, live_url)
    fill_recipe(page, "Once")
    _answer(page, 201, {"id": 1, "version": 1})
    page.route("**/recipes/1", lambda route: route.fulfill(status=204))

    with page.expect_request("**/recipes/1"):
        page.get_by_test_id("save").click()

    expect(page.get_by_test_id("save")).to_be_disabled()
    page.close()


def test_save_is_enabled_again_after_an_error(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    page.get_by_label("Servings").fill("0")

    page.get_by_test_id("save").click()

    expect(page.get_by_test_id("title-error")).to_be_visible()
    expect(page.get_by_test_id("save")).to_be_enabled()
    page.close()


def test_cancel_without_typing_leaves_without_asking(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)

    page.get_by_test_id("cancel").click()

    page.wait_for_url(f"{live_url}/")
    page.close()


def test_long_recipe_read_view_has_no_sideways_scroll(browser: Browser, live_url: str) -> None:
    page = open_new(browser, live_url)
    page.get_by_label("Title").fill("Huge")
    for i in range(38):
        fill_ingredient(page, i, "1", "cup", f"ingredient number {i} with a long name")
    for i in range(21):
        fill_step(page, i, f"Step {i}")
    fill_step(page, 21, " ".join(["simmer"] * 900))

    page.get_by_test_id("save").click()

    page.wait_for_url("**/recipes/1")
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
    page.close()
