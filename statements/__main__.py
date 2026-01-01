"""Print a statement: python -m statements --iban DE.. --month 2025-12 [--format csv]"""
import argparse
import sys

from core.bank import BankCore
from statements.render import render_csv, render_text
from statements.service import StatementService


def main(argv=None):
    parser = argparse.ArgumentParser(description="Musterbank account statements")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    parser.add_argument("--iban", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--format", choices=["text", "csv"], default="text")
    args = parser.parse_args(argv)
    year, month = args.month.split("-")
    bank = BankCore(args.db)
    try:
        statement = StatementService(bank).monthly_statement(args.iban, int(year), int(month))
    finally:
        bank.close()
    sys.stdout.write(render_text(statement) if args.format == "text" else render_csv(statement))


if __name__ == "__main__":
    main()
