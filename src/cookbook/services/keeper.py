"""Recipe keeper (LLD §3). T-01 holds the constructor and the list; later tasks add the rest."""

from datetime import timedelta
from typing import Final

from cookbook.domain.models import RecipeSummary
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
