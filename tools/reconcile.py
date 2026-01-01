"""Compare stored balances with the booking journal and report differences."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bank import BankCore  # noqa: E402
from core.money import format_eur  # noqa: E402


def find_differences(bank):
    rows = bank.db.execute(
        "SELECT a.iban, a.balance_cents, COALESCE(SUM(b.amount_cents), 0) AS journal_cents"
        " FROM accounts a LEFT JOIN bookings b ON b.account_id = a.id"
        " GROUP BY a.id, a.iban, a.balance_cents HAVING a.balance_cents != journal_cents ORDER BY a.id"
    ).fetchall()
    return [dict(row) for row in rows]


def find_orphan_transfers(bank):
    rows = bank.db.execute(
        "SELECT t.id, t.amount_cents, COUNT(b.id) AS legs, COALESCE(SUM(b.amount_cents), 0) AS net_cents"
        " FROM transfers t LEFT JOIN bookings b ON b.transfer_id = t.id"
        " GROUP BY t.id, t.amount_cents HAVING legs != 2 OR net_cents != 0 ORDER BY t.id"
    ).fetchall()
    return [dict(row) for row in rows]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reconcile balances and journal")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    args = parser.parse_args(argv)
    bank = BankCore(args.db)
    try:
        differences = find_differences(bank)
        orphans = find_orphan_transfers(bank)
        total = bank.total_balance()
    finally:
        bank.close()
    for line in differences:
        print("%s Saldo %s, Journal %s" % (line["iban"], format_eur(line["balance_cents"]),
                                           format_eur(line["journal_cents"])))
    for line in orphans:
        print("Überweisung %d: %d Buchungen, Saldo %s" % (line["id"], line["legs"], format_eur(line["net_cents"])))
    print("Summe aller Salden: %s" % format_eur(total))
    print("%d Saldendifferenzen, %d unvollständige Überweisungen" % (len(differences), len(orphans)))
    return 1 if differences or orphans else 0


if __name__ == "__main__":
    sys.exit(main())
