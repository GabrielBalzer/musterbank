"""Dunning for accounts above their overdraft limit."""
from core.dates import parse_date
from core.iban import format_iban
from core.mailbox import Mailbox
from core.money import format_eur

DAYS_BETWEEN_LEVELS = 14
FEE_BY_LEVEL = {1: 0, 2: 500, 3: 1500}
MAX_LEVEL = 3

LETTER_LEVEL_1 = """Musterbank AG
Musterstadt, den {date}

Kontoüberziehung

Guten Tag {name},

Ihr Konto {iban} weist einen Saldo von {balance} aus und liegt damit {excess} über dem
vereinbarten Überziehungsrahmen. Bitte gleichen Sie den Betrag zeitnah aus.

Mit freundlichen Grüßen
Ihre Musterbank AG
"""

LETTER_LEVEL_2 = """Musterbank AG
Musterstadt, den {date}

Zweite Erinnerung: Kontoüberziehung

Guten Tag {name},

trotz unserer Erinnerung liegt Ihr Konto {iban} mit einem Saldo von {balance} weiterhin {excess}
über dem vereinbarten Überziehungsrahmen. Für diese Erinnerung berechnen wir {fee}.

Mit freundlichen Grüßen
Ihre Musterbank AG
"""

LETTER_LEVEL_3 = """Musterbank AG
Musterstadt, den {date}

Letzte Mahnung: Kontoüberziehung

Guten Tag {name},

Ihr Konto {iban} liegt mit einem Saldo von {balance} weiterhin {excess} über dem vereinbarten
Überziehungsrahmen. Für diese Mahnung berechnen wir {fee}. Sollte der Betrag nicht binnen 14 Tagen
ausgeglichen werden, sperren wir das Konto.

Mit freundlichen Grüßen
Ihre Musterbank AG
"""

LETTERS = {1: LETTER_LEVEL_1, 2: LETTER_LEVEL_2, 3: LETTER_LEVEL_3}


class DunningProcessor:
    def __init__(self, bank):
        self.bank = bank
        self.db = bank.db

    def open_notice(self, iban):
        return self.db.execute(
            "SELECT * FROM dunning_notices WHERE iban = ? AND resolved_on IS NULL ORDER BY level DESC, id DESC LIMIT 1",
            (iban,),
        ).fetchone()

    def _resolve(self, iban, day):
        self.db.execute(
            "UPDATE dunning_notices SET resolved_on = ? WHERE iban = ? AND resolved_on IS NULL",
            (day.isoformat(), iban),
        )

    def _next_level(self, notice, day):
        if notice is None:
            return 1
        if notice["level"] >= MAX_LEVEL:
            return None
        waited = (day - parse_date(notice["notice_date"])).days
        if waited < DAYS_BETWEEN_LEVELS:
            return None
        return notice["level"] + 1

    def _issue(self, account, level, day):
        excess = -account["balance_cents"] - account["overdraft_limit_cents"]
        fee = FEE_BY_LEVEL[level]
        cur = self.db.execute(
            "INSERT INTO dunning_notices (iban, level, notice_date, excess_cents, fee_cents) VALUES (?, ?, ?, ?, ?)",
            (account["iban"], level, day.isoformat(), excess, fee),
        )
        if fee:
            self.bank._insert_booking(account["id"], day, day, -fee, "FEE", purpose="Mahnung Stufe %d" % level)
            self.db.execute(
                "UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?", (fee, account["id"])
            )
        return cur.lastrowid

    def run(self, business_date):
        """Issue the notices due on business_date and close the ones no longer needed."""
        day = parse_date(business_date)
        issued = []
        resolved = 0
        with self.bank.transaction():
            open_rows = self.db.execute(
                "SELECT DISTINCT iban FROM dunning_notices WHERE resolved_on IS NULL"
            ).fetchall()
            for row in open_rows:
                account = self.bank.getAccount(row["iban"])
                if account["balance_cents"] >= -account["overdraft_limit_cents"]:
                    self._resolve(row["iban"], day)
                    resolved += 1
            for account in self.bank.accounts_over_limit():
                level = self._next_level(self.open_notice(account["iban"]), day)
                if level is None:
                    continue
                self._issue(account, level, day)
                issued.append({"iban": account["iban"], "level": level})
                if level == MAX_LEVEL and account["status"] == "ACTIVE":
                    self.bank.blockAccount(account["iban"])
        return {"issued": issued, "resolved": resolved}

    def render_letter(self, notice_id):
        notice = self.db.execute("SELECT * FROM dunning_notices WHERE id = ?", (notice_id,)).fetchone()
        if notice is None:
            raise ValueError("unknown notice %s" % notice_id)
        account = self.bank.getAccount(notice["iban"])
        customer = self.bank.getCustomer(account["customer_id"])
        day = parse_date(notice["notice_date"])
        return LETTERS[notice["level"]].format(
            date=day.strftime("%d.%m.%Y"),
            name=self.bank.customer_display_name(customer),
            iban=format_iban(account["iban"]),
            balance=format_eur(account["balance_cents"]),
            excess=format_eur(notice["excess_cents"]),
            fee=format_eur(notice["fee_cents"]),
        )

    def deliver_letters(self, business_date):
        """Put the letters of all notices issued on business_date into the customer mailboxes."""
        mailbox = Mailbox(self.bank)
        rows = self.db.execute(
            "SELECT id, iban, level FROM dunning_notices WHERE notice_date = ? ORDER BY id",
            (parse_date(business_date).isoformat(),),
        ).fetchall()
        for row in rows:
            account = self.bank.getAccount(row["iban"])
            subject = "Kontoüberziehung, Stufe %d" % row["level"]
            mailbox.deliver(account["customer_id"], subject, self.render_letter(row["id"]))
        return len(rows)

    def history(self, iban):
        return self.db.execute(
            "SELECT * FROM dunning_notices WHERE iban = ? ORDER BY notice_date, id", (iban,)
        ).fetchall()
