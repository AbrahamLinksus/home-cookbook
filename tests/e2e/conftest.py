"""Start the app on a free port for browser tests and always stop it."""

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from werkzeug.serving import BaseWSGIServer, make_server

from cookbook.app.config import Settings
from cookbook.app.factory import create_app


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
