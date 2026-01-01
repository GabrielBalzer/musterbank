"""Generate the demo data set: customers, accounts and one year of bookings.

Writes straight to the tables so the result only depends on the seed and the size.
Only random.random() is used, so a seed always gives the same data.
"""
import argparse
import os
import random
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db as dbmod  # noqa: E402
from core.bank import CLEARING_IBAN, FIRST_ACCOUNT_NUMBER  # noqa: E402
from core.dates import month_end, next_business_day  # noqa: E402
from core.iban import BANK_CODE, build_de_iban  # noqa: E402

DEFAULT_CUSTOMERS = 2000
DEFAULT_SEED = 20250101
YEAR = 2025
YEAR_START = date(YEAR, 1, 1)
YEAR_END = date(YEAR, 12, 31)
BATCH_SIZE = 20000

FIRST_NAMES = [
    "Anna", "Ben", "Clara", "David", "Elif", "Finn", "Greta", "Hannes", "Ida", "Jonas", "Klara", "Lars",
    "Mara", "Nils", "Olga", "Paul", "Quirin", "Rosa", "Samir", "Tilda", "Uwe", "Vera", "Wim", "Xenia",
    "Yannick", "Zoe", "Jörg", "Björn", "Änne", "Sören", "Merle", "Tarek", "Leonie", "Mirko", "Nadja",
    "Ole", "Pia", "Ruben", "Svea", "Timo",
]
LAST_NAMES = [
    "Ahrenskötter", "Bachwieser", "Birkenhauer", "Dornhagen", "Eichwaldt", "Faltermoser", "Grünspecht",
    "Hasenklee", "Höllriegler", "Immenkamp", "Jungbluth", "Kesselhuth", "Klammerer", "Lindenfels",
    "Moosrainer", "Nesselrath", "Oberländer", "Pfefferkorn", "Quellmalz", "Rübenacker", "Sandhagen",
    "Schäfermeier", "Stöckelhuber", "Tannenbrink", "Ulmenrath", "Vogelsanger", "Wiesengrund", "Zaunkönig",
    "Hölzl-Brandt", "Meier-Sandhagen", "von der Heidkamp", "Özkantar", "Rosenthaler", "Weidenbusch",
]
COMPANY_STEMS = [
    "Kaltenbrück", "Sonnfeldau", "Mühlbachtal", "Fichtenrodt", "Nordkampen", "Weißenbruck", "Eichelhain",
    "Birkenried", "Tannhagen", "Lindhagenau", "Ostermoorau", "Silberau",
]
COMPANY_TRADES = [
    "Logistik GmbH", "Bäckerei KG", "Metallbau GmbH", "Gartenpflege e.K.", "Softwarehaus GmbH",
    "Malerbetrieb GmbH", "Reisedienst OHG", "Haustechnik GmbH", "Buchhandel KG", "Getränkevertrieb GmbH",
]
STREETS = [
    "Am Musterbach", "Beispielweg", "Birkenallee", "Erfundene Straße", "Fiktivgasse", "Lindenhof",
    "Probenplatz", "Sandkoppel", "Testring", "Hauptstraße",
]
CITIES = ["Musterstadt", "Beispielhausen", "Fiktingen", "Erfundenau", "Neu-Testhagen"]
MERCHANTS = [
    "Kaltenbrück Markt", "Sonnfeldau Drogerie", "Eichelhain Tankstelle", "Bäckerei Lindhagenau",
    "Silberau Apotheke", "Nordkampen Elektro", "Café Ostermoorau", "Fichtenrodt Baumarkt",
]
RENT_NAMES = ["Hausverwaltung Tannhagen", "Wohnbau Birkenried", "Immobilien Weißenbruck"]
UTILITIES = ["Stadtwerke Musterstadt", "Fernsprechdienst Fiktingen", "Versicherung Beispielhausen"]


class Rng:
    def __init__(self, seed):
        self.next = random.Random(seed).random

    def between(self, low, high):
        return low + int(self.next() * (high - low + 1))

    def choice(self, items):
        return items[int(self.next() * len(items))]

    def chance(self, probability):
        return self.next() < probability

    def day_in(self, start, end):
        return start + timedelta(days=self.between(0, (end - start).days))


def _ascii(text):
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", " ": "-"})
    return text.translate(table).lower()


def _foreign_iban(rng):
    bank_code = "0%07d" % rng.between(1000000, 9999999)
    return build_de_iban(bank_code, rng.between(1000000, 9999999999))


def _make_customer(rng, customer_id, retail):
    street = "%s %d" % (rng.choice(STREETS), rng.between(1, 140))
    zip_code = "00%03d" % rng.between(100, 999)
    city = rng.choice(CITIES)
    created = rng.day_in(date(2011, 3, 1), date(2024, 12, 31)).isoformat()
    customer_no = "K%08d" % customer_id
    if retail:
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        birth = rng.day_in(date(1945, 1, 1), date(2005, 12, 31)).isoformat()
        email = "%s.%s.%d@example.org" % (_ascii(first), _ascii(last), customer_id)
        return (customer_id, customer_no, "RETAIL", first, last, None, birth, street, zip_code, city, email, created)
    company = "%s %s" % (rng.choice(COMPANY_STEMS), rng.choice(COMPANY_TRADES))
    email = "kontakt.%d@example.org" % customer_id
    return (customer_id, customer_no, "BUSINESS", None, None, company, None, street, zip_code, city, email, created)


class BookingWriter:
    def __init__(self, conn):
        self.conn = conn
        self.pending = []
        self.count = 0
        self.next_id = 1

    def add(self, account_id, booking_day, value_day, amount, kind, name, iban, purpose):
        self.pending.append((self.next_id, account_id, booking_day.isoformat(), value_day.isoformat(), amount, kind,
                             name, iban, purpose))
        self.next_id += 1
        self.count += 1
        if len(self.pending) >= BATCH_SIZE:
            self.flush()

    def flush(self):
        self.conn.executemany(
            "INSERT INTO bookings (id, account_id, booking_date, value_date, amount_cents, kind,"
            " counterparty_name, counterparty_iban, purpose) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self.pending,
        )
        self.pending = []


def _month_firsts():
    return [date(YEAR, month, 1) for month in range(1, 13)]


def _giro_events(rng, retail, partners, start):
    """Events of one current account as (booking day, value day, amount, kind, name, iban, purpose)."""
    events = []
    salary = rng.between(220000, 550000) if retail else 0
    rent = rng.between(50000, 140000) if retail else 0
    payer = rng.choice(partners)
    landlord = rng.choice(partners)
    utility = rng.choice(partners)
    card_count = 7 if retail else 3
    for first in _month_firsts():
        last = month_end(first)
        if last < start:
            continue
        if retail:
            pay_day = next_business_day(max(last - timedelta(days=2), start))
            events.append((pay_day, pay_day, salary + rng.between(-5000, 5000), "SALARY", payer[0], payer[1],
                           "Gehalt %02d/%d" % (first.month, YEAR)))
            if first >= start:
                rent_day = next_business_day(first)
                events.append((rent_day, rent_day, -rent, "DIRECT_DEBIT", rng.choice(RENT_NAMES), landlord[1],
                               "Miete %02d/%d" % (first.month, YEAR)))
                util_day = next_business_day(first + timedelta(days=14))
                events.append((util_day, util_day, -rng.between(3000, 18000), "DIRECT_DEBIT", rng.choice(UTILITIES),
                               utility[1], "Abschlag %02d/%d" % (first.month, YEAR)))
        else:
            for _ in range(rng.between(8, 18)):
                day = next_business_day(rng.day_in(max(first, start), last))
                if day > YEAR_END:
                    continue
                partner = rng.choice(partners)
                amount = rng.between(5000, 900000)
                if rng.chance(0.47):
                    amount = -amount
                events.append((day, day, amount, "TRANSFER_IN" if amount > 0 else "TRANSFER_OUT", partner[0], partner[1],
                               "Rechnung %d" % rng.between(10000, 99999)))
        for _ in range(card_count + rng.between(0, 4)):
            used_on = rng.day_in(max(first, start), last)
            booked = next_business_day(used_on + timedelta(days=rng.between(0, 2)))
            if booked > YEAR_END:
                continue
            events.append((booked, used_on, -rng.between(300, 15000), "CARD", rng.choice(MERCHANTS), None,
                           "Kartenzahlung"))
    return events


def _savings_events(rng, giro_name, start):
    events = []
    for first in _month_firsts():
        if first < start or not rng.chance(0.3):
            continue
        day = next_business_day(first + timedelta(days=rng.between(0, 20)))
        amount = rng.between(5000, 100000)
        if rng.chance(0.2):
            amount = -amount // 2
        events.append((day, day, amount, "TRANSFER_IN" if amount > 0 else "TRANSFER_OUT", giro_name, None, "Umbuchung"))
    return events


def _opening_day(rng):
    if rng.chance(0.05):
        return rng.day_in(date(YEAR, 1, 2), date(YEAR, 9, 30))
    return rng.day_in(date(2012, 1, 1), date(2024, 12, 31))


def _write_account(conn, writer, account_id, customer_id, product, opened, limit, maturity, opening_cents, events):
    iban = build_de_iban(BANK_CODE, FIRST_ACCOUNT_NUMBER + account_id)
    start = max(opened, YEAR_START)
    balance = opening_cents + sum(event[2] for event in events)
    conn.execute(
        "INSERT INTO accounts (id, iban, customer_id, product_code, balance_cents, overdraft_limit_cents,"
        " opened_on, status, maturity_date) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
        (account_id, iban, customer_id, product, balance, limit, opened.isoformat(),
         maturity.isoformat() if maturity else None),
    )
    writer.add(account_id, start, start, opening_cents, "OPENING", None, None, "Anfangsbestand")
    for booked, value, amount, kind, partner_name, partner_iban, purpose in sorted(events, key=lambda e: (e[0], e[1])):
        writer.add(account_id, booked, value, amount, kind, partner_name, partner_iban, purpose)
    return iban


def generate(db_path, customers=DEFAULT_CUSTOMERS, seed=DEFAULT_SEED):
    if os.path.exists(db_path):
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(db_path + suffix):
                os.remove(db_path + suffix)
    folder = os.path.dirname(db_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = dbmod.connect(db_path)
    dbmod.migrate(conn)
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("BEGIN")
    rng = Rng(seed)
    writer = BookingWriter(conn)
    partners = [("%s %s" % (rng.choice(COMPANY_STEMS), rng.choice(COMPANY_TRADES)), _foreign_iban(rng)) for _ in range(200)]
    account_id = 0
    for customer_id in range(1, customers + 1):
        retail = customer_id == 1 or rng.chance(0.85)
        row = _make_customer(rng, customer_id, retail)
        conn.execute(
            "INSERT INTO customers (id, customer_no, kind, first_name, last_name, company_name, birth_date, street,"
            " zip, city, email, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
        display = row[5] if not retail else "%s %s" % (row[3], row[4])
        opened = _opening_day(rng)
        start = max(opened, YEAR_START)
        limit = rng.choice([0, 50000, 100000, 200000]) if retail else rng.choice([0, 500000, 1000000])
        opening = rng.between(10000, 600000) if retail else rng.between(500000, 8000000)
        account_id += 1
        _write_account(conn, writer, account_id, customer_id, "GIRO", opened, limit, None, opening,
                       _giro_events(rng, retail, partners, start))
        if customer_id == 1 or rng.chance(0.4 if retail else 0.2):
            saved_from = _opening_day(rng)
            account_id += 1
            _write_account(conn, writer, account_id, customer_id, "TAGESGELD", saved_from, 0, None,
                           rng.between(100000, 5000000), _savings_events(rng, display, max(saved_from, YEAR_START)))
        if customer_id == 1 or rng.chance(0.1):
            fixed_from = rng.day_in(date(YEAR, 1, 2), date(YEAR, 9, 30))
            maturity = YEAR_END if rng.chance(0.3) else month_end(rng.day_in(date(YEAR + 1, 1, 1), date(YEAR + 2, 12, 1)))
            account_id += 1
            _write_account(conn, writer, account_id, customer_id, "FESTGELD", fixed_from, 0, maturity,
                           rng.between(500000, 10000000), [])
    account_id += 1
    conn.execute(
        "INSERT INTO accounts (id, iban, product_code, opened_on) VALUES (?, ?, 'CLEARING', ?)",
        (account_id, CLEARING_IBAN, "2011-03-01"),
    )
    writer.flush()
    conn.execute("COMMIT")
    conn.close()
    return {"customers": customers, "accounts": account_id, "bookings": writer.count}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the Musterbank demo data set")
    parser.add_argument("--db", default="data/musterbank.sqlite")
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    result = generate(args.db, args.customers, args.seed)
    print("%(customers)d Kunden, %(accounts)d Konten, %(bookings)d Buchungen" % result)
    print("Dauer: %.1f s, Datei: %s" % (time.perf_counter() - started, args.db))


if __name__ == "__main__":
    main()
