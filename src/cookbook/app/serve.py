"""Start the app on the home network (LLD §0.6)."""

import contextlib
import logging
import signal
import socket
import sys
from types import FrameType

from waitress.server import create_server

from cookbook.app.config import InvalidSettingsError, Settings
from cookbook.app.factory import MAX_UPLOAD_BYTES, create_app

logger = logging.getLogger("cookbook")

THREADS = 4
EXIT_CANNOT_START = 2  # bad settings, port in use, data file unusable
_PROBE_ADDRESS = ("192.0.2.1", 9)  # documentation address; a UDP connect sends nothing


def lan_ip() -> str:
    """The address phones and laptops on the home network can use; 127.0.0.1 if unknown."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(_PROBE_ADDRESS)
            return str(probe.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def banner(port: int) -> str:
    return (
        "Home Cookbook is running. On your phone or laptop open: "
        f"http://{lan_ip()}:{port} (or http://{socket.gethostname()}.local:{port})"
    )


def _stop(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def _cannot_start(error: Exception) -> SystemExit:
    sys.stderr.write(f"Home Cookbook cannot start: {error}\n")
    return SystemExit(EXIT_CANNOT_START)


def _serve(settings: Settings) -> None:
    try:
        server = create_server(
            create_app(settings),
            host=settings.host,
            port=settings.port,
            threads=THREADS,
            max_request_body_size=MAX_UPLOAD_BYTES,
        )
    except OSError as error:  # port in use, data folder not writable, unknown host
        raise _cannot_start(error) from error
    logger.info(banner(settings.port))
    server.run()


def main() -> None:
    try:
        settings = Settings.from_env()
    except InvalidSettingsError as error:
        raise _cannot_start(error) from error
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Stop cleanly even if asked to stop while starting up (the port listens before the banner).
    signal.signal(signal.SIGTERM, _stop)
    with contextlib.suppress(KeyboardInterrupt):
        _serve(settings)
    logger.info("Home Cookbook stopped")
