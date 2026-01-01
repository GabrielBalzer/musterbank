"""Start the transfer service: python -m payments --db data/musterbank.sqlite"""
import argparse
import logging

from core.bank import BankCore
from payments.api import PaymentsServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Musterbank transfer API")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    BankCore(args.db).close()
    server = PaymentsServer((args.host, args.port), args.db)
    logging.getLogger("musterbank.payments").info("listening on %s:%d", args.host, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
