"""
Load the live transit catalog from data/transit_catalog.json
and from the Route Information database (with active reroutes applied).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "transit_catalog.json"


def load_file_catalog() -> dict:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def file_locations() -> list[dict]:
    return list(load_file_catalog().get("locations") or [])


def file_lines() -> list[dict]:
    """Shape expected by routing.planner: code, name, mode, stops[], base_fare."""
    out = []
    for line in load_file_catalog().get("lines") or []:
        out.append({
            "code": line["code"],
            "name": line["name"],
            "mode": line["mode"],
            "stops": list(line.get("stops") or []),
            "base_fare": line.get("base_fare", 13),
            "hours_from": line.get("hours_from"),
            "hours_to": line.get("hours_to"),
            "frequency_min": line.get("frequency_min"),
        })
    return out


def lines_for_planner(conn) -> list[dict]:
    """
    Prefer published DB routes; fall back to file catalog.
    Apply active temporary/permanent reroutes to stop lists.
    """
    from services import route_info as ri

    rows = conn.execute(
        "SELECT id, code, name, mode, fare_reference, frequency_min FROM ri_routes WHERE status='published'"
    ).fetchall()
    if not rows:
        lines = file_lines()
    else:
        lines = []
        for row in rows:
            stops = conn.execute(
                """SELECT s.name FROM ri_route_stops rs
                   JOIN ri_stops s ON s.id = rs.stop_id
                   WHERE rs.route_id=? ORDER BY rs.stop_order""",
                (row["id"],),
            ).fetchall()
            fare_ref = row["fare_reference"] or ""
            base = 13
            try:
                # "₱15 base (estimate)" → 15
                digits = "".join(ch for ch in fare_ref if ch.isdigit())
                if digits:
                    base = int(digits[:3])
            except ValueError:
                pass
            lines.append({
                "code": row["code"],
                "name": row["name"],
                "mode": row["mode"],
                "stops": [s["name"] for s in stops],
                "base_fare": base,
                "frequency_min": row["frequency_min"],
            })

    for ln in lines:
        ln["stops"] = ri.effective_line_stops(conn, ln["code"], ln["stops"])
    return deepcopy(lines)


def locations_for_search(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT name, lat, lng, city, barangay FROM ri_stops ORDER BY name"
    ).fetchall()
    if rows:
        return [
            {
                "name": r["name"],
                "type": "stop",
                "city": r["city"],
                "barangay": r["barangay"],
                "lat": r["lat"],
                "lng": r["lng"],
            }
            for r in rows
        ]
    return file_locations()
