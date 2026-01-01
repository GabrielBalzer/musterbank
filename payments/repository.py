"""Persistence for transfers."""
import sqlite3
from typing import List, Optional

from payments.models import Transfer

STATUS_PENDING = "PENDING"
STATUS_EXECUTED = "EXECUTED"
STATUS_REJECTED = "REJECTED"


def _to_transfer(row: sqlite3.Row) -> Transfer:
    return Transfer(
        id=row["id"],
        debtor_iban=row["debtor_iban"],
        creditor_iban=row["creditor_iban"],
        creditor_name=row["creditor_name"],
        amount_cents=row["amount_cents"],
        purpose=row["purpose"],
        status=row["status"],
        created_at=row["created_at"],
    )


class TransferRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def insert(self, debtor_iban: str, creditor_iban: str, creditor_name: str, amount_cents: int,
               purpose: str, status: str, created_at: str) -> int:
        cursor = self._conn.execute(
            "INSERT INTO transfers (debtor_iban, creditor_iban, creditor_name, amount_cents,"
            " purpose, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (debtor_iban, creditor_iban, creditor_name, amount_cents, purpose, status, created_at),
        )
        return cursor.lastrowid

    def set_status(self, transfer_id: int, status: str) -> None:
        self._conn.execute("UPDATE transfers SET status = ? WHERE id = ?", (status, transfer_id))

    def get(self, transfer_id: int) -> Optional[Transfer]:
        row = self._conn.execute("SELECT * FROM transfers WHERE id = ?", (transfer_id,)).fetchone()
        return _to_transfer(row) if row is not None else None

    def list_for_debtor(self, debtor_iban: str, limit: int) -> List[Transfer]:
        rows = self._conn.execute(
            "SELECT * FROM transfers WHERE debtor_iban = ? ORDER BY id DESC LIMIT ?", (debtor_iban, limit)
        ).fetchall()
        return [_to_transfer(row) for row in rows]
