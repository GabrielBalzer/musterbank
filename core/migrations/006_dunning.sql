CREATE TABLE dunning_notices (
    id           INTEGER PRIMARY KEY,
    iban         TEXT NOT NULL,
    level        INTEGER NOT NULL,
    notice_date  TEXT NOT NULL,
    excess_cents INTEGER NOT NULL,
    fee_cents    INTEGER NOT NULL,
    resolved_on  TEXT
);

CREATE INDEX idx_dunning_iban ON dunning_notices (iban);
