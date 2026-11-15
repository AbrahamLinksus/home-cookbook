"""Start the app for browser tests (in a thread or as `uv run cookbook`) and always stop it."""

import os
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import BrowserContext
from werkzeug.serving import BaseWSGIServer, make_server

from cookbook.app.config import Settings
from cookbook.app.factory import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HARD_DEADLINE_S = 300  # `timeout` kills the app even if pytest itself is killed
BANNER_WAIT_S = 20
START_ATTEMPTS = 3  # a free port can be taken between probing it and the app binding it
BANNER_START = "Home Cookbook is running. On your phone or laptop open: http://"


@pytest.fixture
def live_url(tmp_path: Path) -> Iterator[str]:
    app = create_app(Settings(db_path=tmp_path / "cookbook.db"))
    server: BaseWSGIServer = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def seed() -> Callable[..., int]:
    """Add a recipe through the JSON API and return its id."""

    def add(ctx: BrowserContext, url: str, title: str, **fields: Any) -> int:
        recipe = {"title": title, "servings": 4, "ingredients": [], "steps": ["Mix."], **fields}
        response = ctx.request.post(f"{url}/api/recipes", data={"recipe": recipe})
        assert response.ok, response.text()
        return int(response.json()["id"])

    return add


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", 0))  # same interface the app binds
        return int(probe.getsockname()[1])


def _stop(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()  # `timeout` passes SIGTERM on through uv to the app
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _wait_for_banner(proc: subprocess.Popen[bytes], log: Path) -> str | None:
    """The 'open:' log line, or None if the app exited first."""
    deadline = time.monotonic() + BANNER_WAIT_S
    while time.monotonic() < deadline:
        found = [ln for ln in log.read_text(errors="replace").splitlines() if "open: " in ln]
        if found:
            return found[0]
        if proc.poll() is not None:
            return None
        time.sleep(0.1)  # polling a log file: there is no event to wait on
    _stop(proc)
    pytest.fail(f"the app never printed its address:\n{log.read_text(errors='replace')}")


def _launch(db: Path, log: Path) -> tuple[subprocess.Popen[bytes], str]:
    uv = shutil.which("uv")
    assert uv, "uv is not on PATH"
    command = ["timeout", "-k", "5", str(HARD_DEADLINE_S), uv, "run", "--no-sync", "cookbook"]
    for _ in range(START_ATTEMPTS):
        env = {**os.environ, "COOKBOOK_DB": str(db)}
        env["COOKBOOK_PORT"] = str(_free_port())
        with log.open("wb") as sink:
            proc = subprocess.Popen(command, env=env, stderr=sink, cwd=PROJECT_ROOT)
        banner = _wait_for_banner(proc, log)
        if banner is not None:
            return proc, banner
        if "cannot start" not in log.read_text(errors="replace"):
            break
    pytest.fail(f"the app exited ({proc.returncode}):\n{log.read_text(errors='replace')}")


@pytest.fixture
def start_app(tmp_path: Path) -> Iterator[Callable[[str], str]]:
    """Start `timeout … uv run cookbook` on a temp data file; return the printed LAN address."""
    procs: list[subprocess.Popen[bytes]] = []

    def start(name: str) -> str:
        proc, banner = _launch(tmp_path / f"{name}.db", tmp_path / f"{name}.log")
        procs.append(proc)
        assert BANNER_START in banner
        url = banner.split("open: ", 1)[1].split()[0]
        if url.startswith("http://127."):
            pytest.skip("this machine has no LAN address, so the LAN check cannot run")
        assert "127.0.0.1" not in url and "localhost" not in url
        return url

    yield start
    for proc in procs:
        _stop(proc)
