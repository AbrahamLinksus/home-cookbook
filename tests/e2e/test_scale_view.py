"""Scaling on the recipe read view (US-06, S-02, S-13)."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from cookbook.web import messages

PHONE = {"width": 390, "height": 844}


def ing(amount: str | None, unit: str, name: str) -> dict[str, str | None]:
    return {"amount": amount, "unit": unit, "name": name}


PIE = ("Grandma's Apple Pie", 8, [
    ing("2", "cups", "flour"), ing("1", "cup", "butter"), ing("6", "", "apples"),
    ing("¾", "cup", "sugar"), ing("1", "tsp", "cinnamon"), ing(None, "", "salt, to taste"),
])  # fmt: skip
PANCAKES = ("Buttermilk Pancakes", 4, [ing("3", "", "eggs"), ing("⅓", "cup", "sugar")])
COOKIES = ("Oat Cookies", 24, [ing("1", "cup", "oats"), ing("1", "", "egg")])
SCONES = ("Aunt May's Scones", 3, [
    ing("253", "g", "flour"), ing("150", "ml", "buttermilk"), ing("2", "tbsp", "sugar"),
    ing("1", "g", "yeast"), ing("1", "", "egg"), ing("1/8", "tsp", "salt"),
    ing("125", "g", "butter"),
])  # fmt: skip


@pytest.fixture
def ctx(browser: Browser) -> Iterator[BrowserContext]:
    c = browser.new_context(viewport=PHONE)
    yield c
    c.close()


@pytest.fixture
def open_recipe(ctx: BrowserContext, live_url: str) -> Callable[..., Page]:
    def make(spec: tuple[str, int, list[dict[str, str | None]]]) -> Page:
        title, servings, ingredients = spec
        recipe = {
            "title": title,
            "servings": servings,
            "ingredients": ingredients,
            "steps": ["Mix"],
        }
        rid = ctx.request.post(f"{live_url}/api/recipes", data={"recipe": recipe}).json()["id"]
        page = ctx.new_page()
        page.goto(f"{live_url}/recipes/{rid}")
        return page

    return make


def lines(page: Page) -> list[str]:
    return [t.strip() for t in page.get_by_test_id("ingredient-line").all_inner_texts()]


def set_servings(page: Page, value: str) -> None:
    box = page.get_by_test_id("servings-input")
    box.fill(value)
    box.press("Enter")


def test_pie_8_to_4_then_reset(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    saved = lines(page)
    assert saved[:2] == ["2 cups flour", "1 cup butter"]
    assert saved[3:] == ["¾ cup sugar", "1 tsp cinnamon", "salt, to taste"]
    set_servings(page, "4")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(
        [
            "1 cup flour",
            "½ cup butter",
            "3 apples",
            "⅓ cup sugar",
            "½ tsp cinnamon",
            "salt, to taste",
        ]
    )
    note = page.get_by_test_id("scaled-note")
    expect(note).to_be_visible()
    assert note.inner_text().strip() == "Scaled from 8 servings · Reset"
    page.get_by_test_id("reset-scale").click()
    expect(page.get_by_test_id("servings-input")).to_have_value("8")
    expect(page.get_by_test_id("servings")).to_have_text("8")
    assert lines(page) == saved
    expect(note).to_be_hidden()


def test_pancakes_4_to_6(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PANCAKES)
    set_servings(page, "6")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["4½ eggs", "½ cup sugar"])


def test_s13_cookies_24_to_36(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(COOKIES)
    set_servings(page, "36")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["1½ cups oats", "1½ eggs"])


def test_s02_scones_3_to_1(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(SCONES)
    set_servings(page, "1")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(
        [
            "84 g flour",
            "50 ml buttermilk",
            "⅔ tbsp sugar",
            "1 g yeast",
            "½ egg",
            "¼ tsp salt",
            "42 g butter",
        ]
    )
    assert not any(t.startswith("0") for t in lines(page))


def test_pie_8_to_1_names_read_singular(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    set_servings(page, "1")
    expect(page.get_by_test_id("ingredient-line").nth(2)).to_have_text("1 apple")


def test_eggs_4_to_2_shows_one_egg(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(("Omelette", 4, [ing("2", "", "eggs")]))
    set_servings(page, "2")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["1 egg"])


def test_62_5_grams_rounds_to_63(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(("Rounding", 8, [ing("125", "g", "flour")]))
    set_servings(page, "4")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["63 g flour"])


@pytest.mark.parametrize("bad", ["0", "-1", "abc", "", "2.5", "1e2", "1001", "9007199254740991"])
def test_bad_servings_refused_and_input_resets(open_recipe: Callable[..., Page], bad: str) -> None:
    page = open_recipe(PIE)
    saved = lines(page)
    set_servings(page, bad)
    expect(page.get_by_test_id("servings-input")).to_have_value("8")
    assert lines(page) == saved
    expect(page.get_by_test_id("scaled-note")).to_be_hidden()


def test_bad_servings_after_valid_scale_reset_to_current(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    set_servings(page, "4")
    set_servings(page, "abc")
    expect(page.get_by_test_id("servings-input")).to_have_value("4")
    expect(page.get_by_test_id("ingredient-line").first).to_have_text("1 cup flour")


def test_stepper_buttons(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    page.get_by_test_id("servings-down").click()
    expect(page.get_by_test_id("servings-input")).to_have_value("7")
    page.get_by_test_id("servings-up").click()
    page.get_by_test_id("servings-up").click()
    expect(page.get_by_test_id("servings-input")).to_have_value("9")
    expect(page.get_by_test_id("scaled-note")).to_contain_text("Scaled from 8 servings")


def test_servings_at_max_1000_accepted_and_up_refused(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(("Big", 1, [ing("1", "g", "salt")]))
    set_servings(page, "1000")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["1000 g salt"])
    page.get_by_test_id("servings-up").click()
    expect(page.get_by_test_id("servings-input")).to_have_value("1000")


def test_scaled_note_saved_one_serving_reads_singular(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(("Solo", 1, [ing("2", "cups", "flour")]))
    set_servings(page, "2")
    expect(page.get_by_test_id("scaled-text")).to_have_text(
        messages.UI_TEXTS["scaled_from_one"].format(n=1)
    )


def test_scale_status_announces_new_servings(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    status = page.get_by_test_id("scale-status")
    expect(status).to_have_attribute("role", "status")
    set_servings(page, "4")
    expect(status).to_have_text(messages.UI_TEXTS["scaled_to"].format(n=4))
    set_servings(page, "1")
    expect(status).to_have_text(messages.UI_TEXTS["scaled_to_one"].format(n=1))


def test_reset_is_a_44px_button(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    set_servings(page, "4")
    reset = page.get_by_role("button", name="Reset")
    expect(reset).to_have_attribute("data-testid", "reset-scale")
    box = reset.bounding_box()
    assert box is not None
    assert box["height"] >= 44
    assert box["width"] >= 44


def test_saved_servings_copy_hidden_from_screen_readers(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    hidden = page.locator('[aria-hidden="true"]:has([data-testid="servings"])')
    expect(hidden).to_have_count(1)


def test_stepper_down_stops_at_one(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(("Solo", 1, [ing("2", "cups", "flour")]))
    page.get_by_test_id("servings-down").click()
    expect(page.get_by_test_id("servings-input")).to_have_value("1")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["2 cups flour"])


def test_returning_to_saved_servings_shows_saved_text(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    set_servings(page, "4")
    set_servings(page, "8")
    assert lines(page)[3] == "¾ cup sugar"
    expect(page.get_by_test_id("scaled-note")).to_be_hidden()


def test_reload_shows_saved_servings_and_amounts(open_recipe: Callable[..., Page]) -> None:
    page = open_recipe(PIE)
    saved = lines(page)
    set_servings(page, "4")
    page.reload()
    expect(page.get_by_test_id("servings-input")).to_have_value("8")
    expect(page.get_by_test_id("servings")).to_have_text("8")
    assert lines(page) == saved


def test_delete_and_undo_still_work_after_scaling(
    open_recipe: Callable[..., Page], live_url: str
) -> None:
    page = open_recipe(PIE)
    set_servings(page, "4")
    page.get_by_test_id("delete").click()
    page.wait_for_url(f"{live_url}/")
    expect(page.get_by_test_id("undo-bar")).to_contain_text("'Grandma's Apple Pie' deleted")
    expect(page.get_by_test_id("recipe-row")).to_have_count(0)
    page.get_by_test_id("undo-button").click()
    expect(page.get_by_test_id("recipe-row")).to_have_count(1)
    page.get_by_test_id("recipe-row").click()
    expect(page.get_by_test_id("servings")).to_have_text("8")
    assert lines(page)[0] == "2 cups flour"
