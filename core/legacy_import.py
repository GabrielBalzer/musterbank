"""Import of booking files in the fixed-width format of the former batch system.

Record layout (one booking per line, 112 characters):
    0-21   IBAN
   22-29   booking date YYYYMMDD
   30-37   value date YYYYMMDD
   38-49   amount in cents, zero padded
   50      sign, 'S' debit or 'H' credit
   51-54   transaction key
   55-111  purpose, padded with blanks
Lines starting with 'V' are the header, the last line starting with 'E' holds the record
count (positions 1-8) and the control total in cents (positions 9-23).
"""
from datetime import datetime, timezone

from core.dates import parse_date
from core.errors import UnknownAccount

RECORD_LENGTH = 112
KEY_TO_KIND = {
    "0051": "TRANSFER_IN",
    "0020": "TRANSFER_OUT",
    "0005": "DIRECT_DEBIT",
    "0053": "SALARY",
    "0082": "CASH_IN",
    "0083": "CASH_OUT",
    "0004": "CARD",
}


class LegacyFormatError(Exception):
    pass


def _parse_day(text):
    return parse_date("%s-%s-%s" % (text[0:4], text[4:6], text[6:8]))


def parse_record(line):
    if len(line) != RECORD_LENGTH:
        raise LegacyFormatError("record has %d characters instead of %d" % (len(line), RECORD_LENGTH))
    sign = line[50]
    if sign not in ("S", "H"):
        raise LegacyFormatError("unknown sign %r" % sign)
    key = line[51:55]
    if key not in KEY_TO_KIND:
        raise LegacyFormatError("unknown transaction key %r" % key)
    amount = int(line[38:50])
    return {
        "iban": line[0:22],
        "booking_date": _parse_day(line[22:30]),
        "value_date": _parse_day(line[30:38]),
        "amount_cents": amount if sign == "H" else -amount,
        "kind": KEY_TO_KIND[key],
        "purpose": line[55:112].rstrip(),
    }


def parse_file(text):
    lines = [l.rstrip("\r\n") for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("V"):
        raise LegacyFormatError("header record is missing")
    if not lines[-1].startswith("E"):
        raise LegacyFormatError("trailer record is missing")
    records = [parse_record(l) for l in lines[1:-1]]
    trailer = lines[-1]
    expected_count = int(trailer[1:9])
    expected_total = int(trailer[9:24])
    if expected_count != len(records):
        raise LegacyFormatError("trailer announces %d records, file has %d" % (expected_count, len(records)))
    total = sum(abs(r["amount_cents"]) for r in records)
    if expected_total != total:
        raise LegacyFormatError("control total %d does not match %d" % (expected_total, total))
    return records


class LegacyImporter:
    def __init__(self, bank):
        self.bank = bank

    def import_text(self, text):
        """Book a whole file in one transaction. Unknown accounts abort the import."""
        records = parse_file(text)
        with self.bank.transaction():
            for rec in records:
                try:
                    account = self.bank.getAccount(rec["iban"])
                except UnknownAccount:
                    raise LegacyFormatError("unknown account %s" % rec["iban"])
                moment = datetime(rec["booking_date"].year, rec["booking_date"].month, rec["booking_date"].day,
                                  12, 0, tzinfo=timezone.utc)
                self.bank.post_booking(account["iban"], rec["amount_cents"], rec["kind"], at=moment,
                                       value_date=rec["value_date"], purpose=rec["purpose"])
        return len(records)


def format_record(iban, booking_day, value_day, amount_cents, key, purpose=""):
    sign = "H" if amount_cents >= 0 else "S"
    return "%-22s%s%s%012d%s%s%-57s" % (iban, booking_day.strftime("%Y%m%d"), value_day.strftime("%Y%m%d"),
                                        abs(amount_cents), sign, key, purpose[:57])


def format_file(records):
    """Build a file from (iban, booking_day, value_day, amount_cents, key, purpose) tuples."""
    lines = ["V" + "MUSTERBANK".ljust(RECORD_LENGTH - 1)]
    total = 0
    for rec in records:
        lines.append(format_record(*rec))
        total += abs(rec[3])
    lines.append("E%08d%015d" % (len(records), total))
    return "\n".join(lines) + "\n"
