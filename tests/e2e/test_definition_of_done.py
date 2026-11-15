"""SPEC §12 definition of done on the real app at its LAN address (US-01..US-09, S-03, S-04).

The app runs as `timeout … uv run cookbook` (the `start_app` fixture in conftest.py), and a
390x844 phone and a 1280x800 laptop both use the address it prints.
"""

import json
from collections.abc import Callable, Iterator
from operator import itemgetter
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Locator, Page, Response, expect

PHONE = {"width": 390, "height": 844}
LAPTOP = {"width": 1280, "height": 800}
PIE = "Grandma's Apple Pie"
SCONES = "Aunt May's Scones"  # buttermilk only in its ingredients
DECOY = "Buttermilk Biscuits"  # buttermilk only in its title
COOKIES = "Oat Cookies"
Devices = tuple[BrowserContext, BrowserContext, BrowserContext]


@pytest.fixture
def devices(browser: Browser) -> Iterator[Devices]:
    """Phone, laptop, and a phone for the fresh app; closed even when a step fails."""
    phone = browser.new_context(viewport=PHONE)
    laptop = browser.new_context(viewport=LAPTOP)
    fresh = browser.new_context(viewport=PHONE)
    yield phone, laptop, fresh
    for ctx in (phone, laptop, fresh):
        ctx.close()


def _titles(page: Page) -> Locator:
    return page.get_by_test_id("recipe-row").locator(".row-title")


def _row(page: Page, title: str) -> Locator:
    return page.get_by_test_id("recipe-row").filter(has_text=title)


def _is_put_favourite(response: Response) -> bool:
    return response.request.method == "PUT" and response.url.endswith("/favourite")


def _seed_kitchen(ctx: BrowserContext, url: str, seed: Callable[..., int]) -> None:
    def ingredient(name: str) -> dict[str, str]:
        return {"amount": "1", "unit": "cup", "name": name}

    seed(ctx, url, SCONES, ingredients=[ingredient("flour"), ingredient("buttermilk")])
    seed(ctx, url, DECOY, ingredients=[ingredient("flour"), ingredient("butter")])
    seed(ctx, url, COOKIES, ingredients=[ingredient("oats")])


def _add_pie_on_phone(page: Page, url: str) -> None:
    page.goto(url)
    page.get_by_test_id("add-recipe").click()
    page.get_by_label("Title").fill(PIE)
    page.get_by_label("Servings").fill("8")
    page.get_by_test_id("add-ingredient").click()
    row = page.get_by_test_id("ingredient-row").first
    row.get_by_label("Amount").fill("1")
    row.get_by_label("Unit").fill("cup")
    row.get_by_label("Name").fill("butter")
    page.get_by_test_id("add-step").click()
    page.get_by_test_id("step-row").first.get_by_label("Step", exact=True).fill("Bake.")
    page.get_by_test_id("save").click()
    expect(page.get_by_test_id("recipe-title")).to_have_text(PIE)


def _search(page: Page, url: str, text: str, by: str) -> None:
    page.goto(url)
    page.locator("label").filter(has=page.get_by_test_id(f"search-by-{by}")).click()
    expect(page.get_by_test_id(f"search-by-{by}")).to_be_checked()
    page.get_by_test_id("search-input").fill(text)
    page.get_by_test_id("search-input").press("Enter")


def _search_by_name_and_ingredient(laptop: Page, url: str) -> None:
    _search(laptop, url, "pie", "name")
    expect(_titles(laptop)).to_have_text([PIE])
    _search(laptop, url, "buttermilk", "ingredient")
    expect(_titles(laptop)).to_have_text([SCONES])  # not the decoy titled "Buttermilk …"
    _search(laptop, url, "buttermilk", "name")
    expect(_titles(laptop)).to_have_text([DECOY])  # so the toggle really changed the search


def _scale_without_saving(phone: Page, url: str) -> None:
    phone.goto(url)
    _row(phone, PIE).click()
    lines = phone.get_by_test_id("ingredient-line")
    expect(lines).to_have_text(["1 cup butter"])
    phone.get_by_test_id("servings-input").fill("4")
    phone.get_by_test_id("servings-input").press("Enter")
    expect(lines).to_have_text(["½ cup butter"])
    phone.reload()
    expect(lines).to_have_text(["1 cup butter"])
    expect(phone.get_by_test_id("servings-input")).to_have_value("8")


def _star_goes_on_top(phone: Page, url: str) -> None:
    phone.goto(url)
    expect(_titles(phone)).to_have_text([SCONES, DECOY, PIE, COOKIES])
    star = _row(phone, COOKIES).get_by_test_id("star")
    with phone.expect_response(_is_put_favourite) as put:
        star.click()
    assert put.value.ok
    expect(star).to_have_attribute("aria-pressed", "true")
    phone.reload()
    expect(_titles(phone)).to_have_text([COOKIES, SCONES, DECOY, PIE])


def _delete_then_undo(phone: Page, url: str) -> None:
    _row(phone, SCONES).click()
    phone.get_by_test_id("delete").click()
    phone.wait_for_url(f"{url}/")
    expect(_titles(phone)).to_have_text([COOKIES, DECOY, PIE])
    with phone.expect_response(lambda r: r.url.endswith("/restore")) as restore:
        phone.get_by_test_id("undo-button").click()
    assert restore.value.ok
    expect(_row(phone, SCONES)).to_have_count(1)
    phone.reload()
    expect(_titles(phone)).to_have_text([COOKIES, SCONES, DECOY, PIE])


def _export_and_import_fresh(
    phone: BrowserContext,
    fresh: BrowserContext,
    start_app: Callable[[str], str],
    url: str,
    backup: Path,
) -> None:
    backup.write_bytes(phone.request.get(f"{url}/export").body())
    source = json.loads(backup.read_text(encoding="utf-8"))
    assert source["recipe_count"] == 4
    pie = next(r for r in source["recipes"] if r["title"] == PIE)
    assert pie["servings"] == 8  # scaling never saved
    assert pie["ingredients"] == [{"amount": "1", "unit": "cup", "name": "butter"}]
    assert [r["title"] for r in source["recipes"] if r["favourite"]] == [COOKIES]

    fresh_url = start_app("fresh")
    page = fresh.new_page()
    page.goto(fresh_url)
    expect(page.get_by_test_id("empty-state")).to_be_visible()
    page.get_by_test_id("menu-button").click()
    page.get_by_test_id("import-input").set_input_files(str(backup))
    expect(page.get_by_test_id("menu-message")).to_have_text("Imported 4 recipes")
    expect(_titles(page)).to_have_text([COOKIES, SCONES, DECOY, PIE])
    again = page.request.get(f"{fresh_url}/export").json()
    assert again["recipe_count"] == 4
    key = itemgetter("title")
    assert sorted(again["recipes"], key=key) == sorted(source["recipes"], key=key)


def test_journey_phone_and_laptop_on_lan_meets_definition_of_done(
    start_app: Callable[[str], str],
    devices: Devices,
    seed: Callable[..., int],
    tmp_path: Path,
) -> None:
    phone_ctx, laptop_ctx, fresh_ctx = devices
    url = start_app("home")
    phone, laptop = phone_ctx.new_page(), laptop_ctx.new_page()
    assert phone.viewport_size == PHONE and laptop.viewport_size == LAPTOP
    _seed_kitchen(phone_ctx, url, seed)

    _add_pie_on_phone(phone, url)
    laptop.goto(url)
    assert laptop.url.startswith(url) and phone.url.startswith(url)
    expect(_titles(laptop)).to_have_text([SCONES, DECOY, PIE, COOKIES])

    _search_by_name_and_ingredient(laptop, url)
    _scale_without_saving(phone, url)
    _star_goes_on_top(phone, url)
    _delete_then_undo(phone, url)
    _export_and_import_fresh(phone_ctx, fresh_ctx, start_app, url, tmp_path / "backup.json")
