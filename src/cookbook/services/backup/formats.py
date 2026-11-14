"""Export file format and its upgrade steps (LLD §5.1, §5.3)."""

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from cookbook.domain.errors import InvalidRecipe, NewerExportFormat, NotAnExport
from cookbook.domain.models import Ingredient, NewRecipe, Recipe
from cookbook.domain.rules import parse_draft

FORMAT_MARKER: Final = "home-cookbook-export"
CURRENT_FORMAT_VERSION: Final = 1
# n -> pure step turning a version-n document into version n+1. Steps are never edited or removed.
UPGRADES: Final[dict[int, Callable[[dict[str, Any]], dict[str, Any]]]] = {}
# v1 ingredient row: key -> accepted types; a missing key counts as "".
_INGREDIENT_TYPES: Final[dict[str, tuple[type, ...]]] = {
    "amount": (str, type(None)),
    "unit": (str,),
    "name": (str,),
}


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


def upgrade(doc: dict[str, Any]) -> dict[str, Any]:
    """Bring a document of any older version up to the current one."""
    found = doc.get("format")
    version = doc.get("format_version")
    if found != FORMAT_MARKER or not isinstance(version, int) or isinstance(version, bool):
        raise NotAnExport("missing marker or version")
    if version > CURRENT_FORMAT_VERSION:
        raise NewerExportFormat(version, CURRENT_FORMAT_VERSION)
    if version < 1:
        raise NotAnExport("version below 1")
    for step in range(version, CURRENT_FORMAT_VERSION):
        doc = UPGRADES[step](doc)
    return doc


def _moment(value: object, default: datetime) -> datetime:
    if value is None:
        return default
    if not isinstance(value, str):
        raise NotAnExport("bad date")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise NotAnExport("bad date") from error
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_str(value: object) -> bool:
    return isinstance(value, str)


def _ingredient_ok(row: object) -> bool:
    return isinstance(row, Mapping) and all(
        isinstance(row.get(key, ""), kinds) for key, kinds in _INGREDIENT_TYPES.items()
    )


def _list_of(value: object, item_ok: Callable[[object], bool]) -> bool:
    return value is None or (isinstance(value, list) and all(item_ok(item) for item in value))


def _check_types(raw: Mapping[str, object]) -> None:
    """Strict v1 field types; parse_draft is lenient (form input) and would drop or coerce."""
    ok = (
        _is_str(raw.get("title"))
        and _is_int(raw.get("servings"))
        and isinstance(raw.get("favourite", False), bool)
        and _list_of(raw.get("ingredients"), _ingredient_ok)
        and _list_of(raw.get("steps"), _is_str)
    )
    if not ok:
        raise NotAnExport("wrong field type")


def _new_recipe(raw: object, now: datetime) -> NewRecipe:
    if not isinstance(raw, Mapping):
        raise NotAnExport("recipe is not an object")
    _check_types(raw)
    favourite = bool(raw.get("favourite", False))
    try:
        draft = parse_draft(raw)
    except InvalidRecipe as error:
        raise NotAnExport(str(error)) from error
    created = _moment(raw.get("created_at"), now)
    updated = _moment(raw.get("updated_at"), created)
    return NewRecipe(draft, favourite, created, updated)


def from_document(doc: dict[str, Any], now: datetime) -> list[NewRecipe]:
    """Recipes of an upgraded document; NotAnExport on any bad field or a wrong count."""
    recipes = doc.get("recipes")
    count = doc.get("recipe_count")
    if not isinstance(recipes, list) or isinstance(count, bool) or count != len(recipes):
        raise NotAnExport("recipe list or count is wrong")
    return [_new_recipe(raw, now) for raw in recipes]
