"""Shared pytest fixtures."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from cookbook.app.config import Settings
from cookbook.app.factory import create_app
from cookbook.domain.models import Ingredient, NewRecipe, RecipeDraft

START = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)


class FakeClock:
    """A Clock whose time only moves when the test says so."""

    def __init__(self, now: datetime = START) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(db_path=tmp_path / "data" / "cookbook.db")


@pytest.fixture
def app(settings: Settings, clock: FakeClock) -> Flask:
    flask_app = create_app(settings, clock=clock)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def new_recipe() -> Callable[..., NewRecipe]:
    def make(title: str = "Pancakes", *, favourite: bool = False) -> NewRecipe:
        draft = RecipeDraft(
            title=title,
            servings=4,
            ingredients=(
                Ingredient("2", "cups", "flour"),
                Ingredient(None, "", "salt, to taste"),
                Ingredient("1 1/2", "tsp", "cinnamon"),
            ),
            steps=("Mix", "Preheat oven to 200°C", "Bake"),
        )
        return NewRecipe(draft, favourite, START, START)

    return make
