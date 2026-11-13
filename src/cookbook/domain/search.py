"""Forgiving text matching for search (LLD §1.4, D-24)."""

import unicodedata

from cookbook.domain.models import Recipe, SearchBy


def normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    without_apostrophes = stripped.replace("'", "").replace("\u2019", "")
    return " ".join(without_apostrophes.casefold().split())


def matches(recipe: Recipe, query: str, by: SearchBy) -> bool:
    words = normalise(query).split()
    if not words:
        return True
    if by is SearchBy.NAME:
        targets = [normalise(recipe.title)]
    else:
        targets = [normalise(ingredient.name) for ingredient in recipe.ingredients]
    return any(all(word in target for word in words) for target in targets)
