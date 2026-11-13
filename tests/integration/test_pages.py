"""GET / and the error page render (T-01)."""

import html as html_lib
import json
import re
from collections.abc import Callable

from flask.testing import FlaskClient

from cookbook.adapters.sqlite_repo import SqliteRecipeRepository
from cookbook.app.config import Settings
from cookbook.domain.models import NewRecipe
from cookbook.web import messages


def test_list_page_empty_app_shows_empty_state_and_menu(client: FlaskClient) -> None:
    response = client.get("/", environ_overrides={"REMOTE_ADDR": "192.168.1.20"})

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No recipes yet" in html
    assert "Add recipe" in html
    assert "Export all recipes" in html
    assert "Import recipes" in html


def test_list_page_with_recipes_shows_favourites_group_first(
    client: FlaskClient, settings: Settings, new_recipe: Callable[..., NewRecipe]
) -> None:
    repo = SqliteRecipeRepository(settings.db_path)
    repo.add(new_recipe("Lemon Cake"))
    repo.add(new_recipe("Apple Pie", favourite=True))

    html = client.get("/").get_data(as_text=True)

    assert "No recipes yet" not in html
    assert html.index("Favourites") < html.index("Apple Pie") < html.index("Lemon Cake")
    assert "4 servings" in html


def test_list_page_escapes_recipe_title(
    client: FlaskClient, settings: Settings, new_recipe: Callable[..., NewRecipe]
) -> None:
    SqliteRecipeRepository(settings.db_path).add(new_recipe("<script>x</script>"))

    html = client.get("/").get_data(as_text=True)

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_unknown_page_renders_error_page_with_link_home(client: FlaskClient) -> None:
    response = client.get("/nope")

    html = response.get_data(as_text=True)
    assert response.status_code == 404
    assert "That page isn&#39;t here" in html
    assert 'href="/"' in html


def _ui_texts(page: str) -> object:
    found = re.search(r"<body data-texts='([^']*)'>", page)
    assert found is not None
    return json.loads(html_lib.unescape(found[1]))


def test_list_page_carries_browser_texts_from_messages(client: FlaskClient) -> None:
    page = client.get("/").get_data(as_text=True)
    assert _ui_texts(page) == messages.UI_TEXTS


def test_error_page_carries_browser_texts_from_messages(client: FlaskClient) -> None:
    page = client.get("/no-such-page").get_data(as_text=True)
    assert _ui_texts(page) == messages.UI_TEXTS


def test_restored_renamed_uses_the_shared_browser_text() -> None:
    expected = "'Soup' is back as 'Soup (2)' because another recipe now has its name"
    assert messages.restored_renamed("Soup", "Soup (2)") == expected
