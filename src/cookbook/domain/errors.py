# ruff: noqa: N818
"""Domain exceptions (LLD §1.1). Mapped to HTTP only in web/errors.py."""


class CookbookError(Exception):
    """Base of every expected, named failure."""


class InvalidRecipe(CookbookError):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(f"invalid recipe: {sorted(fields)}")
        self.fields = fields


class DuplicateTitle(CookbookError):
    def __init__(self, existing_title: str) -> None:
        super().__init__("a live recipe already has this title")
        self.existing_title = existing_title


class RecipeNotFound(CookbookError):
    pass


class ChangedElsewhere(CookbookError):
    def __init__(self, current_version: int) -> None:
        super().__init__(f"recipe is now at version {current_version}")
        self.current_version = current_version


class DeletedElsewhere(CookbookError):
    pass


class UndoExpired(CookbookError):
    def __init__(self, title: str) -> None:
        super().__init__("undo window is over")
        self.title = title


class NotAnExport(CookbookError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class NewerExportFormat(CookbookError):
    def __init__(self, found: int, supported: int) -> None:
        super().__init__(f"export format {found} is newer than supported {supported}")
        self.found = found
        self.supported = supported


class ImportInterrupted(CookbookError):
    pass
