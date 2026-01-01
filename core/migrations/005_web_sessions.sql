CREATE TABLE web_sessions (
    token       TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id),
    expires_at  TEXT NOT NULL
);
