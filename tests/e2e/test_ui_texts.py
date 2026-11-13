"""Browser texts come from web/messages.py via base.html (m-9)."""

from playwright.sync_api import Browser, expect

from cookbook.web import messages

PHONE = {"width": 390, "height": 844}


def test_undo_bar_shows_texts_from_messages(browser: Browser, live_url: str) -> None:
    page = browser.new_page(viewport=PHONE)
    page.goto(live_url)

    page.evaluate(
        "async () => (await import('/static/js/undo.js')).startUndo(7, \"Gran's Soup\", 10)"
    )

    expect(page.get_by_test_id("undo-bar")).to_contain_text("'Gran's Soup' deleted")
    expect(page.get_by_test_id("undo-button")).to_have_text(messages.UI_TEXTS["undo"])
    page.close()


def test_network_failure_message_comes_from_messages(browser: Browser, live_url: str) -> None:
    page = browser.new_page(viewport=PHONE)
    page.goto(live_url)
    page.route("**/api/**", lambda route: route.abort())

    result = page.evaluate(
        "async () => (await import('/static/js/api.js')).api('GET', '/api/anything')"
    )

    assert result == {
        "status": 0,
        "data": {"error": "network", "message": messages.UI_TEXTS["network"]},
    }
    page.close()
