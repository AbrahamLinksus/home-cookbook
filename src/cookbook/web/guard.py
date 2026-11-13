"""Request guard: home addresses, home host names, same-site writes (LLD §6.5, D-32)."""

import ipaddress
from urllib.parse import urlsplit

from flask import Flask, Response, request

from cookbook.web import messages

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_LOCAL_SUFFIX = ".local"


def _is_home_address(remote_addr: str | None) -> bool:
    if not remote_addr:
        return False
    try:
        address = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_private or address.is_loopback or address.is_link_local


def _is_home_host(host: str) -> bool:
    """True for an IP literal, "localhost" or a "*.local" name (D-32: stops DNS rebinding)."""
    try:
        name = urlsplit(f"//{host}").hostname or ""
    except ValueError:  # e.g. an unclosed "[" in the Host header
        return False
    if name == "localhost" or (name.endswith(_LOCAL_SUFFIX) and name != _LOCAL_SUFFIX):
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


def _refuse(text: str) -> Response:
    return Response(text, status=403, mimetype="text/plain")


def check_request() -> Response | None:
    if not _is_home_address(request.remote_addr) or not _is_home_host(request.host):
        return _refuse(messages.OUTSIDE_HOME)
    origin = request.headers.get("Origin")
    if request.method in _WRITE_METHODS and origin and urlsplit(origin).netloc != request.host:
        return _refuse(messages.OTHER_WEBSITE)
    return None


def register(app: Flask) -> None:
    app.before_request(check_request)
