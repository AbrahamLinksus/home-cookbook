"""Starting the app for real (LLD §0.5, §0.6)."""

import os
import socket
import sqlite3  # noqa: TID251 (reads PRAGMA user_version directly)
import subprocess
import sys
import time
from pathlib import Path

import pytest

from cookbook.app.config import InvalidSettingsError, Settings


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _run(env_extra: dict[str, str]) -> subprocess.Popen[str]:
    env = {**os.environ, **env_extra}
    return subprocess.Popen(
        [sys.executable, "-m", "cookbook"],
        env=env,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )


def _wait_until_listening(port: int) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        except OSError:
            time.sleep(0.1)
        else:
            return
    pytest.fail("the app never started listening")


def test_serve_starts_logs_banner_creates_db_and_stops_cleanly(tmp_path: Path) -> None:
    db = tmp_path / "data" / "cookbook.db"
    port = _free_port()
    proc = _run({"COOKBOOK_DB": str(db), "COOKBOOK_PORT": str(port), "COOKBOOK_HOST": "127.0.0.1"})
    try:
        _wait_until_listening(port)
    finally:
        proc.terminate()
    _, err = proc.communicate(timeout=10)

    assert proc.returncode == 0
    assert "Home Cookbook is running. On your phone or laptop open: http://" in err
    assert f":{port}" in err
    assert "Traceback" not in err
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_serve_bad_port_exits_2_with_one_line_message(tmp_path: Path) -> None:
    proc = _run({"COOKBOOK_DB": str(tmp_path / "c.db"), "COOKBOOK_PORT": "abc"})
    _, err = proc.communicate(timeout=20)

    assert proc.returncode == 2
    assert len(err.strip().splitlines()) == 1
    assert "COOKBOOK_PORT" in err


def _assert_cannot_start(proc: subprocess.Popen[str]) -> str:
    _, err = proc.communicate(timeout=20)
    assert proc.returncode == 2
    assert "Traceback" not in err
    assert len(err.strip().splitlines()) == 1
    assert err.startswith("Home Cookbook cannot start: ")
    return err


def test_serve_port_in_use_exits_2_with_one_line_message(tmp_path: Path) -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = str(taken.getsockname()[1])
        proc = _run(
            {
                "COOKBOOK_DB": str(tmp_path / "c.db"),
                "COOKBOOK_PORT": port,
                "COOKBOOK_HOST": "127.0.0.1",
            }
        )
        err = _assert_cannot_start(proc)
    assert "in use" in err


def test_serve_unwritable_data_folder_exits_2_with_one_line_message(tmp_path: Path) -> None:
    folder = tmp_path / "locked"
    folder.mkdir(mode=0o555)
    try:
        for db in (folder / "cookbook.db", folder / "sub" / "cookbook.db"):
            proc = _run({"COOKBOOK_DB": str(db), "COOKBOOK_PORT": str(_free_port())})
            _assert_cannot_start(proc)
    finally:
        folder.chmod(0o755)


@pytest.mark.parametrize(
    ("name", "value"),
    [("COOKBOOK_PORT", "0"), ("COOKBOOK_UNDO_SECONDS", "x"), ("COOKBOOK_PORT", "9" * 5000)],
    ids=["port-zero", "undo-not-a-number", "port-5000-digits"],
)
def test_settings_from_env_invalid_value_raises(name: str, value: str) -> None:
    with pytest.raises(InvalidSettingsError, match=name):
        Settings.from_env({name: value})


def test_settings_from_env_defaults_and_overrides(tmp_path: Path) -> None:
    default = Settings.from_env({"XDG_DATA_HOME": str(tmp_path), "COOKBOOK_DB": ""})
    assert default.db_path == tmp_path / "home-cookbook" / "cookbook.db"
    assert (default.host, default.port, default.undo_seconds) == ("0.0.0.0", 8765, 10)

    custom = Settings.from_env({"COOKBOOK_PORT": "9000", "COOKBOOK_DB": str(tmp_path / "x.db")})
    assert (custom.port, custom.db_path) == (9000, tmp_path / "x.db")
