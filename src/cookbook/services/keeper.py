"""Recipe keeper (LLD §3). T-01 holds the constructor and the list; later tasks add the rest."""

from datetime import timedelta
from typing import Final

from cookbook.domain.errors import (
    ChangedElsewhere,
    DeletedElsewhere,
    DuplicateTitle,
    RecipeNotFound,
    UndoExpired,
)
from cookbook.domain.models import NewRecipe, Recipe, RecipeDraft, RecipeSummary
from cookbook.domain.ports import Clock, RecipeRepository
from cookbook.domain.rules import free_title, list_order

UNDO_GRACE_SECONDS: Final = 2
RESTORE_ATTEMPTS: Final = 3


class RecipeKeeper:
    def __init__(self, repo: RecipeRepository, clock: Clock, undo_seconds: int) -> None:
        self._repo = repo
        self._clock = clock
        self._undo_seconds = undo_seconds

    @property
    def undo_seconds(self) -> int:
        return self._undo_seconds

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

    def update(self, recipe_id: int, draft: RecipeDraft, base_version: int) -> Recipe:
        """Save an edit made from `base_version`.

        DeletedElsewhere when the recipe is gone or waiting out its undo window;
        ChangedElsewhere when a save by another device came first; DuplicateTitle when
        another live recipe has the title. Starring never bumps `version` (LLD §3.5).
        """
        current = self._repo.get(recipe_id, include_deleted=True)
        if current is None or current.deleted_at is not None:
            raise DeletedElsewhere(str(recipe_id))
        if current.version != base_version:
            raise ChangedElsewhere(current.version)
        saved = self._repo.update_if_version(recipe_id, draft, base_version, self._clock.now())
        if saved is None:
            return self._lost_race(recipe_id)
        return saved

    def _lost_race(self, recipe_id: int) -> Recipe:
        """update_if_version matched no row: someone saved or deleted in between."""
        now_current = self._repo.get(recipe_id)
        if now_current is None:
            raise DeletedElsewhere(str(recipe_id))
        raise ChangedElsewhere(now_current.version)

    def delete(self, recipe_id: int) -> Recipe:
        """Hide the recipe for the undo window; any earlier pending delete becomes final."""
        deleted = self._repo.mark_deleted(recipe_id, self._clock.now())
        if deleted is None:
            raise RecipeNotFound(str(recipe_id))
        return deleted

    def restore(self, recipe_id: int) -> tuple[Recipe, str | None]:
        """Undo a delete; the second item is the new title when the old one was taken meanwhile."""
        recipe = self._repo.get(recipe_id, include_deleted=True)
        if recipe is None:
            raise UndoExpired("")
        if recipe.deleted_at is None:
            return recipe, None
        window = timedelta(seconds=self._undo_seconds + UNDO_GRACE_SECONDS)
        if self._clock.now() > recipe.deleted_at + window:
            raise UndoExpired(recipe.title)
        return self._unmark(recipe)

    def _unmark(self, recipe: Recipe) -> tuple[Recipe, str | None]:
        for _attempt in range(RESTORE_ATTEMPTS):
            title = free_title(recipe.title, self._repo.live_title_keys())
            try:
                restored = self._repo.unmark_deleted(recipe.id, title)
            except DuplicateTitle:
                continue  # a save took the name between the check and the write
            if restored is None:
                return self._restored_elsewhere(recipe)
            return restored, (title if title != recipe.title else None)
        raise UndoExpired(recipe.title)

    def _restored_elsewhere(self, recipe: Recipe) -> tuple[Recipe, str | None]:
        """unmark_deleted found no pending row: another Undo won (live) or it was purged."""
        live = self._repo.get(recipe.id)
        if live is None:
            raise UndoExpired(recipe.title)
        return live, None
