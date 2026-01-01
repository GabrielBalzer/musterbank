from datetime import datetime, timezone

import pytest

from core.errors import EodAlreadyRun

BOOKED_AT = datetime(2025, 1, 2, 9, 40, tzinfo=timezone.utc)


def _kinds(bank, iban):
    return [row["kind"] for row in bank.list_bookings(iban)]


def test_month_end_closes_savings(bank, tagesgeld):
    bank.credit(tagesgeld, 1000000, at=BOOKED_AT, value_date="2025-01-02")
    result = bank.run_end_of_day("2025-01-31")
    assert result["accounts"] == 1
    assert result["interest_cents"] > 0
    assert "INTEREST" in _kinds(bank, tagesgeld)
    assert bank.check_balance(tagesgeld)


def test_no_closing_within_month(bank, tagesgeld):
    bank.credit(tagesgeld, 1000000, at=BOOKED_AT, value_date="2025-01-02")
    result = bank.run_end_of_day("2025-01-15")
    assert result["interest_cents"] == 0
    assert "INTEREST" not in _kinds(bank, tagesgeld)


def test_month_end_charges_fee(bank, giro):
    before = bank.getBalance(giro)
    result = bank.run_end_of_day("2025-02-28")
    assert result["fee_cents"] == 490
    assert bank.getBalance(giro) == before - 490


def test_current_account_closes_quarterly(bank, customer_id):
    iban = bank.open_account(customer_id, "GIRO", opened_on="2025-01-01", overdraft_limit_cents=100000)
    bank.debit(iban, 36000, at=BOOKED_AT, value_date="2025-01-02")
    bank.run_end_of_day("2025-02-28")
    assert "INTEREST" not in _kinds(bank, iban)
    bank.run_end_of_day("2025-03-31")
    assert "INTEREST" in _kinds(bank, iban)


def test_fixed_term_matures(bank, customer_id):
    fixed = bank.open_account(customer_id, "FESTGELD", opened_on="2025-01-02", maturity_date="2025-06-30")
    bank.credit(fixed, 5000000, at=BOOKED_AT, value_date="2025-01-02")
    bank.run_end_of_day("2025-06-30")
    assert bank.getAccount(fixed)["status"] == "MATURED"
    assert bank.getBalance(fixed) > 5000000


def test_run_only_once(bank, giro):
    bank.run_end_of_day("2025-03-14")
    with pytest.raises(EodAlreadyRun):
        bank.run_end_of_day("2025-03-14")


def test_checksum_is_reproducible(tmp_path):
    from core.bank import BankCore

    checksums = []
    for name in ("a.sqlite", "b.sqlite"):
        bank = BankCore(str(tmp_path / name))
        customer = bank.createCustomer("Vera", "Lindenfels")
        iban = bank.open_account(customer, "TAGESGELD", opened_on="2025-01-01")
        bank.credit(iban, 250000, at=BOOKED_AT, value_date="2025-01-02")
        checksums.append(bank.run_end_of_day("2025-01-31")["checksum"])
        bank.close()
    assert checksums[0] == checksums[1]
    assert len(checksums[0]) == 64
