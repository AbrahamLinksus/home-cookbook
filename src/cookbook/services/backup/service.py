"""Backup service (LLD §5): export every recipe, import any past version all or nothing."""

import json
from dataclasses import dataclass, replace
from typing import Any

from cookbook.domain.errors import DuplicateTitle, ImportInterrupted, NotAnExport
from cookbook.domain.models import NewRecipe
from cookbook.domain.ports import Clock, RecipeRepository
from cookbook.domain.rules import MAX_TITLE, free_title, title_key
from cookbook.services.backup.formats import from_document, to_document, upgrade


@dataclass(frozen=True)
class ExportFile:
    filename: str
    content: bytes


@dataclass(frozen=True)
class ImportResult:
    imported: int
    skipped: int
    renamed: int
    skipped_titles: tuple[str, ...] = ()


class BackupService:
    def __init__(self, repo: RecipeRepository, clock: Clock, app_version: str) -> None:
        self._repo = repo
        self._clock = clock
        self._app_version = app_version

    def export_all(self) -> ExportFile:
        """Every live recipe as one UTF-8 JSON file named for the local date."""
        now = self._clock.now()
        document = to_document(self._repo.list_live(), now, self._app_version)
        text = json.dumps(document, ensure_ascii=False, indent=2)
        return ExportFile(f"cookbook-{now.astimezone():%Y-%m-%d}.json", text.encode("utf-8"))

    def import_file(self, data: bytes) -> ImportResult:
        """Add every recipe of an export file, or change nothing."""
        incoming = from_document(upgrade(_load(data)), self._clock.now())
        to_add, skipped, renamed = _plan(incoming, self._repo.live_title_keys())
        try:
            self._repo.add_many(to_add)
        except DuplicateTitle as error:
            raise ImportInterrupted from error
        return ImportResult(len(to_add), len(skipped), renamed, tuple(skipped))


def _load(data: bytes) -> dict[str, Any]:
    try:
        doc = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise NotAnExport("not readable JSON") from error
    if not isinstance(doc, dict):
        raise NotAnExport("not an object")
    return doc


def _plan(incoming: list[NewRecipe], taken: set[str]) -> tuple[list[NewRecipe], list[str], int]:
    """Split file recipes into those to add (repeats renamed), skipped titles, rename count."""
    occupied = set(taken)
    to_add: list[NewRecipe] = []
    skipped: list[str] = []
    renamed = 0
    for item in incoming:
        title = item.draft.title
        if title_key(title) in taken:
            skipped.append(title)
            continue
        free = free_title(title, occupied)
        if len(free) > MAX_TITLE:
            raise NotAnExport("renamed title too long")
        if free != title:
            renamed += 1
            item = replace(item, draft=replace(item.draft, title=free))  # noqa: PLW2901
        occupied.add(title_key(free))
        to_add.append(item)
    return to_add, skipped, renamed
