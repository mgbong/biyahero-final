-- Route Information, Advisories, Reroutes, User Reports
-- Timestamps stored as UTC ISO strings.

CREATE TABLE IF NOT EXISTS ri_stops (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  city TEXT,
  barangay TEXT,
  landmark TEXT,
  UNIQUE(name, lat, lng)
);

CREATE TABLE IF NOT EXISTS ri_routes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  mode TEXT NOT NULL,
  operator_name TEXT,
  terminal_start TEXT,
  terminal_end TEXT,
  hours_from TEXT,
  hours_to TEXT,
  frequency_min INTEGER,
  fare_reference TEXT,
  geometry_json TEXT,
  status TEXT NOT NULL DEFAULT 'published',
  -- draft | pending_review | published | archived
  verified INTEGER NOT NULL DEFAULT 0,
  verified_by TEXT,
  verified_at TEXT,
  source_label TEXT,
  source_url TEXT,
  last_reviewed_at TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_by_role TEXT,
  created_by_id INTEGER,
  created_by_name TEXT
);

CREATE TABLE IF NOT EXISTS ri_route_stops (
  route_id INTEGER NOT NULL,
  stop_id INTEGER NOT NULL,
  stop_order INTEGER NOT NULL,
  PRIMARY KEY (route_id, stop_order),
  FOREIGN KEY (route_id) REFERENCES ri_routes(id) ON DELETE CASCADE,
  FOREIGN KEY (stop_id) REFERENCES ri_stops(id)
);

CREATE TABLE IF NOT EXISTS ri_reroutes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  route_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  change_type TEXT NOT NULL, -- permanent | temporary
  description TEXT,
  affected_stops TEXT,
  detour_stops_json TEXT,
  original_stops_json TEXT,
  starts_at TEXT NOT NULL,
  ends_at TEXT,
  until_further_notice INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'published',
  source_label TEXT,
  source_url TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_by_role TEXT,
  created_by_id INTEGER,
  created_by_name TEXT,
  FOREIGN KEY (route_id) REFERENCES ri_routes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ri_advisories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  advisory_type TEXT NOT NULL,
  -- road_closure | service_suspension | delay | reduced_frequency | weather | special_event
  severity TEXT NOT NULL, -- info | warning | critical
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  affected_route_codes TEXT,
  affected_stops TEXT,
  starts_at TEXT NOT NULL,
  ends_at TEXT,
  status TEXT NOT NULL DEFAULT 'published',
  source_label TEXT,
  source_url TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_by_role TEXT,
  created_by_id INTEGER,
  created_by_name TEXT,
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS ri_change_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  actor_role TEXT,
  actor_id INTEGER,
  actor_name TEXT,
  previous_json TEXT,
  new_json TEXT,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ri_approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  requested_by_role TEXT,
  requested_by_id INTEGER,
  requested_by_name TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  -- pending | approved | rejected
  reviewer_name TEXT,
  review_note TEXT,
  created_at TEXT NOT NULL,
  reviewed_at TEXT
);

-- User reports
CREATE TABLE IF NOT EXISTS ur_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_code TEXT NOT NULL UNIQUE,
  user_role TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  user_name TEXT,
  category TEXT NOT NULL,
  route_code TEXT,
  stop_name TEXT,
  description TEXT NOT NULL,
  suggested_correction TEXT,
  lat REAL,
  lng REAL,
  observed_at TEXT,
  status TEXT NOT NULL DEFAULT 'submitted',
  priority TEXT NOT NULL DEFAULT 'normal',
  duplicate_of INTEGER,
  linked_change_id INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  withdrawn INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ur_attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  original_name TEXT,
  size_bytes INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY (report_id) REFERENCES ur_reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ur_status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL,
  from_status TEXT,
  to_status TEXT NOT NULL,
  actor_role TEXT,
  actor_id INTEGER,
  actor_name TEXT,
  note TEXT,
  is_internal INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY (report_id) REFERENCES ur_reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ur_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL,
  author_role TEXT,
  author_id INTEGER,
  author_name TEXT,
  body TEXT NOT NULL,
  is_internal INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY (report_id) REFERENCES ur_reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ur_reputation (
  user_role TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  trust_score REAL NOT NULL DEFAULT 0,
  approved_count INTEGER NOT NULL DEFAULT 0,
  rejected_count INTEGER NOT NULL DEFAULT 0,
  flagged INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_role, user_id)
);

CREATE INDEX IF NOT EXISTS idx_ri_routes_status ON ri_routes(status);
CREATE INDEX IF NOT EXISTS idx_ri_advisories_status ON ri_advisories(status);
CREATE INDEX IF NOT EXISTS idx_ur_reports_user ON ur_reports(user_role, user_id);
CREATE INDEX IF NOT EXISTS idx_ur_reports_status ON ur_reports(status);
