"""GET /export through the real app (T-03)."""

import json
from typing import Any

from flask.testing import FlaskClient

from cookbook.domain.ports import Clock


def _post(client: FlaskClient, title: str) -> None:
    recipe: dict[str, Any] = {
        "title": title,
        "servings": 4,
        "ingredients": [{"amount": "", "unit": "", "name": "sugar"}],
        "steps": ["Heat to 200°C"],
    }
    assert client.post("/api/recipes", json={"recipe": recipe}).status_code == 201


def test_export_downloads_all_recipes_as_readable_utf8(client: FlaskClient, clock: Clock) -> None:
    for number in range(42):
        _post(client, f"Recipe {number}")
    _post(client, "Crème Brûlée")

    response = client.get("/export")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    name = f"cookbook-{clock.now().astimezone():%Y-%m-%d}.json"
    assert response.headers["Content-Disposition"] == f'attachment; filename="{name}"'
    text = response.get_data(as_text=True)
    assert "Crème Brûlée" in text and "200°C" in text
    doc = json.loads(text)
    assert doc["recipe_count"] == len(doc["recipes"]) == 43
    assert doc["recipes"][0]["ingredients"][0]["amount"] is None


def test_empty_app_exports_zero_recipes(client: FlaskClient) -> None:
    doc = client.get("/export").get_json(force=True)

    assert doc["recipe_count"] == 0
    assert doc["recipes"] == []


def test_exactly_42_recipes_keep_order_and_fields(client: FlaskClient) -> None:
    for number in range(42):
        _post(client, f"Recipe {number}")

    doc = json.loads(client.get("/export").get_data(as_text=True))

    assert doc["recipe_count"] == len(doc["recipes"]) == 42
    assert sorted(doc["recipes"][0]) == sorted(
        ["title", "servings", "favourite", "ingredients", "steps", "created_at", "updated_at"]
    )
    assert doc["recipes"][0]["steps"] == ["Heat to 200°C"]
    assert doc["format"] == "home-cookbook-export" and doc["format_version"] == 1
    assert doc["app_version"] and doc["exported_at"]
