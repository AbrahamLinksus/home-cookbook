"""Recipe finder (LLD §4). Search behaviour arrives with its own task."""

from cookbook.domain.ports import RecipeRepository


class RecipeFinder:
    def __init__(self, repo: RecipeRepository) -> None:
        self._repo = repo
