CREATE TABLE IF NOT EXISTS email_codes (
    challenge TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS email_limits (
    bucket TEXT PRIMARY KEY,
    started REAL NOT NULL,
    count INTEGER NOT NULL
);
