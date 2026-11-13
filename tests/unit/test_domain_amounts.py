"""parse_amount and display_amount (LLD §1.4, S-01)."""

from fractions import Fraction

import pytest

from cookbook.domain.amounts import UnclearAmountError, display_amount, parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2", Fraction(2)),
        ("2.5", Fraction(5, 2)),
        ("0,5", Fraction(1, 2)),
        ("2,25", Fraction(9, 4)),
        ("1,0", Fraction(1)),
        ("1,0000", Fraction(1)),
        ("1.000", Fraction(1)),
        ("1/2", Fraction(1, 2)),
        ("1 1/2", Fraction(3, 2)),
        ("½", Fraction(1, 2)),
        ("1 ½", Fraction(3, 2)),
        ("1½", Fraction(3, 2)),
        ("2½", Fraction(5, 2)),
        (" ¾ ", Fraction(3, 4)),
    ],
)
def test_parse_amount_valid_text_returns_value(text: str, expected: Fraction) -> None:
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["2-3", "2 to 3", "0", "abc", "", "1/0", "0/5", "2 ½ ½", "-1"])
def test_parse_amount_invalid_text_raises(text: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        parse_amount(text)


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        ("2.5", "2½"),
        ("1 1/2", "1½"),
        ("2", "2"),
        ("1/2", "½"),
        ("½", "½"),
        ("0.3", "0.3"),
        ("0,75", "¾"),
    ],
)
def test_display_amount_shows_kitchen_form(text: str, shown: str) -> None:
    assert display_amount(text) == shown


@pytest.mark.parametrize("text", ["1,000", "12,500", " 0,250 "])
def test_parse_amount_comma_with_three_digits_is_unclear(text: str) -> None:
    with pytest.raises(UnclearAmountError):
        parse_amount(text)


def test_unclear_amount_is_a_value_error() -> None:
    assert issubclass(UnclearAmountError, ValueError)
