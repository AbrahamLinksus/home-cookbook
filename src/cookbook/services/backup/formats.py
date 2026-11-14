"""Export file format, version 1 (LLD §5.1, §5.3). Import helpers arrive with the import task."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Final

from cookbook.domain.models import Ingredient, Recipe

FORMAT_MARKER: Final = "home-cookbook-export"
CURRENT_FORMAT_VERSION: Final = 1


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ingredient(item: Ingredient) -> dict[str, Any]:
    return {"amount": item.amount, "unit": item.unit, "name": item.name}


def _recipe(recipe: Recipe) -> dict[str, Any]:
    return {
        "title": recipe.title,
        "servings": recipe.servings,
        "favourite": recipe.favourite,
        "ingredients": [_ingredient(item) for item in recipe.ingredients],
        "steps": list(recipe.steps),
        "created_at": _stamp(recipe.created_at),
        "updated_at": _stamp(recipe.updated_at),
    }


def to_document(
    recipes: Sequence[Recipe], exported_at: datetime, app_version: str
) -> dict[str, Any]:
    return {
        "format": FORMAT_MARKER,
        "format_version": CURRENT_FORMAT_VERSION,
        "app_version": app_version,
        "exported_at": _stamp(exported_at),
        "recipe_count": len(recipes),
        "recipes": [_recipe(recipe) for recipe in recipes],
    }
