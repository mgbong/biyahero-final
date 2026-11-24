"""
User Reports — service layer
=============================
Public transportation realtime reports for Biyahero.

Who can submit:
  - Registered users (commuter / driver / operator) — user_id is their
    real DB id. Identity is verified via session.
  - Guests CANNOT submit. The API returns 401 with login_required=True
    so the front end can prompt Log in / Sign up.

Removed (not needed for public transit capstone):
  - ur_comments     (staff/user threading)
  - ur_reputation   (trust scoring)
  - ri_approvals    (approval queue)
  - ri_change_log   (audit log)
  - apply_correction_draft (linked to removed tables)
  - add_staff_comment / add_user_note (linked to ur_comments)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any

from services.route_info import utc_now, is_staff, is_admin

# ---------------------------------------------------------------------------
# Report categories
# ---------------------------------------------------------------------------
CATEGORIES = {
    "incorrect_stop":    "Incorrect stop location",
    "missing_stop":      "Missing stop",
    "outdated_fare":     "Outdated fare information",
    "route_change":      "Route change or detour not shown",
    "service_disruption":"Service disruption or road closure",
    "other":             "Other route-related concern",
}

# Status flow:
#   submitted → under_review → approved → implemented
#                            → needs_more_info → under_review
#                            → rejected
#   any active status → withdrawn (by owner only)
#   any active status → duplicate (by staff only)
TRANSITIONS = {
    "submitted":       {"under_review", "rejected", "duplicate", "withdrawn"},
    "under_review":    {"needs_more_info", "approved", "rejected", "duplicate"},
    "needs_more_info": {"under_review", "withdrawn", "rejected"},
    "approved":        {"implemented", "rejected"},
    "implemented":     set(),
    "rejected":        set(),
    "duplicate":       set(),
    "withdrawn":       set(),
}

DAILY_LIMIT     = 5
MAX_PHOTOS      = 3
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB per photo
SPAM_WORDS      = {"viagra", "crypto pump", "free money", "click here now"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize(text: str, limit: int = 2000) -> str:
    """Strip HTML tags and trim to limit."""
    text = (text or "").strip()
    text = re.sub(r"<[^>]+>", "", text)
    return text[:limit]


def next_ref_code(conn) -> str:
    """Generate a unique report reference like BR-20261122-0001."""
    n   = conn.execute("SELECT COUNT(*) AS c FROM ur_reports").fetchone()["c"] + 1
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"BR-{day}-{n:04d}"


def user_daily_count(conn, user: dict) -> int:
    """How many reports has this user submitted in the last 24 hours?"""
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    row = conn.execute(
        """SELECT COUNT(*) AS c FROM ur_reports
           WHERE user_role=? AND user_id=? AND created_at >= ? AND withdrawn=0""",
        (user["role"], user["id"], since),
    ).fetchone()
    return row["c"]


def find_similar(conn, category: str, route_code: str | None, description: str) -> list[dict]:
    """Return up to 5 recent open reports that look like duplicates."""
    q      = """SELECT id, ref_code, category, route_code, status, created_at, description
                FROM ur_reports
                WHERE withdrawn=0
                  AND status NOT IN ('rejected', 'withdrawn', 'implemented')
                  AND category=?"""
    params: list[Any] = [category]
    if route_code:
        q += " AND route_code=?"
        params.append(route_code)
    q += " ORDER BY created_at DESC LIMIT 8"

    rows    = conn.execute(q, params).fetchall()
    needles = set(re.findall(r"[a-z0-9]{4,}", (description or "").lower()))
    out     = []
    for row in rows:
        hay     = set(re.findall(r"[a-z0-9]{4,}", (row["description"] or "").lower()))
        overlap = len(needles & hay)
        if overlap >= 2 or (route_code and row["route_code"] == route_code):
            out.append({
                "id":         row["id"],
                "ref_code":   row["ref_code"],
                "category":   row["category"],
                "route_code": row["route_code"],
                "status":     row["status"],
                "created_at": row["created_at"],
            })
    return out[:5]


def looks_like_spam(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in SPAM_WORDS)


# ---------------------------------------------------------------------------
# Create report  (requires identified / logged-in user)
# ---------------------------------------------------------------------------

def create_report(
    conn,
    user:  dict,
    data:  dict,
    files: list[tuple[str, bytes]] | None = None,
) -> tuple[dict | None, str | None]:
    """
    Submit a new realtime report.

    Parameters
    ----------
    user  : session user dict — must have role, id, fullname.
    data  : POST body fields.
    files : list of (filename, bytes) tuples — photos attached to report.

    Returns (report_dict, None) on success or (None, error_string) on failure.
    """
    # Only registered commuters may submit
    if user.get("role") != "commuter":
        return None, "Please log in as a commuter to send a report."

    category = data.get("category")
    if category not in CATEGORIES:
        return None, "Pick a valid report type."

    description = _sanitize(data.get("description", ""), 2000)
    if len(description) < 10:
        return None, "Please write a bit more about the problem (at least 10 characters)."

    if looks_like_spam(description):
        return None, "This message looks like spam. Please rewrite your note."

    if user_daily_count(conn, user) >= DAILY_LIMIT:
        return None, f"You have reached the daily limit of {DAILY_LIMIT} reports. Try again tomorrow."

    files = files or []
    if len(files) > MAX_PHOTOS:
        return None, f"You can attach at most {MAX_PHOTOS} photos."
    for _name, blob in files:
        if len(blob) > MAX_PHOTO_BYTES:
            return None, "Each photo must be under 5 MB."

    # Warn about similar open reports — let the user confirm before submitting
    similar = find_similar(conn, category, data.get("route_code"), description)
    if data.get("confirm_similar") is not True and similar:
        # Return the magic string "similar" — the API layer handles the 409 response
        return None, "similar"

    now = utc_now()
    ref = next_ref_code(conn)

    cur = conn.execute(
        """INSERT INTO ur_reports (
            ref_code, reporter_type, user_role, user_id, user_name,
            category, route_code, stop_name,
            description, suggested_correction,
            lat, lng, observed_at,
            status, duplicate_of,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ref,
            "registered",
            user["role"],
            user["id"],
            user.get("fullname"),
            category,
            data.get("route_code"),
            data.get("stop_name"),
            description,
            _sanitize(data.get("suggested_correction", ""), 1000) or None,
            data.get("lat"),
            data.get("lng"),
            data.get("observed_at") or now,
            "submitted",
            None,
            now,
            now,
        ),
    )
    rid = cur.lastrowid

    # Initial status history entry
    conn.execute(
        """INSERT INTO ur_status_history
           (report_id, from_status, to_status, actor_role, actor_id, actor_name, note, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (rid, None, "submitted", user["role"], user["id"], user.get("fullname"), "Submitted by user", now),
    )

    conn.commit()

    return {
        "id":       rid,
        "ref_code": ref,
        "status":   "submitted",
        "similar":  similar,
        "message":  f"Thanks! Your report number is {ref}.",
    }, None


# ---------------------------------------------------------------------------
# Attach a photo to an existing report
# ---------------------------------------------------------------------------

def attach_file(conn, report_id: int, path: str, original: str, size: int) -> None:
    conn.execute(
        """INSERT INTO ur_attachments (report_id, file_path, original_name, size_bytes, created_at)
           VALUES (?,?,?,?,?)""",
        (report_id, path, original, size, utc_now()),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Read / list reports
# ---------------------------------------------------------------------------

def get_report(conn, report_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None
    return _serialize(conn, row, include_internal=False)


def get_report_for_user(conn, report_id: int, user: dict) -> tuple[dict | None, str | None]:
    """Users can only read their own reports. Staff can read all."""
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None, "Report not found."
    staff = is_staff(user)
    if not staff and (row["user_role"] != user.get("role") or row["user_id"] != user.get("id")):
        return None, "You can only view your own reports."
    return _serialize(conn, row, include_internal=staff), None


def list_my_reports(conn, user: dict) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM ur_reports WHERE user_role=? AND user_id=? ORDER BY created_at DESC",
        (user["role"], user["id"]),
    ).fetchall()
    return [_serialize(conn, r, include_internal=False) for r in rows]


def list_admin_reports(conn, filters: dict) -> list[dict]:
    """Staff view — all reports with optional filters."""
    q      = "SELECT * FROM ur_reports WHERE 1=1"
    params: list[Any] = []

    if filters.get("status"):
        q += " AND status=?"
        params.append(filters["status"])
    if filters.get("category"):
        q += " AND category=?"
        params.append(filters["category"])
    if filters.get("route_code"):
        q += " AND route_code=?"
        params.append(filters["route_code"])
    if filters.get("q"):
        q    += " AND (ref_code LIKE ? OR description LIKE ?)"
        like  = f"%{filters['q']}%"
        params.extend([like, like])

    q += " ORDER BY created_at DESC" if (filters.get("sort") or "newest") != "oldest" else " ORDER BY created_at ASC"

    rows = conn.execute(q, params).fetchall()
    return [_serialize(conn, r, include_internal=True) for r in rows]


# ---------------------------------------------------------------------------
# Status transition  (staff changes status; owner can withdraw)
# ---------------------------------------------------------------------------

def transition(
    conn,
    report_id:    int,
    to_status:    str,
    user:         dict,
    note:         str = "",
    *,
    duplicate_of: int | None = None,
) -> tuple[dict | None, str | None]:
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None, "Report not found."

    is_owner = row["user_role"] == user.get("role") and row["user_id"] == user.get("id")

    if to_status == "withdrawn":
        if not is_owner:
            return None, "Only you can withdraw your own report."
        if row["status"] not in ("submitted", "needs_more_info", "under_review"):
            return None, "This report can no longer be withdrawn."
    elif not is_staff(user):
        return None, "Staff login required to change report status."

    allowed = TRANSITIONS.get(row["status"], set())
    if to_status not in allowed:
        return None, f"Cannot move from '{row['status']}' to '{to_status}'."

    if to_status == "rejected" and not (note or "").strip():
        return None, "A reject reason is required."

    if to_status == "duplicate" and not duplicate_of:
        return None, "Link the original report id when marking as duplicate."

    now = utc_now()
    conn.execute(
        """UPDATE ur_reports
           SET status=?, updated_at=?, duplicate_of=COALESCE(?, duplicate_of), withdrawn=?
           WHERE id=?""",
        (to_status, now, duplicate_of, 1 if to_status == "withdrawn" else 0, report_id),
    )
    conn.execute(
        """INSERT INTO ur_status_history
           (report_id, from_status, to_status, actor_role, actor_id, actor_name, note, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            report_id, row["status"], to_status,
            user.get("role"), user.get("id"), user.get("fullname"),
            _sanitize(note, 500),
            now,
        ),
    )
    conn.commit()
    return {"id": report_id, "status": to_status}, None


# ---------------------------------------------------------------------------
# Analytics  (simple counts for staff dashboard)
# ---------------------------------------------------------------------------

def analytics(conn) -> dict:
    by_status = conn.execute(
        "SELECT status, COUNT(*) AS c FROM ur_reports GROUP BY status"
    ).fetchall()
    by_cat = conn.execute(
        "SELECT category, COUNT(*) AS c FROM ur_reports GROUP BY category"
    ).fetchall()
    top_routes = conn.execute(
        """SELECT route_code, COUNT(*) AS c FROM ur_reports
           WHERE route_code IS NOT NULL AND route_code != ''
           GROUP BY route_code ORDER BY c DESC LIMIT 5"""
    ).fetchall()
    return {
        "by_status":    {r["status"]:   r["c"] for r in by_status},
        "by_category":  {r["category"]: r["c"] for r in by_cat},
        "top_routes":   [dict(r) for r in top_routes],
    }


# ---------------------------------------------------------------------------
# Serializer  (converts a DB row to a clean dict for the API)
# ---------------------------------------------------------------------------

def _serialize(conn, row, include_internal: bool) -> dict:
    hist = conn.execute(
        "SELECT * FROM ur_status_history WHERE report_id=? ORDER BY created_at ASC",
        (row["id"],),
    ).fetchall()
    atts = conn.execute(
        "SELECT id, file_path, original_name, size_bytes FROM ur_attachments WHERE report_id=?",
        (row["id"],),
    ).fetchall()
    return {
        "id":                   row["id"],
        "ref_code":             row["ref_code"],
        "category":             row["category"],
        "category_label":       CATEGORIES.get(row["category"], row["category"]),
        "route_code":           row["route_code"],
        "stop_name":            row["stop_name"],
        "description":          row["description"],
        "suggested_correction": row["suggested_correction"],
        "lat":                  row["lat"],
        "lng":                  row["lng"],
        "observed_at":          row["observed_at"],
        "status":               row["status"],
        "duplicate_of":         row["duplicate_of"],
        "created_at":           row["created_at"],
        "updated_at":           row["updated_at"],
        "reporter": {
            "role": row["user_role"],
            # Only expose the reporter's name to staff (privacy)
            "name": row["user_name"] if include_internal else None,
        },
        "timeline": [
            {
                "from": h["from_status"],
                "to":   h["to_status"],
                "at":   h["created_at"],
                "by":   h["actor_name"] if include_internal else "Staff",
                "note": h["note"],
            }
            for h in hist
        ],
        "attachments": [dict(a) for a in atts],
    }
