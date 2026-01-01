CREATE TABLE mailbox_messages (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id),
    created_at  TEXT NOT NULL,
    subject     TEXT NOT NULL,
    body        TEXT NOT NULL,
    read_at     TEXT
);

CREATE INDEX idx_mailbox_customer ON mailbox_messages (customer_id);
