"""Customer mailbox in the online banking. Letters are delivered here instead of by post."""
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Mailbox:
    def __init__(self, bank):
        self.bank = bank
        self.db = bank.db

    def deliver(self, customer_id, subject, body):
        self.bank.getCustomer(customer_id)
        cur = self.db.execute(
            "INSERT INTO mailbox_messages (customer_id, created_at, subject, body) VALUES (?, ?, ?, ?)",
            (customer_id, _now(), subject, body),
        )
        return cur.lastrowid

    def list_messages(self, customer_id, limit=50):
        return self.db.execute(
            "SELECT id, created_at, subject, read_at FROM mailbox_messages WHERE customer_id = ?"
            " ORDER BY id DESC LIMIT ?",
            (customer_id, limit),
        ).fetchall()

    def unread_count(self, customer_id):
        row = self.db.execute(
            "SELECT COUNT(*) FROM mailbox_messages WHERE customer_id = ? AND read_at IS NULL", (customer_id,)
        ).fetchone()
        return row[0]

    def read_message(self, customer_id, message_id):
        """Return the message and mark it as read, or None if it belongs to someone else."""
        row = self.db.execute(
            "SELECT * FROM mailbox_messages WHERE id = ? AND customer_id = ?", (message_id, customer_id)
        ).fetchone()
        if row is None:
            return None
        if row["read_at"] is None:
            self.db.execute("UPDATE mailbox_messages SET read_at = ? WHERE id = ?", (_now(), message_id))
        return row

    def delete_message(self, customer_id, message_id):
        cur = self.db.execute(
            "DELETE FROM mailbox_messages WHERE id = ? AND customer_id = ?", (message_id, customer_id)
        )
        return cur.rowcount == 1
