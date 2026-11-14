"""Export, load back in, and refuse bad files (US-08, US-09, S-05, S-07, S-11)."""

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, expect

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}
NOT_AN_EXPORT = "This file isn't a Home Cookbook export; nothing was changed"


def make_export(count: int) -> dict[str, Any]:
    recipes = [
        {
            "title": f"Recipe {n:02d} café",
            "servings": 2 + n % 5,
            "favourite": n % 7 == 0,
            "ingredients": [
                {"amount": "1 1/2", "unit": "cups", "name": "flour"},
                {"amount": "2.5", "unit": "tbsp", "name": "butter"},
                {"amount": None, "unit": "", "name": "salt, to taste"},
            ],
            "steps": [f"Mix number {n}.", "Bake."],
            "created_at": "2026-11-01T10:00:00Z",
            "updated_at": "2026-11-02T10:00:00Z",
        }
        for n in range(count)
    ]
    return {
        "format": "home-cookbook-export",
        "format_version": 1,
        "app_version": "1.0.0",
        "exported_at": "2026-11-13T18:02:11Z",
        "recipe_count": count,
        "recipes": recipes,
    }


def load_file(page: Page, path: Path) -> None:
    page.get_by_test_id("menu-button").click()
    page.get_by_test_id("import-input").set_input_files(str(path))


def test_import_into_empty_app_lists_all_and_exports_identically(
    browser: Browser, live_url: str, tmp_path: Path
) -> None:
    source = make_export(42)
    path = tmp_path / "backup.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    page = browser.new_page(viewport=PHONE)
    page.goto(live_url)
    load_file(page, path)
    expect(page.get_by_test_id("menu-message")).to_have_text("Imported 42 recipes")
    expect(page.get_by_test_id("recipe-row")).to_have_count(42)
    again = page.request.get(f"{live_url}/export").json()
    assert again["recipe_count"] == 42
    key = lambda r: r["title"]  # noqa: E731
    assert sorted(again["recipes"], key=key) == sorted(source["recipes"], key=key)
    page.close()


def test_bad_file_shows_message_and_changes_nothing(
    browser: Browser, live_url: str, tmp_path: Path
) -> None:
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(make_export(3))[:-40], encoding="utf-8")
    page = browser.new_page(viewport=DESKTOP)
    page.goto(live_url)
    load_file(page, path)
    expect(page.get_by_test_id("menu-message")).to_have_text(NOT_AN_EXPORT)
    expect(page.get_by_test_id("recipe-row")).to_have_count(0)
    page.close()


def test_favourites_are_on_top_after_import(
    browser: Browser, live_url: str, tmp_path: Path
) -> None:
    path = tmp_path / "backup.json"
    path.write_text(json.dumps(make_export(42)), encoding="utf-8")
    page = browser.new_page(viewport=PHONE)
    page.goto(live_url)
    load_file(page, path)
    expect(page.get_by_test_id("recipe-row")).to_have_count(42)
    stars = page.get_by_test_id("recipe-row").locator("[aria-pressed]")
    states = [stars.nth(i).get_attribute("aria-pressed") for i in range(42)]
    favourites = states.count("true")
    assert favourites == 6  # n = 0, 7, 14, 21, 28, 35
    assert states == ["true"] * favourites + ["false"] * (42 - favourites)
    page.close()


def test_skipped_and_renamed_text_shows_in_the_menu(
    browser: Browser, live_url: str, tmp_path: Path
) -> None:
    doc = make_export(3)
    doc["recipes"][1]["title"] = doc["recipes"][0]["title"]  # repeated in the file
    path = tmp_path / "first.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    page = browser.new_page(viewport=PHONE)
    page.goto(live_url)
    load_file(page, path)
    message = page.get_by_test_id("menu-message")
    expect(message).to_have_text("Imported 3 recipes · renamed 1 with a repeated title")
    load_file(page, path)
    expect(message).to_contain_text("Imported 0 recipes · skipped 3 with the same title: ")
    expect(message).to_contain_text("Recipe 00 café")
    expect(message).to_contain_text("To restore one, delete it first, then import again")
    page.close()


def test_every_bad_file_leaves_the_count_unchanged(
    browser: Browser, live_url: str, tmp_path: Path
) -> None:
    good = tmp_path / "good.json"
    good.write_text(json.dumps(make_export(2)), encoding="utf-8")
    jpg = tmp_path / "holiday.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF holiday")
    truncated = tmp_path / "cut.json"
    truncated.write_text(json.dumps(make_export(3))[:-40], encoding="utf-8")
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({**make_export(3), "recipe_count": 9}), encoding="utf-8")
    newer = tmp_path / "newer.json"
    newer.write_text(json.dumps({**make_export(3), "format_version": 2}), encoding="utf-8")
    page = browser.new_page(viewport=PHONE)
    page.goto(live_url)
    load_file(page, good)
    expect(page.get_by_test_id("recipe-row")).to_have_count(2)
    message = page.get_by_test_id("menu-message")
    for bad in (jpg, truncated, wrong):
        load_file(page, bad)
        expect(message).to_have_text(NOT_AN_EXPORT)
        expect(page.get_by_test_id("recipe-row")).to_have_count(2)
    load_file(page, newer)
    expect(message).to_have_text(
        "This file was made by a newer version of Home Cookbook. "
        "Update the app to load it; nothing was changed"
    )
    expect(page.get_by_test_id("recipe-row")).to_have_count(2)
    page.close()
