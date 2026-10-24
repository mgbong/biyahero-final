-- =============================================================
--  Biyahero Database Schema
--  Database: biyahero.db (SQLite)
-- =============================================================

-- -------------------------------------------------------------
--  COMMUTERS
--  Source: html/commuter-signup.html
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commuters (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Account
    fullname          TEXT    NOT NULL,
    email             TEXT    NOT NULL UNIQUE,
    password_hash     TEXT    NOT NULL,       -- store hashed password, never plaintext

    -- Metadata
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------
--  DRIVERS
--  Source: html/driver-signup.html          (Step 1 – personal)
--          html/driver-signup-vehicle.html  (Step 2 – vehicle & route)
--          html/driver-signup-documents.html (Step 3 – documents)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drivers (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Step 1 – Personal info
    fullname                TEXT    NOT NULL,
    contact                 TEXT    NOT NULL,
    email                   TEXT    NOT NULL UNIQUE,
    password_hash           TEXT    NOT NULL,
    municipality            TEXT    NOT NULL,  -- Cebu City | Mandaue City | Lapu-Lapu City | Talisay City | Minglanilla

    -- Step 2 – Vehicle & route
    vehicle_type            TEXT    NOT NULL,  -- Traditional Jeepney | Modern Jeepney | Bus
    plate_number            TEXT    NOT NULL,
    franchise_number        TEXT,              -- optional
    route                   TEXT    NOT NULL,
    terminal                TEXT    NOT NULL,
    seats                   INTEGER NOT NULL,
    operating_hours_from    TEXT    NOT NULL,  -- e.g. "06:00 AM"
    operating_hours_to      TEXT    NOT NULL,  -- e.g. "09:00 PM"
    operating_days          TEXT    NOT NULL,  -- comma-separated, e.g. "Monday,Tuesday,Wednesday"
    wheelchair_accessible   INTEGER NOT NULL DEFAULT 0,  -- 0 = No, 1 = Yes

    -- Step 3 – Documents
    id_type                 TEXT    NOT NULL,  -- Driver's License | National ID | Passport | UMID
    id_number               TEXT    NOT NULL,
    id_front_path           TEXT    NOT NULL,  -- file path / URL to uploaded image
    id_back_path            TEXT    NOT NULL,
    or_cr_path              TEXT    NOT NULL,  -- Official Receipt / Certificate of Registration
    selfie_path             TEXT    NOT NULL,  -- selfie holding ID
    vehicle_photo_path      TEXT,              -- optional

    -- Application status (reviewed by operator/admin)
    approval_status         TEXT    NOT NULL DEFAULT 'pending',  -- pending | approved | declined
    approval_notes          TEXT,

    -- Metadata
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------
--  OPERATORS
--  Source: html/operator-signup.html
--  Note: The public-facing operator signup form is currently
--        disabled. This table is reserved for admin-created
--        operator accounts managed via the dashboard.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operators (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Account
    fullname            TEXT    NOT NULL,
    email               TEXT    NOT NULL UNIQUE,
    password_hash       TEXT    NOT NULL,
    contact             TEXT,

    -- Organization
    company_name        TEXT,                  -- transport company / cooperative name
    franchise_number    TEXT,                  -- operator franchise / CPC number
    municipality        TEXT,                  -- primary area of operation

    -- Status
    is_active           INTEGER NOT NULL DEFAULT 1,  -- 0 = suspended, 1 = active

    -- Metadata
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
