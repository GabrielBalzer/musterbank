"""Request and response types of the transfer service."""
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

MAX_PURPOSE_LENGTH = 140
MAX_NAME_LENGTH = 70


class ValidationError(Exception):
    """The request itself is not acceptable (HTTP 400)."""


@dataclass(frozen=True)
class TransferRequest:
    debtor_iban: str
    creditor_iban: str
    creditor_name: str
    amount: float
    purpose: str = ""

    @classmethod
    def from_json(cls, payload: Any) -> "TransferRequest":
        if not isinstance(payload, dict):
            raise ValidationError("body must be a JSON object")
        for field_name in ("debtor_iban", "creditor_iban", "creditor_name"):
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{field_name} is required")
        amount = payload.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValidationError("amount must be a number")
        if amount != amount or amount in (float("inf"), float("-inf")):
            raise ValidationError("amount must be finite")
        if amount <= 0:
            raise ValidationError("amount must be positive")
        purpose = payload.get("purpose", "")
        if not isinstance(purpose, str):
            raise ValidationError("purpose must be a string")
        if len(purpose) > MAX_PURPOSE_LENGTH:
            raise ValidationError("purpose is too long")
        if len(payload["creditor_name"]) > MAX_NAME_LENGTH:
            raise ValidationError("creditor_name is too long")
        return cls(
            debtor_iban=payload["debtor_iban"],
            creditor_iban=payload["creditor_iban"],
            creditor_name=payload["creditor_name"].strip(),
            amount=float(amount),
            purpose=purpose,
        )


@dataclass(frozen=True)
class Transfer:
    id: int
    debtor_iban: str
    creditor_iban: str
    creditor_name: str
    amount_cents: int
    purpose: Optional[str]
    status: str
    created_at: str

    def to_json(self) -> Dict[str, Any]:
        data = asdict(self)
        data["amount"] = self.amount_cents / 100
        return data
