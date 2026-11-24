-- =============================================================
--  Biyahero Route Information Schema  —  biyahero.db (SQLite)
--  Public transportation data: stops, routes, advisories,
--  reroutes, and user realtime reports.
--
--  Design principle:
--    * PUBLIC (no account):  browse stops, routes, advisories,
--      reroutes. Session ID is random — no personal data stored.
--    * IDENTIFIED (must log in):  submit a realtime report.
--      user_id links to commuters / drivers / operators table.
--
--  Removed tables (not needed for a public transit capstone):
--    - ri_change_log   (audit log — over-engineered for MVP)
--    - ri_approvals    (approval queue — simplified to status field)
--    - ur_comments     (staff/user threading — not in scope)
--    - ur_reputation   (trust scoring — not in scope)
-- =============================================================


-- -------------------------------------------------------------
--  STOPS
--  Every boarding / alighting point in the coverage area.
--  Seeded from data/transit_catalog.json on first run.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ri_stops (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL,
    lat       REAL    NOT NULL,
    lng       REAL    NOT NULL,
    city      TEXT,                 -- Cebu City | Mandaue City | Talisay City | City of Naga | Minglanilla
    barangay  TEXT,
    landmark  TEXT,                 -- human-readable area label
    UNIQUE(name, lat, lng)
);


-- -------------------------------------------------------------
--  ROUTES
--  Published jeepney / bus / modern jeepney lines.
--  status: published | draft | archived
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ri_routes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code             TEXT    NOT NULL UNIQUE,   -- e.g. 01K, BUS-02
    name             TEXT    NOT NULL,
    mode             TEXT    NOT NULL,           -- jeepney | modern_jeepney | bus
    operator_name    TEXT,
    terminal_start   TEXT,
    terminal_end     TEXT,
    hours_from       TEXT,                       -- e.g. 05:00
    hours_to         TEXT,                       -- e.g. 22:00
    frequency_min    INTEGER,                    -- avg minutes between trips
    fare_reference   TEXT,                       -- human-readable fare note
    geometry_json    TEXT,                       -- GeoJSON LineString of stop coords
    status           TEXT    NOT NULL DEFAULT 'published',
    verified         INTEGER NOT NULL DEFAULT 0, -- 1 = staff-confirmed data
    verified_by      TEXT,
    verified_at      TEXT,
    source_label     TEXT,                       -- agency | lgu | operator | admin
    source_url       TEXT,
    last_reviewed_at TEXT,
    updated_at       TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    created_by_role  TEXT,
    created_by_name  TEXT
);


-- -------------------------------------------------------------
--  ROUTE STOPS  (junction table — ordered stop list per route)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ri_route_stops (
    route_id   INTEGER NOT NULL,
    stop_id    INTEGER NOT NULL,
    stop_order INTEGER NOT NULL,
    PRIMARY KEY (route_id, stop_order),
    FOREIGN KEY (route_id) REFERENCES ri_routes(id) ON DELETE CASCADE,
    FOREIGN KEY (stop_id)  REFERENCES ri_stops(id)
);


-- -------------------------------------------------------------
--  REROUTES  (temporary or permanent path / stop changes)
--  Posted by operator or admin. Affects route planner output.
--  status: published | draft | archived
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ri_reroutes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id             INTEGER NOT NULL,
    title                TEXT    NOT NULL,
    change_type          TEXT    NOT NULL,  -- temporary | permanent
    description          TEXT,
    affected_stops       TEXT,
    detour_stops_json    TEXT,              -- JSON array of stop names
    original_stops_json  TEXT,             -- JSON array of original stop names
    starts_at            TEXT    NOT NULL,
    ends_at              TEXT,
    until_further_notice INTEGER NOT NULL DEFAULT 0,
    status               TEXT    NOT NULL DEFAULT 'published',
    source_label         TEXT,
    source_url           TEXT,
    updated_at           TEXT    NOT NULL,
    created_at           TEXT    NOT NULL,
    created_by_role      TEXT,
    created_by_id        INTEGER,
    created_by_name      TEXT,
    FOREIGN KEY (route_id) REFERENCES ri_routes(id) ON DELETE CASCADE
);


-- -------------------------------------------------------------
--  ADVISORIES  (road closures, delays, service suspensions)
--  Posted by operator or admin. Visible on public Updates page.
--  advisory_type: road_closure | service_suspension | delay |
--                 reduced_frequency | weather | special_event
--  severity:      info | warning | critical
--  status:        published | draft | archived
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ri_advisories (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    advisory_type        TEXT    NOT NULL,
    severity             TEXT    NOT NULL,
    title                TEXT    NOT NULL,
    description          TEXT    NOT NULL,
    affected_route_codes TEXT,              -- comma-separated route codes
    affected_stops       TEXT,
    starts_at            TEXT    NOT NULL,
    ends_at              TEXT,
    status               TEXT    NOT NULL DEFAULT 'published',
    source_label         TEXT,
    source_url           TEXT,
    updated_at           TEXT    NOT NULL,
    created_at           TEXT    NOT NULL,
    created_by_role      TEXT,
    created_by_id        INTEGER,
    created_by_name      TEXT,
    resolved_at          TEXT               -- set when staff marks resolved
);


-- -------------------------------------------------------------
--  REALTIME REPORTS  (submitted by identified users only)
--
--  reporter_type:
--    'registered' — user has a commuter / driver / operator
--                   account; user_id is their real DB id.
--    'guest'      — no account; user_id is a random session
--                   token generated client-side. Name is
--                   optional and not linked to any account.
--
--  NOTE: Guests CAN view the app freely. They need an account
--  ONLY to submit a report (so we can track abuse and follow up).
--
--  category: incorrect_stop | missing_stop | outdated_fare |
--            route_change | service_disruption | other
--  status:   submitted | under_review | needs_more_info |
--            approved | implemented | rejected | withdrawn
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ur_reports (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_code             TEXT    NOT NULL UNIQUE,  -- e.g. BR-20261122-0001

    -- Who submitted (must be a logged-in user)
    reporter_type        TEXT    NOT NULL DEFAULT 'registered',  -- registered | guest (future)
    user_role            TEXT    NOT NULL,         -- commuter | driver | operator
    user_id              INTEGER NOT NULL,         -- FK to commuters / drivers / operators
    user_name            TEXT,                     -- denormalized fullname at submit time

    -- What they reported
    category             TEXT    NOT NULL,
    route_code           TEXT,
    stop_name            TEXT,
    description          TEXT    NOT NULL,
    suggested_correction TEXT,
    lat                  REAL,
    lng                  REAL,
    observed_at          TEXT,

    -- Workflow
    status               TEXT    NOT NULL DEFAULT 'submitted',
    duplicate_of         INTEGER,                  -- id of original if duplicate

    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,
    withdrawn            INTEGER NOT NULL DEFAULT 0
);


-- -------------------------------------------------------------
--  REPORT ATTACHMENTS  (photos attached to a report)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ur_attachments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id     INTEGER NOT NULL,
    file_path     TEXT    NOT NULL,
    original_name TEXT,
    size_bytes    INTEGER,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (report_id) REFERENCES ur_reports(id) ON DELETE CASCADE
);


-- -------------------------------------------------------------
--  REPORT STATUS HISTORY  (timeline of status changes)
--  Keeps a simple audit trail: who changed what and when.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ur_status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id   INTEGER NOT NULL,
    from_status TEXT,
    to_status   TEXT    NOT NULL,
    actor_role  TEXT,
    actor_id    INTEGER,
    actor_name  TEXT,
    note        TEXT,
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (report_id) REFERENCES ur_reports(id) ON DELETE CASCADE
);


-- =============================================================
--  INDEXES  (speed up common queries)
-- =============================================================
CREATE INDEX IF NOT EXISTS idx_ri_routes_status    ON ri_routes(status);
CREATE INDEX IF NOT EXISTS idx_ri_advisories_status ON ri_advisories(status);
CREATE INDEX IF NOT EXISTS idx_ur_reports_user     ON ur_reports(user_role, user_id);
CREATE INDEX IF NOT EXISTS idx_ur_reports_status   ON ur_reports(status);
CREATE INDEX IF NOT EXISTS idx_ur_reports_route    ON ur_reports(route_code);
