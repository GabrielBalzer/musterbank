import threading
from datetime import datetime, timezone

import pytest

from core.bank import BankCore
from payments.api import PaymentsServer
from web.app import WebServer

OPENING_TIME = datetime(2025, 1, 2, 11, 5, tzinfo=timezone.utc)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "bank.sqlite")


@pytest.fixture
def bank(db_path):
    instance = BankCore(db_path)
    yield instance
    instance.close()


@pytest.fixture
def customer_id(bank):
    return bank.createCustomer("Tilda", "Rosenthaler", birth_date="1980-05-17", street="Testring 4", zip_code="00123",
                               city="Musterstadt", email="tilda@example.org")


@pytest.fixture
def giro(bank, customer_id):
    iban = bank.open_account(customer_id, "GIRO", opened_on="2025-01-01", overdraft_limit_cents=50000)
    bank.credit(iban, 100000, "OPENING", at=OPENING_TIME, value_date="2025-01-01")
    return iban


@pytest.fixture
def tagesgeld(bank, customer_id):
    return bank.open_account(customer_id, "TAGESGELD", opened_on="2025-01-01")


@pytest.fixture
def payments_url(db_path, bank):
    server = PaymentsServer(("127.0.0.1", 0), db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d" % server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture
def web_url(db_path, bank, payments_url):
    server = WebServer(("127.0.0.1", 0), db_path, payments_url)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d" % server.server_address[1]
    server.shutdown()
    server.server_close()
