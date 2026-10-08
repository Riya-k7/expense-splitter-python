CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY, name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS members (
    id SERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    name TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS bills (
    id SERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    payer_id INT NOT NULL REFERENCES members(id),
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS shares (
    bill_id INT NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    member_id INT NOT NULL REFERENCES members(id),
    paise BIGINT NOT NULL,
    PRIMARY KEY (bill_id, member_id));
