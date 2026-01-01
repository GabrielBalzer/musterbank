from datetime import datetime, timezone

BOOKED_AT = datetime(2025, 1, 2, 9, 40, tzinfo=timezone.utc)
NEW_YEAR = datetime(2025, 1, 1, 14, 30, tzinfo=timezone.utc)


def test_savings_interest_for_a_month(bank, tagesgeld):
    bank.credit(tagesgeld, 1000000, at=BOOKED_AT, value_date="2025-01-02")
    assert bank.calculate_interest(tagesgeld, "2025-03-01", "2025-03-31") == 1274


def test_no_balance_no_interest(bank, tagesgeld):
    assert bank.calculate_interest(tagesgeld, "2025-03-01", "2025-03-31") == 0


def test_fixed_term_earns_interest(bank, customer_id):
    fixed = bank.open_account(customer_id, "FESTGELD", opened_on="2025-01-02", maturity_date="2025-12-31")
    bank.credit(fixed, 2500000, at=BOOKED_AT, value_date="2025-01-02")
    assert bank.calculate_interest(fixed, "2025-01-02", "2025-06-30") > 0


def test_current_account_pays_no_credit_interest(bank, giro):
    assert bank.calculate_interest(giro, "2025-01-01", "2025-03-31") == 0


def test_overdraft_costs_interest(bank, customer_id):
    iban = bank.open_account(customer_id, "GIRO", opened_on="2025-01-01", overdraft_limit_cents=100000)
    bank.debit(iban, 40000, at=NEW_YEAR, value_date="2025-01-01")
    assert bank.calculate_interest(iban, "2025-01-01", "2025-03-31") == -1150


def test_february_counts_thirty_days_on_current_accounts(bank, customer_id):
    iban = bank.open_account(customer_id, "GIRO", opened_on="2025-01-01", overdraft_limit_cents=100000)
    bank.debit(iban, 36000, at=NEW_YEAR, value_date="2025-01-01")
    february = bank.calculate_interest(iban, "2025-02-01", "2025-02-28")
    april = bank.calculate_interest(iban, "2025-04-01", "2025-04-30")
    assert february == april


def test_rate_and_booked_interest(bank, tagesgeld):
    assert bank.rate_for(tagesgeld)["credit_bp"] == 150
    assert bank.interest_booked(tagesgeld, 2025) == 0
