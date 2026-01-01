"""Transfer use cases on top of the core bank."""
from typing import List, Optional

from core.bank import BankCore
from core.dates import utc_now
from core.errors import AccountNotActive, InsufficientFunds, InvalidIban, UnknownAccount
from core.iban import normalize_iban, validate_iban
from core.money import to_cents
from payments.models import Transfer, TransferRequest, ValidationError
from payments.repository import STATUS_EXECUTED, TransferRepository


class TransferRejected(Exception):
    """A valid request the bank declines, for example for lack of funds (HTTP 409)."""


class AccountNotFound(Exception):
    """The debtor account does not exist (HTTP 404)."""


class TransferService:
    def __init__(self, db_path: str):
        self._bank = BankCore(db_path)
        self._transfers = TransferRepository(self._bank.db)

    def close(self) -> None:
        self._bank.close()

    def create_transfer(self, request: TransferRequest) -> Transfer:
        debtor = normalize_iban(request.debtor_iban)
        creditor = normalize_iban(request.creditor_iban)
        if not validate_iban(debtor):
            raise ValidationError("debtor_iban is not a valid IBAN")
        if not validate_iban(creditor):
            raise ValidationError("creditor_iban is not a valid IBAN")
        if debtor == creditor:
            raise ValidationError("debtor and creditor must differ")
        amount_cents = to_cents(request.amount)
        if amount_cents <= 0:
            raise ValidationError("amount must be at least one cent")
        now = utc_now()
        try:
            with self._bank.transaction():
                transfer_id = self._transfers.insert(
                    debtor, creditor, request.creditor_name, amount_cents, request.purpose,
                    STATUS_EXECUTED, now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
                self._bank.post_transfer(debtor, creditor, amount_cents, request.creditor_name,
                                         request.purpose, at=now, transfer_id=transfer_id)
        except UnknownAccount as exc:
            raise AccountNotFound(str(exc)) from exc
        except (InsufficientFunds, AccountNotActive, InvalidIban) as exc:
            raise TransferRejected(type(exc).__name__) from exc
        transfer = self._transfers.get(transfer_id)
        assert transfer is not None
        return transfer

    def get_transfer(self, transfer_id: int) -> Optional[Transfer]:
        return self._transfers.get(transfer_id)

    def list_transfers(self, debtor_iban: str, limit: int = 50) -> List[Transfer]:
        return self._transfers.list_for_debtor(normalize_iban(debtor_iban), limit)

    def get_balance(self, iban: str) -> int:
        try:
            return self._bank.get_balance(iban)
        except UnknownAccount as exc:
            raise AccountNotFound(str(exc)) from exc
