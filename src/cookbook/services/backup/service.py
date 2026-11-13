"""Backup service (LLD §5). Export and import arrive with their own tasks."""

from dataclasses import dataclass

from cookbook.domain.ports import Clock, RecipeRepository


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
