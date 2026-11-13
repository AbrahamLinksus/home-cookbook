"""Ingredient amounts: parsing and kitchen-style display (LLD §1.4, D-22)."""

import re
from fractions import Fraction

GLYPHS: dict[str, Fraction] = {
    "¼": Fraction(1, 4),
    "½": Fraction(1, 2),
    "¾": Fraction(3, 4),
    "⅓": Fraction(1, 3),
    "⅔": Fraction(2, 3),
    "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8),
    "⅝": Fraction(5, 8),
    "⅞": Fraction(7, 8),
}
_GLYPH_OF = {value: glyph for glyph, value in GLYPHS.items()}
_CLASS = "".join(GLYPHS)

_DECIMAL = re.compile(r"(\d+)(?:([.,])(\d+))?")
_THOUSANDS_DIGITS = 3  # "1,000": a thousand or one? (D-33)


class UnclearAmountError(ValueError):
    """A comma followed by exactly three digits, e.g. "1,000" (D-33)."""


_FRACTION = re.compile(r"(\d+)/(\d+)")
_MIXED = re.compile(r"(\d+)\s+(\d+)/(\d+)")
_WITH_GLYPH = re.compile(rf"(\d*)\s*([{_CLASS}])")


def parse_amount(text: str) -> Fraction:
    """Return the one positive number written in `text`; raise ValueError otherwise."""
    value = _parse(text.strip())
    if value <= 0:
        raise ValueError("amount must be more than zero")
    return value


def _parse(text: str) -> Fraction:
    if m := _DECIMAL.fullmatch(text):
        if m[2] == "," and len(m[3]) == _THOUSANDS_DIGITS:
            raise UnclearAmountError(f"unclear amount: {text!r}")
        return Fraction(f"{m[1]}.{m[3]}") if m[3] else Fraction(int(m[1]))
    if m := _FRACTION.fullmatch(text):
        return Fraction(int(m[1]), _nonzero(int(m[2])))
    if m := _MIXED.fullmatch(text):
        return int(m[1]) + Fraction(int(m[2]), _nonzero(int(m[3])))
    if m := _WITH_GLYPH.fullmatch(text):
        return int(m[1] or 0) + GLYPHS[m[2]]
    raise ValueError(f"not a single amount: {text!r}")


def _nonzero(denominator: int) -> int:
    if denominator == 0:
        raise ValueError("zero denominator")
    return denominator


def display_amount(text: str) -> str:
    """Kitchen form of a valid amount; the typed text when no tidy form exists."""
    value = parse_amount(text)
    whole, rest = divmod(value, 1)
    if rest == 0:
        return str(whole)
    glyph = _GLYPH_OF.get(rest)
    if glyph is None:
        return text.strip()
    return f"{whole}{glyph}" if whole else glyph
