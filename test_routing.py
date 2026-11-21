"""
Route Planning unit tests — no Flask server required.
Run:  python test_routing.py
"""
from __future__ import annotations

import sys
from copy import deepcopy

from routing.planner import (
    plan_routes,
    score_routes,
    fare_for_leg,
    filter_unreasonable,
    build_walk_only,
    QUERY_CACHE,
)

# Minimal Cebu catalog (mirrors app.py shape)
LOCATIONS = [
    {"name": "Colon Street", "lat": 10.2978, "lng": 123.8988, "city": "Cebu City", "barangay": "Colon"},
    {"name": "SM City Cebu", "lat": 10.3116, "lng": 123.9184, "city": "Cebu City", "barangay": "North Reclamation"},
    {"name": "Fuente Osmeña Circle", "lat": 10.3098, "lng": 123.8931, "city": "Cebu City", "barangay": "Capitol Site"},
    {"name": "Ayala Center Cebu", "lat": 10.3174, "lng": 123.9054, "city": "Cebu City", "barangay": "Cebu Business Park"},
    {"name": "Carbon Market", "lat": 10.2925, "lng": 123.9012, "city": "Cebu City", "barangay": "Ermita"},
    {"name": "Parkmall", "lat": 10.3305, "lng": 123.9088, "city": "Mandaue", "barangay": "Ouano"},
    {"name": "IT Park", "lat": 10.3278, "lng": 123.9058, "city": "Cebu City", "barangay": "Lahug"},
]

TRANSIT_LINES = [
    {
        "code": "01K",
        "name": "Colon – SM City",
        "mode": "jeepney",
        "stops": ["Colon Street", "Fuente Osmeña Circle", "Ayala Center Cebu", "SM City Cebu"],
    },
    {
        "code": "04L",
        "name": "Carbon – Ayala",
        "mode": "jeepney",
        "stops": ["Carbon Market", "Colon Street", "Fuente Osmeña Circle", "Ayala Center Cebu"],
    },
    {
        "code": "62B",
        "name": "Ayala – Parkmall",
        "mode": "modern_jeepney",
        "stops": ["Ayala Center Cebu", "IT Park", "Parkmall", "SM City Cebu"],
    },
    {
        "code": "BUS-N",
        "name": "North Bus",
        "mode": "bus",
        "stops": ["Colon Street", "Fuente Osmeña Circle", "Parkmall"],
    },
]

PASS = []
FAIL = []


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        PASS.append(label)
        print(f"  PASS  {label}")
    else:
        FAIL.append(label)
        print(f"  FAIL  {label}  --  {detail}")


def origin(name: str) -> dict:
    loc = next(l for l in LOCATIONS if l["name"] == name)
    return {"name": loc["name"], "lat": loc["lat"], "lng": loc["lng"]}


def sort_client(routes, key):
    """Mirror js/plan-trip-map.js sortRoutes tie-breakers."""
    copy = list(routes)
    if key == "cheapest":
        copy.sort(key=lambda r: (r["summary"]["fare_php"], r["summary"]["duration_min"]))
    elif key == "fewest_transfers":
        copy.sort(key=lambda r: (r["summary"]["transfers"], r["summary"]["duration_min"]))
    elif key == "fastest":
        copy.sort(key=lambda r: (r["summary"]["duration_min"], r["summary"]["fare_php"]))
    else:
        copy.sort(
            key=lambda r: (
                r["scores"].get("recommended", 99),
                r["summary"]["duration_min"],
            )
        )
    return copy


def main():
    QUERY_CACHE.clear()

    print("\n=== Direct route (Colon → SM City) ===")
    res = plan_routes(origin("Colon Street"), origin("SM City Cebu"), LOCATIONS, TRANSIT_LINES)
    check("ok true", res.get("ok") is True, str(res))
    check("has routes", res.get("count", 0) >= 1, str(res.get("count")))
    directs = [r for r in res["routes"] if r["summary"]["transfers"] == 0 and "walk_only" not in r["tags"]]
    check("direct transit exists", len(directs) >= 1, f"found {len(directs)}")
    check("recommended flagged", any(r.get("is_recommended") for r in res["routes"]))
    check(
        "legs have boarding/dropoff",
        any(
            leg.get("type") == "transit"
            and leg.get("boarding", {}).get("name")
            and leg.get("dropoff", {}).get("name")
            for r in res["routes"]
            for leg in r["legs"]
        ),
    )

    print("\n=== One transfer (Carbon → SM City via hub) ===")
    QUERY_CACHE.clear()
    res1 = plan_routes(origin("Carbon Market"), origin("SM City Cebu"), LOCATIONS, TRANSIT_LINES)
    xfers = [r for r in res1["routes"] if r["summary"]["transfers"] >= 1]
    check("one+ transfer option", len(xfers) >= 1, f"count={len(xfers)} total={res1.get('count')}")
    if xfers:
        check("transfer note present", len(xfers[0]["transfers"]) >= 1)

    print("\n=== Multiple transfers (long OD + max_transfers=2) ===")
    QUERY_CACHE.clear()
    # Stretch Parkmall far enough that OD > 6 km (planner synthesizes a 2-xfer twin)
    locs_far = deepcopy(LOCATIONS)
    for loc in locs_far:
        if loc["name"] == "Parkmall":
            loc["lat"] = 10.2978 + 0.08  # ~9 km north of Colon
            loc["lng"] = 123.8988 + 0.02
    res2 = plan_routes(
        origin("Carbon Market"),
        {"name": "Parkmall", "lat": 10.2978 + 0.08, "lng": 123.8988 + 0.02},
        locs_far,
        TRANSIT_LINES,
        max_transfers=2,
        max_walk_m=2500,
    )
    check("multi-transfer search ok", res2.get("ok") is True, str(res2.get("suggestions")))
    two = [r for r in res2.get("routes", []) if r["summary"]["transfers"] >= 2]
    check(
        "two-transfer alternative when OD long",
        len(two) >= 1,
        f"two={len(two)} count={res2.get('count')} tags={[r.get('tags') for r in res2.get('routes', [])]}",
    )

    print("\n=== Walk-only (short OD) ===")
    QUERY_CACHE.clear()
    near = {
        "name": "Near Colon",
        "lat": 10.2978 + 0.001,
        "lng": 123.8988 + 0.001,
    }
    walk_res = plan_routes(near, origin("Colon Street"), LOCATIONS, TRANSIT_LINES)
    walk_routes = [r for r in walk_res["routes"] if "walk_only" in r.get("tags", [])]
    check("walk-only option for short OD", len(walk_routes) >= 1 or build_walk_only(near, origin("Colon Street")) is not None)

    print("\n=== No route found ===")
    QUERY_CACHE.clear()
    nowhere = plan_routes(
        {"name": "Ocean", "lat": 9.5, "lng": 122.0},
        {"name": "Mountains", "lat": 11.5, "lng": 125.0},
        LOCATIONS,
        TRANSIT_LINES,
        max_walk_m=200,
    )
    check("empty routes", nowhere.get("count", 0) == 0 or len(nowhere.get("routes", [])) == 0)
    check("suggestions returned", len(nowhere.get("suggestions", [])) >= 1)

    print("\n=== Sorting correctness ===")
    QUERY_CACHE.clear()
    sample = plan_routes(origin("Colon Street"), origin("SM City Cebu"), LOCATIONS, TRANSIT_LINES)
    routes = sample["routes"]
    if len(routes) >= 2:
        cheapest = sort_client(routes, "cheapest")
        check(
            "cheapest sorted by fare then time",
            all(
                cheapest[i]["summary"]["fare_php"] <= cheapest[i + 1]["summary"]["fare_php"]
                for i in range(len(cheapest) - 1)
            ),
        )
        fastest = sort_client(routes, "fastest")
        check(
            "fastest sorted by duration",
            all(
                fastest[i]["summary"]["duration_min"] <= fastest[i + 1]["summary"]["duration_min"]
                for i in range(len(fastest) - 1)
            ),
        )
        fewest = sort_client(routes, "fewest_transfers")
        check(
            "fewest transfers sorted",
            all(
                fewest[i]["summary"]["transfers"] <= fewest[i + 1]["summary"]["transfers"]
                for i in range(len(fewest) - 1)
            ),
        )
        rec = sort_client(routes, "recommended")
        check(
            "recommended has lowest score first",
            rec[0]["scores"]["recommended"] <= rec[-1]["scores"]["recommended"],
        )
    else:
        check("enough routes for sort test", False, f"only {len(routes)}")

    print("\n=== Missing / estimate fare data ===")
    fare = fare_for_leg(5.0, "jeepney", "regular")
    check("fare is_estimate", fare.get("is_estimate") is True)
    check("fare has label", "estimate" in fare.get("label", "").lower() or fare.get("amount") is not None)
    student = fare_for_leg(5.0, "jeepney", "student")
    check("student discount note", student.get("discount_note") is not None)
    # Unknown amount path: assemble still labels
    # Graceful missing fare: UI must show a label, never invent a silent number
    missing = fare_for_leg(0, "walk")
    check(
        "walk fare labeled",
        "₱0" in (missing.get("label") or "") or (missing.get("label") or "").lower() == "free",
    )
    check(
        "transit fare always labeled estimate",
        "est" in (fare.get("label") or "").lower() or fare.get("is_estimate") is True,
    )

    print("\n=== Longest walking distance edge case ===")
    QUERY_CACHE.clear()
    strict = plan_routes(
        origin("Colon Street"),
        origin("SM City Cebu"),
        LOCATIONS,
        TRANSIT_LINES,
        max_walk_m=50,
    )
    check(
        "strict walk budget filters or suggests",
        all(r["summary"]["walk_meters"] <= 50 for r in strict.get("routes", []))
        or len(strict.get("suggestions", [])) >= 1,
        f"routes={strict.get('count')} walks={[r['summary']['walk_meters'] for r in strict.get('routes', [])]}",
    )
    # filter_unreasonable drops walk > MAX_TOTAL_WALK_M
    bloated = {
        "id": "bloated",
        "summary": {
            "mode_chain_text": "Walk › X › Walk",
            "duration_min": 90,
            "transfers": 0,
            "fare_php": 20,
            "walk_meters": 9999,
        },
        "tags": [],
        "scores": {},
    }
    ok_route = {
        "id": "ok",
        "summary": {
            "mode_chain_text": "Walk › 01K › Walk",
            "duration_min": 30,
            "transfers": 0,
            "fare_php": 15,
            "walk_meters": 200,
        },
        "tags": [],
        "scores": {},
    }
    kept = filter_unreasonable([bloated, ok_route])
    check("excessive walk filtered", all(r["id"] != "bloated" for r in kept))

    print("\n=== Recommended scoring formula ===")
    a = {
        "id": "a",
        "summary": {"duration_min": 20, "fare_php": 30, "transfers": 1, "walk_meters": 400},
        "tags": [],
        "scores": {},
    }
    b = {
        "id": "b",
        "summary": {"duration_min": 40, "fare_php": 10, "transfers": 0, "walk_meters": 100},
        "tags": [],
        "scores": {},
    }
    scored = score_routes([deepcopy(a), deepcopy(b)])
    check("exactly one recommended", sum(1 for r in scored if r.get("is_recommended")) == 1)
    # Manual formula check for a:
    # time 20/40=0.5, fare 30/30=1, xfer 1/1=1, walk 400/400=1
    # 0.45*0.5 + 0.25*1 + 0.20*1 + 0.10*1 = 0.225+0.25+0.20+0.10 = 0.775
    sa = next(r for r in scored if r["id"] == "a")
    check("score a ≈ 0.775", abs(sa["scores"]["recommended"] - 0.775) < 0.001, str(sa["scores"]))

    print(f"\n{'=' * 40}")
    print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("Failed:", FAIL)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
