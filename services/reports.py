"""
User Reports and Feedback — service layer
=========================================
Guests cannot submit. Users see only their own reports.
Admins/operators (staff) can review all.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any

from services.route_info import utc_now, is_staff, is_admin, log_change

CATEGORIES = {
    "incorrect_stop": "Incorrect stop",
    "missing_stop": "Missing stop",
    "outdated_fare": "Outdated fare information",
    "route_change": "Route change or detour not shown",
    "service_disruption": "Service disruption or road closure",
    "other": "Other route-related concern",
}

# submitted > under_review > needs_more_info > verified > approved > implemented
# or rejected | duplicate | withdrawn
TRANSITIONS = {
    "submitted": {"under_review", "rejected", "duplicate", "withdrawn"},
    "under_review": {"needs_more_info", "verified", "rejected", "duplicate", "approved"},
    "needs_more_info": {"under_review", "withdrawn", "rejected"},
    "verified": {"approved", "rejected"},
    "approved": {"implemented", "rejected"},
    "implemented": set(),
    "rejected": set(),
    "duplicate": set(),
    "withdrawn": set(),
}

DAILY_LIMIT = 5
MAX_PHOTOS = 3
MAX_PHOTO_BYTES = 5 * 1024 * 1024
SPAM_WORDS = {"viagra", "crypto pump", "free money", "click here now"}


def _sanitize(text: str, limit: int = 2000) -> str:
    text = (text or "").strip()
    text = re.sub(r"<[^>]+>", "", text)
    return text[:limit]


def next_ref_code(conn) -> str:
    n = conn.execute("SELECT COUNT(*) AS c FROM ur_reports").fetchone()["c"] + 1
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"BR-{day}-{n:04d}"


def user_daily_count(conn, user: dict) -> int:
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    row = conn.execute(
        """SELECT COUNT(*) AS c FROM ur_reports
           WHERE user_role=? AND user_id=? AND created_at >= ? AND withdrawn=0""",
        (user["role"], user["id"], since),
    ).fetchone()
    return row["c"]


def find_similar(conn, category: str, route_code: str | None, description: str) -> list[dict]:
    q = """SELECT id, ref_code, category, route_code, status, created_at, description
           FROM ur_reports
           WHERE withdrawn=0 AND status NOT IN ('rejected','withdrawn','implemented')
             AND category=?"""
    params: list[Any] = [category]
    if route_code:
        q += " AND route_code=?"
        params.append(route_code)
    q += " ORDER BY created_at DESC LIMIT 8"
    rows = conn.execute(q, params).fetchall()
    needles = set(re.findall(r"[a-z0-9]{4,}", (description or "").lower()))
    out = []
    for row in rows:
        hay = set(re.findall(r"[a-z0-9]{4,}", (row["description"] or "").lower()))
        overlap = len(needles & hay)
        if overlap >= 2 or (route_code and row["route_code"] == route_code):
            out.append({
                "id": row["id"],
                "ref_code": row["ref_code"],
                "category": row["category"],
                "route_code": row["route_code"],
                "status": row["status"],
                "created_at": row["created_at"],
            })
    return out[:5]


def looks_like_spam(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in SPAM_WORDS)


NOTIFICATION_TEMPLATES = {
    "under_review": "Your report {ref} is now under review. Thank you for helping Biyahero.",
    "needs_more_info": "We need more info on report {ref}. Please open My Reports and add details.",
    "verified": "Report {ref} was verified. An admin may apply a map update next.",
    "approved": "Report {ref} was approved. A route update draft may follow.",
    "implemented": "Good news — report {ref} is implemented on the map.",
    "rejected": "Report {ref} was not accepted. Reason: {note}",
    "duplicate": "Report {ref} was marked as a duplicate of another report.",
    "withdrawn": "You withdrew report {ref}.",
}


def notify_message(status: str, ref: str, note: str = "") -> str:
    tmpl = NOTIFICATION_TEMPLATES.get(status, "Report {ref} status is now {status}.")
    return tmpl.format(ref=ref, note=note or "—", status=status)


def create_report(conn, user: dict, data: dict, files: list[tuple[str, bytes]] | None = None) -> tuple[dict | None, str | None]:
    if user.get("role") not in ("commuter", "driver", "operator"):
        return None, "Please log in to send a report."

    category = data.get("category")
    if category not in CATEGORIES:
        return None, "Pick a valid report type."

    description = _sanitize(data.get("description", ""), 2000)
    if len(description) < 10:
        return None, "Please write a bit more about the problem."

    if looks_like_spam(description):
        return None, "This looks like spam. Please rewrite your note."

    if user_daily_count(conn, user) >= DAILY_LIMIT:
        return None, f"Daily limit reached ({DAILY_LIMIT} reports). Try again tomorrow."

    similar = find_similar(conn, category, data.get("route_code"), description)
    if data.get("confirm_similar") is not True and similar:
        return None, "similar"
        # caller should show similar and resubmit with confirm_similar=true

    now = utc_now()
    ref = next_ref_code(conn)
    cur = conn.execute(
        """INSERT INTO ur_reports (
            ref_code, user_role, user_id, user_name, category, route_code, stop_name,
            description, suggested_correction, lat, lng, observed_at, status, priority,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ref, user["role"], user["id"], user.get("fullname"), category,
            data.get("route_code"), data.get("stop_name"), description,
            _sanitize(data.get("suggested_correction", ""), 1000) or None,
            data.get("lat"), data.get("lng"), data.get("observed_at") or now,
            "submitted", data.get("priority") or "normal", now, now,
        ),
    )
    rid = cur.lastrowid
    conn.execute(
        """INSERT INTO ur_status_history
           (report_id, from_status, to_status, actor_role, actor_id, actor_name, note, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (rid, None, "submitted", user["role"], user["id"], user.get("fullname"), "Submitted by user", now),
    )

    files = files or []
    if len(files) > MAX_PHOTOS:
        conn.rollback()
        return None, f"Max {MAX_PHOTOS} photos."
    for name, blob in files:
        if len(blob) > MAX_PHOTO_BYTES:
            conn.rollback()
            return None, "Each photo must be under 5 MB."
        # path written by caller after we return ids — store placeholder path later

    conn.commit()
    return {
        "id": rid,
        "ref_code": ref,
        "status": "submitted",
        "similar": similar,
        "message": f"Thanks! Your report number is {ref}.",
    }, None


def attach_file(conn, report_id: int, path: str, original: str, size: int) -> None:
    conn.execute(
        """INSERT INTO ur_attachments (report_id, file_path, original_name, size_bytes, created_at)
           VALUES (?,?,?,?,?)""",
        (report_id, path, original, size, utc_now()),
    )
    conn.commit()


def get_report(conn, report_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None
    return _serialize(conn, row, include_internal=False)


def get_report_for_user(conn, report_id: int, user: dict) -> tuple[dict | None, str | None]:
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None, "Not found."
    staff = is_staff(user)
    if not staff and (row["user_role"] != user.get("role") or row["user_id"] != user.get("id")):
        return None, "You can only open your own reports."
    return _serialize(conn, row, include_internal=staff), None


def list_my_reports(conn, user: dict) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM ur_reports WHERE user_role=? AND user_id=?
           ORDER BY created_at DESC""",
        (user["role"], user["id"]),
    ).fetchall()
    return [_serialize(conn, r, include_internal=False) for r in rows]


def list_admin_reports(conn, filters: dict) -> list[dict]:
    q = "SELECT * FROM ur_reports WHERE 1=1"
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
        q += " AND (ref_code LIKE ? OR description LIKE ?)"
        like = f"%{filters['q']}%"
        params.extend([like, like])
    sort = filters.get("sort") or "newest"
    if sort == "oldest":
        q += " ORDER BY created_at ASC"
    else:
        q += " ORDER BY created_at DESC"
    rows = conn.execute(q, params).fetchall()
    return [_serialize(conn, r, include_internal=True) for r in rows]


def _serialize(conn, row, include_internal: bool) -> dict:
    hist = conn.execute(
        """SELECT * FROM ur_status_history WHERE report_id=? ORDER BY created_at ASC""",
        (row["id"],),
    ).fetchall()
    comments_q = "SELECT * FROM ur_comments WHERE report_id=?"
    if not include_internal:
        comments_q += " AND is_internal=0"
    comments_q += " ORDER BY created_at ASC"
    comments = conn.execute(comments_q, (row["id"],)).fetchall()
    atts = conn.execute(
        "SELECT id, file_path, original_name, size_bytes FROM ur_attachments WHERE report_id=?",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"],
        "ref_code": row["ref_code"],
        "category": row["category"],
        "category_label": CATEGORIES.get(row["category"], row["category"]),
        "route_code": row["route_code"],
        "stop_name": row["stop_name"],
        "description": row["description"],
        "suggested_correction": row["suggested_correction"],
        "lat": row["lat"],
        "lng": row["lng"],
        "observed_at": row["observed_at"],
        "status": row["status"],
        "priority": row["priority"],
        "duplicate_of": row["duplicate_of"],
        "linked_change_id": row["linked_change_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "reporter": {
            "role": row["user_role"],
            "name": row["user_name"] if include_internal else None,
        },
        "timeline": [
            {
                "from": h["from_status"],
                "to": h["to_status"],
                "at": h["created_at"],
                "by": h["actor_name"] if include_internal or h["actor_role"] == row["user_role"] else "Staff",
                "note": h["note"] if (include_internal or not h["is_internal"]) else None,
            }
            for h in hist
            if include_internal or not h["is_internal"]
        ],
        "comments": [dict(c) for c in comments],
        "attachments": [dict(a) for a in atts],
    }


def transition(conn, report_id: int, to_status: str, user: dict, note: str = "", *, duplicate_of: int | None = None) -> tuple[dict | None, str | None]:
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None, "Not found."

    # User withdraw / add info
    is_owner = row["user_role"] == user.get("role") and row["user_id"] == user.get("id")
    if to_status == "withdrawn":
        if not is_owner:
            return None, "Only you can withdraw your report."
        if row["status"] not in ("submitted", "needs_more_info", "under_review"):
            return None, "This report can no longer be withdrawn."
    elif not is_staff(user):
        return None, "Staff only."

    allowed = TRANSITIONS.get(row["status"], set())
    if to_status not in allowed:
        return None, f"Cannot move from {row['status']} to {to_status}."

    if to_status == "rejected" and not (note or "").strip():
        return None, "A reject reason is required."

    if to_status == "duplicate" and not duplicate_of:
        return None, "Link the original report id."

    now = utc_now()
    conn.execute(
        """UPDATE ur_reports SET status=?, updated_at=?, duplicate_of=COALESCE(?, duplicate_of),
           withdrawn=? WHERE id=?""",
        (to_status, now, duplicate_of, 1 if to_status == "withdrawn" else 0, report_id),
    )
    conn.execute(
        """INSERT INTO ur_status_history
           (report_id, from_status, to_status, actor_role, actor_id, actor_name, note, is_internal, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            report_id, row["status"], to_status, user.get("role"), user.get("id"),
            user.get("fullname"), _sanitize(note, 500), 0, now,
        ),
    )

    # Reputation bump
    if to_status in ("approved", "implemented"):
        _bump_reputation(conn, row["user_role"], row["user_id"], approved=True)
    elif to_status == "rejected":
        _bump_reputation(conn, row["user_role"], row["user_id"], approved=False)

    conn.commit()
    msg = notify_message(to_status, row["ref_code"], note)
    return {"id": report_id, "status": to_status, "notification": msg}, None


def add_user_note(conn, report_id: int, user: dict, body: str) -> tuple[bool, str]:
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return False, "Not found."
    is_owner = row["user_role"] == user.get("role") and row["user_id"] == user.get("id")
    if not is_owner:
        return False, "Only your own report."
    if row["status"] not in ("submitted", "needs_more_info", "under_review"):
        return False, "This report is closed for new notes."
    body = _sanitize(body, 1000)
    if len(body) < 3:
        return False, "Write a short note."
    conn.execute(
        """INSERT INTO ur_comments
           (report_id, author_role, author_id, author_name, body, is_internal, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (report_id, user["role"], user["id"], user.get("fullname"), body, 0, utc_now()),
    )
    conn.execute("UPDATE ur_reports SET updated_at=? WHERE id=?", (utc_now(), report_id))
    conn.commit()
    return True, "Note added."


def add_staff_comment(conn, report_id: int, user: dict, body: str, internal: bool = True) -> tuple[bool, str]:
    if not is_staff(user):
        return False, "Staff only."
    body = _sanitize(body, 1000)
    if len(body) < 2:
        return False, "Empty note."
    conn.execute(
        """INSERT INTO ur_comments
           (report_id, author_role, author_id, author_name, body, is_internal, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (report_id, user["role"], user["id"], user.get("fullname"), body, 1 if internal else 0, utc_now()),
    )
    conn.commit()
    return True, "Saved."


def apply_correction_draft(conn, report_id: int, user: dict) -> tuple[dict | None, str | None]:
    """Create a draft route change linked to an approved report (Route Info workflow)."""
    if not is_admin(user) and not is_staff(user):
        return None, "Staff only."
    row = conn.execute("SELECT * FROM ur_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None, "Not found."
    if row["status"] not in ("approved", "verified"):
        return None, "Approve or verify the report first."
    now = utc_now()
    # Lightweight: store as change_log + approval request referencing suggested correction
    cur = conn.execute(
        """INSERT INTO ri_approvals
           (entity_type, entity_id, requested_by_role, requested_by_id, requested_by_name,
            status, created_at) VALUES (?,?,?,?,?,?,?)""",
        ("report_correction", report_id, user.get("role"), user.get("id"), user.get("fullname"), "pending", now),
    )
    link_id = cur.lastrowid
    conn.execute(
        "UPDATE ur_reports SET linked_change_id=?, updated_at=? WHERE id=?",
        (link_id, now, report_id),
    )
    log_change(
        conn, "report_correction", report_id, "draft_from_report", user, None,
        {
            "route_code": row["route_code"],
            "suggested_correction": row["suggested_correction"],
            "ref_code": row["ref_code"],
        },
        "Draft change from user report",
    )
    conn.commit()
    return {"approval_id": link_id, "report_id": report_id}, None


def _bump_reputation(conn, role: str, uid: int, approved: bool):
    row = conn.execute(
        "SELECT * FROM ur_reputation WHERE user_role=? AND user_id=?", (role, uid)
    ).fetchone()
    if not row:
        conn.execute(
            """INSERT INTO ur_reputation (user_role, user_id, trust_score, approved_count, rejected_count)
               VALUES (?,?,?,?,?)""",
            (role, uid, 1.0 if approved else -0.5, 1 if approved else 0, 0 if approved else 1),
        )
        return
    if approved:
        conn.execute(
            """UPDATE ur_reputation SET approved_count=approved_count+1, trust_score=trust_score+1
               WHERE user_role=? AND user_id=?""",
            (role, uid),
        )
    else:
        conn.execute(
            """UPDATE ur_reputation SET rejected_count=rejected_count+1, trust_score=trust_score-0.5
               WHERE user_role=? AND user_id=?""",
            (role, uid),
        )


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
        "by_status": {r["status"]: r["c"] for r in by_status},
        "by_category": {r["category"]: r["c"] for r in by_cat},
        "top_routes": [dict(r) for r in top_routes],
    }
