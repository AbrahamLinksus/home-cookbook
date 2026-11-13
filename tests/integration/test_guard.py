"""Request guard (LLD §6.5): home addresses only, same-site writes only."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

OUTSIDE = "Home Cookbook only answers inside the home"


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    app.add_url_rule("/_ping", "ping", lambda: "pong", methods=["GET", "POST"])
    return app.test_client()


@pytest.mark.parametrize("address", ["8.8.8.8", "2001:4860:4860::8888", "not-an-ip", ""])
def test_guard_non_home_address_gets_403(client: FlaskClient, address: str) -> None:
    response = client.get("/_ping", environ_overrides={"REMOTE_ADDR": address})
    assert response.status_code == 403
    assert OUTSIDE in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "address", ["192.168.1.20", "127.0.0.1", "10.0.0.5", "169.254.1.1", "::1", "::ffff:192.168.1.5"]
)
def test_guard_home_address_is_served(client: FlaskClient, address: str) -> None:
    response = client.get("/_ping", environ_overrides={"REMOTE_ADDR": address})
    assert (response.status_code, response.get_data(as_text=True)) == (200, "pong")


def test_guard_post_from_other_origin_gets_403(client: FlaskClient) -> None:
    response = client.post("/_ping", headers={"Origin": "http://evil.example"})
    assert response.status_code == 403


def test_guard_post_from_own_origin_is_served(client: FlaskClient) -> None:
    response = client.post("/_ping", headers={"Origin": "http://localhost"})
    assert response.status_code == 200


def test_guard_post_without_origin_is_served(client: FlaskClient) -> None:
    assert client.post("/_ping").status_code == 200


def test_guard_get_with_other_origin_is_served(client: FlaskClient) -> None:
    response = client.get("/_ping", headers={"Origin": "http://evil.example"})
    assert response.status_code == 200


def test_guard_real_home_page_outside_is_403_inside_is_served(client: FlaskClient) -> None:
    outside = client.get("/", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert outside.status_code == 403
    assert OUTSIDE in outside.get_data(as_text=True)
    for address in ("192.168.1.20", "127.0.0.1"):
        assert client.get("/", environ_overrides={"REMOTE_ADDR": address}).status_code == 200


LAN = {"REMOTE_ADDR": "192.168.1.20"}


@pytest.mark.parametrize(
    "host", ["evil.example:8765", "evil.example", "local", "evil.local.example:8765", "[::1"]
)
def test_guard_foreign_host_name_from_home_address_gets_403(client: FlaskClient, host: str) -> None:
    response = client.get("/_ping", headers={"Host": host}, environ_overrides=LAN)
    assert response.status_code == 403
    assert OUTSIDE in response.get_data(as_text=True)


def test_guard_dns_rebinding_write_gets_403(client: FlaskClient) -> None:
    headers = {"Host": "evil.example:8765", "Origin": "http://evil.example:8765"}
    response = client.post("/_ping", headers=headers, environ_overrides=LAN)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "host",
    [
        "192.168.1.10:8765",
        "localhost",
        "localhost:8765",
        "myhost.local",
        "MyHost.Local:8765",
        "127.0.0.1",
        "[::1]:8765",
        "[::ffff:192.168.1.10]:8765",
    ],
)
def test_guard_home_host_name_is_served(client: FlaskClient, host: str) -> None:
    response = client.get("/_ping", headers={"Host": host}, environ_overrides=LAN)
    assert (response.status_code, response.get_data(as_text=True)) == (200, "pong")


def test_guard_allowed_host_with_other_origin_write_gets_403(client: FlaskClient) -> None:
    headers = {"Host": "192.168.1.10:8765", "Origin": "http://evil.example:8765"}
    response = client.post("/_ping", headers=headers, environ_overrides=LAN)
    assert response.status_code == 403


def test_guard_allowed_host_with_own_origin_write_is_served(client: FlaskClient) -> None:
    headers = {"Host": "192.168.1.10:8765", "Origin": "http://192.168.1.10:8765"}
    response = client.post("/_ping", headers=headers, environ_overrides=LAN)
    assert response.status_code == 200
