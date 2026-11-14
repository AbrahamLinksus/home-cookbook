"""Import: format upgrade, validation and planning with an in-memory repository (T-04)."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cookbook.domain.errors import DuplicateTitle, ImportInterrupted, NewerExportFormat, NotAnExport
from cookbook.domain.models import NewRecipe
from cookbook.domain.rules import title_key
from cookbook.services.backup.formats import upgrade
from cookbook.services.backup.service import BackupService

FIXTURES = Path(__file__).parent.parent / "fixtures" / "exports"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 13, 9, 0, tzinfo=UTC)


class Repo:
    def __init__(self, live: set[str] | None = None, clash: bool = False) -> None:
        self.keys = live or set()
        self.added: list[NewRecipe] = []
        self.clash = clash

    def live_title_keys(self) -> set[str]:
        return set(self.keys)

    def add_many(self, items: Sequence[NewRecipe]) -> None:
        if self.clash:
            raise DuplicateTitle("x")
        self.added.extend(items)


def _service(repo: Repo) -> BackupService:
    return BackupService(repo, FixedClock(), "1.0.0")  # type: ignore[arg-type]


def _doc(items: list[dict[str, Any]], **over: Any) -> bytes:
    doc = {"format": "home-cookbook-export", "format_version": 1, "app_version": "1",
           "exported_at": "x", "recipe_count": len(items), "recipes": items}  # fmt: skip
    return json.dumps({**doc, **over}).encode()


def _recipe(title: str, **over: Any) -> dict[str, Any]:
    return {"title": title, "servings": 2, "favourite": False,
            "ingredients": [{"amount": "1", "unit": "", "name": "egg"}],
            "steps": ["Cook"], **over}  # fmt: skip


def test_every_fixture_imports_with_every_field() -> None:
    files = sorted(FIXTURES.glob("v*-*.json"))
    assert files
    for path in files:
        repo = Repo()
        result = _service(repo).import_file(path.read_bytes())
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert result.imported == doc["recipe_count"] == len(repo.added)
        for item, raw in zip(repo.added, doc["recipes"], strict=True):
            assert item.draft.title == raw["title"]
            assert item.draft.servings == raw["servings"]
            assert item.favourite == raw["favourite"]
            assert [
                {"amount": i.amount, "unit": i.unit, "name": i.name} for i in item.draft.ingredients
            ] == raw["ingredients"]
            assert list(item.draft.steps) == raw["steps"]
            assert item.created_at == datetime.fromisoformat(raw["created_at"])
            assert item.updated_at == datetime.fromisoformat(raw["updated_at"])


def test_skips_titles_already_in_the_app_and_renames_repeats() -> None:
    repo = Repo({title_key("Lemon Cake")})
    data = _doc([_recipe("lemon cake "), _recipe("Pancakes"), _recipe("pancakes"), _recipe("Pie")])

    result = _service(repo).import_file(data)

    assert (result.imported, result.skipped, result.renamed) == (3, 1, 1)
    assert result.skipped_titles == ("lemon cake",)
    assert [r.draft.title for r in repo.added] == ["Pancakes", "pancakes (2)", "Pie"]


def test_missing_dates_become_now() -> None:
    repo = Repo()
    _service(repo).import_file(_doc([_recipe("A")]))
    assert repo.added[0].created_at == FixedClock().now() == repo.added[0].updated_at
    assert repo.added[0].created_at.tzinfo == UTC


@pytest.mark.parametrize(
    "data",
    [
        b"\xff\xfe",
        b"not json",
        b"[1]",
        b'{"format": "other", "format_version": 1}',
        b'{"format": "home-cookbook-export"}',
        b'{"format": "home-cookbook-export", "format_version": true}',
        b'{"format": "home-cookbook-export", "format_version": 0}',
        _doc([_recipe("A")], recipe_count=2),
        _doc([_recipe("A")], recipes="x"),
        _doc(["x"]),
        _doc([_recipe("")]),
        _doc([_recipe("A", favourite="yes")]),
        _doc([_recipe("A", created_at="yesterday")]),
        _doc([_recipe("A", created_at=5)]),
        _doc([_recipe("A", servings=0)]),
    ],
)
def test_bad_files_are_refused_and_nothing_is_written(data: bytes) -> None:
    repo = Repo()
    with pytest.raises(NotAnExport):
        _service(repo).import_file(data)
    assert repo.added == []


def test_newer_version_is_refused() -> None:
    with pytest.raises(NewerExportFormat):
        upgrade({"format": "home-cookbook-export", "format_version": 2})


def test_clash_while_writing_is_import_interrupted() -> None:
    with pytest.raises(ImportInterrupted):
        _service(Repo(clash=True)).import_file(_doc([_recipe("A")]))


@pytest.mark.parametrize(
    "recipe",
    [
        _recipe("A", ingredients=[{"amount": 2, "unit": "cup", "name": "flour"}]),
        _recipe("A", ingredients=[{"amount": "1", "unit": 5, "name": "flour"}]),
        _recipe("A", ingredients=[{"amount": "1", "unit": "", "name": None}]),
        _recipe("A", ingredients=["2 eggs"]),
        _recipe("A", ingredients={"amount": "1"}),
        _recipe("A", steps=[5]),
        _recipe("A", steps="Cook"),
        _recipe(5),  # type: ignore[arg-type]
        _recipe("A", servings="4"),
        _recipe("A", servings=2.0),
        _recipe("A", servings=True),
        _recipe("A", favourite=1),
        _recipe("A", favourite=None),
    ],
    ids=[
        "amount-number",
        "unit-number",
        "name-null",
        "row-not-object",
        "ingredients-not-list",
        "step-number",
        "steps-not-list",
        "title-number",
        "servings-string",
        "servings-float",
        "servings-bool",
        "favourite-int",
        "favourite-null",
    ],
)
def test_import_file_wrong_field_type_refused_and_nothing_written(recipe: dict[str, Any]) -> None:
    repo = Repo()

    with pytest.raises(NotAnExport):
        _service(repo).import_file(_doc([_recipe("Good"), recipe]))

    assert repo.added == []


def test_import_file_missing_unit_and_amount_keys_accepted() -> None:
    repo = Repo()

    _service(repo).import_file(_doc([_recipe("A", ingredients=[{"name": "salt"}])]))

    assert repo.added[0].draft.ingredients[0].name == "salt"
    assert repo.added[0].draft.ingredients[0].amount is None


def test_import_file_rename_past_title_limit_refused_and_nothing_written() -> None:
    repo = Repo()
    long_title = "x" * 200

    with pytest.raises(NotAnExport):
        _service(repo).import_file(_doc([_recipe(long_title), _recipe(long_title)]))

    assert repo.added == []


def test_import_file_utf8_bom_accepted() -> None:
    repo = Repo()

    result = _service(repo).import_file(b"\xef\xbb\xbf" + _doc([_recipe("A")]))

    assert result.imported == 1


def test_import_file_offset_dates_stored_as_utc() -> None:
    repo = Repo()

    _service(repo).import_file(_doc([_recipe("A", created_at="2026-11-13T10:00:00+02:00")]))

    assert repo.added[0].created_at == datetime(2026, 11, 13, 8, 0, tzinfo=UTC)
    assert repo.added[0].created_at.utcoffset() == UTC.utcoffset(None)
