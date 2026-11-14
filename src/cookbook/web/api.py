"""JSON endpoints (LLD §3.2, §5.2). Feature tasks add their routes here."""

from collections.abc import Mapping
from typing import Any

from flask import Blueprint, Response, abort, jsonify, request
from flask.blueprints import BlueprintSetupState
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


def export_download() -> Response:
    """GET /export: every live recipe as one downloadable JSON file (LLD §5.2)."""
    export = services().backup.export_all()
    response = Response(export.content, mimetype="application/json")
    response.headers["Content-Disposition"] = f'attachment; filename="{export.filename}"'
    return response


@bp.record_once
def _mount_export(state: BlueprintSetupState) -> None:
    # `/export` sits outside this blueprint's `/api` prefix, and the factory registers only
    # this blueprint, so the route is added to the app when the blueprint is registered.
    state.app.add_url_rule("/export", endpoint="export", view_func=export_download)
