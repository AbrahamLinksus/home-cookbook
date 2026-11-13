"""The only place exceptions become HTTP answers (LLD §6.3)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from cookbook.domain import errors as domain
from cookbook.web import messages

HTTP_SERVER_ERROR = 500
logger = logging.getLogger("cookbook")


@dataclass(frozen=True)
class Mapped:
    status: int
    code: str
    message: str
    extra: dict[str, Any]


Builder = Callable[[Any], Mapped]


def _invalid(exc: domain.InvalidRecipe) -> Mapped:
    fields = {key: messages.field_message(code) for key, code in exc.fields.items()}
    return Mapped(422, "invalid", "Some fields need attention", {"fields": fields})


def _duplicate(exc: domain.DuplicateTitle) -> Mapped:
    text = messages.duplicate_title(exc.existing_title)
    return Mapped(409, "duplicate_title", text, {"existing_title": exc.existing_title})


def _changed(exc: domain.ChangedElsewhere) -> Mapped:
    extra = {"current_version": exc.current_version}
    return Mapped(409, "changed_elsewhere", messages.CHANGED_ELSEWHERE, extra)


def _simple(status: int, code: str, text: str) -> Builder:
    return lambda _exc: Mapped(status, code, text, {})


def _undo_expired(exc: domain.UndoExpired) -> Mapped:
    return Mapped(410, "undo_expired", messages.undo_expired(exc.title), {})


# One row per exception kind; a new kind is a new class plus one row here.
BUILDERS: dict[type[domain.CookbookError], Builder] = {
    domain.InvalidRecipe: _invalid,
    domain.DuplicateTitle: _duplicate,
    domain.ChangedElsewhere: _changed,
    domain.DeletedElsewhere: _simple(410, "deleted_elsewhere", messages.DELETED_ELSEWHERE),
    domain.RecipeNotFound: _simple(404, "not_found", messages.RECIPE_GONE),
    domain.UndoExpired: _undo_expired,
    domain.NotAnExport: _simple(400, "not_an_export", messages.NOT_AN_EXPORT),
    domain.NewerExportFormat: _simple(400, "newer_version", messages.NEWER_VERSION),
    domain.ImportInterrupted: _simple(409, "import_interrupted", messages.IMPORT_INTERRUPTED),
}

_HTTP_CODES = {400: "bad_request", 404: "not_found", 413: "not_an_export"}
_HTTP_MESSAGES = {
    400: messages.BAD_REQUEST,
    404: messages.PAGE_GONE,
    413: messages.NOT_AN_EXPORT,
}


def _answer(mapped: Mapped) -> tuple[Response | str, int]:
    if request.path.startswith("/api/"):
        body = {"error": mapped.code, "message": mapped.message, **mapped.extra}
        return jsonify(body), mapped.status
    page = render_template(
        "error.html", status=mapped.status, heading=mapped.message, message=mapped.message
    )
    return page, mapped.status


def _handle_cookbook_error(exc: domain.CookbookError) -> tuple[Response | str, int]:
    for kind in type(exc).__mro__:
        builder = BUILDERS.get(kind)
        if builder is not None:
            return _answer(builder(exc))
    return _handle_unexpected(exc)


def _handle_http_error(exc: HTTPException) -> tuple[Response | str, int]:
    status = exc.code or 500
    if status >= HTTP_SERVER_ERROR:
        return _handle_unexpected(exc)
    code = _HTTP_CODES.get(status, "bad_request")
    text = _HTTP_MESSAGES.get(status, exc.description or messages.BAD_REQUEST)
    return _answer(Mapped(status, code, text, {}))


def _handle_unexpected(exc: Exception) -> tuple[Response | str, int]:
    logger.error("unhandled_error kind=%s", type(exc).__name__, exc_info=exc)
    return _answer(Mapped(500, "server_error", messages.SERVER_ERROR, {}))


def register(app: Flask) -> None:
    app.register_error_handler(domain.CookbookError, _handle_cookbook_error)
    app.register_error_handler(HTTPException, _handle_http_error)
    app.register_error_handler(Exception, _handle_unexpected)
