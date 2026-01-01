from datetime import date, datetime, timezone

import pytest

from core.bank import CLEARING_IBAN
from core.errors import BankError, InsufficientFunds, InvalidAmount, InvalidIban
from core.iban import build_de_iban

BOOKED_AT = datetime(2025, 3, 3, 10, 15, tzinfo=timezone.utc)
EXTERNAL = build_de_iban("09876500", 555)


def test_credit_raises_balance(bank, giro):
    before = bank.getBalance(giro)
    bank.credit(giro, 2500, at=BOOKED_AT)
    assert bank.getBalance(giro) == before + 2500
    assert bank.check_balance(giro)


def test_debit_lowers_balance(bank, giro):
    before = bank.getBalance(giro)
    bank.debit(giro, 2500, at=BOOKED_AT)
    assert bank.getBalance(giro) == before - 2500
    assert bank.check_balance(giro)


def test_debit_respects_overdraft(bank, giro):
    with pytest.raises(InsufficientFunds):
        bank.debit(giro, 10000000, at=BOOKED_AT)


def test_debit_can_use_overdraft(bank, giro):
    bank.debit(giro, 120000, at=BOOKED_AT)
    assert bank.getBalance(giro) < 0


@pytest.mark.parametrize("amount", [0, -5])
def test_amount_must_be_positive(bank, giro, amount):
    with pytest.raises(InvalidAmount):
        bank.credit(giro, amount)
    with pytest.raises(InvalidAmount):
        bank.debit(giro, amount)


def test_post_booking_rejects_zero(bank, giro):
    with pytest.raises(InvalidAmount):
        bank.post_booking(giro, 0, "CREDIT")


def test_booking_dates(bank, giro):
    booking_id = bank.credit(giro, 100, at=BOOKED_AT)
    row = bank.db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    assert row["booking_date"] == "2025-03-03"
    assert row["value_date"] == "2025-03-03"


def test_value_date_moves_to_next_business_day(bank, giro):
    saturday = datetime(2025, 3, 1, 16, 20, tzinfo=timezone.utc)
    booking_id = bank.credit(giro, 100, at=saturday)
    row = bank.db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    assert row["value_date"] == "2025-03-03"


def test_transfer_between_own_bank_accounts(bank, giro, customer_id):
    other = bank.open_account(customer_id, "GIRO", opened_on="2025-01-01")
    bank.post_transfer(giro, other, 5000, "Tilda", "Miete", at=BOOKED_AT)
    assert bank.getBalance(other) == 5000
    assert bank.list_bookings(other)[0]["counterparty_name"] == "Tilda Rosenthaler"


def test_transfer_to_external_uses_clearing(bank, giro):
    before = bank.total_balance()
    bank.post_transfer(giro, EXTERNAL, 5000, "Fremdbank Kunde", "Rechnung", at=BOOKED_AT)
    assert bank.getBalance(CLEARING_IBAN) == 5000
    assert bank.total_balance() == before


def test_transfer_checks(bank, giro):
    with pytest.raises(InvalidIban):
        bank.post_transfer(giro, "DE00123", 100)
    with pytest.raises(BankError):
        bank.post_transfer(giro, giro, 100)


def test_failed_transfer_leaves_no_trace(bank, giro):
    before = len(bank.list_bookings(giro))
    with pytest.raises(InsufficientFunds):
        bank.post_transfer(giro, EXTERNAL, 10000000, at=BOOKED_AT)
    assert len(bank.list_bookings(giro)) == before


def test_cash(bank, giro):
    before = bank.getBalance(giro)
    bank.cash_deposit(giro, 1000, at=BOOKED_AT)
    bank.cash_withdrawal(giro, 400, at=BOOKED_AT)
    assert bank.getBalance(giro) == before + 600


def test_cash_not_from_fixed_term(bank, customer_id):
    fixed = bank.open_account(customer_id, "FESTGELD", opened_on="2025-01-01", maturity_date="2025-12-31")
    with pytest.raises(BankError):
        bank.cash_withdrawal(fixed, 100)


def test_card_payment_uses_day_of_use_as_value_date(bank, giro, tagesgeld):
    booking_id = bank.card_payment(giro, 1999, "Kaltenbrueck Markt", used_on="2025-03-01", at=BOOKED_AT)
    row = bank.db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    assert row["value_date"] == "2025-03-01"
    assert row["kind"] == "CARD"
    with pytest.raises(BankError):
        bank.card_payment(tagesgeld, 100, "x")


def test_direct_debit_and_return(bank, giro, tagesgeld):
    before = bank.getBalance(giro)
    booking_id = bank.directDebit(giro, 3000, "Stadtwerke Musterstadt", EXTERNAL, "M-1", at=BOOKED_AT)
    assert bank.getBalance(giro) == before - 3000
    bank.returnDirectDebit(booking_id, at=BOOKED_AT)
    assert bank.getBalance(giro) == before
    with pytest.raises(BankError):
        bank.directDebit(tagesgeld, 100, "x", EXTERNAL, "M-2")
    with pytest.raises(BankError):
        bank.returnDirectDebit(999999)
    other = bank.credit(giro, 100, at=BOOKED_AT)
    with pytest.raises(BankError):
        bank.returnDirectDebit(other)


def test_salary_and_fee(bank, giro):
    before = bank.getBalance(giro)
    bank.salary_credit(giro, 300000, "Birkenried Logistik GmbH", "03/2025", at=BOOKED_AT)
    bank.chargeFee(giro, 490, at=BOOKED_AT)
    assert bank.getBalance(giro) == before + 300000 - 490


def test_reverse_booking(bank, giro):
    before = bank.getBalance(giro)
    booking_id = bank.debit(giro, 700, at=BOOKED_AT, purpose="Kauf")
    bank.reverse_booking(booking_id, at=BOOKED_AT)
    assert bank.getBalance(giro) == before
    with pytest.raises(BankError):
        bank.reverse_booking(999999)


def test_move_between_own_accounts(bank, giro, tagesgeld, customer_id):
    bank.move_between_own_accounts(giro, tagesgeld, 5000, at=BOOKED_AT)
    assert bank.getBalance(tagesgeld) == 5000
    other_customer = bank.createCustomer("Uwe", "Immenkamp")
    foreign = bank.open_account(other_customer, "GIRO")
    with pytest.raises(BankError):
        bank.move_between_own_accounts(giro, foreign, 100)
    fixed = bank.open_account(customer_id, "FESTGELD", opened_on="2025-01-01", maturity_date="2025-12-31")
    with pytest.raises(BankError):
        bank.move_between_own_accounts(giro, fixed, 100)


def test_list_bookings_filters(bank, giro):
    bank.credit(giro, 100, at=BOOKED_AT)
    assert bank.list_bookings(giro, date(2025, 3, 1), date(2025, 3, 31))
    assert not bank.list_bookings(giro, date(2024, 1, 1), date(2024, 1, 31))
    assert len(bank.list_bookings(giro, limit=1)) == 1
    assert bank.getBookingsForPeriod(giro, "2025-03-01", "2025-03-31")
    assert bank.getBookingsForPeriod(giro, "2025-03-01", "2025-03-31", kind="CREDIT")


def test_balance_at(bank, giro):
    assert bank.balance_at(giro, "2024-12-31") == 0
    assert bank.balance_at(giro, "2030-01-01") == bank.getBalance(giro)
