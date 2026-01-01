"""Back office command line: look up customers and accounts, print reports."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bank import BankCore  # noqa: E402
from core.dunning import DunningProcessor  # noqa: E402
from core.iban import format_iban  # noqa: E402
from core.money import format_eur, parse_eur  # noqa: E402
from core.reports import ReportGenerator  # noqa: E402


def cmd_customer(bank, args):
    rows = bank.find_customers(args.name)
    for row in rows:
        print("%s  %-36s %s %s" % (row["customer_no"], bank.customer_display_name(row), row["zip"], row["city"]))
    print("%d Treffer" % len(rows))


def cmd_accounts(bank, args):
    customer = bank.get_customer_by_no(args.customer_no)
    if customer is None:
        sys.exit("Unbekannte Kundennummer")
    summary = bank.customer_summary(customer["id"])
    print(summary["name"])
    for line in summary["accounts"]:
        print("  %-28s %-20s %18s" % (format_iban(line["iban"]), line["product"], line["balance"]))
    print("  %-49s %18s" % ("Summe", summary["total"]))


def cmd_bookings(bank, args):
    for row in bank.list_bookings(args.iban, args.from_date, args.to_date, args.limit):
        print("%s %s %18s %-14s %s" % (row["booking_date"], row["value_date"], format_eur(row["amount_cents"]),
                                       row["kind"], row["purpose"] or ""))


def cmd_block(bank, args):
    bank.blockAccount(args.iban)
    print("Konto gesperrt")


def cmd_unblock(bank, args):
    bank.unblockAccount(args.iban)
    print("Konto entsperrt")


def cmd_limit(bank, args):
    bank.set_overdraft_limit(args.iban, parse_eur(args.amount))
    print("Limit gesetzt")


def cmd_report(bank, args):
    reports = ReportGenerator(bank)
    if args.name == "products":
        sys.stdout.write(reports.product_report_csv())
    elif args.name == "overdrafts":
        sys.stdout.write(reports.overdraft_report_csv())
    elif args.name == "month":
        year, month = args.period.split("-")
        sys.stdout.write(reports.monthly_report_csv(int(year), int(month)))
    elif args.name == "forecast":
        sys.stdout.write(reports.interest_forecast_csv(int(args.period)))


def cmd_dunning(bank, args):
    processor = DunningProcessor(bank)
    result = processor.run(args.date)
    processor.deliver_letters(args.date)
    print("%d Mahnungen, %d erledigt" % (len(result["issued"]), result["resolved"]))


def build_parser():
    parser = argparse.ArgumentParser(description="Musterbank back office")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)

    customer = commands.add_parser("customer", help="Kunden suchen")
    customer.add_argument("name")
    customer.set_defaults(func=cmd_customer)

    accounts = commands.add_parser("accounts", help="Konten eines Kunden")
    accounts.add_argument("customer_no")
    accounts.set_defaults(func=cmd_accounts)

    bookings = commands.add_parser("bookings", help="Buchungen eines Kontos")
    bookings.add_argument("iban")
    bookings.add_argument("--from-date")
    bookings.add_argument("--to-date")
    bookings.add_argument("--limit", type=int, default=50)
    bookings.set_defaults(func=cmd_bookings)

    block = commands.add_parser("block", help="Konto sperren")
    block.add_argument("iban")
    block.set_defaults(func=cmd_block)

    unblock = commands.add_parser("unblock", help="Konto entsperren")
    unblock.add_argument("iban")
    unblock.set_defaults(func=cmd_unblock)

    limit = commands.add_parser("limit", help="Überziehungsrahmen setzen")
    limit.add_argument("iban")
    limit.add_argument("amount")
    limit.set_defaults(func=cmd_limit)

    report = commands.add_parser("report", help="Bericht als CSV")
    report.add_argument("name", choices=["products", "overdrafts", "month", "forecast"])
    report.add_argument("--period", default="2025-12", help="YYYY-MM oder Tage für forecast")
    report.set_defaults(func=cmd_report)

    dunning = commands.add_parser("dunning", help="Mahnlauf")
    dunning.add_argument("date")
    dunning.set_defaults(func=cmd_dunning)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    bank = BankCore(args.db)
    try:
        args.func(bank, args)
    finally:
        bank.close()


if __name__ == "__main__":
    main()
