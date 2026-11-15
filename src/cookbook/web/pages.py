"""HTML pages (LLD §7). Views stay thin: one service call, then render."""

from dataclasses import dataclass

from flask import Blueprint, render_template, request

from cookbook.domain.amounts import display_amount, parse_amount
from cookbook.domain.models import Ingredient, Recipe, SearchBy
from cookbook.web import messages, services

bp = Blueprint("pages", __name__)


@dataclass(frozen=True, slots=True)
class IngredientLine:
    """One ingredient as the read view shows it; qty_* feed the browser scaler (LLD §7.3)."""

    amount_text: str | None
    unit: str
    name: str
    qty_num: int | None
    qty_den: int | None


def ingredient_line(ingredient: Ingredient) -> IngredientLine:
    if ingredient.amount is None:
        return IngredientLine(None, ingredient.unit, ingredient.name, None, None)
    quantity = parse_amount(ingredient.amount)
    return IngredientLine(
        display_amount(ingredient.amount),
        ingredient.unit,
        ingredient.name,
        quantity.numerator,
        quantity.denominator,
    )


def form_data(recipe: Recipe | None) -> dict[str, object]:
    """RecipeIn (LLD §3.2) for the edit form; blank form when `recipe` is None."""
    if recipe is None:
        return {"title": "", "servings": 4, "ingredients": [], "steps": []}
    return {
        "title": recipe.title,
        "servings": recipe.servings,
        "ingredients": [
            {"amount": i.amount or "", "unit": i.unit, "name": i.name} for i in recipe.ingredients
        ],
        "steps": list(recipe.steps),
    }


@bp.app_context_processor
def ui_texts() -> dict[str, dict[str, str]]:
    """Browser texts for base.html, so every page (error pages too) carries them."""
    return {"ui_texts": messages.UI_TEXTS}


def parse_by(raw: str | None) -> SearchBy:
    """`by` query value; anything unknown means name (LLD §4.2)."""
    return SearchBy.INGREDIENT if raw == SearchBy.INGREDIENT.value else SearchBy.NAME


def list_context() -> dict[str, object]:
    """Template context for the list page and its fragment (LLD §7.2)."""
    q = request.args.get("q", "")
    by = parse_by(request.args.get("by"))
    svc = services()
    total_live = len(svc.keeper.list_recipes())
    recipes = svc.finder.search(q, by)
    return {"recipes": recipes, "q": q, "by": by.value, "total_live": total_live}


@bp.get("/")
def recipe_list() -> str:
    return render_template("list.html", **list_context())


@bp.get("/recipes/_list")
def recipe_list_items() -> str:
    return render_template("_list_items.html", **list_context())


@bp.get("/recipes/new")
def new_recipe() -> str:
    return render_template("edit.html", recipe=None, form_json=form_data(None), version=None)


@bp.get("/recipes/<int:recipe_id>")
def view_recipe(recipe_id: int) -> str:
    recipe = services().keeper.get(recipe_id)
    lines = [ingredient_line(i) for i in recipe.ingredients]
    return render_template("view.html", recipe=recipe, lines=lines)
