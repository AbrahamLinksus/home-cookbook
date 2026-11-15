"""JSON endpoints (LLD §3.2, §5.2). Feature tasks add their routes here."""

from collections.abc import Mapping
from typing import Any

from flask import Blueprint, Response, abort, jsonify, request
from flask.blueprints import BlueprintSetupState
from flask.typing import ResponseReturnValue

from cookbook.domain.errors import NotAnExport
from cookbook.domain.rules import parse_draft
from cookbook.web import messages, services

bp = Blueprint("api", __name__, url_prefix="/api")


def _recipe_in() -> Mapping[str, object]:
    """The `recipe` object of the JSON body; 400 when the body is not that shape."""
    body: Any = request.get_json(silent=True)
    recipe = body.get("recipe") if isinstance(body, dict) else None
    if not isinstance(recipe, dict):
        abort(400)
    return recipe


def _base_version_in() -> int:
    """`base_version` of the JSON body; 400 when missing or not a whole number."""
    body: Any = request.get_json(silent=True)
    value = body.get("base_version") if isinstance(body, dict) else None
    if not isinstance(value, int) or isinstance(value, bool):
        abort(400)
    return value


@bp.post("/recipes")
def create_recipe() -> ResponseReturnValue:
    recipe = services().keeper.create(parse_draft(_recipe_in()))
    return jsonify({"id": recipe.id, "version": recipe.version}), 201


@bp.put("/recipes/<int:recipe_id>")
def update_recipe(recipe_id: int) -> ResponseReturnValue:
    base_version = _base_version_in()
    recipe = services().keeper.update(recipe_id, parse_draft(_recipe_in()), base_version)
    return jsonify({"id": recipe.id, "version": recipe.version})


@bp.put("/recipes/<int:recipe_id>/favourite")
def set_favourite(recipe_id: int) -> ResponseReturnValue:
    body: Any = request.get_json(silent=True)
    value = body.get("favourite") if isinstance(body, dict) else None
    if not isinstance(value, bool):
        abort(400)
    services().keeper.set_favourite(recipe_id, value)
    return jsonify({"favourite": value})


@bp.delete("/recipes/<int:recipe_id>")
def delete_recipe(recipe_id: int) -> ResponseReturnValue:
    keeper = services().keeper
    recipe = keeper.delete(recipe_id)
    return jsonify({"id": recipe.id, "title": recipe.title, "undo_seconds": keeper.undo_seconds})


@bp.post("/recipes/<int:recipe_id>/restore")
def restore_recipe(recipe_id: int) -> ResponseReturnValue:
    recipe, renamed_to = services().keeper.restore(recipe_id)
    # free_title only ever appends " (n)", so cutting it off gives the deleted name.
    # `title` is the name it had when deleted (the bar text quotes it); `renamed_to` the new one.
    title = recipe.title if renamed_to is None else renamed_to.rsplit(" (", 1)[0]
    return jsonify({"id": recipe.id, "title": title, "renamed_to": renamed_to})


@bp.post("/import")
def import_recipes() -> ResponseReturnValue:
    upload = request.files.get("file")
    if upload is None:
        raise NotAnExport("no file in the request")
    result = services().backup.import_file(upload.read())
    return jsonify(
        {
            "imported": result.imported,
            "skipped": result.skipped,
            "renamed": result.renamed,
            "skipped_titles": list(result.skipped_titles),
            "message": messages.imported(result),
        }
    )


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
