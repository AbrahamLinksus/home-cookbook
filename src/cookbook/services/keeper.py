"""Recipe keeper (LLD §3). T-01 holds the constructor and the list; later tasks add the rest."""

from datetime import timedelta
from typing import Final

from cookbook.domain.errors import RecipeNotFound
from cookbook.domain.models import NewRecipe, Recipe, RecipeDraft, RecipeSummary
from cookbook.domain.ports import Clock, RecipeRepository
from cookbook.domain.rules import list_order

UNDO_GRACE_SECONDS: Final = 2


class RecipeKeeper:
    def __init__(self, repo: RecipeRepository, clock: Clock, undo_seconds: int) -> None:
        self._repo = repo
        self._clock = clock
        self._undo_seconds = undo_seconds

    def list_recipes(self) -> list[RecipeSummary]:
        """Favourites first, then A-Z; purges deletes whose undo window is over."""
        window = timedelta(seconds=self._undo_seconds + UNDO_GRACE_SECONDS)
        self._repo.purge_deleted_before(self._clock.now() - window)
        return list_order(self._repo.list_live())

    def get(self, recipe_id: int) -> Recipe:
        """The live recipe; RecipeNotFound when missing or waiting out its undo window."""
        recipe = self._repo.get(recipe_id)
        if recipe is None:
            raise RecipeNotFound(str(recipe_id))
        return recipe

    def create(self, draft: RecipeDraft) -> Recipe:
        """Save a new recipe; DuplicateTitle when a live recipe has the same title."""
        now = self._clock.now()
        return self._repo.add(NewRecipe(draft, favourite=False, created_at=now, updated_at=now))
