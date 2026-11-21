"""
Fare and Travel Time Estimation
================================
Clean layer used by Route Planning. Swap fare JSON or time models later
without touching the Plan Trip UI.

Data:
  data/fare_rules.json  — versioned FareRule rows (admin can edit; no redeploy)

Passenger types: regular | student | senior | pwd
Rounding: nearest peso (documented in JSON)
Missing fare → amount=None, label="Fare unavailable" (never invent a number)
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FARE_RULES_PATH = ROOT / "data" / "fare_rules.json"

# In-memory estimate cache (query key → payload). Cleared when rules reload.
_ESTIMATE_CACHE: dict[str, dict] = {}
_CACHE_MAX = 128
_RULES_MTIME: float | None = None


def _today() -> date:
    return date.today()


def invalidate_caches() -> None:
    """Call after fare rules or schedules change."""
    global _RULES_MTIME
    _ESTIMATE_CACHE.clear()
    load_fare_catalog.cache_clear()
    _RULES_MTIME = None


@lru_cache(maxsize=1)
def load_fare_catalog() -> dict:
    """Load fare rules JSON. Cached until invalidate_caches()."""
    with open(FARE_RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _ensure_fresh_catalog() -> dict:
    """Reload if the JSON file changed on disk (admin edit without restart)."""
    global _RULES_MTIME
    try:
        mtime = os.path.getmtime(FARE_RULES_PATH)
    except OSError:
        return load_fare_catalog()
    if _RULES_MTIME is None:
        _RULES_MTIME = mtime
        return load_fare_catalog()
    if mtime != _RULES_MTIME:
        invalidate_caches()
        _RULES_MTIME = mtime
        return load_fare_catalog()
    return load_fare_catalog()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def rule_is_active(rule: dict, on: date | None = None) -> bool:
    on = on or _today()
    start = parse_iso_date(rule.get("effective_from"))
    end = parse_iso_date(rule.get("effective_to"))
    if start and on < start:
        return False
    if end and on > end:
        return False
    return True


def pick_fare_rule(
    mode: str,
    line_code: str | None = None,
    on: date | None = None,
    *,
    include_outdated: bool = False,
) -> dict | None:
    """
    Prefer line-specific active rule, else mode-wide active rule.
    If include_outdated=True, return the newest expired rule (for tests / audit).
    """
    catalog = _ensure_fresh_catalog()
    rules = catalog.get("rules", [])
    on = on or _today()

    def score(r: dict) -> tuple:
        # Higher is better: line match, then latest effective_from
        line_hit = 1 if r.get("line_code") and r.get("line_code") == line_code else 0
        mode_hit = 1 if r.get("mode") == mode else 0
        start = parse_iso_date(r.get("effective_from")) or date.min
        return (line_hit, mode_hit, start)

    active = [
        r for r in rules
        if r.get("mode") == mode and rule_is_active(r, on)
        and (r.get("line_code") in (None, "", line_code) or r.get("line_code") == line_code)
    ]
    # Prefer exact line_code match when present
    if line_code:
        exact = [r for r in active if r.get("line_code") == line_code]
        if exact:
            return max(exact, key=score)
    mode_level = [r for r in active if not r.get("line_code")]
    if mode_level:
        return max(mode_level, key=score)
    if active:
        return max(active, key=score)

    if include_outdated:
        expired = [r for r in rules if r.get("mode") == mode and not rule_is_active(r, on)]
        if line_code:
            expired_line = [r for r in expired if r.get("line_code") == line_code]
            if expired_line:
                return max(expired_line, key=score)
        if expired:
            return max(expired, key=score)
    return None


def round_fare(amount: float, method: str | None = None) -> int:
    catalog = _ensure_fresh_catalog()
    method = method or catalog.get("rounding", "nearest_peso")
    if method == "floor_peso":
        return int(amount)
    if method == "ceil_peso":
        import math
        return int(math.ceil(amount))
    return int(round(amount))


def apply_discount(amount: float, passenger: str) -> tuple[int, str | None]:
    catalog = _ensure_fresh_catalog()
    discounts = catalog.get("discount_rules", {})
    key = (passenger or "regular").lower()
    rule = discounts.get(key) or discounts.get("regular") or {"factor": 1.0, "note": None}
    discounted = amount * float(rule.get("factor", 1.0))
    return round_fare(discounted), rule.get("note")


def _matrix_key(board: str, alight: str) -> str:
    return f"{board}|{alight}"


def _compute_raw_fare(rule: dict, distance_km: float, board: str | None, alight: str | None) -> float | None:
    model = rule.get("model")
    if model == "fixed":
        return float(rule.get("fixed_fare", rule.get("minimum_fare", 0)))

    if model == "matrix":
        matrix = rule.get("matrix") or {}
        if board and alight:
            key = _matrix_key(board, alight)
            rev = _matrix_key(alight, board)
            if key in matrix:
                return float(matrix[key])
            if rev in matrix:
                return float(matrix[rev])
        # Optional fallback to distance on same rule
        if rule.get("fallback_model") == "distance":
            return _distance_fare(rule, distance_km)
        return None

    if model == "zone":
        # Stage/zone: use stages ≈ ceil(distance / zone_km) if provided
        zone_km = float(rule.get("zone_km", 2.0))
        stage_fare = float(rule.get("stage_fare", rule.get("base_fare", 13)))
        stages = max(1, int((distance_km + zone_km - 1e-9) // zone_km) + (0 if distance_km <= zone_km else 0))
        # Simpler: stages = max(1, ceil(distance_km / zone_km))
        import math
        stages = max(1, int(math.ceil(distance_km / zone_km))) if distance_km > 0 else 1
        return stage_fare * stages

    if model == "distance":
        return _distance_fare(rule, distance_km)

    return None


def _distance_fare(rule: dict, distance_km: float) -> float:
    base = float(rule.get("base_fare", 13))
    base_km = float(rule.get("base_distance_km", 4))
    per_km = float(rule.get("per_km_rate", 1.8))
    return base + max(0.0, distance_km - base_km) * per_km


def estimate_leg_fare(
    *,
    mode: str,
    distance_km: float = 0.0,
    line_code: str | None = None,
    board_stop: str | None = None,
    alight_stop: str | None = None,
    passenger: str = "regular",
    air_conditioned: bool = False,
    peak: bool = False,
    on: date | None = None,
) -> dict[str, Any]:
    """
    Compute fare for one transit (or walk) leg.
    Never invents a number when no active rule exists.
    """
    if mode == "walk":
        return {
            "amount": 0,
            "currency": "PHP",
            "label": "Est. fare ₱0 (walk)",
            "aria_label": "Estimated fare, 0 pesos, walking",
            "is_estimate": True,
            "available": True,
            "model": "fixed",
            "passenger": passenger,
            "discount_note": None,
            "confidence": "high",
            "source": "n/a",
            "last_updated": None,
            "rule_id": None,
            "effective_from": None,
        }

    rule = pick_fare_rule(mode, line_code, on=on)
    if not rule:
        # Outdated-only rule → still unavailable for live pricing
        outdated = pick_fare_rule(mode, line_code, on=on, include_outdated=True)
        note = None
        if outdated:
            note = (
                f"Fare rule '{outdated.get('id')}' expired "
                f"({outdated.get('effective_to')}). Fare unavailable."
            )
        return {
            "amount": None,
            "currency": "PHP",
            "label": "Fare unavailable",
            "aria_label": "Fare unavailable for this segment",
            "is_estimate": True,
            "available": False,
            "model": None,
            "passenger": passenger,
            "discount_note": note,
            "confidence": "low",
            "source": outdated.get("source") if outdated else "missing",
            "last_updated": outdated.get("last_updated") if outdated else None,
            "rule_id": outdated.get("id") if outdated else None,
            "effective_from": outdated.get("effective_from") if outdated else None,
            "outdated": bool(outdated),
        }

    raw = _compute_raw_fare(rule, distance_km, board_stop, alight_stop)
    if raw is None:
        return {
            "amount": None,
            "currency": "PHP",
            "label": "Fare unavailable",
            "aria_label": "Fare unavailable for this segment",
            "is_estimate": True,
            "available": False,
            "model": rule.get("model"),
            "passenger": passenger,
            "discount_note": "No matrix entry for these stops.",
            "confidence": rule.get("confidence", "low"),
            "source": rule.get("source"),
            "last_updated": rule.get("last_updated"),
            "rule_id": rule.get("id"),
            "effective_from": rule.get("effective_from"),
        }

    if air_conditioned:
        raw += float(rule.get("ac_surcharge", 0) or 0)
    if peak:
        raw += float(rule.get("peak_surcharge", 0) or 0)

    minimum = float(rule.get("minimum_fare", 0) or 0)
    raw = max(raw, minimum)

    amount, discount_note = apply_discount(raw, passenger)

    return {
        "amount": amount,
        "currency": "PHP",
        "label": f"Est. fare ₱{amount}",
        "aria_label": f"Estimated fare, {amount} pesos",
        "is_estimate": True,
        "available": True,
        "model": rule.get("model"),
        "passenger": passenger,
        "discount_note": discount_note,
        "confidence": rule.get("confidence", "medium"),
        "source": rule.get("source"),
        "last_updated": rule.get("last_updated"),
        "rule_id": rule.get("id"),
        "effective_from": rule.get("effective_from"),
        "distance_km": round(distance_km, 3),
        "air_conditioned": air_conditioned,
        "peak": peak,
    }


def walk_speed_m_per_min(accessible: bool = False) -> float:
    catalog = _ensure_fresh_catalog()
    td = catalog.get("time_defaults", {})
    kmh = td.get("walk_speed_accessible_kmh" if accessible else "walk_speed_kmh", 4.5)
    return float(kmh) * 1000 / 60.0


def estimate_walk_time(distance_m: float, *, accessible: bool = False) -> dict:
    speed = walk_speed_m_per_min(accessible)
    mins = max(1, int(round(distance_m / speed))) if distance_m > 0 else 0
    return {
        "component": "walking",
        "duration_min": mins,
        "distance_m": int(round(distance_m)),
        "data_source": "assumed",
        "confidence": "medium",
        "assumption": f"Walk speed {4.5 if not accessible else 3.0} km/h",
        "label": f"About {mins} min walk",
        "aria_label": f"About {mins} minutes walking",
    }


def estimate_ride_time(distance_km: float, mode: str) -> dict:
    catalog = _ensure_fresh_catalog()
    speeds = catalog.get("time_defaults", {}).get("urban_speeds_kmh", {})
    speed = float(speeds.get(mode, 16))
    mins = max(5, int(round((distance_km / speed) * 60))) if distance_km > 0 else 0
    return {
        "component": "riding",
        "duration_min": mins,
        "distance_km": round(distance_km, 3),
        "data_source": "historical_average",
        "confidence": "medium",
        "assumption": f"Urban speed ~{speed} km/h for {mode}",
        "label": f"About {mins} min ride",
        "aria_label": f"About {mins} minutes riding",
    }


def estimate_wait_time(mode: str, headway_min: int | None = None) -> dict:
    catalog = _ensure_fresh_catalog()
    td = catalog.get("time_defaults", {})
    if headway_min is None:
        headway_min = int(td.get("headway_min", {}).get(mode, 10))
        has_freq = mode in td.get("headway_min", {})
    else:
        has_freq = True

    if has_freq and headway_min > 0:
        wait = max(2, headway_min // 2)
        return {
            "component": "waiting",
            "duration_min": wait,
            "headway_min": headway_min,
            "data_source": "assumed_frequency",
            "confidence": "medium",
            "assumption": "Expected wait ≈ half headway",
            "label": f"About {wait} min wait",
            "aria_label": f"About {wait} minutes waiting",
        }

    # No frequency data — do not invent a wait; mark unknown
    return {
        "component": "waiting",
        "duration_min": None,
        "headway_min": None,
        "data_source": "missing",
        "confidence": "low",
        "assumption": "No frequency data — wait time unknown",
        "label": "Wait time unavailable",
        "aria_label": "Wait time unavailable",
    }


def estimate_transfer_time(
    walk_m: float,
    mode_next: str,
    *,
    headway_min: int | None = None,
    accessible: bool = False,
) -> dict:
    walk = estimate_walk_time(walk_m, accessible=accessible)
    wait = estimate_wait_time(mode_next, headway_min=headway_min)
    parts = [walk["duration_min"] or 0]
    if wait["duration_min"] is not None:
        parts.append(wait["duration_min"])
        total = sum(parts)
        available = True
    else:
        total = walk["duration_min"] or 0
        available = False

    return {
        "component": "transfer",
        "duration_min": total if available else None,
        "walk": walk,
        "wait": wait,
        "data_source": "composite",
        "confidence": "low" if not available else "medium",
        "label": (
            f"About {total} min transfer"
            if available
            else f"About {walk['duration_min']} min walk + unknown wait"
        ),
        "aria_label": (
            f"About {total} minutes for transfer"
            if available
            else "Transfer time partly unavailable"
        ),
    }


def summarize_journey_fare(leg_fares: list[dict]) -> dict:
    """Sum segment fares; support partial totals when some legs are missing."""
    known = [f for f in leg_fares if f.get("available") and f.get("amount") is not None]
    missing = [f for f in leg_fares if not f.get("available") or f.get("amount") is None]
    # Walk ₱0 counts as known
    total = sum(int(f["amount"]) for f in known)
    missing_n = len([f for f in missing if f.get("mode") != "walk"])

    if missing_n == 0:
        label = f"Est. fare ₱{total}"
        partial = False
        aria = f"Estimated fare, {total} pesos"
    elif known:
        label = f"₱{total} + unknown fare for {missing_n} segment" + ("s" if missing_n != 1 else "")
        partial = True
        aria = f"Partial estimated fare, {total} pesos, plus unknown fare for {missing_n} segments"
    else:
        label = "Fare unavailable"
        partial = True
        total = 0
        aria = "Fare unavailable"

    confidences = [f.get("confidence", "low") for f in leg_fares if f.get("mode") != "walk"]
    confidence = _worst_confidence(confidences) if confidences else "high"
    last_updated = max(
        (f.get("last_updated") or "" for f in known if f.get("last_updated")),
        default=None,
    ) or None

    catalog = _ensure_fresh_catalog()
    return {
        "total_php": total if known else None,
        "total_known_php": total,
        "missing_segments": missing_n,
        "partial": partial,
        "label": label,
        "aria_label": aria,
        "is_estimate": True,
        "confidence": confidence,
        "last_updated": last_updated or catalog.get("updated_at"),
        "source_note": catalog.get("source_note"),
        "breakdown": leg_fares,
        "disclaimer": "Actual fares may differ. Estimates only — verify with the driver.",
    }


def summarize_journey_time(components: list[dict]) -> dict:
    riding = sum(c["duration_min"] or 0 for c in components if c.get("component") == "riding")
    walking = sum(c["duration_min"] or 0 for c in components if c.get("component") == "walking")
    waiting = sum(
        c["duration_min"] or 0
        for c in components
        if c.get("component") in ("waiting", "transfer") and c.get("duration_min") is not None
    )
    unknown_wait = any(
        c.get("component") in ("waiting", "transfer") and c.get("duration_min") is None
        for c in components
    )
    total = riding + walking + waiting
    label = f"About {total} min"
    if unknown_wait:
        label += " (+ unknown wait)"

    return {
        "total_min": total,
        "riding_min": riding,
        "walking_min": walking,
        "waiting_min": waiting,
        "unknown_wait": unknown_wait,
        "label": label,
        "aria_label": f"About {total} minutes total travel time",
        "is_estimate": True,
        "confidence": "low" if unknown_wait else "medium",
        "components": components,
        "disclaimer": "Actual times vary with traffic, queues, and vehicle availability.",
    }


def _worst_confidence(values: list[str]) -> str:
    order = {"high": 3, "medium": 2, "low": 1}
    if not values:
        return "low"
    return min(values, key=lambda v: order.get(v, 0))


def enrich_legs_with_estimates(
    legs: list[dict],
    *,
    passenger: str = "regular",
    accessible: bool = False,
    air_conditioned: bool = False,
    peak: bool = False,
) -> tuple[list[dict], dict, dict]:
    """
    Attach fare + time estimates to each leg; return (legs, fare_summary, time_summary).
    """
    cache_key = _legs_cache_key(legs, passenger, accessible, air_conditioned, peak)
    if cache_key in _ESTIMATE_CACHE:
        cached = deepcopy(_ESTIMATE_CACHE[cache_key])
        return cached["legs"], cached["fare"], cached["time"]

    fare_rows: list[dict] = []
    time_components: list[dict] = []
    out_legs: list[dict] = []

    for leg in legs:
        leg = deepcopy(leg)
        if leg.get("type") == "walk":
            fare = estimate_leg_fare(mode="walk", passenger=passenger)
            fare["mode"] = "walk"
            walk_t = estimate_walk_time(leg.get("distance_m", 0), accessible=accessible)
            leg["fare"] = fare
            leg["time_estimate"] = walk_t
            leg["duration_min"] = walk_t["duration_min"]
            fare_rows.append(fare)
            time_components.append(walk_t)
        else:
            dist_km = (leg.get("distance_m") or 0) / 1000.0
            if not dist_km and leg.get("distance_km"):
                dist_km = float(leg["distance_km"])
            fare = estimate_leg_fare(
                mode=leg.get("mode", "jeepney"),
                distance_km=dist_km,
                line_code=leg.get("line_code"),
                board_stop=(leg.get("boarding") or {}).get("name"),
                alight_stop=(leg.get("dropoff") or {}).get("name"),
                passenger=passenger,
                air_conditioned=air_conditioned or leg.get("mode") == "modern_jeepney",
                peak=peak,
            )
            fare["mode"] = leg.get("mode")
            fare["line_code"] = leg.get("line_code")
            ride = estimate_ride_time(dist_km, leg.get("mode", "jeepney"))
            wait = estimate_wait_time(leg.get("mode", "jeepney"), leg.get("headway_min"))
            wait_min = wait["duration_min"] if wait["duration_min"] is not None else 0
            leg["fare"] = fare
            leg["time_estimate"] = {
                "riding": ride,
                "waiting": wait,
                "duration_min": ride["duration_min"] + wait_min,
            }
            leg["ride_min"] = ride["duration_min"]
            leg["expected_wait_min"] = wait["duration_min"]
            leg["duration_min"] = ride["duration_min"] + wait_min
            leg["headway_min"] = wait.get("headway_min") or leg.get("headway_min")
            fare_rows.append(fare)
            time_components.append(wait)
            time_components.append(ride)

        out_legs.append(leg)

    fare_summary = summarize_journey_fare(fare_rows)
    time_summary = summarize_journey_time(time_components)

    payload = {"legs": out_legs, "fare": fare_summary, "time": time_summary}
    if len(_ESTIMATE_CACHE) >= _CACHE_MAX:
        _ESTIMATE_CACHE.pop(next(iter(_ESTIMATE_CACHE)))
    _ESTIMATE_CACHE[cache_key] = deepcopy(payload)
    return out_legs, fare_summary, time_summary


def _legs_cache_key(legs, passenger, accessible, air_conditioned, peak) -> str:
    parts = []
    for leg in legs:
        if leg.get("type") == "walk":
            parts.append(f"w:{leg.get('distance_m')}")
        else:
            parts.append(
                f"t:{leg.get('mode')}:{leg.get('line_code')}:"
                f"{(leg.get('boarding') or {}).get('name')}->"
                f"{(leg.get('dropoff') or {}).get('name')}:"
                f"{leg.get('distance_m')}"
            )
    return f"{passenger}|{accessible}|{air_conditioned}|{peak}|{'|'.join(parts)}"


def estimation_meta() -> dict:
    catalog = _ensure_fresh_catalog()
    td = catalog.get("time_defaults", {})
    return {
        "fare_updated_at": catalog.get("updated_at"),
        "source_note": catalog.get("source_note"),
        "rounding": catalog.get("rounding"),
        "passenger_types": list(catalog.get("discount_rules", {}).keys()),
        "walk_speed_kmh": td.get("walk_speed_kmh", 4.5),
        "walk_speed_accessible_kmh": td.get("walk_speed_accessible_kmh", 3.0),
        "realtime": td.get("realtime", False),
        "disclaimer": (
            "Fares and times are estimates. Traffic, fare changes, and vehicle "
            "availability can change what you pay and how long you wait."
        ),
        "how_it_works": [
            "Jeepney/bus fares usually use a base fare plus a per-km rate after a few kilometers.",
            "Some lines use a stop-to-stop fare matrix when available.",
            "Student, senior, and PWD discounts apply ~20% when selected — always verify with ID.",
            "Walk time assumes 4.5 km/h (slower if accessibility mode is on).",
            "Wait time assumes about half the usual headway when frequency is known.",
            "Missing rules show “Fare unavailable” — we never guess a peso amount.",
        ],
    }


# Back-compat helpers used by older planner code paths
def fare_for_leg(distance_km: float, mode: str, passenger: str = "regular") -> dict:
    return estimate_leg_fare(mode=mode, distance_km=distance_km, passenger=passenger)
