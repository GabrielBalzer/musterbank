"""Core banking operations of Musterbank AG.

BankCore is the entry point the other modules use. It started out as the customer
and account register and took over bookings and interest when the old batch scripts
were retired, which is why everything lives in one class.
"""
import logging
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal

from core import db as dbmod
from core.dates import berlin_date, next_business_day, parse_date, utc_now
from core.errors import (
    AccountNotActive,
    BankError,
    InsufficientFunds,
    InvalidAmount,
    InvalidIban,
    UnknownAccount,
    UnknownCustomer,
)
from core.iban import BANK_CODE, build_de_iban, normalize_iban, validate_iban
from core.money import format_eur

log = logging.getLogger("musterbank.core")

CLEARING_ACCOUNT_NUMBER = 9999999999
CLEARING_IBAN = build_de_iban(BANK_CODE, CLEARING_ACCOUNT_NUMBER)
FIRST_ACCOUNT_NUMBER = 1000000
KIND_RETAIL = "RETAIL"
KIND_BUSINESS = "BUSINESS"
STATUS_ACTIVE = "ACTIVE"
STATUS_BLOCKED = "BLOCKED"
STATUS_CLOSED = "CLOSED"
STATUS_MATURED = "MATURED"


class BankCore:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db = dbmod.connect(db_path)
        dbmod.migrate(self.db)

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        if self.db.in_transaction:
            yield
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")

    # ------------------------------------------------------------------
    # customers
    # ------------------------------------------------------------------

    def createCustomer(self, first_name, last_name, birth_date=None, street=None, zip_code=None,
                       city=None, email=None, kind=KIND_RETAIL, company_name=None, created_at=None):
        with self.transaction():
            row = self.db.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM customers").fetchone()
            customer_no = "K%08d" % row[0]
            cur = self.db.execute(
                "INSERT INTO customers (customer_no, kind, first_name, last_name, company_name,"
                " birth_date, street, zip, city, email, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (customer_no, kind, first_name, last_name, company_name, _iso(birth_date), street,
                 zip_code, city, email, _iso(created_at) or _today()),
            )
        return cur.lastrowid

    def getCustomer(self, customerId):
        row = self.db.execute("SELECT * FROM customers WHERE id = ?", (customerId,)).fetchone()
        if row is None:
            raise UnknownCustomer(str(customerId))
        return row

    def get_customer_by_no(self, customer_no):
        return self.db.execute("SELECT * FROM customers WHERE customer_no = ?", (customer_no,)).fetchone()

    def find_customers(self, name):
        pattern = "%" + name + "%"
        return self.db.execute(
            "SELECT * FROM customers WHERE last_name LIKE ? OR first_name LIKE ? OR company_name LIKE ?"
            " ORDER BY id",
            (pattern, pattern, pattern),
        ).fetchall()

    def listCustomers(self, limit=100, offset=0):
        return self.db.execute(
            "SELECT * FROM customers ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()

    def updateCustomerAddress(self, customerId, street, zip_code, city):
        self.getCustomer(customerId)
        self.db.execute(
            "UPDATE customers SET street = ?, zip = ?, city = ? WHERE id = ?",
            (street, zip_code, city, customerId),
        )

    def update_customer_email(self, customer_id, email):
        self.getCustomer(customer_id)
        self.db.execute("UPDATE customers SET email = ? WHERE id = ?", (email, customer_id))

    def closeCustomer(self, customerId):
        """A customer can only leave when all accounts are closed."""
        open_accounts = [a for a in self.getAccountsForCustomer(customerId) if a["status"] != STATUS_CLOSED]
        if open_accounts:
            raise BankError("customer still has %d open accounts" % len(open_accounts))
        self.db.execute("UPDATE customers SET email = NULL, street = NULL WHERE id = ?", (customerId,))

    def merge_customers(self, source_id, target_id):
        """Move all accounts to the target customer, for duplicate master data."""
        self.getCustomer(source_id)
        self.getCustomer(target_id)
        with self.transaction():
            self.db.execute("UPDATE accounts SET customer_id = ? WHERE customer_id = ?", (target_id, source_id))
            self.db.execute("UPDATE mailbox_messages SET customer_id = ? WHERE customer_id = ?", (target_id, source_id))
            self.db.execute("DELETE FROM web_sessions WHERE customer_id = ?", (source_id,))

    def customer_display_name(self, customer):
        if customer["kind"] == KIND_BUSINESS and customer["company_name"]:
            return customer["company_name"]
        return ("%s %s" % (customer["first_name"] or "", customer["last_name"] or "")).strip()

    # ------------------------------------------------------------------
    # accounts
    # ------------------------------------------------------------------

    def _next_account_number(self):
        row = self.db.execute(
            "SELECT COALESCE(MAX(id), 0) FROM accounts WHERE iban != ?", (CLEARING_IBAN,)
        ).fetchone()
        return FIRST_ACCOUNT_NUMBER + row[0] + 1

    def open_account(self, customer_id, product_code, opened_on=None, overdraft_limit_cents=0,
                     maturity_date=None):
        """Open an account and return its IBAN."""
        self.getCustomer(customer_id)
        product = self._get_product(product_code)
        if product["closing_cycle"] == "MATURITY" and maturity_date is None:
            raise BankError("maturity date required for %s" % product_code)
        opened = _iso(opened_on) or _today()
        with self.transaction():
            iban = build_de_iban(BANK_CODE, self._next_account_number())
            self.db.execute(
                "INSERT INTO accounts (iban, customer_id, product_code, overdraft_limit_cents,"
                " opened_on, maturity_date) VALUES (?, ?, ?, ?, ?, ?)",
                (iban, customer_id, product_code, overdraft_limit_cents, opened, _iso(maturity_date)),
            )
        return iban

    def ensure_clearing_account(self):
        row = self.db.execute("SELECT id FROM accounts WHERE iban = ?", (CLEARING_IBAN,)).fetchone()
        if row is None:
            self.db.execute(
                "INSERT OR IGNORE INTO accounts (iban, product_code, opened_on) VALUES (?, 'CLEARING', ?)",
                (CLEARING_IBAN, _today()),
            )
        return CLEARING_IBAN

    def closeAccount(self, iban, closed_on=None):
        account = self.getAccount(iban)
        if account["balance_cents"] != 0:
            raise BankError("account balance must be zero before closing")
        self.db.execute(
            "UPDATE accounts SET status = ?, closed_on = ? WHERE id = ?",
            (STATUS_CLOSED, _iso(closed_on) or _today(), account["id"]),
        )
        log.info("account %d closed", account["id"])

    def getAccount(self, iban):
        row = self.db.execute("SELECT * FROM accounts WHERE iban = ?", (normalize_iban(iban),)).fetchone()
        if row is None:
            raise UnknownAccount(iban)
        return row

    def get_account_by_id(self, account_id):
        row = self.db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise UnknownAccount(str(account_id))
        return row

    def account_exists(self, iban):
        row = self.db.execute("SELECT 1 FROM accounts WHERE iban = ?", (normalize_iban(iban),)).fetchone()
        return row is not None

    def getAccountsForCustomer(self, customerId):
        return self.db.execute(
            "SELECT * FROM accounts WHERE customer_id = ? ORDER BY id", (customerId,)
        ).fetchall()

    def get_account_rows_for_customer(self, custId):
        return self.db.execute(
            "SELECT a.*, p.name AS product_name, p.credit_rate_bp, p.debit_rate_bp"
            " FROM accounts a JOIN products p ON p.code = a.product_code"
            " WHERE a.customer_id = ? AND a.status != 'CLOSED' ORDER BY a.id",
            (custId,),
        ).fetchall()

    def getBalance(self, iban):
        return self.getAccount(iban)["balance_cents"]

    def get_balance(self, iban):
        return self.getBalance(iban)

    def get_available(self, iban):
        account = self.getAccount(iban)
        return account["balance_cents"] + account["overdraft_limit_cents"]

    def set_overdraft_limit(self, iban, limit_cents):
        if limit_cents < 0:
            raise InvalidAmount("limit must not be negative")
        account = self.getAccount(iban)
        self.db.execute(
            "UPDATE accounts SET overdraft_limit_cents = ? WHERE id = ?", (limit_cents, account["id"])
        )

    def blockAccount(self, iban):
        account = self.getAccount(iban)
        self.db.execute("UPDATE accounts SET status = ? WHERE id = ?", (STATUS_BLOCKED, account["id"]))

    def unblockAccount(self, iban):
        account = self.getAccount(iban)
        self.db.execute("UPDATE accounts SET status = ? WHERE id = ?", (STATUS_ACTIVE, account["id"]))

    def _active_account(self, iban):
        account = self.getAccount(iban)
        if account["status"] != STATUS_ACTIVE:
            raise AccountNotActive(iban)
        return account

    def _get_product(self, code):
        row = self.db.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
        if row is None:
            raise BankError("unknown product %s" % code)
        return row

    def list_products(self):
        return self.db.execute("SELECT * FROM products ORDER BY code").fetchall()

    # ------------------------------------------------------------------
    # bookings
    # ------------------------------------------------------------------

    def _insert_booking(self, account_id, booking_day, value_day, amount_cents, kind,
                        counterparty_name=None, counterparty_iban=None, purpose=None, transfer_id=None):
        cur = self.db.execute(
            "INSERT INTO bookings (account_id, booking_date, value_date, amount_cents, kind,"
            " counterparty_name, counterparty_iban, purpose, transfer_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (account_id, booking_day.isoformat(), value_day.isoformat(), amount_cents, kind,
             counterparty_name, counterparty_iban, purpose, transfer_id),
        )
        return cur.lastrowid

    def _booking_days(self, at, value_date):
        moment = at or utc_now()
        booking_day = moment.date()
        if value_date is not None:
            return booking_day, parse_date(value_date)
        return booking_day, next_business_day(booking_day)

    def post_booking(self, iban, amount_cents, kind, at=None, value_date=None, counterparty_name=None,
                     counterparty_iban=None, purpose=None, transfer_id=None):
        """Post a signed amount to an account without limit checks. Returns the booking id."""
        if amount_cents == 0:
            raise InvalidAmount("amount must not be zero")
        booking_day, value_day = self._booking_days(at, value_date)
        with self.transaction():
            account = self.getAccount(iban)
            booking_id = self._insert_booking(account["id"], booking_day, value_day, amount_cents, kind,
                                              counterparty_name, counterparty_iban, purpose, transfer_id)
            self.db.execute(
                "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?",
                (amount_cents, account["id"]),
            )
        return booking_id

    def credit(self, iban, amount_cents, kind="CREDIT", at=None, value_date=None, counterparty_name=None,
               counterparty_iban=None, purpose=None, transfer_id=None):
        if amount_cents <= 0:
            raise InvalidAmount("amount must be positive")
        self._active_account(iban)
        return self.post_booking(iban, amount_cents, kind, at, value_date, counterparty_name,
                                 counterparty_iban, purpose, transfer_id)

    def debit(self, iban, amount_cents, kind="DEBIT", at=None, value_date=None, counterparty_name=None,
              counterparty_iban=None, purpose=None, transfer_id=None):
        if amount_cents <= 0:
            raise InvalidAmount("amount must be positive")
        booking_day, value_day = self._booking_days(at, value_date)
        account = self._active_account(iban)
        new_balance = account["balance_cents"] - amount_cents
        if new_balance < -account["overdraft_limit_cents"]:
            raise InsufficientFunds(iban)
        self.db.execute(
            "UPDATE accounts SET balance_cents = ? WHERE id = ?", (new_balance, account["id"])
        )
        return self._insert_booking(account["id"], booking_day, value_day, -amount_cents, kind,
                                    counterparty_name, counterparty_iban, purpose, transfer_id)

    def post_transfer(self, debtor_iban, creditor_iban, amount_cents, creditor_name=None, purpose=None,
                      at=None, transfer_id=None):
        """Move money between two accounts. External creditors go through the clearing account."""
        if not validate_iban(creditor_iban):
            raise InvalidIban(creditor_iban)
        debtor_iban = normalize_iban(debtor_iban)
        creditor_iban = normalize_iban(creditor_iban)
        if debtor_iban == creditor_iban:
            raise BankError("debtor and creditor are the same account")
        with self.transaction():
            debtor = self.getAccount(debtor_iban)
            self.debit(debtor_iban, amount_cents, "TRANSFER_OUT", at, None, creditor_name, creditor_iban,
                       purpose, transfer_id)
            debtor_name = self._account_holder_name(debtor)
            if self.account_exists(creditor_iban):
                self.credit(creditor_iban, amount_cents, "TRANSFER_IN", at, None, debtor_name, debtor_iban,
                            purpose, transfer_id)
            else:
                self.ensure_clearing_account()
                self.credit(CLEARING_IBAN, amount_cents, "CLEARING", at, None, creditor_name, creditor_iban,
                            purpose, transfer_id)

    def _account_holder_name(self, account):
        if account["customer_id"] is None:
            return None
        return self.customer_display_name(self.getCustomer(account["customer_id"]))

    def cash_deposit(self, iban, amount_cents, branch="Hauptstelle", at=None):
        return self.credit(iban, amount_cents, "CASH_IN", at=at, purpose="Bareinzahlung %s" % branch)

    def cash_withdrawal(self, iban, amount_cents, branch="Hauptstelle", at=None):
        account = self.getAccount(iban)
        if account["product_code"] == "FESTGELD":
            raise BankError("no cash withdrawal from fixed term accounts")
        return self.debit(iban, amount_cents, "CASH_OUT", at=at, purpose="Barauszahlung %s" % branch)

    def card_payment(self, iban, amount_cents, merchant, used_on=None, at=None):
        """Card clearing: the booking arrives later, the value date is the day the card was used."""
        account = self.getAccount(iban)
        if account["product_code"] != "GIRO":
            raise BankError("cards are only issued for current accounts")
        return self.debit(iban, amount_cents, "CARD", at=at, value_date=used_on, counterparty_name=merchant,
                          purpose="Kartenzahlung")

    def directDebit(self, iban, amountCents, creditorName, creditorIban, mandateRef, at=None):
        account = self.getAccount(iban)
        if account["product_code"] != "GIRO":
            raise BankError("direct debits are only possible from current accounts")
        return self.debit(iban, amountCents, "DIRECT_DEBIT", at=at, counterparty_name=creditorName,
                          counterparty_iban=creditorIban, purpose="Mandat %s" % mandateRef)

    def returnDirectDebit(self, bookingId, reason="Widerspruch", at=None):
        row = self.db.execute("SELECT * FROM bookings WHERE id = ?", (bookingId,)).fetchone()
        if row is None:
            raise BankError("unknown booking %s" % bookingId)
        if row["kind"] != "DIRECT_DEBIT":
            raise BankError("booking %s is not a direct debit" % bookingId)
        account = self.get_account_by_id(row["account_id"])
        return self.post_booking(account["iban"], -row["amount_cents"], "DIRECT_DEBIT_RETURN", at=at,
                                 value_date=row["value_date"], counterparty_name=row["counterparty_name"],
                                 counterparty_iban=row["counterparty_iban"], purpose="Rueckgabe: %s" % reason)

    def salary_credit(self, iban, amount_cents, employer, month_label, at=None):
        return self.credit(iban, amount_cents, "SALARY", at=at, counterparty_name=employer,
                           purpose="Gehalt %s" % month_label)

    def move_between_own_accounts(self, from_iban, to_iban, amount_cents, at=None):
        """Book between two accounts of the same customer, no IBAN check needed."""
        source = self.getAccount(from_iban)
        target = self.getAccount(to_iban)
        if source["customer_id"] != target["customer_id"]:
            raise BankError("accounts belong to different customers")
        if source["product_code"] == "FESTGELD" or target["product_code"] == "FESTGELD":
            raise BankError("fixed term accounts cannot take part in transfers")
        with self.transaction():
            self.debit(source["iban"], amount_cents, "TRANSFER_OUT", at=at, counterparty_iban=target["iban"],
                       purpose="Umbuchung")
            self.credit(target["iban"], amount_cents, "TRANSFER_IN", at=at, counterparty_iban=source["iban"],
                        purpose="Umbuchung")

    def extend_maturity(self, iban, new_maturity):
        account = self.getAccount(iban)
        if account["product_code"] != "FESTGELD":
            raise BankError("only fixed term accounts have a maturity date")
        if account["maturity_date"] and _iso(new_maturity) <= account["maturity_date"]:
            raise BankError("new maturity must be later than the current one")
        self.db.execute("UPDATE accounts SET maturity_date = ? WHERE id = ?", (_iso(new_maturity), account["id"]))

    def chargeFee(self, iban, amountCents, purpose="Gebuehr", at=None):
        return self.post_booking(iban, -abs(amountCents), "FEE", at=at, purpose=purpose)

    def reverse_booking(self, booking_id, at=None):
        row = self.db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if row is None:
            raise BankError("unknown booking %s" % booking_id)
        account = self.get_account_by_id(row["account_id"])
        return self.post_booking(account["iban"], -row["amount_cents"], "REVERSAL", at=at,
                                 value_date=row["value_date"], counterparty_name=row["counterparty_name"],
                                 counterparty_iban=row["counterparty_iban"],
                                 purpose="Storno %s" % (row["purpose"] or booking_id))

    def list_bookings(self, iban, from_date=None, to_date=None, limit=None):
        account = self.getAccount(iban)
        sql = "SELECT * FROM bookings WHERE account_id = ?"
        args = [account["id"]]
        if from_date is not None:
            sql += " AND booking_date >= ?"
            args.append(_iso(from_date))
        if to_date is not None:
            sql += " AND booking_date <= ?"
            args.append(_iso(to_date))
        sql += " ORDER BY booking_date, id"
        if limit is not None:
            sql += " LIMIT ?"
            args.append(limit)
        return self.db.execute(sql, args).fetchall()

    def getBookingsForPeriod(self, iban, fromDate, toDate, kind=None):
        account = self.getAccount(iban)
        sql = "SELECT * FROM bookings WHERE account_id = ? AND booking_date >= ? AND booking_date <= ?"
        args = [account["id"], _iso(fromDate), _iso(toDate)]
        if kind is not None:
            sql += " AND kind = ?"
            args.append(kind)
        sql += " ORDER BY booking_date, id"
        return self.db.execute(sql, args).fetchall()

    def balance_at(self, iban, day):
        """Balance by booking date at the end of the given day, used for statements."""
        account = self.getAccount(iban)
        row = self.db.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM bookings WHERE account_id = ? AND booking_date <= ?",
            (account["id"], _iso(day)),
        ).fetchone()
        return row[0]

    def check_balance(self, iban):
        """True when the stored balance matches the sum of the bookings."""
        account = self.getAccount(iban)
        row = self.db.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM bookings WHERE account_id = ?", (account["id"],)
        ).fetchone()
        return row[0] == account["balance_cents"]

    # ------------------------------------------------------------------
    # interest
    # ------------------------------------------------------------------

    def _day_basis(self, day_count):
        if day_count == "30E/360":
            return 360
        return 365

    def _day_weight(self, day_count, day):
        if day_count != "30E/360":
            return 1
        if day.day == 31:
            return 0
        if day.month == 2 and (day + timedelta(days=1)).month == 3:
            return 30 - day.day + 1
        return 1

    def _round_interest(self, numerator, denominator):
        exact = Decimal(numerator) / Decimal(denominator)
        return int(exact.quantize(Decimal(1)))

    def interest_booked(self, iban, year):
        rows = self.getBookingsForPeriod(iban, date(year, 1, 1), date(year, 12, 31), "INTEREST")
        return sum(r["amount_cents"] for r in rows)

    def rate_for(self, iban):
        account = self.getAccount(iban)
        product = self._get_product(account["product_code"])
        return {"credit_bp": product["credit_rate_bp"], "debit_bp": product["debit_rate_bp"],
                "day_count": product["day_count"]}

    def _interest_rows(self, to_date, account_id=None):
        sql = "SELECT account_id, booking_date, amount_cents FROM bookings WHERE booking_date <= ?"
        args = [_iso(to_date)]
        if account_id is not None:
            sql += " AND account_id = ?"
            args.append(account_id)
        sql += " ORDER BY account_id, booking_date, id"
        return self.db.execute(sql, args).fetchall()

    def _interest_from_rows(self, product, rows, from_date, to_date):
        day_count = product["day_count"]
        credit_rate = product["credit_rate_bp"]
        debit_rate = product["debit_rate_bp"]
        numerator = 0
        day = from_date
        while day <= to_date:
            balance = 0
            for row in rows:
                if parse_date(row[1]) <= day:
                    balance += row[2]
            rate = credit_rate if balance >= 0 else debit_rate
            numerator += balance * rate * self._day_weight(day_count, day)
            day += timedelta(days=1)
        return self._round_interest(numerator, 10000 * self._day_basis(day_count))

    def calculate_interest(self, iban, from_date, to_date):
        """Interest in cents for all calendar days from from_date to to_date, both included."""
        account = self.getAccount(iban)
        product = self._get_product(account["product_code"])
        from_day = parse_date(from_date)
        to_day = parse_date(to_date)
        rows = self._interest_rows(to_day, account["id"])
        return self._interest_from_rows(product, rows, from_day, to_day)

    # ------------------------------------------------------------------
    # end of day
    # ------------------------------------------------------------------

    def run_end_of_day(self, business_date):
        from core.eod import EndOfDayProcessor
        return EndOfDayProcessor(self).run(parse_date(business_date))

    # ------------------------------------------------------------------
    # reports
    # ------------------------------------------------------------------

    def customer_summary(self, customerId):
        customer = self.getCustomer(customerId)
        accounts = self.get_account_rows_for_customer(customerId)
        total = 0
        lines = []
        for acct in accounts:
            total += acct["balance_cents"]
            lines.append({
                "iban": acct["iban"],
                "product": acct["product_name"],
                "balance": format_eur(acct["balance_cents"]),
                "balance_cents": acct["balance_cents"],
            })
        return {
            "customer_no": customer["customer_no"],
            "name": self.customer_display_name(customer),
            "accounts": lines,
            "total_cents": total,
            "total": format_eur(total),
        }

    def product_totals(self):
        rows = self.db.execute(
            "SELECT product_code, COUNT(*) AS accounts, SUM(balance_cents) AS balance_cents"
            " FROM accounts WHERE status != 'CLOSED' GROUP BY product_code ORDER BY product_code"
        ).fetchall()
        return [dict(r) for r in rows]

    def overdrawn_accounts(self):
        return self.db.execute(
            "SELECT * FROM accounts WHERE balance_cents < 0 AND product_code != 'CLEARING' ORDER BY balance_cents"
        ).fetchall()

    def accounts_over_limit(self):
        return self.db.execute(
            "SELECT * FROM accounts WHERE balance_cents < -overdraft_limit_cents"
            " AND product_code != 'CLEARING' ORDER BY id"
        ).fetchall()

    def large_movements(self, fromDate, toDate, thresholdCents):
        return self.db.execute(
            "SELECT b.*, a.iban FROM bookings b JOIN accounts a ON a.id = b.account_id"
            " WHERE b.booking_date >= ? AND b.booking_date <= ? AND ABS(b.amount_cents) >= ?"
            " ORDER BY b.booking_date, b.id",
            (_iso(fromDate), _iso(toDate), thresholdCents),
        ).fetchall()

    def daily_turnover(self, day):
        row = self.db.execute(
            "SELECT COUNT(*) AS bookings,"
            " COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) AS credits,"
            " COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) AS debits"
            " FROM bookings WHERE booking_date = ?",
            (_iso(day),),
        ).fetchone()
        return dict(row)

    def dormant_accounts(self, sinceDate):
        return self.db.execute(
            "SELECT a.* FROM accounts a WHERE a.status = 'ACTIVE' AND a.product_code != 'CLEARING'"
            " AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.account_id = a.id AND b.booking_date >= ?)"
            " ORDER BY a.id",
            (_iso(sinceDate),),
        ).fetchall()

    def total_balance(self):
        row = self.db.execute("SELECT COALESCE(SUM(balance_cents), 0) FROM accounts").fetchone()
        return row[0]


def _today():
    return berlin_date(utc_now()).isoformat()


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value
