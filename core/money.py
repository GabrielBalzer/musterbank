"""Amount helpers shared by the bank modules. All stored amounts are integer cents."""
from decimal import Decimal


def to_cents(amount):
    """Convert a euro amount (float, int, str or Decimal) to integer cents."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("not an amount: %r" % (amount,))
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("not an amount: %r" % (amount,))
    return int(value * 100)


def from_cents(cents):
    return Decimal(cents) / 100


def format_eur(cents):
    """1234567 -> '12.345,67 EUR' (German notation)."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    euros, rest = divmod(cents, 100)
    euro_str = "{:,}".format(euros).replace(",", ".")
    return "%s%s,%02d EUR" % (sign, euro_str, rest)


def parse_eur(text):
    """Parse user input such as '1.234,50' or '12,34' to integer cents."""
    cleaned = text.strip().replace("EUR", "").replace("€", "").strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    return to_cents(cleaned)
