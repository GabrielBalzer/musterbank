CREATE TABLE schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE customers (
    id           INTEGER PRIMARY KEY,
    customer_no  TEXT NOT NULL UNIQUE,
    kind         TEXT NOT NULL DEFAULT 'RETAIL',
    first_name   TEXT,
    last_name    TEXT,
    company_name TEXT,
    birth_date   TEXT,
    street       TEXT,
    zip          TEXT,
    city         TEXT,
    email        TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE products (
    code              TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    day_count         TEXT NOT NULL,
    credit_rate_bp    INTEGER NOT NULL DEFAULT 0,
    debit_rate_bp     INTEGER NOT NULL DEFAULT 0,
    monthly_fee_cents INTEGER NOT NULL DEFAULT 0,
    closing_cycle     TEXT NOT NULL
);

INSERT INTO products VALUES ('GIRO', 'Girokonto', '30E/360', 0, 1150, 490, 'QUARTERLY');
INSERT INTO products VALUES ('TAGESGELD', 'Tagesgeldkonto', 'ACT/365', 150, 0, 0, 'MONTHLY');
INSERT INTO products VALUES ('FESTGELD', 'Festgeldkonto', 'ACT/360', 250, 0, 0, 'MATURITY');
INSERT INTO products VALUES ('CLEARING', 'Verrechnungskonto', 'ACT/365', 0, 0, 0, 'NONE');

CREATE TABLE accounts (
    id                    INTEGER PRIMARY KEY,
    iban                  TEXT NOT NULL UNIQUE,
    customer_id           INTEGER REFERENCES customers (id),
    product_code          TEXT NOT NULL REFERENCES products (code),
    balance_cents         INTEGER NOT NULL DEFAULT 0,
    overdraft_limit_cents INTEGER NOT NULL DEFAULT 0,
    opened_on             TEXT NOT NULL,
    closed_on             TEXT,
    status                TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE INDEX idx_accounts_customer ON accounts (customer_id);

CREATE TABLE bookings (
    id                INTEGER PRIMARY KEY,
    account_id        INTEGER NOT NULL REFERENCES accounts (id),
    booking_date      TEXT NOT NULL,
    value_date        TEXT NOT NULL,
    amount_cents      INTEGER NOT NULL,
    kind              TEXT NOT NULL,
    counterparty_name TEXT,
    counterparty_iban TEXT,
    purpose           TEXT
);

CREATE INDEX idx_bookings_account ON bookings (account_id);
