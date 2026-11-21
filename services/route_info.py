"""
Route Information and Updates — service layer
=============================================
Public reads are open. Writes need operator/admin session.
Timestamps: UTC ISO. Display in Asia/Manila on the client.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any

STALE_DAYS = 90
ADMIN_EMAILS = {"admin@biyahero.com", "operator@biyahero.com"}  # sample admin access

VALID_ROUTE_STATUSES = {"draft", "pending_review", "published", "archived"}
VALID_ADVISORY_TYPES = {
    "road_closure", "service_suspension", "delay",
    "reduced_frequency", "weather", "special_event",
}
VALID_SEVERITIES = {"info", "warning", "critical"}

# How often the public Updates screen should refresh (seconds)
UPDATES_REFRESH_SECONDS = 60

# Human-readable source directory
SOURCE_DIRECTORY = {
    "agency": {
        "label": "Transit agency / LGU",
        "trust": "verified",
        "blurb": "Official agency or city notice",
    },
    "lgu": {
        "label": "City / LGU notice",
        "trust": "verified",
        "blurb": "Posted from a city or LGU public notice",
    },
    "official_announcement": {
        "label": "Official announcement",
        "trust": "verified",
        "blurb": "Posted from an official public notice",
    },
    "operator": {
        "label": "Route operator",
        "trust": "verified",
        "blurb": "Confirmed by an approved operator",
    },
    "admin": {
        "label": "Biyahero staff",
        "trust": "verified",
        "blurb": "Checked and published by Biyahero admins",
    },
    "community": {
        "label": "Community report",
        "trust": "advisory",
        "blurb": "Commuter tip — not a verified route change",
    },
    "community_report": {
        "label": "Community report",
        "trust": "advisory",
        "blurb": "Commuter tip — not a verified route change",
    },
}

# Advisory types treated as general traffic (not a verified line change)
TRAFFIC_ADVISORY_TYPES = {
    "road_closure", "delay", "weather", "special_event",
}
# Advisory types that affect a line's service pattern (still not a stop-path change)
SERVICE_ADVISORY_TYPES = {
    "service_suspension", "reduced_frequency",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_schema(conn, schema_path: str) -> None:
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def clear_demo_content(conn) -> None:
    """Remove demo advisories/reroutes that were seeded earlier (system-created)."""
    conn.execute(
        "DELETE FROM ri_advisories WHERE created_by_role='system' OR created_by_name='Seed'"
    )
    conn.execute(
        "DELETE FROM ri_reroutes WHERE created_by_role='system' OR created_by_name='Seed'"
    )
    conn.commit()


def seed_from_catalog(conn, transit_lines: list[dict], locations: list[dict], *, force: bool = False) -> None:
    """Idempotent seed of published verified routes from the transit catalog."""
    cur = conn.execute("SELECT COUNT(*) AS n FROM ri_routes")
    if cur.fetchone()["n"] > 0 and not force:
        clear_demo_content(conn)
        return

    if force:
        conn.execute("DELETE FROM ri_route_stops")
        conn.execute("DELETE FROM ri_reroutes")
        conn.execute("DELETE FROM ri_advisories")
        conn.execute("DELETE FROM ri_routes")
        conn.execute("DELETE FROM ri_stops")
        conn.commit()

    now = utc_now()
    stop_ids: dict[str, int] = {}

    for loc in locations:
        conn.execute(
            """INSERT OR IGNORE INTO ri_stops (name, lat, lng, city, barangay, landmark)
               VALUES (?,?,?,?,?,?)""",
            (loc["name"], loc["lat"], loc["lng"], loc.get("city"), loc.get("barangay"), loc.get("barangay")),
        )
    for row in conn.execute("SELECT id, name FROM ri_stops"):
        stop_ids[row["name"]] = row["id"]

    for line in transit_lines:
        stops = line.get("stops") or []
        geom = []
        for sn in stops:
            sid = stop_ids.get(sn)
            if not sid:
                continue
            s = conn.execute("SELECT lat, lng FROM ri_stops WHERE id=?", (sid,)).fetchone()
            if s:
                geom.append([s["lng"], s["lat"]])

        hours_from = line.get("hours_from") or "05:00"
        hours_to = line.get("hours_to") or "22:00"
        freq = line.get("frequency_min") or (8 if line["mode"] == "jeepney" else 12)

        conn.execute(
            """INSERT INTO ri_routes (
                code, name, mode, operator_name, terminal_start, terminal_end,
                hours_from, hours_to, frequency_min, fare_reference, geometry_json,
                status, verified, verified_by, verified_at, source_label, source_url,
                last_reviewed_at, updated_at, created_at, created_by_role, created_by_name
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                line["code"], line["name"], line["mode"], "Cebu transit operators",
                stops[0] if stops else None, stops[-1] if stops else None,
                hours_from, hours_to, freq,
                f"₱{line.get('base_fare', 13)} base (estimate)",
                json.dumps({"type": "LineString", "coordinates": geom}),
                "published", 1, "Biyahero catalog", now,
                "agency", None, now, now, now, "system", "Catalog",
            ),
        )
        rid = conn.execute("SELECT id FROM ri_routes WHERE code=?", (line["code"],)).fetchone()["id"]
        order = 0
        for sn in stops:
            sid = stop_ids.get(sn)
            if not sid:
                continue
            order += 1
            conn.execute(
                "INSERT INTO ri_route_stops (route_id, stop_id, stop_order) VALUES (?,?,?)",
                (rid, sid, order),
            )

    # No demo advisories or reroutes — staff publish real ones when needed
    conn.commit()


def is_staff(user: dict | None) -> bool:
    return bool(user and user.get("role") in ("operator", "admin"))


def is_admin(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return (user.get("email") or "").lower() in ADMIN_EMAILS


def _stale(last_reviewed_at: str | None) -> bool:
    if not last_reviewed_at:
        return True
    try:
        raw = last_reviewed_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - dt > timedelta(days=STALE_DAYS)
    except ValueError:
        return True


def _route_row(conn, row) -> dict:
    stops = conn.execute(
        """SELECT s.name, s.lat, s.lng, s.city, s.barangay, rs.stop_order
           FROM ri_route_stops rs JOIN ri_stops s ON s.id = rs.stop_id
           WHERE rs.route_id=? ORDER BY rs.stop_order""",
        (row["id"],),
    ).fetchall()
    geom = None
    if row["geometry_json"]:
        try:
            geom = json.loads(row["geometry_json"])
        except json.JSONDecodeError:
            geom = None

    verified = bool(row["verified"]) and row["status"] == "published"
    return {
        "id": row["id"],
        "code": row["code"],
        "name": row["name"],
        "mode": row["mode"],
        "operator": row["operator_name"],
        "terminals": {"start": row["terminal_start"], "end": row["terminal_end"]},
        "stops": [dict(s) for s in stops],
        "geometry": geom,
        "hours": {"from": row["hours_from"], "to": row["hours_to"]},
        "frequency_min": row["frequency_min"],
        "fare_reference": row["fare_reference"],
        "status": row["status"],
        "verified": verified,
        "verification": {
            "badge": "Verified" if verified else "Unverified",
            "by": row["verified_by"] if verified else None,
            "at": row["verified_at"] if verified else None,
        },
        "source": {"label": row["source_label"], "url": row["source_url"]},
        "last_updated": row["updated_at"],
        "last_reviewed_at": row["last_reviewed_at"],
        "stale_warning": _stale(row["last_reviewed_at"]),
        "timezone_note": "Stored UTC — show in Asia/Manila on client",
    }


def list_published_routes(conn, q: str | None = None, stop: str | None = None) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM ri_routes WHERE status='published' ORDER BY code"
    ).fetchall()
    out = []
    qn = (q or "").lower().strip()
    sn = (stop or "").lower().strip()
    for row in rows:
        item = _route_row(conn, row)
        if not item["verified"] and row["status"] == "published":
            # Still show but labeled unverified
            pass
        blob = f"{item['code']} {item['name']} {item['mode']}".lower()
        stop_blob = " ".join(s["name"].lower() for s in item["stops"])
        if qn and qn not in blob and qn not in stop_blob:
            continue
        if sn and sn not in stop_blob:
            continue
        out.append(item)
    return out


def get_route(conn, code: str, *, include_unpublished: bool = False) -> dict | None:
    row = conn.execute("SELECT * FROM ri_routes WHERE code=?", (code,)).fetchone()
    if not row:
        return None
    if not include_unpublished and row["status"] != "published":
        return None
    item = _route_row(conn, row)
    item["active_reroutes"] = list_active_reroutes(conn, route_id=row["id"])
    item["active_advisories"] = list_active_advisories(conn, route_code=code)
    return item


def _advisory_active(row, now: datetime) -> bool:
    if row["status"] != "published":
        return False
    if row["resolved_at"]:
        return False
    try:
        start = datetime.fromisoformat(row["starts_at"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if now < start:
            return False
        if row["ends_at"]:
            end = datetime.fromisoformat(row["ends_at"].replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if now > end:
                return False
    except ValueError:
        return False
    return True


def describe_source(raw: str | None, url: str | None = None) -> dict:
    key = (raw or "operator").strip().lower().replace(" ", "_")
    info = SOURCE_DIRECTORY.get(key) or {
        "label": raw or "Unknown source",
        "trust": "advisory",
        "blurb": "Source not fully classified",
    }
    return {
        "key": key,
        "label": info["label"],
        "trust": info["trust"],
        "blurb": info["blurb"],
        "url": url,
        "raw": raw,
    }


def updates_meta() -> dict:
    return {
        "refresh_seconds": UPDATES_REFRESH_SECONDS,
        "refresh_label": f"This page checks for new posts about every {UPDATES_REFRESH_SECONDS} seconds.",
        "publish_sla": "New staff posts usually show within 1–2 minutes after publish.",
        "timezone": "Asia/Manila (display) · stored UTC",
        "categories": {
            "route_change": "Verified change to a line path, stops, or terminals (staff-approved).",
            "traffic_advisory": "General road or service heads-up. Not the same as a verified line rewrite.",
        },
        "sources": [
            {"key": k, **v} for k, v in SOURCE_DIRECTORY.items()
        ],
    }


def list_active_advisories(conn, route_code: str | None = None, history: bool = False) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = conn.execute("SELECT * FROM ri_advisories ORDER BY created_at DESC").fetchall()
    out = []
    for row in rows:
        active = _advisory_active(row, now)
        if history and active:
            continue
        if not history and not active:
            continue
        codes = [c.strip() for c in (row["affected_route_codes"] or "").split(",") if c.strip()]
        if route_code and route_code not in codes and codes:
            # allow global advisories with empty codes
            if codes:
                continue
        src = describe_source(row["source_label"], row["source_url"])
        atype = row["advisory_type"]
        # Traffic advisories are never labeled as verified route changes
        bucket = "traffic_advisory"
        if atype in SERVICE_ADVISORY_TYPES:
            bucket = "service_advisory"
        out.append({
            "id": row["id"],
            "kind": "advisory",
            "bucket": bucket,
            "type": atype,
            "type_label": (atype or "").replace("_", " ").title(),
            "severity": row["severity"],
            "severity_label": row["severity"].title(),
            "title": row["title"],
            "description": row["description"],
            "affected_routes": codes,
            "affected_stops": row["affected_stops"],
            "starts_at": row["starts_at"],
            "ends_at": row["ends_at"],
            "status": row["status"],
            "active": active,
            "verified": False,
            "verified_badge": "Traffic advisory",
            "source": src,
            "last_updated": row["updated_at"],
            "update_frequency_note": updates_meta()["refresh_label"],
        })
    return out


def _reroute_active(row, now: datetime) -> bool:
    if row["status"] != "published":
        return False
    try:
        start = datetime.fromisoformat(row["starts_at"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if now < start:
            return False
        if row["until_further_notice"]:
            return True
        if row["ends_at"]:
            end = datetime.fromisoformat(row["ends_at"].replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            return now <= end
        return True
    except ValueError:
        return False


def list_active_reroutes(conn, route_id: int | None = None) -> list[dict]:
    now = datetime.now(timezone.utc)
    if route_id:
        rows = conn.execute(
            "SELECT * FROM ri_reroutes WHERE route_id=? ORDER BY created_at DESC", (route_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ri_reroutes ORDER BY created_at DESC").fetchall()
    out = []
    for row in rows:
        if not _reroute_active(row, now):
            continue
        route = conn.execute("SELECT code, name FROM ri_routes WHERE id=?", (row["route_id"],)).fetchone()
        src = describe_source(row["source_label"], row["source_url"])
        # Published reroutes are verified route changes (staff approval workflow)
        verified = row["status"] == "published" and src["trust"] == "verified"
        # Even community-sourced drafts shouldn't appear here (only published)
        if row["status"] == "published":
            verified = True
        out.append({
            "id": row["id"],
            "kind": "route_change",
            "bucket": "route_change",
            "route_code": route["code"] if route else None,
            "route_name": route["name"] if route else None,
            "title": row["title"],
            "change_type": row["change_type"],
            "change_type_label": (
                "Permanent route change" if row["change_type"] == "permanent"
                else "Temporary reroute"
            ),
            "description": row["description"],
            "affected_stops": row["affected_stops"],
            "original_stops": json.loads(row["original_stops_json"] or "[]"),
            "detour_stops": json.loads(row["detour_stops_json"] or "[]"),
            "starts_at": row["starts_at"],
            "ends_at": row["ends_at"],
            "until_further_notice": bool(row["until_further_notice"]),
            "verified": verified,
            "verified_badge": "Verified route change" if verified else "Unverified change",
            "source": src,
            "last_updated": row["updated_at"],
            "update_frequency_note": updates_meta()["refresh_label"],
        })
    return out


def list_updates_bundle(conn, *, history: bool = False, severity: str | None = None) -> dict:
    """
    Split feed for the Updates screen:
      - route_changes: verified path/stop changes (reroutes)
      - traffic_advisories: general road/service heads-up
    """
    changes = list_active_reroutes(conn) if not history else []
    advisories = list_active_advisories(conn, history=history)
    if severity:
        advisories = [a for a in advisories if a["severity"] == severity]
    traffic = [a for a in advisories if a["bucket"] == "traffic_advisory"]
    service = [a for a in advisories if a["bucket"] == "service_advisory"]
    # Service advisories sit with traffic section but labeled clearly
    traffic_feed = traffic + service
    meta = updates_meta()
    freshest = None
    for item in changes + traffic_feed:
        ts = item.get("last_updated")
        if ts and (freshest is None or ts > freshest):
            freshest = ts
    meta["last_data_at"] = freshest
    meta["counts"] = {
        "route_changes": len(changes),
        "traffic_advisories": len(traffic_feed),
    }
    return {
        "route_changes": changes,
        "traffic_advisories": traffic_feed,
        "meta": meta,
    }


def effective_line_stops(conn, line_code: str, default_stops: list[str]) -> list[str]:
    """Used by Route Planning: swap in active temporary detour stops when present."""
    row = conn.execute("SELECT id FROM ri_routes WHERE code=? AND status='published'", (line_code,)).fetchone()
    if not row:
        return default_stops
    active = list_active_reroutes(conn, route_id=row["id"])
    for rr in active:
        if rr["change_type"] == "temporary" and rr["detour_stops"]:
            return rr["detour_stops"]
        if rr["change_type"] == "permanent" and rr["detour_stops"]:
            return rr["detour_stops"]
    return default_stops


def log_change(conn, entity_type, entity_id, action, user, previous, new, note=None):
    conn.execute(
        """INSERT INTO ri_change_log
           (entity_type, entity_id, action, actor_role, actor_id, actor_name,
            previous_json, new_json, note, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            entity_type, entity_id, action,
            user.get("role") if user else None,
            user.get("id") if user else None,
            user.get("fullname") if user else None,
            json.dumps(previous) if previous is not None else None,
            json.dumps(new) if new is not None else None,
            note, utc_now(),
        ),
    )


def create_reroute(conn, data: dict, user: dict) -> tuple[dict | None, str | None]:
    """Staff creates a verified route change (temporary or permanent)."""
    code = (data.get("route_code") or "").strip()
    title = (data.get("title") or "").strip()
    change_type = (data.get("change_type") or "temporary").strip()
    if change_type not in ("temporary", "permanent"):
        return None, "change_type must be temporary or permanent."
    if not code or not title or not data.get("starts_at"):
        return None, "Route code, title, and start time are required."
    route = conn.execute(
        "SELECT id, code FROM ri_routes WHERE code=? AND status='published'", (code,)
    ).fetchone()
    if not route:
        return None, f"No published route named {code}."

    detour = data.get("detour_stops") or []
    if isinstance(detour, str):
        detour = [s.strip() for s in detour.split("|") if s.strip()]
    original = data.get("original_stops") or []
    if isinstance(original, str):
        original = [s.strip() for s in original.split("|") if s.strip()]
    if len(detour) < 2:
        return None, "Detour needs at least 2 stops (use | between names)."

    # Admins publish verified changes immediately; operators go to draft
    status = "published" if is_admin(user) else "draft"
    src = data.get("source_label") or ("admin" if is_admin(user) else "operator")
    now = utc_now()
    cur = conn.execute(
        """INSERT INTO ri_reroutes (
            route_id, title, change_type, description, affected_stops,
            detour_stops_json, original_stops_json, starts_at, ends_at,
            until_further_notice, status, source_label, source_url,
            updated_at, created_at, created_by_role, created_by_id, created_by_name
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            route["id"], title, change_type, (data.get("description") or "").strip(),
            data.get("affected_stops"),
            json.dumps(detour), json.dumps(original),
            data["starts_at"], data.get("ends_at"),
            1 if data.get("until_further_notice") else 0,
            status, src, data.get("source_url"),
            now, now, user.get("role"), user.get("id"), user.get("fullname"),
        ),
    )
    rid = cur.lastrowid
    if status == "draft":
        conn.execute(
            """INSERT INTO ri_approvals
               (entity_type, entity_id, requested_by_role, requested_by_id, requested_by_name,
                status, created_at) VALUES (?,?,?,?,?,?,?)""",
            ("reroute", rid, user.get("role"), user.get("id"), user.get("fullname"), "pending", now),
        )
    log_change(conn, "reroute", rid, "create", user, None, data)
    conn.commit()
    return {"id": rid, "status": status, "verified": status == "published"}, None


def create_advisory(conn, data: dict, user: dict) -> tuple[dict | None, str | None]:
    if data.get("advisory_type") not in VALID_ADVISORY_TYPES:
        return None, "Bad advisory type."
    if data.get("severity") not in VALID_SEVERITIES:
        return None, "Bad severity."
    if not (data.get("title") and data.get("description") and data.get("starts_at")):
        return None, "Title, description, and start time are required."
    status = "published" if is_admin(user) else "draft"
    now = utc_now()
    cur = conn.execute(
        """INSERT INTO ri_advisories (
            advisory_type, severity, title, description, affected_route_codes, affected_stops,
            starts_at, ends_at, status, source_label, source_url, updated_at, created_at,
            created_by_role, created_by_id, created_by_name
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data["advisory_type"], data["severity"], data["title"].strip(),
            data["description"].strip(), data.get("affected_route_codes", ""),
            data.get("affected_stops"), data["starts_at"], data.get("ends_at"),
            status, data.get("source_label") or "operator", data.get("source_url"),
            now, now, user.get("role"), user.get("id"), user.get("fullname"),
        ),
    )
    aid = cur.lastrowid
    if status == "draft":
        conn.execute(
            """INSERT INTO ri_approvals
               (entity_type, entity_id, requested_by_role, requested_by_id, requested_by_name,
                status, created_at) VALUES (?,?,?,?,?,?,?)""",
            ("advisory", aid, user.get("role"), user.get("id"), user.get("fullname"), "pending", now),
        )
    log_change(conn, "advisory", aid, "create", user, None, data)
    conn.commit()
    return {"id": aid, "status": status}, None


def review_entity(conn, entity_type: str, entity_id: int, approve: bool, user: dict, note: str = "") -> tuple[bool, str]:
    if not is_admin(user):
        return False, "Only admins can approve or reject."
    now = utc_now()
    table = {"route": "ri_routes", "advisory": "ri_advisories", "reroute": "ri_reroutes"}.get(entity_type)
    if not table:
        return False, "Unknown entity."
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (entity_id,)).fetchone()
    if not row:
        return False, "Not found."
    if approve:
        if entity_type == "route":
            conn.execute(
                """UPDATE ri_routes SET status='published', verified=1, verified_by=?, verified_at=?,
                   last_reviewed_at=?, updated_at=? WHERE id=?""",
                (user.get("fullname"), now, now, now, entity_id),
            )
        else:
            conn.execute(
                f"UPDATE {table} SET status='published', updated_at=? WHERE id=?",
                (now, entity_id),
            )
        appr_status = "approved"
    else:
        if not note.strip():
            return False, "Reject reason is required."
        conn.execute(
            f"UPDATE {table} SET status='archived', updated_at=? WHERE id=?",
            (now, entity_id),
        )
        appr_status = "rejected"
    conn.execute(
        """UPDATE ri_approvals SET status=?, reviewer_name=?, review_note=?, reviewed_at=?
           WHERE entity_type=? AND entity_id=? AND status='pending'""",
        (appr_status, user.get("fullname"), note, now, entity_type, entity_id),
    )
    log_change(conn, entity_type, entity_id, appr_status, user, dict(row), None, note)
    conn.commit()
    return True, appr_status


def rollback_change(conn, changelog_id: int, user: dict) -> tuple[bool, str]:
    if not is_admin(user):
        return False, "Only admins can roll back."
    entry = conn.execute("SELECT * FROM ri_change_log WHERE id=?", (changelog_id,)).fetchone()
    if not entry or not entry["previous_json"]:
        return False, "Nothing to roll back."
    # Soft rollback: restore route fields if entity is route
    if entry["entity_type"] == "route":
        prev = json.loads(entry["previous_json"])
        conn.execute(
            """UPDATE ri_routes SET name=?, mode=?, fare_reference=?, updated_at=? WHERE id=?""",
            (
                prev.get("name"), prev.get("mode"), prev.get("fare_reference"),
                utc_now(), entry["entity_id"],
            ),
        )
        log_change(conn, "route", entry["entity_id"], "rollback", user, None, prev, f"from changelog {changelog_id}")
        conn.commit()
        return True, "Rolled back."
    return False, "Rollback supported for routes in MVP."


def preview_csv_import(text: str) -> tuple[list[dict], list[str]]:
    """Validate CSV: code,name,mode,stops (pipe-separated),lat/lng optional per stop later."""
    errors = []
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(text))
    except Exception:
        return [], ["Could not read CSV."]
    if not reader.fieldnames or "code" not in reader.fieldnames:
        return [], ["CSV needs a code column."]
    seen = set()
    for i, row in enumerate(reader, start=2):
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        mode = (row.get("mode") or "").strip()
        stops = [s.strip() for s in (row.get("stops") or "").split("|") if s.strip()]
        if not code or not name or not mode:
            errors.append(f"Line {i}: code, name, and mode are required.")
            continue
        if code in seen:
            errors.append(f"Line {i}: duplicate code {code}.")
            continue
        seen.add(code)
        if len(stops) < 2:
            errors.append(f"Line {i}: need at least 2 stops.")
            continue
        rows.append({"code": code, "name": name, "mode": mode, "stops": stops, "line": i})
    return rows, errors


def staff_queue(conn) -> dict:
    pending_routes = conn.execute(
        "SELECT id, code, name, status, updated_at FROM ri_routes WHERE status IN ('draft','pending_review') ORDER BY updated_at DESC"
    ).fetchall()
    pending_adv = conn.execute(
        "SELECT id, title, severity, status, updated_at FROM ri_advisories WHERE status='draft' ORDER BY updated_at DESC"
    ).fetchall()
    approvals = conn.execute(
        "SELECT * FROM ri_approvals WHERE status='pending' ORDER BY created_at DESC"
    ).fetchall()
    return {
        "routes": [dict(r) for r in pending_routes],
        "advisories": [dict(a) for a in pending_adv],
        "approvals": [dict(a) for a in approvals],
    }
