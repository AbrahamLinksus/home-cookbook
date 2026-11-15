"""PUT /api/recipes/<id> and GET /recipes/<id>/edit (T-06, S-03)."""

from typing import Any

import pytest
from flask.testing import FlaskClient


def _recipe(title: str = "Lemon Cake", amount: str = "2") -> dict[str, Any]:
    return {
        "title": title,
        "servings": 4,
        "ingredients": [{"amount": amount, "unit": "cups", "name": "flour"}],
        "steps": ["Mix"],
    }


def _make(client: FlaskClient, title: str = "Lemon Cake") -> dict[str, Any]:
    body: Any = client.post("/api/recipes", json={"recipe": _recipe(title)}).get_json()
    return body


def _put(client: FlaskClient, rid: int, base: Any, recipe: Any) -> Any:
    return client.put(f"/api/recipes/{rid}", json={"base_version": base, "recipe": recipe})


def test_put_saves_and_returns_new_version(client: FlaskClient) -> None:
    made = _make(client)

    response = _put(client, made["id"], made["version"], _recipe(amount="2½"))

    assert response.status_code == 200
    body: Any = response.get_json()
    assert body["id"] == made["id"]
    assert body["version"] == made["version"] + 1
    assert "2½ cups flour" in client.get(f"/recipes/{made['id']}").get_data(as_text=True)


def test_put_with_own_title_works(client: FlaskClient) -> None:
    made = _make(client)
    assert _put(client, made["id"], made["version"], _recipe()).status_code == 200


def test_put_other_recipes_title_is_duplicate_and_saves_nothing(client: FlaskClient) -> None:
    _make(client, "Pancakes")
    made = _make(client)

    response = _put(client, made["id"], made["version"], _recipe("pancakes", "9"))

    assert response.status_code == 409
    body: Any = response.get_json()
    assert body["error"] == "duplicate_title"
    assert "You already have a recipe called" in body["message"]
    page = client.get(f"/recipes/{made['id']}").get_data(as_text=True)
    assert "Lemon Cake" in page and "9 cups" not in page


def test_stale_version_is_409_changed_elsewhere_with_current_version(client: FlaskClient) -> None:
    made = _make(client)
    _put(client, made["id"], made["version"], _recipe(amount="3"))

    response = _put(client, made["id"], made["version"], _recipe(amount="4"))

    assert response.status_code == 409
    body: Any = response.get_json()
    assert body["error"] == "changed_elsewhere"
    assert body["message"] == "This recipe changed on another device"
    assert body["current_version"] == made["version"] + 1
    assert _put(client, made["id"], body["current_version"], _recipe(amount="4")).status_code == 200


def test_deleted_recipe_is_410_and_nothing_saved_then_undo_makes_put_work(
    client: FlaskClient,
) -> None:
    made = _make(client)
    client.delete(f"/api/recipes/{made['id']}")

    response = _put(client, made["id"], made["version"], _recipe(amount="4"))

    assert response.status_code == 410
    body: Any = response.get_json()
    assert body["error"] == "deleted_elsewhere"
    assert body["message"] == "This recipe was deleted on another device"
    client.post(f"/api/recipes/{made['id']}/restore")
    assert _put(client, made["id"], made["version"], _recipe(amount="4")).status_code == 200


def test_unknown_id_is_410_on_put_and_404_on_edit_page(client: FlaskClient) -> None:
    assert _put(client, 4242, 1, _recipe()).status_code == 410
    assert client.get("/recipes/4242/edit").status_code == 404


def test_edit_page_of_deleted_recipe_is_404(client: FlaskClient) -> None:
    made = _make(client)
    client.delete(f"/api/recipes/{made['id']}")
    assert client.get(f"/recipes/{made['id']}/edit").status_code == 404


def test_edit_page_carries_version_and_form_data(client: FlaskClient) -> None:
    made = _make(client)
    html = client.get(f"/recipes/{made['id']}/edit").get_data(as_text=True)
    assert f'data-version="{made["version"]}"' in html
    assert "Lemon Cake" in html


@pytest.mark.parametrize("base", ["abc", None, 1.5, [], True, "1"])
def test_bad_base_version_is_400(client: FlaskClient, base: Any) -> None:
    made = _make(client)
    response = _put(client, made["id"], base, _recipe())
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_missing_base_version_or_recipe_is_400(client: FlaskClient) -> None:
    made = _make(client)
    url = f"/api/recipes/{made['id']}"
    assert client.put(url, json={"recipe": _recipe()}).status_code == 400
    assert client.put(url, json={"base_version": made["version"]}).status_code == 400
    assert client.put(url, json={"base_version": made["version"], "recipe": "x"}).status_code == 400


def test_invalid_recipe_is_422_with_fields(client: FlaskClient) -> None:
    made = _make(client)
    bad = _recipe(title="  ")
    response = _put(client, made["id"], made["version"], bad)
    assert response.status_code == 422
    assert "title" in response.get_json()["fields"]
