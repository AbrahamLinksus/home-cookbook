"""Backup service (LLD §5). Export and import arrive with their own tasks."""

import json
from dataclasses import dataclass

from cookbook.domain.ports import Clock, RecipeRepository
from cookbook.services.backup.formats import to_document


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
