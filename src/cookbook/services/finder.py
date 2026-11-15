"""Recipe finder (LLD §4): live search over live recipes, ordered like the list."""

from cookbook.domain.models import RecipeSummary, SearchBy
from cookbook.domain.ports import RecipeRepository
from cookbook.domain.rules import list_order
from cookbook.domain.search import matches


class RecipeFinder:
    def __init__(self, repo: RecipeRepository) -> None:
        self._repo = repo

    def search(self, query: str, by: SearchBy) -> list[RecipeSummary]:
        """Live recipes matching `query`; favourites first, then A-Z. Blank query keeps all."""
        found = (r for r in self._repo.list_live() if matches(r, query, by))
        return list_order(found)
