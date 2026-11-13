"""JSON endpoints (LLD §3.2, §5.2). Feature tasks add their routes here."""

from flask import Blueprint

bp = Blueprint("api", __name__, url_prefix="/api")
