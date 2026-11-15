"""Search over HTTP: list page, fragment, no-JS form, timing (T-07, S-08, S-10)."""

import time
from collections.abc import Callable

import pytest
from flask.testing import FlaskClient

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.models import NewRecipe


@pytest.fixture
def repo(settings: Settings) -> SqliteRecipeRepository:
    r = SqliteRecipeRepository(settings.db_path)
    r.init_schema()
    return r


@pytest.fixture
def seeded(repo: SqliteRecipeRepository, new_recipe: Callable[..., NewRecipe]) -> None:
    for title in ("Grandma's Apple Pie", "Shepherd's Pie", "Lemon Cake"):
        repo.add(new_recipe(title))


def _get(client: FlaskClient, url: str) -> str:
    response = client.get(url)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_full_page_no_js_form_path_filters(client: FlaskClient, seeded: None) -> None:
    html = _get(client, "/?q=pie&by=name")

    assert "Shepherd&#39;s Pie" in html
    assert "Grandma&#39;s Apple Pie" in html
    assert "Lemon Cake" not in html
    assert 'method="get"' in html
    assert 'value="pie"' in html


def test_fragment_filters_and_has_no_page_chrome(client: FlaskClient, seeded: None) -> None:
    html = _get(client, "/recipes/_list?q=pie&by=name")

    assert "Shepherd&#39;s Pie" in html
    assert "Lemon Cake" not in html
    assert "<html" not in html
    assert "search-form" not in html


def test_unknown_by_falls_back_to_name(client: FlaskClient, seeded: None) -> None:
    html = _get(client, "/recipes/_list?q=lemon&by=bogus")

    assert "Lemon Cake" in html
    page = _get(client, "/?q=lemon&by=bogus")
    assert "Lemon Cake" in page


def test_by_ingredient_via_http(client: FlaskClient, seeded: None) -> None:
    html = _get(client, "/recipes/_list?q=flour&by=ingredient")

    assert html.count('data-testid="recipe-row"') == 3
    assert "No recipes match" not in _get(client, "/recipes/_list?q=salt&by=ingredient")
    assert "No recipes match 'cup'" in _get(client, "/recipes/_list?q=cup&by=ingredient")


def test_no_match_shows_message_and_clear_search(client: FlaskClient, seeded: None) -> None:
    for url in ("/?q=soup", "/recipes/_list?q=soup"):
        html = _get(client, url)
        assert "No recipes match 'soup'" in html
        assert 'href="/"' in html
        assert "Clear search" in html


def test_no_match_message_escapes_query(client: FlaskClient, seeded: None) -> None:
    html = _get(client, "/recipes/_list?q=%3Cb%3Ex")

    assert "<b>x" not in html
    assert "&lt;b&gt;x" in html


def test_clear_search_brings_back_full_list(client: FlaskClient, seeded: None) -> None:
    html = _get(client, "/")

    assert html.count('data-testid="recipe-row"') == 3


def test_empty_app_search_shows_no_recipes_yet_without_form(client: FlaskClient) -> None:
    html = _get(client, "/?q=soup")

    assert "No recipes yet" in html
    assert 'data-testid="search-form"' not in html


def test_results_favourites_first(
    client: FlaskClient, repo: SqliteRecipeRepository, new_recipe: Callable[..., NewRecipe]
) -> None:
    repo.add(new_recipe("Apple Pie"))
    repo.add(new_recipe("Zed Pie", favourite=True))

    html = _get(client, "/recipes/_list?q=pie")

    assert html.index("Zed Pie") < html.index("Apple Pie")
    assert html.index("Favourites") < html.index("Zed Pie")


def test_500_recipes_search_under_one_second(
    client: FlaskClient, repo: SqliteRecipeRepository, new_recipe: Callable[..., NewRecipe]
) -> None:
    repo.add_many([new_recipe(f"Recipe {i:03d}") for i in range(500)])

    started = time.perf_counter()
    html = _get(client, "/recipes/_list?q=recipe 49&by=name")
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0
    assert html.count('data-testid="recipe-row"') == 15
    started = time.perf_counter()
    _get(client, "/recipes/_list?q=flour&by=ingredient")
    assert time.perf_counter() - started < 1.0
