"""Start the online banking: python -m web --db data/musterbank.sqlite"""
import argparse
import logging

from core.bank import BankCore
from web.app import WebServer


def main():
    parser = argparse.ArgumentParser(description="Musterbank online banking")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--payments-url", default="http://127.0.0.1:8081")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    BankCore(args.db).close()
    server = WebServer((args.host, args.port), args.db, args.payments_url)
    logging.getLogger("musterbank.web").info("listening on %s:%d", args.host, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
