"""IBAN handling (ISO 13616)."""
import re

BANK_CODE = "01234500"

_IBAN_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]+$")


def _to_digits(text):
    out = []
    for ch in text:
        if ch.isdigit():
            out.append(ch)
        else:
            out.append(str(ord(ch) - 55))
    return "".join(out)


def _mod97(text):
    rest = 0
    for ch in _to_digits(text):
        rest = (rest * 10 + int(ch)) % 97
    return rest


def normalize_iban(iban):
    return iban.replace(" ", "").upper()


def validate_iban(iban):
    if not iban:
        return False
    s = normalize_iban(iban)[:22]
    if not _IBAN_RE.match(s):
        return False
    return _mod97(s[4:] + s[:4]) == 1


def build_de_iban(bank_code, account_number):
    """Build a German IBAN from bank code and account number."""
    bban = bank_code.zfill(8) + str(account_number).zfill(10)
    check = 98 - _mod97(bban + "DE00")
    return "DE%02d%s" % (check, bban)


def format_iban(iban):
    s = normalize_iban(iban)
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def mask_iban(iban):
    s = normalize_iban(iban)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]
