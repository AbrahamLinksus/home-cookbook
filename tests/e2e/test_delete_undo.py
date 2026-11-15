"""Delete a recipe and undo it in the browser (US-05, S-04)."""

import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, expect
from werkzeug.serving import make_server

from cookbook.app.config import Settings
from cookbook.app.factory import create_app

PHONE = {"width": 390, "height": 844}
BAR = "undo-bar"


@pytest.fixture
def served(tmp_path: Path, clock: Any) -> Iterator[tuple[str, Any]]:
    """A live app on a fake server clock (the browser keeps its own clock)."""
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
def make_recipe(served: tuple[str, Any], browser: Browser) -> Callable[[str], int]:
    url = served[0]
    ctx = browser.new_context()

    def make(title: str) -> int:
        recipe = {"title": title, "servings": 4, "ingredients": [], "steps": ["Mix"]}
        response = ctx.request.post(f"{url}/api/recipes", data={"recipe": recipe})
        assert response.ok, response.text()
        return int(response.json()["id"])

    return make


def _open(browser: Browser, url: str, path: str = "/") -> Page:
    page = browser.new_page(viewport=PHONE)
    page.goto(f"{url}{path}")
    return page


def _rows(page: Page) -> object:
    return page.get_by_test_id("recipe-row")


def _delete_from_view(page: Page, url: str, rid: int) -> None:
    page.goto(f"{url}/recipes/{rid}")
    page.get_by_test_id("delete").click()
    page.wait_for_url(f"{url}/")


def test_delete_returns_to_list_at_once_with_bar_and_undo_restores(
    browser: Browser, served: tuple[str, Any], make_recipe: Callable[[str], int]
) -> None:
    url, _ = served
    rid = make_recipe("Lemon Cake")
    page = _open(browser, url, f"/recipes/{rid}")
    dialogs: list[str] = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    page.get_by_test_id("delete").click()

    page.wait_for_url(f"{url}/")
    assert dialogs == []
    expect(_rows(page)).to_have_count(0)
    expect(page.get_by_test_id(BAR)).to_contain_text("'Lemon Cake' deleted")
    expect(page.get_by_test_id(BAR)).to_contain_text("Undo")
    page.get_by_test_id("undo-button").click()
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page)).to_contain_text("Lemon Cake")
    expect(page.get_by_test_id(BAR)).to_have_text("'Lemon Cake' is back")
    page.goto(f"{url}/recipes/{rid}")
    expect(page.get_by_test_id("recipe-title")).to_have_text("Lemon Cake")
    expect(page.get_by_test_id("servings")).to_have_text("4")
    expect(page.get_by_test_id("step")).to_have_text(["Mix"])
    page.close()


def test_s04_bar_persists_when_opening_another_recipe_then_undo_is_refused(
    browser: Browser, served: tuple[str, Any], make_recipe: Callable[[str], int]
) -> None:
    url, server_clock = served
    cake = make_recipe("Lemon Cake")
    soup = make_recipe("Soup")
    page = _open(browser, url)
    page.clock.install()
    _delete_from_view(page, url, cake)
    expect(page.get_by_test_id(BAR)).to_contain_text("'Lemon Cake' deleted")

    page.get_by_test_id("recipe-row").first.click()
    page.wait_for_url(f"{url}/recipes/{soup}")

    expect(page.get_by_test_id(BAR)).to_contain_text("'Lemon Cake' deleted")
    # the window ends on the server (10 s + grace) while the bar is still shown
    server_clock.advance(13)
    page.get_by_test_id("undo-button").click()
    expect(page.get_by_test_id(BAR)).to_have_text("Too late to undo; 'Lemon Cake' is gone")
    page.goto(url)
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page)).not_to_contain_text("Lemon Cake")
    page.close()


def test_s04_bar_disappears_when_browser_window_ends(
    browser: Browser, served: tuple[str, Any], make_recipe: Callable[[str], int]
) -> None:
    url, server_clock = served
    cake = make_recipe("Lemon Cake")
    page = _open(browser, url)
    page.clock.install()
    _delete_from_view(page, url, cake)
    expect(page.get_by_test_id(BAR)).to_be_visible()

    page.clock.fast_forward(11_000)
    server_clock.advance(13)

    expect(page.get_by_test_id(BAR)).to_be_hidden()
    page.reload()
    expect(page.get_by_test_id(BAR)).to_be_hidden()
    expect(_rows(page)).to_have_count(0)
    page.close()


def test_second_delete_replaces_bar_and_first_is_final(
    browser: Browser, served: tuple[str, Any], make_recipe: Callable[[str], int]
) -> None:
    url, _ = served
    cake = make_recipe("Lemon Cake")
    soup = make_recipe("Soup")
    page = _open(browser, url)
    _delete_from_view(page, url, cake)
    expect(page.get_by_test_id(BAR)).to_contain_text("'Lemon Cake' deleted")

    _delete_from_view(page, url, soup)

    expect(page.get_by_test_id(BAR)).to_contain_text("'Soup' deleted")
    expect(page.get_by_test_id(BAR)).not_to_contain_text("Lemon Cake")
    expect(_rows(page)).to_have_count(0)
    page.get_by_test_id("undo-button").click()
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page)).to_contain_text("Soup")
    status = page.request.post(f"{url}/api/recipes/{cake}/restore").status
    assert status == 410
    page.close()


def test_undo_after_same_name_saved_restores_as_lemon_cake_2(
    browser: Browser, served: tuple[str, Any], make_recipe: Callable[[str], int]
) -> None:
    url, _ = served
    cake = make_recipe("Lemon Cake")
    page = _open(browser, url)
    _delete_from_view(page, url, cake)
    make_recipe("Lemon Cake")
    page.goto(url)  # bar resumes from session storage
    expect(page.get_by_test_id(BAR)).to_contain_text("'Lemon Cake' deleted")

    page.get_by_test_id("undo-button").click()

    expect(page.get_by_test_id(BAR)).to_have_text(
        "'Lemon Cake' is back as 'Lemon Cake (2)' because another recipe now has its name"
    )
    expect(_rows(page)).to_have_count(2)
    expect(page.locator(".row-title", has_text="Lemon Cake (2)")).to_be_visible()
    page.close()


def test_s04_undo_after_other_tab_delete_names_the_purged_recipe(
    browser: Browser, served: tuple[str, Any], make_recipe: Callable[[str], int]
) -> None:
    url, _ = served
    cake = make_recipe("Lemon Cake")
    soup = make_recipe("Soup")
    first = _open(browser, url)
    _delete_from_view(first, url, cake)
    second = _open(browser, url)
    _delete_from_view(second, url, soup)  # purges the first delete's row

    first.get_by_test_id("undo-button").click()

    expect(first.get_by_test_id(BAR)).to_have_text("Too late to undo; 'Lemon Cake' is gone")
    first.close()
    second.close()
