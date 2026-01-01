CREATE TABLE eod_runs (
    business_date TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    checksum      TEXT
);

CREATE TABLE eod_results (
    business_date         TEXT NOT NULL,
    iban                  TEXT NOT NULL,
    interest_cents        INTEGER NOT NULL,
    fee_cents             INTEGER NOT NULL,
    closing_balance_cents INTEGER NOT NULL,
    PRIMARY KEY (business_date, iban)
);
