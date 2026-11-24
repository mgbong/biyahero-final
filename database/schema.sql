-- =============================================================
--  Biyahero Database Schema  —  biyahero.db (SQLite)
--  Commuter-only public transportation assistant for Cebu.
--
--  Coverage: Cebu City · Mandaue City · Talisay City ·
--            City of Naga · Minglanilla
--
--  Design principle:
--    * Anyone can browse routes, stops, fares, and updates
--      with NO account (guest / random session).
--    * An account is required ONLY to submit a realtime report.
-- =============================================================


-- -------------------------------------------------------------
--  COMMUTERS
--  Registered users who can submit realtime reports and save
--  their profile. Identity verified by email + password.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commuters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fullname      TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    contact       TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
