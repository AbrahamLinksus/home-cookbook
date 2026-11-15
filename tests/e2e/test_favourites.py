"""Favourites on top, in the browser, with two devices (US-07, US-03, T-08)."""

import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect
from werkzeug.serving import make_server

from cookbook.app.config import Settings
from cookbook.app.factory import create_app

LAPTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}
CHANGED = "This recipe changed on another device"
DELETED = "This recipe was deleted on another device"


@pytest.fixture
def served(tmp_path: Path, clock: Any) -> Iterator[tuple[str, Any]]:
    app = create_app(Settings(db_path=tmp_path / "cookbook.db"), clock=clock)
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", clock
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def url(served: tuple[str, Any]) -> str:
    return served[0]


@pytest.fixture
def laptop_ctx(browser: Browser) -> Iterator[BrowserContext]:
    c = browser.new_context(viewport=LAPTOP)
    yield c
    c.close()


@pytest.fixture
def phone_ctx(browser: Browser) -> Iterator[BrowserContext]:
    c = browser.new_context(viewport=PHONE)
    yield c
    c.close()


@pytest.fixture
def make_recipe(laptop_ctx: BrowserContext, url: str) -> Callable[..., int]:
    def make(title: str = "Lemon Cake") -> int:
        recipe = {
            "title": title,
            "servings": 4,
            "ingredients": [{"amount": "2", "unit": "cups", "name": "flour"}],
            "steps": ["Bake at 220°C"],
        }
        response = laptop_ctx.request.post(f"{url}/api/recipes", data={"recipe": recipe})
        assert response.ok, response.text()
        return int(response.json()["id"])

    return make


def _titles(page: Page) -> list[str]:
    return [t.strip() for t in page.locator(".row-title").all_inner_texts()]


def _row_star(page: Page, title: str) -> Any:
    return page.get_by_test_id("recipe-row").filter(has_text=title).get_by_test_id("star")


def _list(ctx: BrowserContext, url: str) -> Page:
    page = ctx.new_page()
    page.goto(url)
    return page


def _edit(ctx: BrowserContext, url: str, rid: int) -> Page:
    page = ctx.new_page()
    page.goto(f"{url}/recipes/{rid}/edit")
    expect(page.get_by_test_id("ingredient-row")).not_to_have_count(0)
    return page


def _phone_stars(ctx: BrowserContext, url: str, rid: int) -> None:
    page = ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")
    page.get_by_test_id("star").click()
    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    page.close()


def _set_step(page: Page, text: str) -> None:
    page.get_by_test_id("step-rows").locator("textarea").first.fill(text)


def _read_pressed(ctx: BrowserContext, url: str, rid: int) -> str | None:
    page = ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")
    value = page.get_by_test_id("star").get_attribute("aria-pressed")
    page.close()
    return value


def test_star_in_list_moves_to_top_and_unstar_returns_to_az(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    make_recipe("Aunt May's Scones")
    make_recipe("Buttermilk Pancakes")
    make_recipe("Sunday Roast Chicken")
    page = _list(laptop_ctx, url)
    assert _titles(page) == ["Aunt May's Scones", "Buttermilk Pancakes", "Sunday Roast Chicken"]

    _row_star(page, "Sunday Roast").click()

    expect(page.locator(".row-title").first).to_have_text("Sunday Roast Chicken")
    assert _titles(page) == ["Sunday Roast Chicken", "Aunt May's Scones", "Buttermilk Pancakes"]
    expect(page.locator("h2.group")).to_have_count(2)
    expect(page.get_by_test_id("recipe-row").first.get_by_test_id("star")).to_have_attribute(
        "aria-pressed", "true"
    )
    _row_star(page, "Buttermilk").click()
    expect(page.locator(".row-title").first).to_have_text("Buttermilk Pancakes")
    assert _titles(page) == ["Buttermilk Pancakes", "Sunday Roast Chicken", "Aunt May's Scones"]

    _row_star(page, "Sunday Roast").click()
    _row_star(page, "Buttermilk").click()
    expect(page.locator(".row-title").first).to_have_text("Aunt May's Scones")
    assert _titles(page) == ["Aunt May's Scones", "Buttermilk Pancakes", "Sunday Roast Chicken"]


def test_tapping_star_does_not_open_recipe(
    phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    make_recipe("Sunday Roast Chicken")
    page = _list(phone_ctx, url)

    _row_star(page, "Sunday").click()

    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    assert page.url == f"{url}/"


def test_star_button_aria_label_and_size(
    phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe("Sunday Roast Chicken")
    page = _list(phone_ctx, url)
    star = page.get_by_test_id("star")
    expect(star).to_have_attribute("aria-pressed", "false")
    expect(star).to_have_attribute("aria-label", "Add to favourites")
    box = star.bounding_box()
    assert box is not None and box["width"] >= 44 and box["height"] >= 44

    star.click()

    expect(star).to_have_attribute("aria-pressed", "true")
    expect(star).to_have_attribute("aria-label", "Remove from favourites")
    page.goto(f"{url}/recipes/{rid}")
    view_star = page.get_by_test_id("star")
    expect(view_star).to_have_attribute("aria-label", "Remove from favourites")
    box = view_star.bounding_box()
    assert box is not None and box["width"] >= 44 and box["height"] >= 44
    view_star.click()
    expect(view_star).to_have_attribute("aria-pressed", "false")
    expect(view_star).to_have_attribute("aria-label", "Add to favourites")


def test_star_while_searching_keeps_search_and_resorts(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    make_recipe("Aunt May's Scones")
    make_recipe("Roast Potatoes")
    make_recipe("Sunday Roast Chicken")
    page = _list(laptop_ctx, url)
    page.get_by_test_id("search-input").fill("roast")
    expect(page.get_by_test_id("recipe-row")).to_have_count(2)
    assert _titles(page) == ["Roast Potatoes", "Sunday Roast Chicken"]

    _row_star(page, "Sunday Roast").click()

    expect(page.locator(".row-title").first).to_have_text("Sunday Roast Chicken")
    assert _titles(page) == ["Sunday Roast Chicken", "Roast Potatoes"]
    expect(page.get_by_test_id("search-input")).to_have_value("roast")


def test_double_tap_is_harmless(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe("Sunday Roast Chicken")
    page = _list(laptop_ctx, url)

    page.get_by_test_id("star").evaluate("b => { b.click(); b.click(); }")

    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    page.reload()
    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    assert _read_pressed(laptop_ctx, url, rid) == "true"


def test_star_from_read_view_shows_in_list_survives_reload_and_other_context(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    url: str,
    make_recipe: Callable[..., int],
) -> None:
    make_recipe("Aunt May's Scones")
    rid = make_recipe("Sunday Roast Chicken")
    page = laptop_ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")
    star = page.get_by_test_id("star")
    expect(star).to_have_attribute("aria-pressed", "false")

    star.click()

    expect(star).to_have_attribute("aria-pressed", "true")
    page.reload()
    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    page.goto(url)
    assert _titles(page)[0] == "Sunday Roast Chicken"
    expect(_row_star(page, "Sunday Roast")).to_have_attribute("aria-pressed", "true")
    other = _list(phone_ctx, url)
    assert _titles(other) == ["Sunday Roast Chicken", "Aunt May's Scones"]
    assert _read_pressed(phone_ctx, url, rid) == "true"


def test_phone_star_while_laptop_edits_saves_without_warning_and_keeps_star(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    url: str,
    make_recipe: Callable[..., int],
) -> None:
    rid = make_recipe("Lemon Cake")
    laptop = _edit(laptop_ctx, url, rid)
    dialogs: list[str] = []
    laptop.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    _set_step(laptop, "Laptop edit")
    _phone_stars(phone_ctx, url, rid)

    laptop.get_by_test_id("save").click()

    laptop.wait_for_url(f"{url}/recipes/{rid}")
    expect(laptop.get_by_test_id("step")).to_have_text(["Laptop edit"])
    expect(laptop.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    expect(laptop.get_by_test_id("conflict-dialog")).to_be_hidden()
    assert dialogs == []
    assert _read_pressed(phone_ctx, url, rid) == "true"


@pytest.mark.parametrize("choice", ["reload-theirs", "keep-mine"])
def test_real_conflict_keeps_current_star(
    choice: str,
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    url: str,
    make_recipe: Callable[..., int],
) -> None:
    rid = make_recipe("Lemon Cake")
    laptop = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Laptop rewrite")
    _phone_stars(phone_ctx, url, rid)
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}/edit")
    expect(phone.get_by_test_id("ingredient-row")).not_to_have_count(0)
    _set_step(phone, "Bake at 180°C")
    phone.get_by_test_id("save").click()
    phone.wait_for_url(f"{url}/recipes/{rid}")

    laptop.get_by_test_id("save").click()
    expect(laptop.get_by_test_id("conflict-message")).to_have_text(CHANGED)
    laptop.get_by_test_id(choice).click()

    laptop.wait_for_url(f"{url}/recipes/{rid}")
    expected = "Laptop rewrite" if choice == "keep-mine" else "Bake at 180°C"
    expect(laptop.get_by_test_id("step")).to_have_text([expected])
    expect(laptop.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")
    assert _read_pressed(phone_ctx, url, rid) == "true"


def test_unstar_on_phone_while_laptop_edits_keeps_unstarred(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    url: str,
    make_recipe: Callable[..., int],
) -> None:
    """The star is the current one, not the one the laptop loaded (starred -> unstarred)."""
    rid = make_recipe("Lemon Cake")
    _phone_stars(phone_ctx, url, rid)
    laptop = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Laptop edit")
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}")
    phone.get_by_test_id("star").click()
    expect(phone.get_by_test_id("star")).to_have_attribute("aria-pressed", "false")

    laptop.get_by_test_id("save").click()

    laptop.wait_for_url(f"{url}/recipes/{rid}")
    expect(laptop.get_by_test_id("star")).to_have_attribute("aria-pressed", "false")


def test_delete_starred_then_undo_brings_it_back_starred(
    phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    make_recipe("Aunt May's Scones")
    rid = make_recipe("Lemon Cake")
    _phone_stars(phone_ctx, url, rid)
    page = phone_ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")
    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "true")

    page.get_by_test_id("delete").click()
    page.wait_for_url(f"{url}/")
    expect(page.get_by_test_id("recipe-row")).to_have_count(1)
    page.get_by_test_id("undo-button").click()

    expect(page.get_by_test_id("recipe-row")).to_have_count(2)
    assert _titles(page) == ["Lemon Cake", "Aunt May's Scones"]
    expect(_row_star(page, "Lemon Cake")).to_have_attribute("aria-pressed", "true")
    assert _read_pressed(phone_ctx, url, rid) == "true"


def test_star_on_recipe_deleted_elsewhere_shows_deleted_message(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    url: str,
    make_recipe: Callable[..., int],
) -> None:
    make_recipe("Aunt May's Scones")
    rid = make_recipe("Lemon Cake")
    page = _list(laptop_ctx, url)
    assert phone_ctx.request.delete(f"{url}/api/recipes/{rid}").ok

    _row_star(page, "Lemon Cake").click()

    expect(page.get_by_test_id("menu-message")).to_have_text(DELETED)
    expect(page.get_by_test_id("recipe-row")).to_have_count(1)
    assert _titles(page) == ["Aunt May's Scones"]


def test_read_view_star_on_deleted_recipe_shows_message_and_stays_unstarred(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    url: str,
    make_recipe: Callable[..., int],
) -> None:
    rid = make_recipe("Lemon Cake")
    page = laptop_ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")
    assert phone_ctx.request.delete(f"{url}/api/recipes/{rid}").ok

    page.get_by_test_id("star").click()

    expect(page.get_by_test_id("menu-message")).to_have_text(DELETED)
    expect(page.get_by_test_id("star")).to_have_attribute("aria-pressed", "false")
