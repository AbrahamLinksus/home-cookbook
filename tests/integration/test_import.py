"""POST /api/import through the real app (T-04)."""

import io
import json
from pathlib import Path
from typing import Any

from flask import Flask
from flask.testing import FlaskClient

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.app.factory import create_app
from cookbook.domain.ports import Clock
from cookbook.web import messages

FIXTURE = Path(__file__).parent.parent / "fixtures" / "exports" / "v1-basic.json"


def _post(client: FlaskClient, title: str) -> None:
    recipe: dict[str, Any] = {
        "title": title,
        "servings": 4,
        "ingredients": [{"amount": "1 1/2", "unit": "cup", "name": "sugar"}],
        "steps": ["Mix"],
    }
    assert client.post("/api/recipes", json={"recipe": recipe}).status_code == 201


def _import(client: FlaskClient, data: bytes) -> Any:
    return client.post("/api/import", data={"file": (io.BytesIO(data), "x.json")})


def _export(client: FlaskClient) -> dict[str, Any]:
    return json.loads(client.get("/export").get_data(as_text=True))


def _count(client: FlaskClient) -> int:
    return int(_export(client)["recipe_count"])


def _fresh(tmp_path: Path, clock: Clock) -> FlaskClient:
    app: Flask = create_app(Settings(db_path=tmp_path / "other" / "c.db"), clock=clock)
    app.config["TESTING"] = True
    return app.test_client()


def test_round_trip_into_an_empty_app(client: FlaskClient, tmp_path: Path, clock: Clock) -> None:
    for number in range(42):
        _post(client, f"Recipe {number}")
    exported = client.get("/export").data
    other = _fresh(tmp_path, clock)

    response = _import(other, exported)

    assert response.status_code == 200
    body = response.get_json()
    assert body["imported"] == 42 and body["message"] == "Imported 42 recipes"
    again = _export(other)
    original = json.loads(exported)
    assert again.pop("exported_at") and original.pop("exported_at")
    assert again == original


def test_skips_same_title_and_keeps_existing(client: FlaskClient, tmp_path: Path) -> None:
    data = FIXTURE.read_bytes()
    _post(client, "lemon cake")

    body = _import(client, data).get_json()

    assert (body["imported"], body["skipped"]) == (2, 1)
    assert body["skipped_titles"] == ["Lemon Cake"]
    assert "skipped 1 with the same title: Lemon Cake" in body["message"]
    assert "To restore one, delete it first, then import again" in body["message"]
    titles = [r["title"] for r in _export(client)["recipes"]]
    assert "lemon cake" in titles and "Lemon Cake" not in titles


def test_repeated_title_in_file_is_renamed(client: FlaskClient) -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["recipes"] = [dict(doc["recipes"][2], title="Pancakes") for _ in range(2)]
    doc["recipe_count"] = 2

    body = _import(client, json.dumps(doc).encode()).get_json()

    assert body["imported"] == 2 and body["renamed"] == 1
    assert "renamed 1 with a repeated title" in body["message"]
    assert [r["title"] for r in _export(client)["recipes"]] == ["Pancakes", "Pancakes (2)"]


def test_refused_files_change_nothing(client: FlaskClient) -> None:
    _post(client, "Keep me")
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for data in (
        b"\xff\xd8\xff\xe0 JFIF holiday",
        FIXTURE.read_bytes()[:400],
        json.dumps({**doc, "recipe_count": 9}).encode(),
    ):
        response = _import(client, data)
        assert response.status_code == 400
        assert response.get_json()["error"] == "not_an_export"
        assert response.get_json()["message"].startswith("This file isn't a Home Cookbook export")
    assert _count(client) == 1


def test_newer_version_is_refused(client: FlaskClient) -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))

    response = _import(client, json.dumps({**doc, "format_version": 2}).encode())

    assert response.status_code == 400
    assert response.get_json()["error"] == "newer_version"
    assert "made by a newer version" in response.get_json()["message"]
    assert _count(client) == 0


def test_missing_file_and_oversized_upload(client: FlaskClient) -> None:
    assert client.post("/api/import", data={}).get_json()["error"] == "not_an_export"
    big = _import(client, b"x" * (6 * 1024 * 1024))
    assert big.status_code == 413
    assert big.get_json()["error"] == "not_an_export"
    assert big.get_json()["message"] == messages.NOT_AN_EXPORT


def _file_42() -> dict[str, Any]:
    recipes = [
        {
            "title": f"Recipe {n:02d}",
            "servings": 2 + n % 5,
            "favourite": n % 7 == 0,
            "ingredients": [
                {"amount": "1 1/2", "unit": "cups", "name": "flour"},
                {"amount": "2.5", "unit": "tbsp", "name": "butter"},
                {"amount": None, "unit": "", "name": "salt, to taste"},
            ],
            "steps": [f"Mix {n}", "Bake"],
            "created_at": "2026-11-01T10:00:00Z",
            "updated_at": "2026-11-02T10:00:00Z",
        }
        for n in range(40)
    ]
    for title, fav in (("Lemon Cake", True), ("Shepherd's Pie", False)):
        recipes.append({**recipes[0], "title": title, "favourite": fav, "steps": ["From file"]})
    return {
        "format": "home-cookbook-export",
        "format_version": 1,
        "app_version": "1.0.0",
        "exported_at": "2026-11-13T18:02:11Z",
        "recipe_count": 42,
        "recipes": recipes,
    }


def _by_title(client: FlaskClient) -> dict[str, dict[str, Any]]:
    return {r["title"]: r for r in _export(client)["recipes"]}


def test_two_skipped_recipes_are_named_and_left_unchanged(client: FlaskClient) -> None:
    _post(client, "Lemon Cake")
    _post(client, "shepherd's pie")
    before = _by_title(client)

    body = _import(client, json.dumps(_file_42()).encode()).get_json()

    assert body["message"].startswith("Imported 40 recipes · skipped 2 with the same title")
    assert "Lemon Cake" in body["message"] and "Shepherd's Pie" in body["message"]
    assert "To restore one, delete it first, then import again" in body["message"]
    after = _by_title(client)
    assert len(after) == 42
    assert after["Lemon Cake"] == before["Lemon Cake"]
    assert after["shepherd's pie"] == before["shepherd's pie"]
    assert "Shepherd's Pie" not in after


def test_deleted_recipe_comes_back_after_the_undo_window(
    client: FlaskClient, app: Flask, settings: Settings, clock: Any
) -> None:
    _post(client, "Lemon Cake")
    _post(client, "shepherd's pie")
    repo = SqliteRecipeRepository(settings.db_path)
    lemon = next(r for r in repo.list_live() if r.title == "Lemon Cake")
    assert repo.mark_deleted(lemon.id, clock.now()) is not None
    clock.advance(3600)
    app.extensions["cookbook"].keeper.list_recipes()  # purges expired deletes
    file = _file_42()

    body = _import(client, json.dumps(file).encode()).get_json()

    assert body["imported"] == 41 and body["skipped"] == 1
    assert body["skipped_titles"] == ["Shepherd's Pie"]
    restored = _by_title(client)["Lemon Cake"]
    expected = next(r for r in file["recipes"] if r["title"] == "Lemon Cake")
    assert {k: restored[k] for k in expected} == expected


def test_app_made_export_with_every_field_kind_imports_under_the_strict_type_check(
    client: FlaskClient, tmp_path: Path, clock: Clock
) -> None:
    recipe: dict[str, Any] = {
        "title": "Crème Brûlée",
        "servings": 4,
        "ingredients": [
            {"amount": "1 1/2", "unit": "cups", "name": "crème fraîche"},
            {"amount": "0.5", "unit": "l", "name": "milk"},
            {"amount": "", "unit": "", "name": "salt, to taste"},
        ],
        "steps": ["Whisk", "Caramelise"],
    }
    assert client.post("/api/recipes", json={"recipe": recipe}).status_code == 201
    exported = _export(client)
    exported["recipes"][0]["favourite"] = True  # a favourite, as an owner would have set
    other = _fresh(tmp_path, clock)

    first = _import(other, json.dumps(exported).encode("utf-8"))
    assert first.status_code == 200 and first.get_json()["imported"] == 1

    # export from the app that took the import, then load that app-made file into a third app
    re_exported = client_export = _export(other)
    assert re_exported["recipes"][0]["favourite"] is True
    third = _fresh(tmp_path / "third", clock)
    second = _import(third, json.dumps(client_export).encode("utf-8"))
    assert second.status_code == 200 and second.get_json()["imported"] == 1
    final = _export(third)
    for doc in (exported, re_exported, final):
        doc.pop("exported_at")
    assert exported == re_exported == final
