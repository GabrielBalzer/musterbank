CREATE TABLE transfers (
    id            INTEGER PRIMARY KEY,
    debtor_iban   TEXT NOT NULL,
    creditor_iban TEXT NOT NULL,
    creditor_name TEXT NOT NULL,
    amount_cents  INTEGER NOT NULL,
    purpose       TEXT,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

ALTER TABLE bookings ADD COLUMN transfer_id INTEGER REFERENCES transfers (id);
CREATE INDEX idx_bookings_transfer ON bookings (transfer_id);
