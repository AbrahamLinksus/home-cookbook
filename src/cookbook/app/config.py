"""Settings read from the environment (LLD §0.5). The only module that reads env vars."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PORT = 8765
DEFAULT_UNDO_SECONDS = 10
MAX_PORT = 65535


class InvalidSettingsError(ValueError):
    """An environment variable holds a value the app cannot use."""


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    host: str = "0.0.0.0"
    port: int = DEFAULT_PORT
    undo_seconds: int = DEFAULT_UNDO_SECONDS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        values = os.environ if env is None else env

        def get(name: str) -> str | None:
            return values.get(name) or None

        db = get("COOKBOOK_DB")
        return cls(
            db_path=Path(db) if db else _default_db_path(values),
            host=get("COOKBOOK_HOST") or "0.0.0.0",
            port=_whole_number("COOKBOOK_PORT", get("COOKBOOK_PORT"), DEFAULT_PORT, 1, MAX_PORT),
            undo_seconds=_whole_number(
                "COOKBOOK_UNDO_SECONDS",
                get("COOKBOOK_UNDO_SECONDS"),
                DEFAULT_UNDO_SECONDS,
                1,
                3600,
            ),
        )


def _default_db_path(env: Mapping[str, str]) -> Path:
    data_home = env.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base / "home-cookbook" / "cookbook.db"


def _whole_number(name: str, text: str | None, default: int, low: int, high: int) -> int:
    if text is None:
        return default
    digits = text.strip()
    in_range = digits.isascii() and digits.isdigit() and len(digits.lstrip("0")) <= len(str(high))
    if not in_range or not low <= int(digits) <= high:
        raise InvalidSettingsError(
            f"{name} must be a whole number from {low} to {high} (got {text!r})"
        )
    return int(digits)
