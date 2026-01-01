"""Text and CSV output for statements."""
import csv
import io

from core.iban import format_iban
from core.money import format_eur

LINE_WIDTH = 96


def _de_date(iso):
    return "%s.%s.%s" % (iso[8:10], iso[5:7], iso[0:4])


def render_text(statement):
    out = []
    out.append("Musterbank AG - Kontoauszug")
    out.append("=" * LINE_WIDTH)
    out.append("Konto:    %s" % format_iban(statement["iban"]))
    out.append("Inhaber:  %s" % statement["holder"])
    out.append("Zeitraum: %s bis %s" % (_de_date(statement["from_date"]), _de_date(statement["to_date"])))
    out.append("-" * LINE_WIDTH)
    out.append("%-10s %-10s %-32s %-22s %18s" % ("Buchung", "Valuta", "Empfaenger/Auftraggeber", "Verwendungszweck", "Betrag"))
    out.append("-" * LINE_WIDTH)
    out.append("%-77s %18s" % ("Anfangssaldo", format_eur(statement["opening_cents"])))
    for line in statement["lines"]:
        out.append("%-10s %-10s %-32s %-22s %18s" % (
            _de_date(line["booking_date"]),
            _de_date(line["value_date"]),
            line["counterparty"][:32],
            line["purpose"][:22],
            line["amount"],
        ))
    out.append("%-77s %18s" % ("Endsaldo", format_eur(statement["closing_cents"])))
    out.append("-" * LINE_WIDTH)
    out.append("Haben: %s  Soll: %s" % (format_eur(statement["credits_cents"]), format_eur(statement["debits_cents"])))
    return "\n".join(out) + "\n"


def render_csv(statement):
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(["Buchungstag", "Valuta", "Betrag", "Art", "Name", "IBAN", "Verwendungszweck"])
    for line in statement["lines"]:
        cents = line["amount_cents"]
        amount = "%s%d,%02d" % ("-" if cents < 0 else "", abs(cents) // 100, abs(cents) % 100)
        writer.writerow([line["booking_date"], line["value_date"], amount, line["kind"], line["counterparty"],
                         line["counterparty_iban"], line["purpose"]])
    return buf.getvalue()
