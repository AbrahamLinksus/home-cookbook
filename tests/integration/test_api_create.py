"""POST /api/recipes and the new/read pages (T-02)."""

from typing import Any

from flask.testing import FlaskClient

from cookbook.domain.models import Ingredient
from cookbook.web.pages import form_data, ingredient_line


def _recipe(title: str = "Pancakes", **overrides: Any) -> dict[str, Any]:
    recipe: dict[str, Any] = {
        "title": title,
        "servings": 8,
        "ingredients": [{"amount": "2", "unit": "cups", "name": "flour"}],
        "steps": ["Preheat oven to 200°C"],
    }
    return recipe | overrides


def _post(client: FlaskClient, recipe: dict[str, Any]) -> Any:
    return client.post("/api/recipes", json={"recipe": recipe})


def test_post_valid_recipe_returns_201_with_id_and_version(client: FlaskClient) -> None:
    response = _post(client, _recipe())

    assert response.status_code == 201
    assert response.get_json() == {"id": 1, "version": 1}
    assert "8 servings" in client.get("/").get_data(as_text=True)


def test_post_same_title_other_spelling_returns_409_and_saves_nothing(client: FlaskClient) -> None:
    _post(client, _recipe("Pancakes"))

    response = _post(client, _recipe(" pancakes "))

    assert response.status_code == 409
    body = response.get_json()
    assert body["error"] == "duplicate_title"
    assert body["existing_title"] == "Pancakes"
    assert body["message"] == (
        "You already have a recipe called 'Pancakes'. "
        "Please choose another name, e.g. 'Pancakes (Gran's)'"
    )
    assert _post(client, _recipe("Pancakes (Gran's)")).status_code == 201


def test_post_bad_fields_returns_422_with_message_per_field_key(client: FlaskClient) -> None:
    response = _post(
        client,
        _recipe(
            title="  ",
            servings=0,
            ingredients=[
                {"amount": "2-3", "unit": "", "name": "garlic"},
                {"amount": "1,000", "unit": "", "name": "salt"},
            ],
        ),
    )

    assert response.status_code == 422
    body = response.get_json()
    assert body["error"] == "invalid"
    assert body["fields"] == {
        "title": "Please fill this in",
        "servings": "Use a whole number of 1 or more",
        "ingredients.0.amount": "Enter one amount, e.g. 2 or 2½",
        "ingredients.1.amount": (
            "This amount is unclear; write e.g. 1000 for a thousand, or 1,0 for one"
        ),
    }


def test_post_malformed_body_returns_400_bad_request(client: FlaskClient) -> None:
    for payload in (b"{nope", b'["x"]', b'{"recipe": 3}'):
        response = client.post("/api/recipes", data=payload, content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error"] == "bad_request"


def test_view_page_for_unknown_recipe_is_404_page_with_message(client: FlaskClient) -> None:
    response = client.get("/recipes/999")

    assert response.status_code == 404
    assert "That recipe isn&#39;t here any more" in response.get_data(as_text=True)


def test_ingredient_line_carries_kitchen_text_and_exact_fraction() -> None:
    line = ingredient_line(Ingredient("1 1/2", "cups", "flour"))

    assert (line.amount_text, line.qty_num, line.qty_den) == ("1½", 3, 2)


def test_ingredient_line_without_amount_has_no_quantity() -> None:
    line = ingredient_line(Ingredient(None, "", "salt, to taste"))

    assert (line.amount_text, line.qty_num, line.qty_den) == (None, None, None)


def test_form_data_blank_and_filled() -> None:
    assert form_data(None) == {"title": "", "servings": 4, "ingredients": [], "steps": []}


def test_blank_row_before_invalid_amount_keeps_sent_index_in_error_key(
    client: FlaskClient,
) -> None:
    response = _post(
        client,
        _recipe(
            ingredients=[
                {"amount": "", "unit": "", "name": ""},
                {"amount": "2-3", "unit": "", "name": "eggs"},
            ],
            steps=["", "Mix"],
        ),
    )

    assert response.status_code == 422
    assert response.get_json()["fields"] == {
        "ingredients.1.amount": "Enter one amount, e.g. 2 or 2½"
    }


def test_blank_rows_are_dropped_and_order_is_kept_on_save(client: FlaskClient) -> None:
    response = _post(
        client,
        _recipe(
            ingredients=[
                {"amount": "", "unit": "", "name": ""},
                {"amount": "1 1/2", "unit": "cup", "name": "sugar"},
                {"amount": "", "unit": "", "name": "salt, to taste"},
            ],
            steps=["", "First", "Second"],
        ),
    )

    page = client.get(f"/recipes/{response.get_json()['id']}").get_data(as_text=True)
    assert page.index("1½") < page.index("salt, to taste")
    assert page.index("First") < page.index("Second")


def test_amounts_typed_in_every_form_display_in_kitchen_form(client: FlaskClient) -> None:
    typed = ["2", "2.5", "1/2", "1 1/2", "½"]
    response = _post(
        client,
        _recipe(
            ingredients=[{"amount": a, "unit": "", "name": f"i{n}"} for n, a in enumerate(typed)]
        ),
    )

    page = client.get(f"/recipes/{response.get_json()['id']}").get_data(as_text=True)
    assert [
        ingredient_line(Ingredient(amount=a, unit="", name="x")).amount_text for a in typed
    ] == [
        "2",
        "2½",
        "½",
        "1½",
        "½",
    ]
    assert 'data-text="2½"' in page


def test_read_view_reopened_shows_exactly_what_was_typed(client: FlaskClient) -> None:
    steps = ["Preheat oven to 200°C.", "Rub butter.", "Slice.", "Fill.", "Bake."]
    response = _post(client, _recipe("Grandma's Apple Pie", steps=steps))
    url = f"/recipes/{response.get_json()['id']}"

    first = client.get(url).get_data(as_text=True)
    second = client.get(url).get_data(as_text=True)

    assert first == second
    assert "Grandma&#39;s Apple Pie" in first
    assert '<span data-testid="servings">8</span>' in first
    for text in steps:
        assert text in first
