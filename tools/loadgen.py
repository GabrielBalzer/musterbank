"""Simple load generator for the transfer API."""
import argparse
import http.client
import json
import os
import random
import sqlite3
import statistics
import sys
import threading
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.iban import build_de_iban  # noqa: E402


def load_debtors(db_path, limit=500):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT iban FROM accounts WHERE product_code = 'GIRO' AND status = 'ACTIVE' ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


class Worker(threading.Thread):
    def __init__(self, url, debtors, creditor, count, seed, results):
        super().__init__(daemon=True)
        parsed = urlparse(url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.debtors = debtors
        self.creditor = creditor
        self.count = count
        self.rng = random.Random(seed)
        self.results = results

    def _payload(self):
        return json.dumps({
            "debtor_iban": self.debtors[int(self.rng.random() * len(self.debtors))],
            "creditor_iban": self.creditor,
            "creditor_name": "Lasttest Empfaenger",
            "amount": 0.01 + int(self.rng.random() * 2000) / 100,
            "purpose": "Lasttest",
        })

    def run(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=60)
        for _ in range(self.count):
            started = time.perf_counter()
            try:
                conn.request("POST", "/transfers", self._payload(), {"Content-Type": "application/json"})
                response = conn.getresponse()
                response.read()
                status = response.status
            except (OSError, http.client.HTTPException):
                conn.close()
                conn = http.client.HTTPConnection(self.host, self.port, timeout=60)
                status = 0
            self.results.append((status, time.perf_counter() - started))
        conn.close()


def run_load(url, debtors, requests, concurrency, seed=1):
    results = []
    creditor = build_de_iban("09876500", 4242424242)
    share = max(1, requests // concurrency)
    workers = [Worker(url, debtors, creditor, share, seed + i, results) for i in range(concurrency)]
    started = time.perf_counter()
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    elapsed = time.perf_counter() - started
    latencies = sorted(r[1] for r in results)
    statuses = {}
    for status, _ in results:
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "requests": len(results),
        "seconds": elapsed,
        "per_second": len(results) / elapsed if elapsed else 0.0,
        "median_ms": statistics.median(latencies) * 1000 if latencies else 0.0,
        "p95_ms": latencies[int(len(latencies) * 0.95) - 1] * 1000 if latencies else 0.0,
        "statuses": statuses,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load generator for the transfer API")
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)
    debtors = load_debtors(args.db)
    if not debtors:
        parser.error("keine Konten gefunden, zuerst Daten erzeugen")
    result = run_load(args.url, debtors, args.requests, args.concurrency, args.seed)
    print("%d Anfragen in %.1f s (%.0f/s)" % (result["requests"], result["seconds"], result["per_second"]))
    print("Median %.1f ms, p95 %.1f ms" % (result["median_ms"], result["p95_ms"]))
    print("Statuscodes: %s" % json.dumps(result["statuses"], sort_keys=True))


if __name__ == "__main__":
    main()
