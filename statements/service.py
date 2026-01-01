"""Account statements and booking queries."""
from datetime import timedelta

from core.dates import month_end, parse_date
from core.money import format_eur


class StatementService:
    def __init__(self, bank):
        self.bank = bank

    def _line(self, booking):
        return {
            "booking_date": booking["booking_date"],
            "value_date": booking["value_date"],
            "amount_cents": booking["amount_cents"],
            "amount": format_eur(booking["amount_cents"]),
            "kind": booking["kind"],
            "counterparty": booking["counterparty_name"] or "",
            "counterparty_iban": booking["counterparty_iban"] or "",
            "purpose": booking["purpose"] or "",
        }

    def transactions(self, iban, from_date=None, to_date=None, limit=None):
        return [self._line(b) for b in self.bank.list_bookings(iban, from_date, to_date, limit)]

    def recent_transactions(self, iban, count=20):
        rows = self.bank.db.execute(
            "SELECT b.* FROM bookings b JOIN accounts a ON a.id = b.account_id"
            " WHERE a.iban = ? ORDER BY b.booking_date DESC, b.id DESC LIMIT ?",
            (iban, count),
        ).fetchall()
        return [self._line(b) for b in rows]

    def statement(self, iban, from_date, to_date):
        start = parse_date(from_date)
        end = parse_date(to_date)
        account = self.bank.getAccount(iban)
        opening = self.bank.balance_at(iban, start - timedelta(days=1))
        closing = self.bank.balance_at(iban, end)
        lines = self.transactions(iban, start, end)
        credits_cents = sum(l["amount_cents"] for l in lines if l["amount_cents"] > 0)
        debits_cents = sum(l["amount_cents"] for l in lines if l["amount_cents"] < 0)
        holder = ""
        if account["customer_id"] is not None:
            holder = self.bank.customer_display_name(self.bank.getCustomer(account["customer_id"]))
        return {
            "iban": account["iban"],
            "holder": holder,
            "product": account["product_code"],
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "opening_cents": opening,
            "closing_cents": closing,
            "credits_cents": credits_cents,
            "debits_cents": debits_cents,
            "lines": lines,
        }

    def monthly_statement(self, iban, year, month):
        start = parse_date("%04d-%02d-01" % (year, month))
        return self.statement(iban, start, month_end(start))

    def turnover_by_kind(self, iban, from_date, to_date):
        totals = {}
        for booking in self.bank.list_bookings(iban, from_date, to_date):
            kind = booking["kind"]
            totals.setdefault(kind, {"count": 0, "amount_cents": 0})
            totals[kind]["count"] += 1
            totals[kind]["amount_cents"] += booking["amount_cents"]
        return totals

    def available_months(self, iban):
        account = self.bank.getAccount(iban)
        rows = self.bank.db.execute(
            "SELECT DISTINCT substr(booking_date, 1, 7) AS month FROM bookings WHERE account_id = ? ORDER BY month DESC",
            (account["id"],),
        ).fetchall()
        return [row["month"] for row in rows]

    def yearly_overview(self, iban, year):
        months = []
        for month in range(1, 13):
            statement = self.monthly_statement(iban, year, month)
            months.append({
                "month": "%04d-%02d" % (year, month),
                "credits_cents": statement["credits_cents"],
                "debits_cents": statement["debits_cents"],
                "closing_cents": statement["closing_cents"],
            })
        return {
            "iban": iban,
            "year": year,
            "months": months,
            "interest_cents": self.bank.interest_booked(iban, year),
        }
