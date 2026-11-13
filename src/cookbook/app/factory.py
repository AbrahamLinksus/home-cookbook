"""Composition root: the only place that builds adapters and services (LLD §6.1)."""

from importlib.metadata import PackageNotFoundError, version

from flask import Flask

from cookbook.adapters.clock import SystemClock
from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.ports import Clock
from cookbook.services.backup.service import BackupService
from cookbook.services.finder import RecipeFinder
from cookbook.services.keeper import RecipeKeeper
from cookbook.web import Services, api, errors, guard, pages

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _app_version() -> str:
    try:
        return version("home-cookbook")
    except PackageNotFoundError:  # pragma: no cover - running from an uninstalled checkout
        return "0.0.0"


def create_app(settings: Settings, clock: Clock | None = None) -> Flask:
    clock = clock or SystemClock()
    repo = SqliteRecipeRepository(settings.db_path)
    repo.init_schema()

    app = Flask("cookbook", template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.extensions["cookbook"] = Services(
        keeper=RecipeKeeper(repo, clock, settings.undo_seconds),
        finder=RecipeFinder(repo),
        backup=BackupService(repo, clock, _app_version()),
    )
    guard.register(app)
    errors.register(app)
    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp)
    return app
