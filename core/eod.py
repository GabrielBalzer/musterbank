"""End of day processing: interest closings, account fees and the daily result set."""
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from core.bank import STATUS_ACTIVE, STATUS_MATURED
from core.dates import is_month_end, is_quarter_end, month_start, parse_date, quarter_start
from core.errors import EodAlreadyRun

log = logging.getLogger("musterbank.eod")


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EndOfDayProcessor:
    def __init__(self, bank):
        self.bank = bank
        self.db = bank.db

    def _closing_period(self, product, account, business_date):
        """The interest period that closes on business_date, or None."""
        cycle = product["closing_cycle"]
        if cycle == "MONTHLY" and is_month_end(business_date):
            start = month_start(business_date)
        elif cycle == "QUARTERLY" and is_quarter_end(business_date):
            start = quarter_start(business_date)
        elif cycle == "MATURITY" and account["maturity_date"] == business_date.isoformat():
            start = parse_date(account["opened_on"])
        else:
            return None
        return start, business_date - timedelta(days=1)

    def _fee_due(self, product, business_date):
        if product["monthly_fee_cents"] and is_month_end(business_date):
            return product["monthly_fee_cents"]
        return 0

    def _fee_purpose(self, holder, business_date):
        label = "Kontofuehrung Geschaeftskonto" if holder["kind"] == "BUSINESS" else "Kontofuehrung"
        return "%s %s" % (label, business_date.strftime("%m/%Y"))

    def _book(self, account, business_date, amount_cents, kind, purpose):
        self.bank._insert_booking(account["id"], business_date, business_date, amount_cents, kind,
                                  purpose=purpose)
        self.db.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?",
            (amount_cents, account["id"]),
        )

    def _process_account(self, account, product, holder, business_date):
        interest = 0
        period = self._closing_period(product, account, business_date)
        if period is not None:
            interest = self.bank.calculate_interest(account["iban"], period[0], period[1])
        if interest:
            self._book(account, business_date, interest, "INTEREST",
                       "Zinsen %s bis %s" % (period[0].isoformat(), period[1].isoformat()))
        if product["closing_cycle"] == "MATURITY" and period is not None:
            self.db.execute("UPDATE accounts SET status = ? WHERE id = ?", (STATUS_MATURED, account["id"]))
        fee = self._fee_due(product, business_date)
        if fee:
            self._book(account, business_date, -fee, "FEE", self._fee_purpose(holder, business_date))
        closing = account["balance_cents"] + interest - fee
        self.db.execute(
            "INSERT INTO eod_results (business_date, iban, interest_cents, fee_cents, closing_balance_cents)"
            " VALUES (?, ?, ?, ?, ?)",
            (business_date.isoformat(), account["iban"], interest, fee, closing),
        )
        return interest, fee

    def checksum(self, business_date):
        digest = hashlib.sha256()
        rows = self.db.execute(
            "SELECT iban, interest_cents, fee_cents, closing_balance_cents FROM eod_results"
            " WHERE business_date = ? ORDER BY iban",
            (business_date.isoformat(),),
        )
        for row in rows:
            line = "%s|%s|%d|%d|%d\n" % (business_date.isoformat(), row[0], row[1], row[2], row[3])
            digest.update(line.encode("ascii"))
        return digest.hexdigest()

    def run(self, business_date):
        day = business_date.isoformat()
        previous = self.db.execute("SELECT finished_at FROM eod_runs WHERE business_date = ?", (day,)).fetchone()
        if previous is not None and previous["finished_at"]:
            raise EodAlreadyRun(day)
        interest_total = 0
        fee_total = 0
        count = 0
        if previous is None:
            self.db.execute("INSERT INTO eod_runs (business_date, started_at) VALUES (?, ?)", (day, _timestamp()))
        customers = self.db.execute("SELECT * FROM customers").fetchall()
        account_ids = self.db.execute(
            "SELECT id FROM accounts WHERE status = ? AND product_code != 'CLEARING' ORDER BY id",
            (STATUS_ACTIVE,),
        ).fetchall()
        # accounts commit one by one, a restart continues with the ones still open
        processed = [row["iban"] for row in self.db.execute(
            "SELECT iban FROM eod_results WHERE business_date = ?", (day,)
        )]
        for account_id in account_ids:
            account = self.bank.get_account_by_id(account_id["id"])
            if account["iban"] in processed:
                continue
            product = self.bank._get_product(account["product_code"])
            holder = None
            for customer in customers:
                if customer["id"] == account["customer_id"]:
                    holder = customer
                    break
            if not self.bank.check_balance(account["iban"]):
                log.warning("balance does not match journal for account %d", account["id"])
            with self.bank.transaction():
                interest, fee = self._process_account(account, product, holder, business_date)
            interest_total += interest
            fee_total += fee
            count += 1
            processed.append(account["iban"])
        checksum = self.checksum(business_date)
        self.db.execute(
            "UPDATE eod_runs SET finished_at = ?, checksum = ? WHERE business_date = ?",
            (_timestamp(), checksum, day),
        )
        log.info("end of day %s: %d accounts", day, count)
        return {
            "business_date": day,
            "accounts": count,
            "interest_cents": interest_total,
            "fee_cents": fee_total,
            "checksum": checksum,
        }
