"""Edit a recipe from a laptop and a phone at once (US-01, US-03, S-03)."""

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
    def make(title: str = "Lemon Cake", amount: str = "2", step: str = "Bake at 220°C") -> int:
        recipe = {
            "title": title,
            "servings": 6,
            "ingredients": [{"amount": amount, "unit": "cups", "name": "flour"}],
            "steps": [step],
        }
        response = laptop_ctx.request.post(f"{url}/api/recipes", data={"recipe": recipe})
        assert response.ok, response.text()
        return int(response.json()["id"])

    return make


def _edit(ctx: BrowserContext, url: str, rid: int) -> tuple[Page, list[tuple[str, str]]]:
    page = ctx.new_page()
    dialogs: list[tuple[str, str]] = []
    page.on("dialog", lambda d: (dialogs.append((d.type, d.message)), d.accept()))
    page.goto(f"{url}/recipes/{rid}/edit")
    expect(page.get_by_test_id("ingredient-row")).not_to_have_count(0)  # edit.js filled the form
    return page, dialogs


DIALOG_BUTTONS = ("reload-theirs", "keep-mine", "save-as-new", "discard")


def _expect_only_buttons(page: Page, shown: tuple[str, ...]) -> None:
    """The dialog shows its own pair of choices and none of the other kind's."""
    for testid in DIALOG_BUTTONS:
        button = page.get_by_test_id(testid)
        if testid in shown:
            expect(button).to_be_visible()
        else:
            expect(button).to_be_hidden()


def _set_step(page: Page, text: str) -> None:
    page.get_by_test_id("step-rows").locator("textarea").first.fill(text)


def _phone_changes_temperature(ctx: BrowserContext, url: str, rid: int) -> None:
    page, _ = _edit(ctx, url, rid)
    _set_step(page, "Bake at 180°C")
    page.get_by_test_id("save").click()
    page.wait_for_url(f"{url}/recipes/{rid}")
    expect(page.get_by_test_id("step")).to_have_text(["Bake at 180°C"])
    page.close()


def _read_steps(ctx: BrowserContext, url: str, rid: int) -> list[str]:
    page = ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")
    steps = [t.strip() for t in page.get_by_test_id("step").all_inner_texts()]
    page.close()
    return steps


def _list_titles(ctx: BrowserContext, url: str) -> list[str]:
    page = ctx.new_page()
    page.goto(url)
    titles = [t.strip() for t in page.get_by_test_id("recipe-row").all_inner_texts()]
    page.close()
    return titles


def test_edit_amount_saves_and_shows_in_read_view_no_prompt(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page, dialogs = _edit(laptop_ctx, url, rid)
    amount = page.get_by_test_id("ingredient-row").first.locator('[data-field="amount"]')
    expect(amount).to_have_value("2")

    amount.fill("2½")
    page.get_by_test_id("save").click()

    page.wait_for_url(f"{url}/recipes/{rid}")
    expect(page.get_by_test_id("ingredient-line")).to_have_text(["2½ cups flour"])
    assert dialogs == []


def test_saving_with_own_title_works(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page, _ = _edit(laptop_ctx, url, rid)
    page.get_by_test_id("save").click()
    page.wait_for_url(f"{url}/recipes/{rid}")
    expect(page.get_by_test_id("recipe-title")).to_have_text("Lemon Cake")


def test_renaming_to_another_recipes_title_shows_message_under_title(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    make_recipe("Pancakes")
    rid = make_recipe()
    page, _ = _edit(laptop_ctx, url, rid)

    page.get_by_test_id("title-input").fill(" pancakes ")
    page.get_by_test_id("save").click()

    expect(page.get_by_test_id("title-error")).to_contain_text(
        "You already have a recipe called 'Pancakes'. Please choose another name"
    )
    assert page.url.endswith("/edit")
    expect(page.get_by_test_id("conflict-dialog")).to_be_hidden()
    page.get_by_test_id("title-input").fill("Lemon Cake 2")
    page.get_by_test_id("save").click()
    page.wait_for_url(f"{url}/recipes/{rid}")
    expect(page.get_by_test_id("recipe-title")).to_have_text("Lemon Cake 2")


def test_changed_elsewhere_reload_theirs_drops_typing_no_prompt(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    laptop, dialogs = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Laptop rewrite at 220°C")
    _phone_changes_temperature(phone_ctx, url, rid)

    laptop.get_by_test_id("save").click()

    expect(laptop.get_by_test_id("conflict-message")).to_have_text(CHANGED)
    expect(laptop.get_by_test_id("reload-theirs")).to_have_text("Reload theirs")
    expect(laptop.get_by_test_id("keep-mine")).to_have_text("Keep mine")
    _expect_only_buttons(laptop, shown=("reload-theirs", "keep-mine"))
    expect(laptop.get_by_test_id("conflict-dialog")).to_be_visible()
    assert _read_steps(phone_ctx, url, rid) == ["Bake at 180°C"]  # nothing saved yet
    laptop.get_by_test_id("reload-theirs").click()
    laptop.wait_for_url(f"{url}/recipes/{rid}")
    expect(laptop.get_by_test_id("step")).to_have_text(["Bake at 180°C"])
    assert "Laptop rewrite" not in laptop.content()
    assert dialogs == []


def test_changed_elsewhere_keep_mine_saves_laptop_version_no_prompt(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    laptop, dialogs = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Laptop rewrite at 200°C")
    _phone_changes_temperature(phone_ctx, url, rid)
    laptop.get_by_test_id("save").click()
    expect(laptop.get_by_test_id("conflict-message")).to_have_text(CHANGED)

    laptop.get_by_test_id("keep-mine").click()

    laptop.wait_for_url(f"{url}/recipes/{rid}")
    expect(laptop.get_by_test_id("step")).to_have_text(["Laptop rewrite at 200°C"])
    assert dialogs == []


def test_deleted_elsewhere_keeps_typing_and_saves_nothing(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    laptop, _ = _edit(laptop_ctx, url, rid)
    laptop.get_by_test_id("title-input").fill("Lemon Cake v2")
    _set_step(laptop, "Typed on laptop")
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}")
    phone.get_by_test_id("delete").click()
    phone.wait_for_url(f"{url}/")

    laptop.get_by_test_id("save").click()

    expect(laptop.get_by_test_id("conflict-message")).to_have_text(DELETED)
    expect(laptop.get_by_test_id("save-as-new")).to_have_text("Save as new")
    expect(laptop.get_by_test_id("discard")).to_have_text("Discard my changes")
    _expect_only_buttons(laptop, shown=("save-as-new", "discard"))
    expect(laptop.get_by_test_id("deleted-dialog")).to_be_visible()
    assert laptop.url.endswith("/edit")
    expect(laptop.get_by_test_id("title-input")).to_have_value("Lemon Cake v2")
    expect(laptop.locator("textarea").first).to_have_value("Typed on laptop")
    assert _list_titles(phone_ctx, url) == []  # nothing saved before a choice


def _delete_then_laptop_save(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, rid: int
) -> tuple[Page, list[tuple[str, str]]]:
    laptop, dialogs = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Typed on laptop")
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}")
    phone.get_by_test_id("delete").click()
    phone.wait_for_url(f"{url}/")
    phone.close()
    laptop.get_by_test_id("save").click()
    expect(laptop.get_by_test_id("conflict-message")).to_have_text(DELETED)
    return laptop, dialogs


def test_deleted_elsewhere_save_as_new_after_window_ends(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    served: tuple[str, Any],
    make_recipe: Callable[..., int],
) -> None:
    url, clock = served
    rid = make_recipe()
    laptop, dialogs = _delete_then_laptop_save(laptop_ctx, phone_ctx, url, rid)
    clock.advance(13)

    laptop.get_by_test_id("save-as-new").click()

    laptop.wait_for_url(lambda u: u != f"{url}/recipes/{rid}/edit")
    new_id = int(laptop.url.rsplit("/", 1)[1])
    assert new_id != rid
    expect(laptop.get_by_test_id("recipe-title")).to_have_text("Lemon Cake")
    expect(laptop.get_by_test_id("step")).to_have_text(["Typed on laptop"])
    titles = _list_titles(phone_ctx, url)
    assert len(titles) == 1 and titles[0].startswith("Lemon Cake") and "6 servings" in titles[0]
    assert dialogs == []


def test_deleted_elsewhere_save_as_new_inside_undo_window_is_reported(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    served: tuple[str, Any],
    make_recipe: Callable[..., int],
) -> None:
    """Title clash with a recipe still waiting out its Undo window: record what happens."""
    url, _ = served
    rid = make_recipe()
    laptop, _ = _delete_then_laptop_save(laptop_ctx, phone_ctx, url, rid)

    laptop.get_by_test_id("save-as-new").click()

    laptop.wait_for_url(lambda u: u != f"{url}/recipes/{rid}/edit", timeout=5000)
    expect(laptop.get_by_test_id("recipe-title")).to_have_text("Lemon Cake")
    expect(laptop.get_by_test_id("step")).to_have_text(["Typed on laptop"])


def test_undo_after_save_as_new_brings_old_one_back_renamed(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    """The phone's Undo bar outlives the laptop's "Save as new": neither recipe is lost."""
    rid = make_recipe()
    laptop, _ = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Typed on laptop")
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}")
    phone.get_by_test_id("delete").click()
    phone.wait_for_url(f"{url}/")
    laptop.get_by_test_id("save").click()
    expect(laptop.get_by_test_id("conflict-message")).to_have_text(DELETED)
    laptop.get_by_test_id("save-as-new").click()
    laptop.wait_for_url(lambda u: u != f"{url}/recipes/{rid}/edit")

    phone.get_by_test_id("undo-button").click()

    expect(phone.get_by_test_id("undo-bar")).to_contain_text(
        "'Lemon Cake' is back as 'Lemon Cake (2)'"
    )
    expect(phone.get_by_test_id("recipe-row")).to_have_count(2)
    assert _read_steps(phone_ctx, url, rid) == ["Bake at 220°C"]


def test_failed_save_as_new_keeps_posting_and_never_overwrites_restored_recipe(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    """LLD §3.5: once "Save as new" is chosen, later Saves create a recipe, never PUT."""
    rid = make_recipe()
    laptop, _ = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Typed on laptop")
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}")
    phone.get_by_test_id("delete").click()
    phone.wait_for_url(f"{url}/")
    laptop.get_by_test_id("save").click()
    expect(laptop.get_by_test_id("conflict-message")).to_have_text(DELETED)
    phone.get_by_test_id("undo-button").click()
    expect(phone.get_by_test_id("recipe-row")).to_have_count(1)

    laptop.get_by_test_id("save-as-new").click()
    expect(laptop.get_by_test_id("title-error")).to_contain_text("Lemon Cake")
    expect(laptop.get_by_test_id("deleted-dialog")).to_be_hidden()
    laptop.get_by_test_id("title-input").fill("Lemon Cake laptop")
    with laptop.expect_request(lambda r: "/api/recipes" in r.url) as sent:
        laptop.get_by_test_id("save").click()

    assert sent.value.method == "POST"
    laptop.wait_for_url(lambda u: not u.endswith("/edit"))
    new_id = int(laptop.url.rsplit("/", 1)[1])
    assert new_id != rid
    expect(laptop.get_by_test_id("recipe-title")).to_have_text("Lemon Cake laptop")
    assert _read_steps(phone_ctx, url, rid) == ["Bake at 220°C"]  # restored one untouched
    assert len(_list_titles(phone_ctx, url)) == 2


def test_double_tap_save_as_new_sends_one_request(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    laptop, _ = _delete_then_laptop_save(laptop_ctx, phone_ctx, url, rid)
    posts: list[str] = []
    laptop.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)

    laptop.get_by_test_id("save-as-new").evaluate("b => { b.click(); b.click(); }")

    laptop.wait_for_url(lambda u: not u.endswith("/edit"))
    assert len(posts) == 1
    assert len(_list_titles(phone_ctx, url)) == 1


def test_deleted_elsewhere_discard_goes_to_list_and_recipe_stays_deleted(
    laptop_ctx: BrowserContext,
    phone_ctx: BrowserContext,
    served: tuple[str, Any],
    make_recipe: Callable[..., int],
) -> None:
    url, clock = served
    rid = make_recipe()
    laptop, dialogs = _delete_then_laptop_save(laptop_ctx, phone_ctx, url, rid)

    laptop.get_by_test_id("discard").click()

    laptop.wait_for_url(f"{url}/")
    clock.advance(13)
    assert _list_titles(phone_ctx, url) == []
    assert dialogs == []


def test_phone_undo_before_laptop_save_lets_save_work_as_normal(
    laptop_ctx: BrowserContext, phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    laptop, _ = _edit(laptop_ctx, url, rid)
    _set_step(laptop, "Typed on laptop")
    phone = phone_ctx.new_page()
    phone.goto(f"{url}/recipes/{rid}")
    phone.get_by_test_id("delete").click()
    phone.wait_for_url(f"{url}/")
    phone.get_by_test_id("undo-button").click()
    expect(phone.get_by_test_id("recipe-row")).to_have_count(1)

    laptop.get_by_test_id("save").click()

    laptop.wait_for_url(f"{url}/recipes/{rid}")
    expect(laptop.get_by_test_id("step")).to_have_text(["Typed on laptop"])


def test_cancel_with_unsaved_changes_asks_and_dismiss_stays(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page = laptop_ctx.new_page()
    dialogs: list[tuple[str, str]] = []
    page.on("dialog", lambda d: (dialogs.append((d.type, d.message)), d.dismiss()))
    page.goto(f"{url}/recipes/{rid}/edit")
    _set_step(page, "Changed")

    page.get_by_test_id("cancel").click()

    assert dialogs == [("confirm", "Discard changes?")]
    assert page.url.endswith("/edit")


def test_cancel_with_unsaved_changes_accept_leaves(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page, dialogs = _edit(laptop_ctx, url, rid)
    _set_step(page, "Changed")

    page.get_by_test_id("cancel").click()

    page.wait_for_url(f"{url}/")
    assert dialogs == [("confirm", "Discard changes?")]
    assert _read_steps(laptop_ctx, url, rid) == ["Bake at 220°C"]


def test_cancel_without_changes_does_not_ask(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page, dialogs = _edit(laptop_ctx, url, rid)
    page.get_by_test_id("cancel").click()
    page.wait_for_url(f"{url}/")
    assert dialogs == []


def test_leaving_page_with_unsaved_changes_prompts_but_not_when_clean(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    other = laptop_ctx.new_page()  # keeps the event loop pumping while the tab closes
    dirty, dirty_dialogs = _edit(laptop_ctx, url, rid)
    dirty.get_by_test_id("step-rows").locator("textarea").first.click()  # user activation
    dirty.keyboard.type(" extra")
    dirty.close(run_before_unload=True)
    other.wait_for_timeout(500)
    assert [d[0] for d in dirty_dialogs] == ["beforeunload"]

    clean, clean_dialogs = _edit(laptop_ctx, url, rid)
    clean.close(run_before_unload=True)
    other.wait_for_timeout(500)
    assert clean_dialogs == []


def test_edit_button_on_read_view_opens_edit_form_and_delete_undo_still_work(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page = laptop_ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")

    page.get_by_test_id("edit").click()

    page.wait_for_url(f"{url}/recipes/{rid}/edit")
    expect(page.get_by_test_id("title-input")).to_have_value("Lemon Cake")
    page.goto(f"{url}/recipes/{rid}")
    page.get_by_test_id("delete").click()
    page.wait_for_url(f"{url}/")
    expect(page.get_by_test_id("recipe-row")).to_have_count(0)
    page.get_by_test_id("undo-button").click()
    expect(page.get_by_test_id("recipe-row")).to_have_count(1)


def test_scaler_on_read_view_still_works_after_an_edit(
    laptop_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe(amount="2")
    page, _ = _edit(laptop_ctx, url, rid)
    page.get_by_test_id("save").click()
    page.wait_for_url(f"{url}/recipes/{rid}")

    page.get_by_test_id("servings-up").click()

    expect(page.get_by_test_id("ingredient-line")).to_have_text(["2⅓ cups flour"])


def test_read_view_header_with_four_controls_fits_phone_width(
    phone_ctx: BrowserContext, url: str, make_recipe: Callable[..., int]
) -> None:
    rid = make_recipe()
    page = phone_ctx.new_page()
    page.goto(f"{url}/recipes/{rid}")

    for testid in ("back", "edit", "delete", "menu-button"):
        expect(page.get_by_test_id(testid)).to_be_in_viewport()
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
    brand = page.locator(".brand").bounding_box()
    assert brand is not None and brand["height"] < 30  # one line, not one letter per line
