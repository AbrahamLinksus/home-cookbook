"""BackupService.export_all with the in-memory repository fake and a fixed clock (T-03)."""

import json
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any

from cookbook.domain.models import NewRecipe, Recipe
from cookbook.domain.ports import Clock
from cookbook.services.backup.service import BackupService


class MemoryRepo:
    """Just enough of RecipeRepository for export: live recipes, some pending deletion."""

    def __init__(self) -> None:
        self.recipes: list[Recipe] = []

    def add(self, new: NewRecipe) -> Recipe:
        recipe = Recipe(
            len(self.recipes) + 1, new.draft.title, new.draft.servings, new.draft.ingredients,
            new.draft.steps, new.favourite, 1, new.created_at, new.updated_at, None,
        )  # fmt: skip
        self.recipes.append(recipe)
        return recipe

    def mark_deleted(self, recipe_id: int, now: datetime) -> None:
        self.recipes = [
            replace(r, deleted_at=now) if r.id == recipe_id else r for r in self.recipes
        ]

    def list_live(self) -> list[Recipe]:
        return [r for r in self.recipes if r.deleted_at is None]

    def add_many(self, items: Sequence[NewRecipe]) -> None:  # pragma: no cover
        raise NotImplementedError


def _export(repo: MemoryRepo, clock: Clock) -> tuple[str, dict[str, Any], str]:
    result = BackupService(repo, clock, "1.2.3").export_all()  # type: ignore[arg-type]
    text = result.content.decode("utf-8")
    return result.filename, json.loads(text), text


def test_export_holds_every_field_in_order(
    new_recipe: Callable[..., NewRecipe], clock: Clock
) -> None:
    repo = MemoryRepo()
    repo.add(new_recipe("Crème Brûlée", favourite=True))

    _, doc, text = _export(repo, clock)

    assert doc["format"] == "home-cookbook-export"
    assert doc["format_version"] == 1
    assert doc["app_version"] == "1.2.3"
    assert doc["exported_at"] == "2026-11-13T09:00:00Z"
    assert doc["recipe_count"] == 1
    assert doc["recipes"][0] == {
        "title": "Crème Brûlée",
        "servings": 4,
        "favourite": True,
        "ingredients": [
            {"amount": "2", "unit": "cups", "name": "flour"},
            {"amount": None, "unit": "", "name": "salt, to taste"},
            {"amount": "1 1/2", "unit": "tsp", "name": "cinnamon"},
        ],
        "steps": ["Mix", "Preheat oven to 200°C", "Bake"],
        "created_at": "2026-11-13T09:00:00Z",
        "updated_at": "2026-11-13T09:00:00Z",
    }
    assert "Crème Brûlée" in text and "200°C" in text
    assert text.startswith('{\n  "format"')


def test_filename_uses_the_local_date(clock: Clock) -> None:
    filename, _, _ = _export(MemoryRepo(), clock)

    assert filename == f"cookbook-{clock.now().astimezone():%Y-%m-%d}.json"


def test_empty_app_exports_a_valid_empty_file(clock: Clock) -> None:
    _, doc, _ = _export(MemoryRepo(), clock)

    assert doc["recipe_count"] == 0
    assert doc["recipes"] == []


def test_recipe_waiting_out_its_undo_window_is_not_exported(
    new_recipe: Callable[..., NewRecipe], clock: Clock
) -> None:
    repo = MemoryRepo()
    repo.add(new_recipe("Keep"))
    gone = repo.add(new_recipe("Going"))
    repo.mark_deleted(gone.id, clock.now())

    _, doc, _ = _export(repo, clock)

    assert [r["title"] for r in doc["recipes"]] == ["Keep"]
    assert doc["recipe_count"] == 1
