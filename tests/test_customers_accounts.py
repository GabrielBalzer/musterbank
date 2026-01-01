import pytest

from core.bank import CLEARING_IBAN, KIND_BUSINESS
from core.errors import AccountNotActive, BankError, InvalidAmount, UnknownAccount, UnknownCustomer
from core.iban import validate_iban


def test_create_and_get_customer(bank, customer_id):
    customer = bank.getCustomer(customer_id)
    assert customer["last_name"] == "Rosenthaler"
    assert customer["customer_no"].startswith("K")
    assert bank.get_customer_by_no(customer["customer_no"])["id"] == customer_id


def test_unknown_customer(bank):
    with pytest.raises(UnknownCustomer):
        bank.getCustomer(999)


def test_find_and_list(bank, customer_id):
    assert len(bank.find_customers("Rosen")) == 1
    assert bank.listCustomers()


def test_update_customer(bank, customer_id):
    bank.updateCustomerAddress(customer_id, "Neuer Weg 1", "00999", "Fiktingen")
    bank.update_customer_email(customer_id, "neu@example.org")
    customer = bank.getCustomer(customer_id)
    assert customer["city"] == "Fiktingen"
    assert customer["email"] == "neu@example.org"


def test_display_name(bank, customer_id):
    assert bank.customer_display_name(bank.getCustomer(customer_id)) == "Tilda Rosenthaler"
    company = bank.createCustomer(None, None, kind=KIND_BUSINESS, company_name="Fichtenrodt Metallbau GmbH")
    assert bank.customer_display_name(bank.getCustomer(company)) == "Fichtenrodt Metallbau GmbH"


def test_close_customer(bank, customer_id, tagesgeld):
    with pytest.raises(BankError):
        bank.closeCustomer(customer_id)
    bank.closeAccount(tagesgeld)
    bank.closeCustomer(customer_id)
    assert bank.getCustomer(customer_id)["email"] is None


def test_merge_customers(bank, customer_id, tagesgeld):
    other = bank.createCustomer("Tilda", "Rosenthaler")
    bank.merge_customers(customer_id, other)
    assert bank.getAccount(tagesgeld)["customer_id"] == other


def test_open_account_gives_valid_iban(bank, customer_id):
    iban = bank.open_account(customer_id, "GIRO")
    assert validate_iban(iban)
    assert bank.account_exists(iban)
    assert bank.getBalance(iban) == 0


def test_open_account_checks_product_and_customer(bank, customer_id):
    with pytest.raises(BankError):
        bank.open_account(customer_id, "BAUSPAR")
    with pytest.raises(UnknownCustomer):
        bank.open_account(404, "GIRO")
    with pytest.raises(BankError):
        bank.open_account(customer_id, "FESTGELD")


def test_account_listing(bank, customer_id, giro, tagesgeld):
    assert len(bank.getAccountsForCustomer(customer_id)) == 2
    rows = bank.get_account_rows_for_customer(customer_id)
    assert rows[0]["product_name"] == "Girokonto"
    assert bank.get_account_by_id(rows[0]["id"])["iban"] == giro
    assert len(bank.list_products()) == 4


def test_unknown_account(bank):
    with pytest.raises(UnknownAccount):
        bank.getAccount("DE00000000000000000000")
    with pytest.raises(UnknownAccount):
        bank.get_account_by_id(404)


def test_close_account_requires_zero_balance(bank, giro, tagesgeld):
    with pytest.raises(BankError):
        bank.closeAccount(giro)
    bank.closeAccount(tagesgeld)
    assert bank.getAccount(tagesgeld)["status"] == "CLOSED"


def test_block_and_unblock(bank, giro):
    bank.blockAccount(giro)
    with pytest.raises(AccountNotActive):
        bank.debit(giro, 100)
    bank.unblockAccount(giro)
    assert bank.debit(giro, 100)


def test_overdraft_limit(bank, giro):
    bank.set_overdraft_limit(giro, 1000)
    assert bank.get_available(giro) == bank.get_balance(giro) + 1000
    with pytest.raises(InvalidAmount):
        bank.set_overdraft_limit(giro, -1)


def test_extend_maturity(bank, customer_id, tagesgeld):
    fixed = bank.open_account(customer_id, "FESTGELD", opened_on="2025-01-01", maturity_date="2025-06-30")
    bank.extend_maturity(fixed, "2025-12-31")
    assert bank.getAccount(fixed)["maturity_date"] == "2025-12-31"
    with pytest.raises(BankError):
        bank.extend_maturity(fixed, "2025-01-31")
    with pytest.raises(BankError):
        bank.extend_maturity(tagesgeld, "2025-12-31")


def test_clearing_account(bank):
    assert bank.ensure_clearing_account() == CLEARING_IBAN
    assert bank.ensure_clearing_account() == CLEARING_IBAN
    assert bank.getBalance(CLEARING_IBAN) == 0
