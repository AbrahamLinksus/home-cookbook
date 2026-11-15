"""DELETE and restore endpoints (T-05)."""

from typing import Any

from flask.testing import FlaskClient


def _make(client: FlaskClient, title: str) -> int:
    recipe = {"title": title, "servings": 4, "ingredients": [], "steps": ["Mix"]}
    return int(client.post("/api/recipes", json={"recipe": recipe}).get_json()["id"])


def _listed(client: FlaskClient, title: str) -> bool:
    return title in client.get("/").get_data(as_text=True)


def test_delete_hides_and_undo_restores_unchanged(client: FlaskClient) -> None:
    rid = _make(client, "Lemon Cake")

    response = client.delete(f"/api/recipes/{rid}")

    assert response.get_json() == {"id": rid, "title": "Lemon Cake", "undo_seconds": 10}
    assert not _listed(client, "Lemon Cake")
    restored = client.post(f"/api/recipes/{rid}/restore")
    assert restored.get_json() == {"id": rid, "title": "Lemon Cake", "renamed_to": None}
    assert _listed(client, "Lemon Cake")


def test_undo_after_window_is_refused_and_recipe_stays_gone(
    client: FlaskClient, clock: Any
) -> None:
    rid = _make(client, "Lemon Cake")
    client.delete(f"/api/recipes/{rid}")
    clock.advance(13)

    response = client.post(f"/api/recipes/{rid}/restore")

    assert response.status_code == 410
    body: Any = response.get_json()
    assert body["error"] == "undo_expired"
    assert body["message"] == "Too late to undo; 'Lemon Cake' is gone"
    assert not _listed(client, "Lemon Cake")


def test_second_delete_makes_first_final(client: FlaskClient) -> None:
    first = _make(client, "Lemon Cake")
    second = _make(client, "Soup")
    client.delete(f"/api/recipes/{first}")
    client.delete(f"/api/recipes/{second}")

    refused = client.post(f"/api/recipes/{first}/restore")
    assert refused.status_code == 410
    assert refused.get_json()["error"] == "undo_expired"  # undo.js names the recipe itself
    assert client.post(f"/api/recipes/{second}/restore").status_code == 200


def test_undo_renames_when_title_was_reused(client: FlaskClient) -> None:
    rid = _make(client, "Lemon Cake")
    client.delete(f"/api/recipes/{rid}")
    _make(client, "Lemon Cake")

    body: Any = client.post(f"/api/recipes/{rid}/restore").get_json()

    assert body["title"] == "Lemon Cake"
    assert body["renamed_to"] == "Lemon Cake (2)"


def test_delete_unknown_is_404(client: FlaskClient) -> None:
    assert client.delete("/api/recipes/99").status_code == 404


def test_undo_rename_keeps_original_title_already_ending_in_number(client: FlaskClient) -> None:
    rid = _make(client, "Pancakes (2)")
    client.delete(f"/api/recipes/{rid}")
    _make(client, "Pancakes (2)")

    body: Any = client.post(f"/api/recipes/{rid}/restore").get_json()

    assert body["title"] == "Pancakes (2)"
    assert body["renamed_to"] == "Pancakes (2) (2)"
