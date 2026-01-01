from decimal import Decimal

import pytest

from core.money import format_eur, from_cents, parse_eur, to_cents


@pytest.mark.parametrize("amount,cents", [(100.0, 10000), (49.99, 4999), (12.34, 1234), (0.07, 7), (3, 300)])
def test_to_cents(amount, cents):
    assert to_cents(amount) == cents


def test_to_cents_accepts_decimal_and_text():
    assert to_cents(Decimal("7.77")) == 777
    assert to_cents("23.45") == 2345


@pytest.mark.parametrize("bad", ["abc", float("nan"), float("inf")])
def test_to_cents_rejects_garbage(bad):
    with pytest.raises(ValueError):
        to_cents(bad)


def test_from_cents():
    assert from_cents(1250) == Decimal("12.50")


def test_format_eur():
    assert format_eur(1234567) == "12.345,67 EUR"
    assert format_eur(-5) == "-0,05 EUR"
    assert format_eur(0) == "0,00 EUR"


def test_parse_eur():
    assert parse_eur("1.234,50") == 123450
    assert parse_eur("99,95 EUR") == 9995
    assert parse_eur("0,07") == 7
