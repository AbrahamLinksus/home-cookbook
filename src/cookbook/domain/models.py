"""Recipe data types (LLD §1.1). Frozen, slotted; datetimes are timezone-aware UTC."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Ingredient:
    amount: str | None  # exactly as typed (trimmed); None when the line has no amount
    unit: str
    name: str


@dataclass(frozen=True, slots=True)
class RecipeDraft:
    title: str
    servings: int
    ingredients: tuple[Ingredient, ...]
    steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NewRecipe:
    draft: RecipeDraft
    favourite: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Recipe:
    id: int
    title: str
    servings: int
    ingredients: tuple[Ingredient, ...]
    steps: tuple[str, ...]
    favourite: bool
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    def draft(self) -> RecipeDraft:
        return RecipeDraft(self.title, self.servings, self.ingredients, self.steps)


@dataclass(frozen=True, slots=True)
class RecipeSummary:
    id: int
    title: str
    servings: int
    favourite: bool


class SearchBy(StrEnum):
    NAME = "name"
    INGREDIENT = "ingredient"
