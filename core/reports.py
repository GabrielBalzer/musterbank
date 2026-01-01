"""Back office reports. Most of them feed the monthly management pack as CSV."""
import csv
import io
from datetime import timedelta

from core.dates import month_end, parse_date
from core.money import format_eur


def _csv(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def _euro(cents):
    sign = "-" if cents < 0 else ""
    return "%s%d,%02d" % (sign, abs(cents) // 100, abs(cents) % 100)


class ReportGenerator:
    def __init__(self, bank):
        self.bank = bank
        self.db = bank.db

    def monthly_report(self, year, month):
        start = parse_date("%04d-%02d-01" % (year, month))
        end = month_end(start)
        turnover = self.db.execute(
            "SELECT kind, COUNT(*) AS bookings, SUM(amount_cents) AS amount_cents FROM bookings"
            " WHERE booking_date >= ? AND booking_date <= ? GROUP BY kind ORDER BY kind",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        new_accounts = self.db.execute(
            "SELECT COUNT(*) FROM accounts WHERE opened_on >= ? AND opened_on <= ?",
            (start.isoformat(), end.isoformat()),
        ).fetchone()[0]
        closed_accounts = self.db.execute(
            "SELECT COUNT(*) FROM accounts WHERE closed_on >= ? AND closed_on <= ?",
            (start.isoformat(), end.isoformat()),
        ).fetchone()[0]
        return {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "turnover": [dict(r) for r in turnover],
            "new_accounts": new_accounts,
            "closed_accounts": closed_accounts,
        }

    def monthly_report_csv(self, year, month):
        report = self.monthly_report(year, month)
        rows = []
        for line in report["turnover"]:
            rows.append([line["kind"], line["bookings"], _euro(line["amount_cents"])])
        return _csv(["Art", "Anzahl", "Summe"], rows)

    def product_report_csv(self):
        rows = []
        for line in self.bank.product_totals():
            rows.append([line["product_code"], line["accounts"], _euro(line["balance_cents"] or 0)])
        return _csv(["Produkt", "Konten", "Bestand"], rows)

    def overdraft_report_csv(self):
        rows = []
        for acct in self.bank.overdrawn_accounts():
            rows.append([acct["iban"], _euro(acct["balance_cents"]), _euro(acct["overdraft_limit_cents"]),
                         "JA" if acct["balance_cents"] < -acct["overdraft_limit_cents"] else "NEIN"])
        return _csv(["IBAN", "Saldo", "Limit", "Ueberzogen"], rows)

    def large_movements_csv(self, from_date, to_date, threshold_cents):
        rows = []
        for line in self.bank.large_movements(from_date, to_date, threshold_cents):
            rows.append([line["booking_date"], line["iban"], _euro(line["amount_cents"]), line["kind"],
                         line["counterparty_name"] or ""])
        return _csv(["Buchungstag", "IBAN", "Betrag", "Art", "Gegenpartei"], rows)

    def dormant_csv(self, since_date):
        rows = []
        for acct in self.bank.dormant_accounts(since_date):
            rows.append([acct["iban"], acct["product_code"], _euro(acct["balance_cents"])])
        return _csv(["IBAN", "Produkt", "Saldo"], rows)

    def top_customers(self, limit=10):
        rows = self.db.execute(
            "SELECT c.id, c.customer_no, SUM(a.balance_cents) AS total_cents"
            " FROM customers c JOIN accounts a ON a.customer_id = c.id"
            " WHERE a.status != 'CLOSED' GROUP BY c.id, c.customer_no ORDER BY total_cents DESC, c.id LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            customer = self.bank.getCustomer(row["id"])
            out.append({
                "customer_no": row["customer_no"],
                "name": self.bank.customer_display_name(customer),
                "total_cents": row["total_cents"],
                "total": format_eur(row["total_cents"]),
            })
        return out

    def customers_by_city(self):
        rows = self.db.execute(
            "SELECT city, COUNT(*) AS customers FROM customers GROUP BY city ORDER BY customers DESC, city"
        ).fetchall()
        return [dict(r) for r in rows]

    def age_structure(self, reference_year):
        buckets = {"unter 30": 0, "30 bis 49": 0, "50 bis 64": 0, "ab 65": 0, "unbekannt": 0}
        for row in self.db.execute("SELECT birth_date FROM customers WHERE kind = 'RETAIL'"):
            if not row["birth_date"]:
                buckets["unbekannt"] += 1
                continue
            age = reference_year - int(row["birth_date"][:4])
            if age < 30:
                buckets["unter 30"] += 1
            elif age < 50:
                buckets["30 bis 49"] += 1
            elif age < 65:
                buckets["50 bis 64"] += 1
            else:
                buckets["ab 65"] += 1
        return buckets

    def maturities(self, from_date, to_date):
        return self.db.execute(
            "SELECT iban, maturity_date, balance_cents FROM accounts WHERE product_code = 'FESTGELD'"
            " AND status = 'ACTIVE' AND maturity_date >= ? AND maturity_date <= ? ORDER BY maturity_date, iban",
            (parse_date(from_date).isoformat(), parse_date(to_date).isoformat()),
        ).fetchall()

    def maturities_csv(self, from_date, to_date):
        rows = []
        for row in self.maturities(from_date, to_date):
            rows.append([row["iban"], row["maturity_date"], _euro(row["balance_cents"])])
        return _csv(["IBAN", "Faelligkeit", "Bestand"], rows)

    def interest_forecast(self, iban, days):
        """Rough interest estimate for customer advice: current balance, no later bookings, 365 days a year."""
        account = self.bank.getAccount(iban)
        product = self.bank._get_product(account["product_code"])
        balance = account["balance_cents"]
        rate = product["credit_rate_bp"] if balance >= 0 else product["debit_rate_bp"]
        return int(round(balance * rate * days / (10000.0 * 365)))

    def interest_forecast_csv(self, days):
        rows = []
        accounts = self.db.execute(
            "SELECT iban, product_code, balance_cents FROM accounts WHERE status = 'ACTIVE'"
            " AND product_code != 'CLEARING' ORDER BY id"
        ).fetchall()
        for acct in accounts:
            rows.append([acct["iban"], acct["product_code"], _euro(acct["balance_cents"]),
                         _euro(self.interest_forecast(acct["iban"], days))])
        return _csv(["IBAN", "Produkt", "Saldo", "Zinsen (Schaetzung)"], rows)

    def daily_turnover_series(self, from_date, to_date):
        day = parse_date(from_date)
        end = parse_date(to_date)
        out = []
        while day <= end:
            line = self.bank.daily_turnover(day)
            line["day"] = day.isoformat()
            out.append(line)
            day += timedelta(days=1)
        return out

    def daily_turnover_csv(self, from_date, to_date):
        rows = []
        for line in self.daily_turnover_series(from_date, to_date):
            rows.append([line["day"], line["bookings"], _euro(line["credits"]), _euro(line["debits"])])
        return _csv(["Tag", "Buchungen", "Haben", "Soll"], rows)

    def eod_history(self):
        return self.db.execute(
            "SELECT business_date, started_at, finished_at, checksum FROM eod_runs ORDER BY business_date"
        ).fetchall()

    def fee_income(self, from_date, to_date):
        row = self.db.execute(
            "SELECT COALESCE(SUM(-amount_cents), 0) FROM bookings WHERE kind = 'FEE'"
            " AND booking_date >= ? AND booking_date <= ?",
            (parse_date(from_date).isoformat(), parse_date(to_date).isoformat()),
        ).fetchone()
        return row[0]

    def interest_paid(self, from_date, to_date):
        row = self.db.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM bookings WHERE kind = 'INTEREST' AND amount_cents > 0"
            " AND booking_date >= ? AND booking_date <= ?",
            (parse_date(from_date).isoformat(), parse_date(to_date).isoformat()),
        ).fetchone()
        return row[0]

    def interest_received(self, from_date, to_date):
        row = self.db.execute(
            "SELECT COALESCE(SUM(-amount_cents), 0) FROM bookings WHERE kind = 'INTEREST' AND amount_cents < 0"
            " AND booking_date >= ? AND booking_date <= ?",
            (parse_date(from_date).isoformat(), parse_date(to_date).isoformat()),
        ).fetchone()
        return row[0]
