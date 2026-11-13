"""Web layer: the services handed to routes (LLD §6.1)."""

from dataclasses import dataclass

from flask import current_app

from cookbook.services.backup.service import BackupService
from cookbook.services.finder import RecipeFinder
from cookbook.services.keeper import RecipeKeeper


@dataclass(frozen=True)
class Services:
    keeper: RecipeKeeper
    finder: RecipeFinder
    backup: BackupService


def services() -> Services:
    found: Services = current_app.extensions["cookbook"]
    return found
