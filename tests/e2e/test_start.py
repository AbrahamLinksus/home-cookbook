"""Empty app start screen (US-01, US-02, S-10)."""

import pytest
from playwright.sync_api import Browser, expect

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}


@pytest.mark.parametrize("viewport", [PHONE, DESKTOP], ids=["phone", "desktop"])
def test_empty_app_shows_no_recipes_yet_without_sideways_scroll(
    browser: Browser, live_url: str, viewport: dict[str, int]
) -> None:
    page = browser.new_page(viewport=viewport)

    page.goto(live_url)

    expect(page.get_by_text("No recipes yet")).to_be_visible()
    expect(page.get_by_test_id("add-recipe-empty")).to_have_text("+ Add recipe")
    scroll_width = page.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= viewport["width"]
    page.close()


def test_header_menu_offers_export_and_import(browser: Browser, live_url: str) -> None:
    page = browser.new_page(viewport=PHONE)

    page.goto(live_url)
    page.get_by_test_id("menu-button").click()

    expect(page.get_by_text("Export all recipes")).to_be_visible()
    expect(page.get_by_text("Import recipes")).to_be_visible()
    page.close()
