"""
app.py  —  Biyahero Flask Backend
===================================
Serves all HTML pages and exposes API endpoints that store
signup / login data in the SQLite database (database/biyahero.db).

Run (local only):
    python app.py

Run (accessible to other devices on the same Wi-Fi):
    python app.py --host
"""

import os
import sys
import socket
import sqlite3
from flask import (
    Flask, request, jsonify, send_from_directory, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, "database", "biyahero.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTS  = {"jpg", "jpeg", "png", "pdf"}
MAX_FILE_MB   = 10

app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = "biyahero-secret-change-in-production"
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
REPORT_UPLOADS = os.path.join(UPLOAD_FOLDER, "reports")
os.makedirs(REPORT_UPLOADS, exist_ok=True)
ROUTE_INFO_SCHEMA = os.path.join(BASE_DIR, "database", "route_info_schema.sql")

# ---------------------------------------------------------------------------
# Transit catalog (file + DB). Live data for Plan Trip / search / fares.
# ---------------------------------------------------------------------------
from services.catalog import file_locations, file_lines

LOCATIONS = file_locations()
TRANSIT_LINES = file_lines()


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA busy_timeout=8000")
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


def save_upload(file_field_name):
    f = request.files.get(file_field_name)
    if not f or f.filename == "":
        return None
    if not allowed_file(f.filename):
        return None
    filename = secure_filename(f.filename)
    dest = os.path.join(UPLOAD_FOLDER, filename)
    f.save(dest)
    return os.path.join("uploads", filename).replace("\\", "/")


def get_initials(fullname):
    parts = fullname.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return fullname[:2].upper() if fullname else "??"


# ---------------------------------------------------------------------------
# Auth helper  — returns the logged-in user dict from session, or None
# ---------------------------------------------------------------------------
def current_user():
    return session.get("user")


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/html/<path:filename>")
def serve_html(filename):
    return send_from_directory(os.path.join(BASE_DIR, "html"), filename)

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, "css"), filename)

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(BASE_DIR, "js"), filename)

@app.route("/img/<path:filename>")
def serve_img(filename):
    return send_from_directory(os.path.join(BASE_DIR, "img"), filename)

@app.route("/api/leaflet/<path:filename>")
def serve_leaflet(filename):
    return send_from_directory(os.path.join(BASE_DIR, "api", "leaflet"), filename)

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ---------------------------------------------------------------------------
# COMMUTER SIGNUP  —  POST /api/commuter/signup
# ---------------------------------------------------------------------------
@app.route("/api/commuter/signup", methods=["POST"])
def commuter_signup():
    data = request.get_json(silent=True) or request.form

    fullname = (data.get("fullname") or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not fullname or not email or not password:
        return jsonify({"ok": False, "error": "All fields are required."}), 400
    if len(password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters."}), 400

    pw_hash = generate_password_hash(password)

    try:
        db = get_db()
        db.execute(
            "INSERT INTO commuters (fullname, email, password_hash) VALUES (?, ?, ?)",
            (fullname, email, pw_hash)
        )
        db.commit()
        db.close()
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "An account with that email already exists."}), 409

    return jsonify({"ok": True, "message": "Account created! Redirecting to login…"})


# ---------------------------------------------------------------------------
# DRIVER SIGNUP  —  3-step wizard
# ---------------------------------------------------------------------------
@app.route("/api/driver/signup/step1", methods=["POST"])
def driver_signup_step1():
    data = request.get_json(silent=True) or request.form

    fullname     = (data.get("fullname")     or "").strip()
    contact      = (data.get("contact")      or "").strip()
    email        = (data.get("email")        or "").strip().lower()
    password     = (data.get("password")     or "").strip()
    municipality = (data.get("municipality") or "").strip()

    if not all([fullname, contact, email, password, municipality]):
        return jsonify({"ok": False, "error": "All fields are required."}), 400
    if len(password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters."}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM drivers WHERE email = ?", (email,)).fetchone()
    db.close()
    if existing:
        return jsonify({"ok": False, "error": "An account with that email already exists."}), 409

    session["driver_step1"] = {
        "fullname": fullname, "contact": contact, "email": email,
        "password": password, "municipality": municipality,
    }
    return jsonify({"ok": True, "message": "Step 1 saved. Proceed to step 2."})


@app.route("/api/driver/signup/step2", methods=["POST"])
def driver_signup_step2():
    if "driver_step1" not in session:
        return jsonify({"ok": False, "error": "Step 1 not completed."}), 400

    data = request.get_json(silent=True) or request.form

    vehicle_type     = (data.get("vehicle-type")     or "").strip()
    plate_number     = (data.get("plate-number")     or "").strip()
    franchise_number = (data.get("franchise-number") or "").strip() or None
    route            = (data.get("route")            or "").strip()
    terminal         = (data.get("terminal")         or "").strip()
    seats            = str(data.get("seats", "")).strip()
    hours_from       = (data.get("hours-from")       or "").strip()
    hours_to         = (data.get("hours-to")         or "").strip()
    days_raw         = request.form.getlist("days") or data.get("days") or []
    if isinstance(days_raw, str):
        days_raw = [d.strip() for d in days_raw.split(",") if d.strip()]
    operating_days   = ",".join(days_raw)
    wheelchair       = 1 if data.get("wheelchair-accessible") in ("on", "true", "1", True) else 0

    if not all([vehicle_type, plate_number, route, terminal, seats, hours_from, hours_to, operating_days]):
        return jsonify({"ok": False, "error": "All required fields must be filled."}), 400

    try:
        seats = int(seats)
    except ValueError:
        return jsonify({"ok": False, "error": "Seats must be a number."}), 400

    session["driver_step2"] = {
        "vehicle_type": vehicle_type, "plate_number": plate_number,
        "franchise_number": franchise_number, "route": route,
        "terminal": terminal, "seats": seats,
        "operating_hours_from": hours_from, "operating_hours_to": hours_to,
        "operating_days": operating_days, "wheelchair_accessible": wheelchair,
    }
    return jsonify({"ok": True, "message": "Step 2 saved. Proceed to step 3."})


@app.route("/api/driver/signup/step3", methods=["POST"])
def driver_signup_step3():
    if "driver_step1" not in session or "driver_step2" not in session:
        return jsonify({"ok": False, "error": "Previous steps not completed."}), 400

    data      = request.form
    id_type   = (data.get("id-type")   or "").strip()
    id_number = (data.get("id-number") or "").strip()

    if not id_type or not id_number:
        return jsonify({"ok": False, "error": "ID type and ID number are required."}), 400

    id_front_path = save_upload("id-front")
    id_back_path  = save_upload("id-back")
    or_cr_path    = save_upload("or-cr")
    selfie_path   = save_upload("selfie")
    vehicle_photo = save_upload("vehicle-photo")

    missing = [f for f, v in [("ID front", id_front_path), ("ID back", id_back_path),
                               ("OR/CR", or_cr_path), ("Selfie", selfie_path)] if not v]
    if missing:
        return jsonify({"ok": False, "error": f"Missing required files: {', '.join(missing)}."}), 400

    s1 = session["driver_step1"]
    s2 = session["driver_step2"]
    pw_hash = generate_password_hash(s1["password"])

    try:
        db = get_db()
        db.execute("""
            INSERT INTO drivers (
                fullname, contact, email, password_hash, municipality,
                vehicle_type, plate_number, franchise_number,
                route, terminal, seats,
                operating_hours_from, operating_hours_to, operating_days, wheelchair_accessible,
                id_type, id_number,
                id_front_path, id_back_path, or_cr_path, selfie_path, vehicle_photo_path,
                approval_status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending')
        """, (
            s1["fullname"], s1["contact"], s1["email"], pw_hash, s1["municipality"],
            s2["vehicle_type"], s2["plate_number"], s2["franchise_number"],
            s2["route"], s2["terminal"], s2["seats"],
            s2["operating_hours_from"], s2["operating_hours_to"],
            s2["operating_days"], s2["wheelchair_accessible"],
            id_type, id_number,
            id_front_path, id_back_path, or_cr_path, selfie_path, vehicle_photo,
        ))
        db.commit()
        db.close()
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "An account with that email already exists."}), 409

    session.pop("driver_step1", None)
    session.pop("driver_step2", None)
    return jsonify({"ok": True, "message": "Application submitted! Redirecting to login…"})


# ---------------------------------------------------------------------------
# LOGIN  —  POST /api/login
# Returns fullname, initials, email, role, id so the client can store them.
# ---------------------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or request.form
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password are required."}), 400

    db = get_db()

    # 1. Commuters
    row = db.execute(
        "SELECT id, fullname, email, password_hash, created_at FROM commuters WHERE email = ?",
        (email,)
    ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        db.close()
        user = {"id": row["id"], "fullname": row["fullname"], "email": row["email"],
                "role": "commuter", "initials": get_initials(row["fullname"]),
                "created_at": row["created_at"]}
        session["user"] = user
        return jsonify({"ok": True, "redirect": "/html/dashboard.html", **user})

    # 2. Drivers
    row = db.execute(
        "SELECT id, fullname, email, password_hash, approval_status, contact, "
        "vehicle_type, route, municipality, created_at FROM drivers WHERE email = ?",
        (email,)
    ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        db.close()
        status = row["approval_status"]
        user = {"id": row["id"], "fullname": row["fullname"], "email": row["email"],
                "role": "driver", "initials": get_initials(row["fullname"]),
                "approval_status": status, "contact": row["contact"],
                "vehicle_type": row["vehicle_type"], "route": row["route"],
                "municipality": row["municipality"], "created_at": row["created_at"]}
        session["user"] = user
        if status == "pending":
            return jsonify({"ok": True, "redirect": "/html/pending-approval.html", **user})
        if status == "declined":
            return jsonify({"ok": True, "redirect": "/html/declined.html", **user})
        return jsonify({"ok": True, "redirect": "/html/driver-dashboard.html", **user})

    # 3. Operators
    row = db.execute(
        "SELECT id, fullname, email, password_hash, company_name, contact, created_at "
        "FROM operators WHERE email = ?",
        (email,)
    ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        db.close()
        user = {"id": row["id"], "fullname": row["fullname"], "email": row["email"],
                "role": "operator", "initials": get_initials(row["fullname"]),
                "company_name": row["company_name"], "contact": row["contact"],
                "created_at": row["created_at"]}
        session["user"] = user
        return jsonify({"ok": True, "redirect": "/html/operator-dashboard.html", **user})

    db.close()
    return jsonify({"ok": False, "error": "Email address or password is incorrect."}), 401


# ---------------------------------------------------------------------------
# LOGOUT  —  POST /api/logout
# ---------------------------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True, "redirect": "/html/login.html"})


# ---------------------------------------------------------------------------
# ME  —  GET /api/me
# Returns the currently logged-in user's full profile from the DB.
# ---------------------------------------------------------------------------
@app.route("/api/me", methods=["GET"])
def me():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Not logged in."}), 401

    db  = get_db()
    row = None

    if user["role"] == "commuter":
        row = db.execute(
            "SELECT id, fullname, email, contact, created_at FROM commuters WHERE id = ?",
            (user["id"],)
        ).fetchone()
        if row:
            db.close()
            return jsonify({"ok": True, "role": "commuter",
                            "id": row["id"], "fullname": row["fullname"],
                            "email": row["email"], "contact": row["contact"],
                            "created_at": row["created_at"],
                            "initials": get_initials(row["fullname"])})

    elif user["role"] == "driver":
        row = db.execute(
            "SELECT id, fullname, email, contact, municipality, vehicle_type, "
            "plate_number, route, terminal, operating_hours_from, operating_hours_to, "
            "operating_days, approval_status, created_at FROM drivers WHERE id = ?",
            (user["id"],)
        ).fetchone()
        if row:
            db.close()
            return jsonify({"ok": True, "role": "driver",
                            "id": row["id"], "fullname": row["fullname"],
                            "email": row["email"], "contact": row["contact"],
                            "municipality": row["municipality"],
                            "vehicle_type": row["vehicle_type"],
                            "plate_number": row["plate_number"],
                            "route": row["route"], "terminal": row["terminal"],
                            "operating_hours_from": row["operating_hours_from"],
                            "operating_hours_to": row["operating_hours_to"],
                            "operating_days": row["operating_days"],
                            "approval_status": row["approval_status"],
                            "created_at": row["created_at"],
                            "initials": get_initials(row["fullname"])})

    elif user["role"] == "operator":
        row = db.execute(
            "SELECT id, fullname, email, contact, company_name, franchise_number, "
            "municipality, created_at FROM operators WHERE id = ?",
            (user["id"],)
        ).fetchone()
        if row:
            db.close()
            return jsonify({"ok": True, "role": "operator",
                            "id": row["id"], "fullname": row["fullname"],
                            "email": row["email"], "contact": row["contact"],
                            "company_name": row["company_name"],
                            "franchise_number": row["franchise_number"],
                            "municipality": row["municipality"],
                            "created_at": row["created_at"],
                            "initials": get_initials(row["fullname"])})

    db.close()
    return jsonify({"ok": False, "error": "User not found."}), 404


# ---------------------------------------------------------------------------
# PROFILE UPDATE  —  POST /api/profile/update
# Commuters can update fullname. Drivers can update fullname + contact.
# Operators can update fullname + contact + company_name.
# Any role can change their password.
# ---------------------------------------------------------------------------
@app.route("/api/profile/update", methods=["POST"])
def profile_update():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Not logged in."}), 401

    data        = request.get_json(silent=True) or request.form
    fullname    = (data.get("fullname")     or "").strip()
    new_password= (data.get("new_password") or "").strip()
    current_pw  = (data.get("current_password") or "").strip()

    if not fullname:
        return jsonify({"ok": False, "error": "Full name is required."}), 400

    db = get_db()

    if user["role"] == "commuter":
        contact = (data.get("contact") or "").strip()
        row = db.execute("SELECT password_hash FROM commuters WHERE id=?", (user["id"],)).fetchone()
        if not row:
            db.close()
            return jsonify({"ok": False, "error": "User not found."}), 404

        if new_password:
            if not current_pw or not check_password_hash(row["password_hash"], current_pw):
                db.close()
                return jsonify({"ok": False, "error": "Current password is incorrect."}), 400
            if len(new_password) < 8:
                db.close()
                return jsonify({"ok": False, "error": "New password must be at least 8 characters."}), 400
            db.execute(
                "UPDATE commuters SET fullname=?, contact=?, password_hash=?, updated_at=datetime('now') WHERE id=?",
                (fullname, contact, generate_password_hash(new_password), user["id"])
            )
        else:
            db.execute(
                "UPDATE commuters SET fullname=?, contact=?, updated_at=datetime('now') WHERE id=?",
                (fullname, contact, user["id"])
            )

    elif user["role"] == "driver":
        contact = (data.get("contact") or "").strip()
        row = db.execute("SELECT password_hash FROM drivers WHERE id=?", (user["id"],)).fetchone()
        if not row:
            db.close()
            return jsonify({"ok": False, "error": "User not found."}), 404

        if new_password:
            if not current_pw or not check_password_hash(row["password_hash"], current_pw):
                db.close()
                return jsonify({"ok": False, "error": "Current password is incorrect."}), 400
            if len(new_password) < 8:
                db.close()
                return jsonify({"ok": False, "error": "New password must be at least 8 characters."}), 400
            db.execute(
                "UPDATE drivers SET fullname=?, contact=?, password_hash=?, updated_at=datetime('now') WHERE id=?",
                (fullname, contact, generate_password_hash(new_password), user["id"])
            )
        else:
            db.execute(
                "UPDATE drivers SET fullname=?, contact=?, updated_at=datetime('now') WHERE id=?",
                (fullname, contact, user["id"])
            )

    elif user["role"] == "operator":
        contact      = (data.get("contact")      or "").strip()
        company_name = (data.get("company_name") or "").strip()
        row = db.execute("SELECT password_hash FROM operators WHERE id=?", (user["id"],)).fetchone()
        if not row:
            db.close()
            return jsonify({"ok": False, "error": "User not found."}), 404

        if new_password:
            if not current_pw or not check_password_hash(row["password_hash"], current_pw):
                db.close()
                return jsonify({"ok": False, "error": "Current password is incorrect."}), 400
            if len(new_password) < 8:
                db.close()
                return jsonify({"ok": False, "error": "New password must be at least 8 characters."}), 400
            db.execute(
                "UPDATE operators SET fullname=?, contact=?, company_name=?, password_hash=?, updated_at=datetime('now') WHERE id=?",
                (fullname, contact, company_name, generate_password_hash(new_password), user["id"])
            )
        else:
            db.execute(
                "UPDATE operators SET fullname=?, contact=?, company_name=?, updated_at=datetime('now') WHERE id=?",
                (fullname, contact, company_name, user["id"])
            )

    db.commit()
    db.close()

    # Refresh session user data
    session["user"] = {**user, "fullname": fullname, "initials": get_initials(fullname)}
    return jsonify({"ok": True, "message": "Profile updated successfully.",
                    "fullname": fullname, "initials": get_initials(fullname)})


# ---------------------------------------------------------------------------
# LOCATIONS SEARCH  —  GET /api/locations?q=<query>&limit=10
# Searches by name, barangay, or city. Supports partial matches.
# ---------------------------------------------------------------------------
@app.route("/api/locations", methods=["GET"])
def locations():
    from services.catalog import locations_for_search

    q     = (request.args.get("q") or "").strip().lower()
    limit = min(int(request.args.get("limit", 10)), 30)

    try:
        db = get_db()
        catalog = locations_for_search(db)
        db.close()
    except Exception:
        catalog = LOCATIONS

    pool = catalog or LOCATIONS

    if not q:
        results = pool[:limit]
    else:
        results = [
            loc for loc in pool
            if q in (loc.get("name") or "").lower()
            or q in (loc.get("barangay") or "").lower()
            or q in (loc.get("city") or "").lower()
        ][:limit]

    return jsonify({"ok": True, "results": results})


def _haversine_km(lat1, lng1, lat2, lng2):
    from math import radians, sin, cos, sqrt, atan2
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def _nearest_location(lat, lng):
    best, best_d = None, 1e9
    for loc in LOCATIONS:
        d = _haversine_km(lat, lng, loc["lat"], loc["lng"])
        if d < best_d:
            best, best_d = loc, d
    return best, best_d


# ---------------------------------------------------------------------------
# REVERSE GEOCODE  —  GET /api/geocode/reverse?lat=&lng=
# Proxies Nominatim so the browser never needs a map API key.
# ---------------------------------------------------------------------------
@app.route("/api/geocode/reverse", methods=["GET"])
def geocode_reverse():
    import urllib.request
    import urllib.parse
    import json as _json

    try:
        lat = float(request.args.get("lat", ""))
        lng = float(request.args.get("lng", ""))
    except ValueError:
        return jsonify({"ok": False, "error": "Bad coordinates."}), 400

    nearest, dist_km = _nearest_location(lat, lng)
    # Prefer nearby catalog place when within ~1.2 km
    if nearest and dist_km <= 1.2:
        return jsonify({
            "ok": True,
            "place": {
                "name": nearest["name"],
                "type": nearest["type"],
                "city": nearest["city"],
                "barangay": nearest["barangay"],
                "lat": lat,
                "lng": lng,
                "address": f"{nearest['barangay']}, {nearest['city']}",
                "source": "catalog",
            },
        })

    url = (
        "https://nominatim.openstreetmap.org/reverse?"
        + urllib.parse.urlencode({
            "format": "jsonv2",
            "lat": lat,
            "lon": lng,
            "zoom": 16,
            "addressdetails": 1,
        })
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BiyaheroTransitApp/1.0 (capstone; local-dev)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Offline / blocked — still return a usable pin label
        label = nearest["name"] if nearest else f"Pin ({lat:.4f}, {lng:.4f})"
        city = nearest["city"] if nearest else "Cebu"
        brgy = nearest["barangay"] if nearest else "Selected point"
        return jsonify({
            "ok": True,
            "place": {
                "name": label,
                "type": "map",
                "city": city,
                "barangay": brgy,
                "lat": lat,
                "lng": lng,
                "address": f"{brgy}, {city}",
                "source": "fallback",
            },
        })

    addr = data.get("address") or {}
    name = (
        data.get("name")
        or addr.get("road")
        or addr.get("neighbourhood")
        or addr.get("suburb")
        or data.get("display_name", "Selected place").split(",")[0]
    )
    city = addr.get("city") or addr.get("town") or addr.get("municipality") or "Cebu"
    barangay = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or city

    return jsonify({
        "ok": True,
        "place": {
            "name": name,
            "type": "map",
            "city": city,
            "barangay": barangay,
            "lat": lat,
            "lng": lng,
            "address": data.get("display_name", f"{barangay}, {city}"),
            "source": "nominatim",
        },
    })


# ---------------------------------------------------------------------------
# ROUTE PLANNING  —  POST /api/routes/search
# Body: {
#   from, to,
#   max_transfers?, max_walk_m?, passenger?, preferred_modes?,
# }
# Returns ranked Route alternatives with full legs (walk + transit).
# Routing logic lives in routing/planner.py (swap-friendly).
# ---------------------------------------------------------------------------
@app.route("/api/routes/search", methods=["POST"])
def routes_search():
    from routing.planner import plan_routes

    body = request.get_json(silent=True) or {}
    frm = body.get("from") or {}
    to = body.get("to") or {}

    try:
        flat, flng = float(frm["lat"]), float(frm["lng"])
        tlat, tlng = float(to["lat"]), float(to["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "Start and end places need valid map points."}), 400

    if flat == tlat and flng == tlng:
        return jsonify({"ok": False, "error": "Start and end cannot be the same place."}), 400

    prefs = body.get("preferences") or {}
    try:
        max_transfers = int(body.get("max_transfers", prefs.get("max_transfers", 3)))
        max_walk_m = int(body.get("max_walk_m", prefs.get("max_walk_m", 1800)))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Bad preference values."}), 400

    passenger = (body.get("passenger") or prefs.get("passenger") or "regular").lower()
    preferred_modes = body.get("preferred_modes") or prefs.get("preferred_modes")

    # Live catalog from DB (+ active reroutes). File catalog is fallback only.
    from services.catalog import lines_for_planner, locations_for_search

    db = get_db()
    try:
        lines_for_plan = lines_for_planner(db)
        locs = locations_for_search(db)
    finally:
        db.close()

    result = plan_routes(
        {"name": frm.get("name"), "lat": flat, "lng": flng},
        {"name": to.get("name"), "lat": tlat, "lng": tlng},
        locs or LOCATIONS,
        lines_for_plan or TRANSIT_LINES,
        max_transfers=max_transfers,
        max_walk_m=max_walk_m,
        passenger=passenger,
        preferred_modes=preferred_modes,
    )

    # Back-compat: also expose `options` summary cards for older clients
    options = []
    for route in result.get("routes", []):
        s = route["summary"]
        options.append({
            "id": route["id"],
            "title": s["mode_chain_text"],
            "mode": next((m["mode"] for m in s["mode_chain"] if m["mode"] != "walk"), "jeepney"),
            "line_code": next((m["label"] for m in s["mode_chain"] if m["mode"] != "walk"), "LOCAL"),
            "transfers": s["transfers"],
            "duration_min": s["duration_min"],
            "fare_php": s["fare_php"],
            "walk_meters": s["walk_meters"],
            "departure_label": s["departure_label"],
            "arrival_label": s["arrival_label"],
            "is_recommended": route.get("is_recommended", False),
            "tags": route.get("tags", []),
            "from": route["from"],
            "to": route["to"],
        })

    return jsonify({
        "ok": True,
        "disclaimer": "Times and fares are estimates — not live arrivals.",
        "routes": result.get("routes", []),
        "options": options,
        "count": result.get("count", 0),
        "suggestions": result.get("suggestions", []),
        "assumptions": result.get("assumptions", {}),
        "cached": result.get("cached", False),
    })


# ---------------------------------------------------------------------------
# ROUTE INFORMATION + UPDATES  (public read / staff write)
# ---------------------------------------------------------------------------
def _init_route_info_db():
    from services import route_info as ri
    conn = get_db()
    ri.ensure_schema(conn, ROUTE_INFO_SCHEMA)
    ri.clear_demo_content(conn)
    # One-time clean rebuild marker so old demo rows are replaced by the live catalog
    marker = os.path.join(BASE_DIR, "database", ".catalog_v2")
    force = not os.path.exists(marker)
    ri.seed_from_catalog(conn, TRANSIT_LINES, LOCATIONS, force=force)
    if force:
        open(marker, "w", encoding="utf-8").write("ok\n")
    conn.close()


try:
    _init_route_info_db()
except Exception as _e:
    print("Route info schema init skipped:", _e)


@app.route("/api/fares/estimate", methods=["POST"])
def api_fares_estimate():
    """Live fare estimate using Route Planning + Fare Estimation (no sample matrix)."""
    from routing.planner import plan_routes
    from services.catalog import lines_for_planner, locations_for_search
    from routing.estimation import estimation_meta

    body = request.get_json(silent=True) or {}
    frm = body.get("from") or {}
    to = body.get("to") or {}
    passenger = (body.get("passenger") or "regular").lower()
    try:
        flat, flng = float(frm["lat"]), float(frm["lng"])
        tlat, tlng = float(to["lat"]), float(to["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "Pick valid From and To places."}), 400

    db = get_db()
    try:
        lines = lines_for_planner(db)
        locs = locations_for_search(db)
    finally:
        db.close()

    result = plan_routes(
        {"name": frm.get("name"), "lat": flat, "lng": flng},
        {"name": to.get("name"), "lat": tlat, "lng": tlng},
        locs or LOCATIONS,
        lines or TRANSIT_LINES,
        max_transfers=int(body.get("max_transfers", 3)),
        max_walk_m=int(body.get("max_walk_m", 1800)),
        passenger=passenger,
    )
    routes = result.get("routes") or []
    if not routes:
        return jsonify({
            "ok": True,
            "found": False,
            "suggestions": result.get("suggestions") or [],
            "meta": estimation_meta(),
        })

    best = routes[0]
    return jsonify({
        "ok": True,
        "found": True,
        "route": {
            "id": best["id"],
            "mode_chain": best["summary"]["mode_chain_text"],
            "fare_label": best["summary"]["fare_label"],
            "fare_php": best["summary"]["fare_php"],
            "fare_summary": best.get("fare_summary"),
            "time_label": best["summary"].get("time_label"),
            "duration_min": best["summary"]["duration_min"],
            "time_breakdown": best["summary"].get("time_breakdown"),
            "transfers": best["summary"]["transfers"],
            "legs": [
                {
                    "type": leg.get("type"),
                    "mode": leg.get("mode"),
                    "line_code": leg.get("line_code"),
                    "fare": leg.get("fare"),
                    "duration_min": leg.get("duration_min"),
                }
                for leg in best.get("legs", [])
            ],
            "is_recommended": best.get("is_recommended"),
        },
        "alternatives": [
            {
                "id": r["id"],
                "mode_chain": r["summary"]["mode_chain_text"],
                "fare_label": r["summary"]["fare_label"],
                "duration_min": r["summary"]["duration_min"],
            }
            for r in routes[:5]
        ],
        "meta": estimation_meta(),
        "disclaimer": "Estimates only — actual fares may differ.",
    })


@app.route("/api/route-info", methods=["GET"])
def api_route_info_list():
    from services import route_info as ri
    q = request.args.get("q")
    stop = request.args.get("stop")
    conn = get_db()
    routes = ri.list_published_routes(conn, q=q, stop=stop)
    advisories = ri.list_active_advisories(conn)
    conn.close()
    resp = jsonify({"ok": True, "routes": routes, "advisories": advisories, "count": len(routes)})
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


@app.route("/api/route-info/<code>", methods=["GET"])
def api_route_info_detail(code):
    from services import route_info as ri
    conn = get_db()
    item = ri.get_route(conn, code)
    conn.close()
    if not item:
        return jsonify({"ok": False, "error": "Route not found."}), 404
    resp = jsonify({"ok": True, "route": item})
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


@app.route("/api/advisories", methods=["GET"])
def api_advisories():
    from services import route_info as ri
    history = request.args.get("history") == "1"
    route_code = request.args.get("route")
    severity = request.args.get("severity")
    conn = get_db()
    items = ri.list_active_advisories(conn, route_code=route_code, history=history)
    conn.close()
    if severity:
        items = [a for a in items if a["severity"] == severity]
    resp = jsonify({
        "ok": True,
        "advisories": items,
        "count": len(items),
        "meta": ri.updates_meta(),
    })
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp


@app.route("/api/reroutes", methods=["GET"])
def api_reroutes():
    from services import route_info as ri
    conn = get_db()
    items = ri.list_active_reroutes(conn)
    conn.close()
    resp = jsonify({
        "ok": True,
        "reroutes": items,
        "count": len(items),
        "meta": ri.updates_meta(),
    })
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp


@app.route("/api/updates", methods=["GET"])
def api_updates_bundle():
    """
    Public Updates feed split into:
      - verified route_changes
      - general traffic_advisories
    Includes data source labels + refresh frequency meta.
    """
    from services import route_info as ri
    history = request.args.get("history") == "1"
    severity = request.args.get("severity") or None
    conn = get_db()
    bundle = ri.list_updates_bundle(conn, history=history, severity=severity)
    conn.close()
    resp = jsonify({"ok": True, **bundle})
    resp.headers["Cache-Control"] = f"public, max-age={ri.UPDATES_REFRESH_SECONDS}"
    return resp


@app.route("/api/staff/advisories", methods=["POST"])
def api_staff_create_advisory():
    from services import route_info as ri
    user = current_user()
    if not ri.is_staff(user):
        return jsonify({"ok": False, "error": "Staff login required."}), 403
    body = request.get_json(silent=True) or {}
    # Default traffic advisories to a clear non-verified source unless staff sets one
    body.setdefault("source_label", "operator")
    conn = get_db()
    item, err = ri.create_advisory(conn, body, user)
    conn.close()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, "advisory": item})


@app.route("/api/staff/reroutes", methods=["POST"])
def api_staff_create_reroute():
    """Create a verified route change (path/stop detour). Admins publish immediately."""
    from services import route_info as ri
    user = current_user()
    if not ri.is_staff(user):
        return jsonify({"ok": False, "error": "Staff login required."}), 403
    body = request.get_json(silent=True) or {}
    conn = get_db()
    item, err = ri.create_reroute(conn, body, user)
    conn.close()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, "reroute": item})


@app.route("/api/staff/review", methods=["POST"])
def api_staff_review():
    from services import route_info as ri
    user = current_user()
    if not ri.is_admin(user):
        return jsonify({"ok": False, "error": "Admin only."}), 403
    body = request.get_json(silent=True) or {}
    conn = get_db()
    ok, msg = ri.review_entity(
        conn,
        body.get("entity_type"),
        int(body.get("entity_id", 0)),
        bool(body.get("approve")),
        user,
        body.get("note") or "",
    )
    conn.close()
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "result": msg})


@app.route("/api/staff/queue", methods=["GET"])
def api_staff_queue():
    from services import route_info as ri
    user = current_user()
    if not ri.is_staff(user):
        return jsonify({"ok": False, "error": "Staff login required."}), 403
    conn = get_db()
    data = ri.staff_queue(conn)
    conn.close()
    return jsonify({"ok": True, **data, "is_admin": ri.is_admin(user)})


@app.route("/api/staff/import/preview", methods=["POST"])
def api_staff_import_preview():
    from services import route_info as ri
    user = current_user()
    if not ri.is_staff(user):
        return jsonify({"ok": False, "error": "Staff login required."}), 403
    text = request.get_data(as_text=True) or ""
    if request.is_json:
        text = (request.get_json() or {}).get("csv") or text
    rows, errors = ri.preview_csv_import(text)
    return jsonify({"ok": len(errors) == 0, "rows": rows, "errors": errors})


# ---------------------------------------------------------------------------
# USER REPORTS
# ---------------------------------------------------------------------------
@app.route("/api/reports", methods=["POST"])
def api_reports_create():
    from services import reports as ur
    user = current_user()
    if not user:
        return jsonify({
            "ok": False,
            "error": "Please log in to send a report.",
            "login_required": True,
            "redirect": "/html/login.html?next=/html/report.html",
        }), 401

    body = request.get_json(silent=True) or {}
    # Also accept multipart
    if not body and request.form:
        body = {k: request.form.get(k) for k in request.form}
        if body.get("lat"):
            try:
                body["lat"] = float(body["lat"])
                body["lng"] = float(body["lng"])
            except (TypeError, ValueError):
                body["lat"] = body["lng"] = None
        body["confirm_similar"] = body.get("confirm_similar") in ("1", "true", "True", True)

    conn = get_db()
    # Similar check pass-through
    if body.get("confirm_similar") in (True, "true", "1"):
        body["confirm_similar"] = True
    item, err = ur.create_report(conn, user, body)
    if err == "similar":
        similar = ur.find_similar(conn, body.get("category"), body.get("route_code"), body.get("description", ""))
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Similar reports exist. Check them, then confirm to send anyway.",
            "similar": similar,
            "needs_confirm": True,
        }), 409
    if err:
        conn.close()
        return jsonify({"ok": False, "error": err}), 400

    # Save photos if multipart
    files = request.files.getlist("photos") if request.files else []
    for f in files[: ur.MAX_PHOTOS]:
        if not f or not f.filename:
            continue
        raw = f.read()
        if len(raw) > ur.MAX_PHOTO_BYTES:
            continue
        fname = secure_filename(f.filename)
        path = os.path.join(REPORT_UPLOADS, f"{item['ref_code']}_{fname}")
        with open(path, "wb") as out:
            out.write(raw)
        rel = os.path.relpath(path, BASE_DIR).replace("\\", "/")
        ur.attach_file(conn, item["id"], rel, fname, len(raw))

    conn.close()
    return jsonify({"ok": True, "report": item})


@app.route("/api/reports/mine", methods=["GET"])
def api_reports_mine():
    from services import reports as ur
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Please log in.", "login_required": True}), 401
    conn = get_db()
    items = ur.list_my_reports(conn, user)
    conn.close()
    return jsonify({"ok": True, "reports": items})


@app.route("/api/reports/<int:report_id>", methods=["GET"])
def api_reports_detail(report_id):
    from services import reports as ur
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Please log in.", "login_required": True}), 401
    conn = get_db()
    item, err = ur.get_report_for_user(conn, report_id, user)
    conn.close()
    if err:
        code = 403 if "own" in err else 404
        return jsonify({"ok": False, "error": err}), code
    return jsonify({"ok": True, "report": item})


@app.route("/api/reports/<int:report_id>/status", methods=["POST"])
def api_reports_status(report_id):
    from services import reports as ur
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Please log in."}), 401
    body = request.get_json(silent=True) or {}
    conn = get_db()
    item, err = ur.transition(
        conn, report_id, body.get("status"), user,
        note=body.get("note") or "",
        duplicate_of=body.get("duplicate_of"),
    )
    conn.close()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, "report": item})


@app.route("/api/reports/<int:report_id>/note", methods=["POST"])
def api_reports_note(report_id):
    from services import reports as ur
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Please log in."}), 401
    body = request.get_json(silent=True) or {}
    conn = get_db()
    ok, msg = ur.add_user_note(conn, report_id, user, body.get("body") or "")
    conn.close()
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "message": msg})


@app.route("/api/staff/reports", methods=["GET"])
def api_staff_reports():
    from services import reports as ur
    from services import route_info as ri
    user = current_user()
    if not ri.is_staff(user):
        return jsonify({"ok": False, "error": "Staff login required."}), 403
    filters = {
        "status": request.args.get("status"),
        "category": request.args.get("category"),
        "route_code": request.args.get("route"),
        "q": request.args.get("q"),
        "sort": request.args.get("sort"),
    }
    conn = get_db()
    items = ur.list_admin_reports(conn, filters)
    stats = ur.analytics(conn)
    conn.close()
    return jsonify({"ok": True, "reports": items, "analytics": stats})


@app.route("/api/staff/reports/<int:report_id>/apply", methods=["POST"])
def api_staff_apply_report(report_id):
    from services import reports as ur
    from services import route_info as ri
    user = current_user()
    if not ri.is_staff(user):
        return jsonify({"ok": False, "error": "Staff login required."}), 403
    conn = get_db()
    item, err = ur.apply_correction_draft(conn, report_id, user)
    conn.close()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, "draft": item})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    lan_mode = "--host" in sys.argv
    host = "0.0.0.0" if lan_mode else "127.0.0.1"

    print("\n" + "=" * 50)
    print("  Biyahero is running!")
    print("=" * 50)
    if lan_mode:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            local_ip = "<your-ip>"
        print(f"  Local:   http://127.0.0.1:5000")
        print(f"  Network: http://{local_ip}:5000")
        print("\n  Other devices on the same Wi-Fi can use the Network URL.")
    else:
        print(f"  Open:    http://127.0.0.1:5000")
        print("\n  Tip: run  python app.py --host  to share with other devices.")
    print("=" * 50)
    print("  Do NOT open HTML files with Live Server — use the URL above.")
    print("=" * 50 + "\n")

    app.run(debug=False, host=host, port=5000)
