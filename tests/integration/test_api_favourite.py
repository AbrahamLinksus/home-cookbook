"""PUT /api/recipes/<id>/favourite (T-08)."""

from typing import Any

import pytest
from flask.testing import FlaskClient


def _recipe(title: str) -> dict[str, Any]:
    return {"title": title, "servings": 4, "ingredients": [], "steps": ["Mix"]}


def _make(client: FlaskClient, title: str) -> dict[str, Any]:
    body: Any = client.post("/api/recipes", json={"recipe": _recipe(title)}).get_json()
    return body


def _star(client: FlaskClient, rid: int, value: Any) -> Any:
    return client.put(f"/api/recipes/{rid}/favourite", json={"favourite": value})


def _list_titles(client: FlaskClient) -> list[str]:
    html = client.get("/recipes/_list").get_data(as_text=True)
    parts = html.split('class="row-title">')[1:]
    return [p.split("<", 1)[0] for p in parts]


def test_star_returns_state_and_unstar_restores(client: FlaskClient) -> None:
    rid = _make(client, "Sunday Roast Chicken")["id"]

    on = _star(client, rid, True)
    assert on.status_code == 200
    assert on.get_json() == {"favourite": True}
    off = _star(client, rid, False)
    assert off.status_code == 200
    assert off.get_json() == {"favourite": False}


def test_star_is_idempotent(client: FlaskClient) -> None:
    rid = _make(client, "Lemon Cake")["id"]
    assert _star(client, rid, True).get_json() == {"favourite": True}
    assert _star(client, rid, True).get_json() == {"favourite": True}
    assert 'aria-pressed="true"' in client.get("/").get_data(as_text=True)


def test_favourites_first_then_a_to_z(client: FlaskClient) -> None:
    _make(client, "Aunt May's Scones")
    roast = _make(client, "Sunday Roast Chicken")["id"]
    _make(client, "Buttermilk Pancakes")
    assert _list_titles(client) == [
        "Aunt May&#39;s Scones",
        "Buttermilk Pancakes",
        "Sunday Roast Chicken",
    ]

    _star(client, roast, True)
    assert _list_titles(client)[0] == "Sunday Roast Chicken"
    assert len(_list_titles(client)) == 3

    _star(client, roast, False)
    assert _list_titles(client)[-1] == "Sunday Roast Chicken"


def test_starring_does_not_change_version(client: FlaskClient) -> None:
    made = _make(client, "Lemon Cake")
    _star(client, made["id"], True)

    saved = client.put(
        f"/api/recipes/{made['id']}",
        json={"base_version": made["version"], "recipe": _recipe("Lemon Cake")},
    )

    assert saved.status_code == 200  # no 409: version was not bumped by the star
    assert saved.get_json()["version"] == made["version"] + 1
    assert 'aria-pressed="true"' in client.get(f"/recipes/{made['id']}").get_data(as_text=True)


@pytest.mark.parametrize("value", ["true", 1, 0, None, [], "yes"])
def test_non_bool_is_400(client: FlaskClient, value: Any) -> None:
    rid = _make(client, "Lemon Cake")["id"]
    response = _star(client, rid, value)
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_bad_bodies_are_400(client: FlaskClient) -> None:
    rid = _make(client, "Lemon Cake")["id"]
    url = f"/api/recipes/{rid}/favourite"
    assert client.put(url, json={}).status_code == 400
    assert client.put(url, json=[True]).status_code == 400
    assert client.put(url, data="not json", content_type="application/json").status_code == 400
    assert client.put(url, data="favourite=true").status_code == 400
    assert 'aria-pressed="true"' not in client.get("/").get_data(as_text=True)


def test_unknown_id_is_410(client: FlaskClient) -> None:
    response = _star(client, 999, True)
    assert response.status_code == 410
    assert response.get_json()["error"] == "deleted_elsewhere"


def test_pending_delete_is_410(client: FlaskClient) -> None:
    rid = _make(client, "Lemon Cake")["id"]
    client.delete(f"/api/recipes/{rid}")
    response = _star(client, rid, True)
    assert response.status_code == 410
    assert response.get_json()["error"] == "deleted_elsewhere"
    assert response.get_json()["message"] == "This recipe was deleted on another device"


def test_delete_then_undo_keeps_star(client: FlaskClient) -> None:
    rid = _make(client, "Lemon Cake")["id"]
    _star(client, rid, True)
    client.delete(f"/api/recipes/{rid}")
    client.post(f"/api/recipes/{rid}/restore")
    assert 'aria-pressed="true"' in client.get("/").get_data(as_text=True)


def test_update_ignores_favourite_in_body(client: FlaskClient) -> None:
    made = _make(client, "Lemon Cake")
    _star(client, made["id"], True)
    recipe = {**_recipe("Lemon Cake"), "favourite": False}
    client.put(
        f"/api/recipes/{made['id']}", json={"base_version": made["version"], "recipe": recipe}
    )
    assert 'aria-pressed="true"' in client.get("/").get_data(as_text=True)
