import json
import urllib.error
import urllib.request

import pytest

from core.iban import build_de_iban
from payments.models import TransferRequest, ValidationError
from payments.service import AccountNotFound, TransferRejected, TransferService

EXTERNAL = build_de_iban("09876500", 555)


def _request(giro, **changes):
    payload = {"debtor_iban": giro, "creditor_iban": EXTERNAL, "creditor_name": "Fremdbank Kunde", "amount": 12.34,
               "purpose": "Rechnung 1"}
    payload.update(changes)
    return payload


def _call(url, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url + path, data=data, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.mark.parametrize("changes", [
    {"debtor_iban": ""},
    {"creditor_iban": None},
    {"creditor_name": "  "},
    {"amount": "zwoelf"},
    {"amount": True},
    {"amount": 0},
    {"amount": -5},
    {"amount": float("inf")},
    {"purpose": 7},
    {"purpose": "x" * 200},
    {"creditor_name": "y" * 100},
])
def test_request_validation(changes):
    with pytest.raises(ValidationError):
        TransferRequest.from_json(_request(build_de_iban("01234500", 1), **changes))


def test_request_must_be_object():
    with pytest.raises(ValidationError):
        TransferRequest.from_json([1, 2])


def test_service_executes_transfer(bank, db_path, giro):
    service = TransferService(db_path)
    transfer = service.create_transfer(TransferRequest.from_json(_request(giro)))
    assert transfer.status == "EXECUTED"
    assert transfer.amount_cents == 1234
    assert service.get_transfer(transfer.id) == transfer
    assert service.list_transfers(giro) == [transfer]
    assert service.get_balance(giro) == 100000 - 1234
    assert transfer.to_json()["amount"] == 12.34
    service.close()


def test_service_rejections(bank, db_path, giro):
    service = TransferService(db_path)
    with pytest.raises(ValidationError):
        service.create_transfer(TransferRequest.from_json(_request(giro, creditor_iban="DE00123")))
    with pytest.raises(ValidationError):
        service.create_transfer(TransferRequest.from_json(_request("DE00123")))
    with pytest.raises(ValidationError):
        service.create_transfer(TransferRequest.from_json(_request(giro, creditor_iban=giro)))
    with pytest.raises(ValidationError):
        service.create_transfer(TransferRequest.from_json(_request(giro, amount=0.001)))
    with pytest.raises(TransferRejected):
        service.create_transfer(TransferRequest.from_json(_request(giro, amount=999999.0)))
    with pytest.raises(AccountNotFound):
        service.create_transfer(TransferRequest.from_json(_request(build_de_iban("01234500", 12345))))
    with pytest.raises(AccountNotFound):
        service.get_balance(build_de_iban("01234500", 12345))
    service.close()


def test_api_health(payments_url):
    assert _call(payments_url, "/health") == (200, {"status": "ok"})


def test_api_transfer(payments_url, bank, giro):
    status, body = _call(payments_url, "/transfers", _request(giro))
    assert status == 201
    assert body["status"] == "EXECUTED"
    assert _call(payments_url, "/transfers/%d" % body["id"])[0] == 200
    status, balance = _call(payments_url, "/accounts/%s/balance" % giro)
    assert status == 200
    assert balance["balance_cents"] == 100000 - 1234
    status, listing = _call(payments_url, "/transfers?debtor_iban=%s&limit=5" % giro)
    assert status == 200
    assert len(listing["transfers"]) == 1


def test_api_errors(payments_url, bank, giro):
    assert _call(payments_url, "/transfers", _request(giro, amount="x"))[0] == 400
    assert _call(payments_url, "/transfers", _request(giro, amount=999999.0))[0] == 409
    assert _call(payments_url, "/transfers", _request(build_de_iban("01234500", 12345)))[0] == 404
    assert _call(payments_url, "/transfers/4711")[0] == 404
    assert _call(payments_url, "/accounts/%s/balance" % build_de_iban("01234500", 12345))[0] == 404
    assert _call(payments_url, "/unbekannt")[0] == 404
    assert _call(payments_url, "/unbekannt", {"a": 1})[0] == 404
    assert _call(payments_url, "/transfers?limit=5")[0] == 400
    assert _call(payments_url, "/transfers?debtor_iban=x&limit=y")[0] == 400


def test_api_rejects_invalid_json(payments_url, bank):
    request = urllib.request.Request(payments_url + "/transfers", data=b"{kein json", method="POST")
    with pytest.raises(urllib.error.HTTPError) as info:
        urllib.request.urlopen(request, timeout=10)
    assert info.value.code == 400
