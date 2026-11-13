"""Phone-size (390px) Playwright smoke: launch, render, close, report timings."""

import time

from playwright.sync_api import sync_playwright

PHONE_WIDTH = 390
MAX_CLOSE_SECONDS = 5


def main() -> None:
    start = time.monotonic()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": PHONE_WIDTH, "height": 844})
        page.set_content("<h1>Home cookbook</h1>")
        width = page.evaluate("window.innerWidth")
        heading = page.inner_text("h1")
        close_start = time.monotonic()
        browser.close()
        close_s = time.monotonic() - close_start
    total = time.monotonic() - start
    print(f"viewport={width}px heading={heading!r}")
    print(f"close={close_s:.2f}s total={total:.2f}s")
    assert width == PHONE_WIDTH and heading == "Home cookbook"
    assert close_s < MAX_CLOSE_SECONDS, "browser.close() too slow"


main()
