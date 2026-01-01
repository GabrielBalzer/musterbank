import http.cookiejar
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode

import pytest

from core.iban import build_de_iban
from core.mailbox import Mailbox

BOOKED_AT = datetime(2025, 3, 3, 10, 15, tzinfo=timezone.utc)
EXTERNAL = build_de_iban("09876500", 555)


class Browser:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, path):
        return self._open(path, None)

    def post(self, path, **form):
        return self._open(path, urlencode(form).encode("utf-8"))

    def _open(self, path, data):
        try:
            with self.opener.open(self.base + path, data=data, timeout=10) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")


@pytest.fixture
def browser(web_url, bank, giro, tagesgeld, customer_id):
    bank.credit(tagesgeld, 50000, at=BOOKED_AT, purpose="Sparen")
    client = Browser(web_url)
    client.post("/login", customer_no=bank.getCustomer(customer_id)["customer_no"], pin="1234")
    return client


def test_login_page_is_public(web_url):
    assert Browser(web_url).get("/login")[0] == 200


def test_anonymous_is_redirected(web_url):
    status, body = Browser(web_url).get("/")
    assert status == 200
    assert "Anmeldung" in body


def test_wrong_pin(web_url, bank, customer_id):
    status, _ = Browser(web_url).post("/login", customer_no=bank.getCustomer(customer_id)["customer_no"], pin="0000")
    assert status == 401


def test_overview(browser, giro):
    status, body = browser.get("/")
    assert status == 200
    assert "Tilda Rosenthaler" in body
    assert giro in body


def test_account_page(browser, tagesgeld):
    status, body = browser.get("/accounts/%s" % tagesgeld)
    assert status == 200
    assert "Sparen" in body


def test_foreign_account_is_hidden(browser, bank):
    other = bank.createCustomer("Ben", "Zaunkoenig")
    foreign = bank.open_account(other, "GIRO")
    assert browser.get("/accounts/%s" % foreign)[0] == 404
    assert browser.get("/statements/%s" % foreign)[0] == 404


def test_statement_page_and_csv(browser, tagesgeld):
    status, body = browser.get("/statements/%s?month=2025-03" % tagesgeld)
    assert status == 200
    assert "Sparen" in body
    assert browser.get("/statements/%s?month=kaputt" % tagesgeld)[0] == 404
    status, body = browser.get("/statements/%s?month=2025-03&format=csv" % tagesgeld)
    assert status == 200
    assert body.startswith("Buchungstag")


def test_transfer(browser, bank, giro):
    assert browser.get("/transfer")[0] == 200
    before = bank.getBalance(giro)
    status, body = browser.post("/transfer", debtor_iban=giro, creditor_iban=EXTERNAL, creditor_name="Fremdbank Kunde",
                                amount="10,00", purpose="Test")
    assert status == 200
    assert "ausgeführt" in body
    assert bank.getBalance(giro) == before - 1000


def test_transfer_errors(browser, giro):
    other = build_de_iban("01234500", 4711)
    assert browser.post("/transfer", debtor_iban=other, creditor_iban=EXTERNAL, creditor_name="X", amount="1,00")[0] == 400
    assert browser.post("/transfer", debtor_iban=giro, creditor_iban=EXTERNAL, creditor_name="X", amount="abc")[0] == 400
    assert browser.post("/transfer", debtor_iban=giro, creditor_iban="DE00", creditor_name="X", amount="1,00")[0] == 400
    assert browser.post("/transfer", debtor_iban=giro, creditor_iban=EXTERNAL, creditor_name="X", amount="99999,00")[0] == 409


def test_move(browser, bank, giro, tagesgeld):
    assert browser.get("/move")[0] == 200
    before = bank.getBalance(tagesgeld)
    assert browser.post("/move", from_iban=giro, to_iban=tagesgeld, amount="5,00")[0] == 200
    assert bank.getBalance(tagesgeld) == before + 500
    assert browser.post("/move", from_iban=giro, to_iban=giro, amount="5,00")[0] == 400
    assert browser.post("/move", from_iban=giro, to_iban=tagesgeld, amount="abc")[0] == 400
    assert browser.post("/move", from_iban=giro, to_iban=tagesgeld, amount="99999,00")[0] == 409


def test_mailbox_pages(browser, bank, customer_id):
    message = Mailbox(bank).deliver(customer_id, "Willkommen", "Guten Tag")
    status, body = browser.get("/mailbox")
    assert status == 200
    assert "Willkommen" in body
    status, body = browser.get("/mailbox/%d" % message)
    assert status == 200
    assert "Guten Tag" in body
    assert browser.get("/mailbox/99999")[0] == 404


def test_profile(browser, bank, customer_id):
    assert browser.get("/profile")[0] == 200
    assert browser.post("/profile", street="Neuer Weg 1", zip="00555", city="Fiktingen", email="n@example.org")[0] == 200
    assert bank.getCustomer(customer_id)["city"] == "Fiktingen"
    assert browser.post("/profile", street="", zip="1", city="", email="n@example.org")[0] == 400
    assert browser.post("/profile", street="Weg", zip="00555", city="Ort", email="kaputt")[0] == 400


def test_logout(browser):
    assert "Anmeldung" in browser.post("/logout")[1]


def test_static_and_unknown(browser):
    assert browser.get("/static/style.css")[0] == 200
    assert browser.get("/static/logo.svg")[0] == 200
    assert browser.get("/static/../app.py")[0] == 404
    assert browser.get("/gibt-es-nicht")[0] == 404
    assert browser.post("/gibt-es-nicht")[0] == 404
