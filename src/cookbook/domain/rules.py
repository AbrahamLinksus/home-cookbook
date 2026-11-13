"""Shared recipe rules: same-title key, validation, list order (LLD §1.1, §1.2)."""

import unicodedata
from collections.abc import Iterable, Mapping

from cookbook.domain.amounts import UnclearAmountError, parse_amount
from cookbook.domain.errors import InvalidRecipe
from cookbook.domain.models import Ingredient, Recipe, RecipeDraft, RecipeSummary

MAX_TITLE = 200
MAX_SERVINGS = 1000
MAX_ROWS = 100
MAX_INGREDIENT_NAME = 200
MAX_UNIT = 30
MAX_STEP = 10_000


def title_key(title: str) -> str:
    return unicodedata.normalize("NFC", title).strip().casefold()


def free_title(title: str, taken_keys: set[str]) -> str:
    if title_key(title) not in taken_keys:
        return title
    number = 2
    while title_key(f"{title} ({number})") in taken_keys:
        number += 1
    return f"{title} ({number})"


def list_order(recipes: Iterable[Recipe]) -> list[RecipeSummary]:
    ordered = sorted(recipes, key=lambda r: (not r.favourite, title_key(r.title), r.id))
    return [RecipeSummary(r.id, r.title, r.servings, r.favourite) for r in ordered]


def parse_draft(raw: Mapping[str, object]) -> RecipeDraft:
    """Validate untyped input; raise InvalidRecipe(fields) listing every problem."""
    errors: dict[str, str] = {}
    title = _parse_title(raw.get("title"), errors)
    servings = _parse_servings(raw.get("servings"), errors)
    ingredients = _parse_ingredients(raw.get("ingredients"), errors)
    steps = _parse_steps(raw.get("steps"), errors)
    if errors:
        raise InvalidRecipe(errors)
    return RecipeDraft(title, servings, ingredients, steps)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_title(value: object, errors: dict[str, str]) -> str:
    title = _text(value)
    if not title:
        errors["title"] = "required"
    elif len(title) > MAX_TITLE:
        errors["title"] = "too_long"
    return title


def _parse_servings(value: object, errors: dict[str, str]) -> int:
    if isinstance(value, str):
        value = value.strip()
        if not value:
            errors["servings"] = "required"
            return 0
        value = _whole_number(value)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_SERVINGS:
        errors.setdefault("servings", "not_whole")
        return 0
    return value


def _whole_number(text: str) -> int | None:
    """The number in an ASCII digit string; None otherwise (also when far too long for int)."""
    if not (text.isascii() and text.isdigit()):
        return None
    digits = text.lstrip("0") or "0"
    return int(digits) if len(digits) <= len(str(MAX_SERVINGS)) else None


def _rows(value: object, key: str, errors: dict[str, str]) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list | tuple) or len(value) > MAX_ROWS:
        errors[key] = "too_long" if isinstance(value, list | tuple) else "required"
        return []
    return list(value)


def _parse_ingredients(value: object, errors: dict[str, str]) -> tuple[Ingredient, ...]:
    rows = (
        _parse_ingredient(index, row, errors)
        for index, row in enumerate(_rows(value, "ingredients", errors))
    )
    return tuple(row for row in rows if row is not None)


def _parse_ingredient(index: int, row: object, errors: dict[str, str]) -> Ingredient | None:
    data = row if isinstance(row, Mapping) else {}
    amount, unit, name = (_text(data.get(k)) for k in ("amount", "unit", "name"))
    if not (amount or unit or name):
        return None
    errors.update(_ingredient_problems(f"ingredients.{index}", amount, unit, name))
    return Ingredient(amount or None, unit, name)


def _ingredient_problems(prefix: str, amount: str, unit: str, name: str) -> dict[str, str]:
    problems = {
        f"{prefix}.name": _length_problem(name, MAX_INGREDIENT_NAME, required=True),
        f"{prefix}.unit": _length_problem(unit, MAX_UNIT, required=False),
        f"{prefix}.amount": _amount_problem(amount),
    }
    return {key: code for key, code in problems.items() if code}


def _length_problem(text: str, limit: int, *, required: bool) -> str | None:
    if required and not text:
        return "required"
    return "too_long" if len(text) > limit else None


def _amount_problem(text: str) -> str | None:
    if not text:
        return None
    try:
        parse_amount(text)
    except UnclearAmountError:
        return "unclear_amount"
    except ValueError:
        return "bad_amount"
    return None


def _parse_steps(value: object, errors: dict[str, str]) -> tuple[str, ...]:
    result: list[str] = []
    for index, row in enumerate(_rows(value, "steps", errors)):
        step = _text(row)
        if not step:
            continue
        if len(step) > MAX_STEP:
            errors[f"steps.{index}"] = "too_long"
        result.append(step)
    return tuple(result)
