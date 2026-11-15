"""List, view and edit at 390 px and 1280 px: no sideways scroll, desktop grid, 44 px taps.

SPEC §12 / T-10 (US-02, US-07, S-03, S-09). Screenshots go to `tmp_path`, or to the folder in
`COOKBOOK_TEST_SHOTS` (e.g. `COOKBOOK_TEST_SHOTS=.results/T-10`) when evidence is wanted.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Response, expect

PHONE = {"width": 390, "height": 844}
LAPTOP = {"width": 1280, "height": 800}
SIZES = [("mobile", PHONE), ("desktop", LAPTOP)]
PIE = "Grandma's Apple Pie"
COOKIES = "Oat Cookies"
MIN_TAP = 44
BUTTONS = "button, a.btn, summary, .menu-item, input[type=submit], a.row-link, .toggle span"
LONG_NAME = "extra-long-ingredient-name-that-must-wrap-nicely-on-a-narrow-phone-screen"
Seeded = tuple[BrowserContext, str, int]


def _undersized(page: Page) -> list[str]:
    return page.evaluate(
        """(sel) => [...document.querySelectorAll(sel)]
          .map(e => [e, e.getBoundingClientRect().height])
          .filter(([e, h]) => h > 0 && h < 44 && getComputedStyle(e).visibility !== 'hidden')
          .map(([e, h]) => (e.dataset.testid || e.className || e.tagName) + ':' + h)""",
        BUTTONS,
    )


def _scroll_width(page: Page) -> int:
    return int(page.evaluate("document.documentElement.scrollWidth"))


def _display(page: Page, selector: str) -> str:
    return str(page.evaluate(f"getComputedStyle(document.querySelector('{selector}')).display"))


def _heights(page: Page, test_id: str) -> list[float]:
    return page.get_by_test_id(test_id).evaluate_all(
        "els => els.map(e => e.getBoundingClientRect().height)"
    )


def _is_put_favourite(response: Response) -> bool:
    return response.request.method == "PUT" and response.url.endswith("/favourite")


def _star(page: Page, title: str) -> None:
    """Star a row and wait until the server has stored it."""
    star = page.get_by_test_id("recipe-row").filter(has_text=title).get_by_test_id("star")
    with page.expect_response(_is_put_favourite) as put:
        star.click()
    assert put.value.ok
    expect(star).to_have_attribute("aria-pressed", "true")


@pytest.fixture
def shots(tmp_path: Path) -> Path:
    folder = Path(os.environ.get("COOKBOOK_TEST_SHOTS") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@pytest.fixture
def seeded(browser: Browser, live_url: str, seed: Callable[..., int]) -> Iterator[Seeded]:
    ctx = browser.new_context()
    rid = seed(
        ctx,
        live_url,
        PIE,
        servings=8,
        ingredients=[
            {"amount": "1", "unit": "cup", "name": LONG_NAME},
            {"amount": None, "unit": "", "name": "salt"},
        ],
        steps=["Bake it for a long time until the whole kitchen smells wonderful."],
    )
    seed(ctx, live_url, COOKIES)
    yield ctx, live_url, rid
    ctx.close()


@pytest.mark.parametrize(("label", "size"), SIZES)
def test_three_screens_at_size_fit_and_have_tall_buttons(
    seeded: Seeded, shots: Path, label: str, size: dict[str, int]
) -> None:
    ctx, url, rid = seeded
    page = ctx.new_page()
    page.set_viewport_size(size)  # type: ignore[arg-type]
    screens = {"list": url, "view": f"{url}/recipes/{rid}", "edit": f"{url}/recipes/{rid}/edit"}
    grids = {"view": ".view-cols", "edit": ".edit-cols"}
    for name, address in screens.items():
        page.goto(address)
        page.wait_for_load_state("networkidle")
        if name == "view":
            page.get_by_test_id("servings-down").click()
            expect(page.get_by_test_id("reset-scale")).to_be_visible()
        if name == "edit":
            expect(page.get_by_test_id("ingredient-row")).to_have_count(2)
        page.get_by_test_id("menu-button").click()
        assert _undersized(page) == [], f"{name} {label}"
        page.get_by_test_id("menu-button").click()
        if label == "mobile":
            assert _scroll_width(page) <= PHONE["width"], f"{name} sideways scroll"
        elif name in grids:
            assert _display(page, grids[name]) == "grid", name
        page.screenshot(path=str(shots / f"{name}-{label}.png"), full_page=True)
    page.close()


@pytest.mark.parametrize(("label", "size"), SIZES)
def test_list_with_star_and_undo_bar_at_size_has_tall_buttons(
    seeded: Seeded, label: str, size: dict[str, int]
) -> None:
    ctx, url, rid = seeded
    page = ctx.new_page()
    page.set_viewport_size(size)  # type: ignore[arg-type]
    page.goto(url)
    _star(page, PIE)
    page.reload()
    expect(page.get_by_test_id("star")).to_have_count(2)
    expect(page.locator("h2.group")).to_have_text(["★ Favourites", "All recipes (A\u2013Z)"])
    stars = page.get_by_test_id("star").evaluate_all(
        "els => els.map(e => e.getBoundingClientRect())"
    )
    assert all(r["height"] >= MIN_TAP and r["width"] >= MIN_TAP for r in stars)
    assert _undersized(page) == [], f"list with favourite {label}"
    if label == "mobile":
        assert _scroll_width(page) <= PHONE["width"]
    else:  # desktop list is a centred column, not full width
        assert page.locator("#recipe-list").bounding_box()["width"] <= 720  # type: ignore[index]
    page.goto(f"{url}/recipes/{rid}")
    page.get_by_test_id("delete").click()
    page.wait_for_url(f"{url}/")
    expect(page.get_by_test_id("undo-button")).to_be_visible()
    assert _undersized(page) == [], f"undo bar {label}"
    assert min(_heights(page, "undo-button")) >= MIN_TAP
    if label == "mobile":
        assert _scroll_width(page) <= PHONE["width"]
    page.close()


@pytest.mark.parametrize(("label", "size"), SIZES)
def test_conflict_dialog_at_size_has_tall_buttons(
    seeded: Seeded, label: str, size: dict[str, int]
) -> None:
    ctx, url, rid = seeded
    mine, theirs = ctx.new_page(), ctx.new_page()
    mine.set_viewport_size(size)  # type: ignore[arg-type]
    for page in (mine, theirs):
        page.goto(f"{url}/recipes/{rid}/edit")
        expect(page.get_by_test_id("ingredient-row")).to_have_count(2)
    theirs.get_by_test_id("title-input").fill("Changed elsewhere")
    theirs.get_by_test_id("save").click()
    theirs.wait_for_url(f"{url}/recipes/{rid}")
    mine.get_by_test_id("title-input").fill("Changed here")
    mine.get_by_test_id("save").click()
    expect(mine.get_by_test_id("conflict-dialog")).to_be_visible()
    for tid in ("reload-theirs", "keep-mine"):
        expect(mine.get_by_test_id(tid)).to_be_visible()
        assert _heights(mine, tid) and min(_heights(mine, tid)) >= MIN_TAP, tid
    assert _undersized(mine) == [], f"conflict {label}"
    if label == "mobile":
        assert _scroll_width(mine) <= PHONE["width"]
    mine.close()
    theirs.close()


@pytest.mark.parametrize(
    ("screen", "tools"),
    [
        ("edit", ("ingredient-up", "ingredient-down", "ingredient-remove", "step-up")),
        ("edit", ("step-down", "step-remove", "add-ingredient", "add-step", "save", "cancel")),
        ("view", ("star", "edit", "delete", "servings-down", "servings-up", "reset-scale")),
        ("view", ("back",)),
    ],
)
def test_phone_screen_tools_are_present_and_tall(
    seeded: Seeded, screen: str, tools: tuple[str, ...]
) -> None:
    ctx, url, rid = seeded
    page = ctx.new_page()
    page.set_viewport_size(PHONE)  # type: ignore[arg-type]
    page.goto(f"{url}/recipes/{rid}" + ("/edit" if screen == "edit" else ""))
    if screen == "view":
        page.get_by_test_id("servings-up").click()  # shows Reset
        expect(page.get_by_test_id("reset-scale")).to_be_visible()
    else:
        expect(page.get_by_test_id("ingredient-row")).to_have_count(2)
    for tid in tools:
        heights = _heights(page, tid)
        assert heights, f"{tid} missing"
        assert min(heights) >= MIN_TAP, (tid, heights)
    page.close()


def test_list_heading_with_search_says_matches_otherwise_all_recipes(
    browser: Browser, live_url: str, seed: Callable[..., int]
) -> None:
    ctx = browser.new_context(viewport=PHONE)
    seed(ctx, live_url, PIE)
    seed(ctx, live_url, COOKIES)
    page = ctx.new_page()
    headings = page.locator("h2.group")
    page.goto(live_url)
    expect(headings).to_have_text(["All recipes (A\u2013Z)"])
    page.get_by_test_id("search-input").fill("pie")
    page.get_by_test_id("search-input").press("Enter")
    expect(page.get_by_test_id("recipe-row")).to_have_count(1)
    expect(headings).to_have_text(["Matches (A\u2013Z)"])
    page.goto(live_url)
    _star(page, PIE)  # a starred match gets its own group above the Matches group
    page.get_by_test_id("search-input").fill("e")
    page.get_by_test_id("search-input").press("Enter")
    expect(page.get_by_test_id("recipe-row")).to_have_count(2)
    expect(headings).to_have_text(["★ Favourites", "Matches (A\u2013Z)"])
    page.get_by_test_id("search-input").fill("zzz")
    page.get_by_test_id("search-input").press("Enter")
    expect(page.get_by_test_id("no-matches")).to_be_visible()
    expect(headings).to_have_count(0)
    ctx.close()
