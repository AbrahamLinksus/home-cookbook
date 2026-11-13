"""HTML pages (LLD §7). Views stay thin: one service call, then render."""

from flask import Blueprint, render_template

from cookbook.domain.models import SearchBy
from cookbook.web import messages, services

bp = Blueprint("pages", __name__)


@bp.app_context_processor
def ui_texts() -> dict[str, dict[str, str]]:
    """Browser texts for base.html, so every page (error pages too) carries them."""
    return {"ui_texts": messages.UI_TEXTS}


@bp.get("/")
def recipe_list() -> str:
    recipes = services().keeper.list_recipes()
    return render_template(
        "list.html",
        recipes=recipes,
        q="",
        by=SearchBy.NAME.value,
        total_live=len(recipes),
    )
