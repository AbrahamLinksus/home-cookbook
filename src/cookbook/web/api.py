"""JSON endpoints (LLD §3.2, §5.2). Feature tasks add their routes here."""

from collections.abc import Mapping
from typing import Any

from flask import Blueprint, abort, jsonify, request
from flask.typing import ResponseReturnValue

from cookbook.domain.rules import parse_draft
from cookbook.web import services

bp = Blueprint("api", __name__, url_prefix="/api")


def _recipe_in() -> Mapping[str, object]:
    """The `recipe` object of the JSON body; 400 when the body is not that shape."""
    body: Any = request.get_json(silent=True)
    recipe = body.get("recipe") if isinstance(body, dict) else None
    if not isinstance(recipe, dict):
        abort(400)
    return recipe


@bp.post("/recipes")
def create_recipe() -> ResponseReturnValue:
    recipe = services().keeper.create(parse_draft(_recipe_in()))
    return jsonify({"id": recipe.id, "version": recipe.version}), 201
