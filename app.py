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

# ---------------------------------------------------------------------------
# Locations data  (used by /api/locations search)
# Each entry: { name, type, city, barangay, lat, lng }
# ---------------------------------------------------------------------------
LOCATIONS = [
    # ── Cebu City ──────────────────────────────────────────────────────────
    {"name": "Colon Street",            "type": "landmark",  "city": "Cebu City",      "barangay": "Parian",          "lat": 10.2978, "lng": 123.8988},
    {"name": "Carbon Market",           "type": "landmark",  "city": "Cebu City",      "barangay": "Ermita",          "lat": 10.2927, "lng": 123.9028},
    {"name": "Fuente Osmeña Circle",    "type": "landmark",  "city": "Cebu City",      "barangay": "Fuente Osmeña",   "lat": 10.3097, "lng": 123.8933},
    {"name": "SM City Cebu",            "type": "landmark",  "city": "Cebu City",      "barangay": "North Reclamation","lat": 10.3116, "lng": 123.9184},
    {"name": "Ayala Center Cebu",       "type": "landmark",  "city": "Cebu City",      "barangay": "Cebu Business Park","lat": 10.3174, "lng": 123.9054},
    {"name": "IT Park",                 "type": "landmark",  "city": "Cebu City",      "barangay": "Apas",            "lat": 10.3275, "lng": 123.9055},
    {"name": "Cebu South Bus Terminal", "type": "terminal",  "city": "Cebu City",      "barangay": "Punta Princesa",  "lat": 10.2851, "lng": 123.8820},
    {"name": "Cebu North Bus Terminal", "type": "terminal",  "city": "Cebu City",      "barangay": "North Reclamation","lat": 10.3160, "lng": 123.9190},
    {"name": "Capitol Site",            "type": "landmark",  "city": "Cebu City",      "barangay": "Capitol Site",    "lat": 10.3180, "lng": 123.8913},
    {"name": "Lahug",                   "type": "barangay",  "city": "Cebu City",      "barangay": "Lahug",           "lat": 10.3285, "lng": 123.9003},
    {"name": "Talamban",                "type": "barangay",  "city": "Cebu City",      "barangay": "Talamban",        "lat": 10.3620, "lng": 123.9120},
    {"name": "Basak",                   "type": "barangay",  "city": "Cebu City",      "barangay": "Basak Pardo",     "lat": 10.2740, "lng": 123.8760},
    {"name": "Mambaling",               "type": "barangay",  "city": "Cebu City",      "barangay": "Mambaling",       "lat": 10.2800, "lng": 123.8730},
    {"name": "Labangon",                "type": "barangay",  "city": "Cebu City",      "barangay": "Labangon",        "lat": 10.2950, "lng": 123.8800},
    {"name": "Banilad",                 "type": "barangay",  "city": "Cebu City",      "barangay": "Banilad",         "lat": 10.3350, "lng": 123.9010},
    {"name": "Guadalupe",               "type": "barangay",  "city": "Cebu City",      "barangay": "Guadalupe",       "lat": 10.3060, "lng": 123.8880},
    {"name": "Kinasang-an",             "type": "barangay",  "city": "Cebu City",      "barangay": "Kinasang-an",     "lat": 10.3420, "lng": 123.8970},
    {"name": "Mabolo",                  "type": "barangay",  "city": "Cebu City",      "barangay": "Mabolo",          "lat": 10.3240, "lng": 123.9110},
    {"name": "Sambag I",                "type": "barangay",  "city": "Cebu City",      "barangay": "Sambag I",        "lat": 10.3010, "lng": 123.8930},
    {"name": "Punta Princesa",          "type": "barangay",  "city": "Cebu City",      "barangay": "Punta Princesa",  "lat": 10.2860, "lng": 123.8830},
    {"name": "Quiot",                   "type": "barangay",  "city": "Cebu City",      "barangay": "Quiot",           "lat": 10.2680, "lng": 123.8630},
    {"name": "Sinsin",                  "type": "barangay",  "city": "Cebu City",      "barangay": "Sinsin",          "lat": 10.2900, "lng": 123.8680},

    # ── Mandaue City ───────────────────────────────────────────────────────
    {"name": "Parkmall",                "type": "landmark",  "city": "Mandaue City",   "barangay": "Tipolo",          "lat": 10.3269, "lng": 123.9348},
    {"name": "SM City Seaside",         "type": "landmark",  "city": "Mandaue City",   "barangay": "South Road Properties","lat": 10.2760, "lng": 123.8860},
    {"name": "Mandaue City Hall",       "type": "landmark",  "city": "Mandaue City",   "barangay": "Mantuyong",       "lat": 10.3250, "lng": 123.9290},
    {"name": "Tipolo",                  "type": "barangay",  "city": "Mandaue City",   "barangay": "Tipolo",          "lat": 10.3290, "lng": 123.9360},
    {"name": "Subangdaku",              "type": "barangay",  "city": "Mandaue City",   "barangay": "Subangdaku",      "lat": 10.3210, "lng": 123.9270},
    {"name": "Basak Mandaue",           "type": "barangay",  "city": "Mandaue City",   "barangay": "Basak",           "lat": 10.3180, "lng": 123.9400},
    {"name": "Cabancalan",              "type": "barangay",  "city": "Mandaue City",   "barangay": "Cabancalan",      "lat": 10.3400, "lng": 123.9300},
    {"name": "Tabok",                   "type": "barangay",  "city": "Mandaue City",   "barangay": "Tabok",           "lat": 10.3490, "lng": 123.9360},
    {"name": "Umapad",                  "type": "barangay",  "city": "Mandaue City",   "barangay": "Umapad",          "lat": 10.3560, "lng": 123.9390},

    # ── Lapu-Lapu City ─────────────────────────────────────────────────────
    {"name": "Mactan-Cebu International Airport", "type": "landmark", "city": "Lapu-Lapu City", "barangay": "Pajo", "lat": 10.3074, "lng": 123.9794},
    {"name": "Maribago",                "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Maribago",        "lat": 10.2950, "lng": 124.0110},
    {"name": "Mactan",                  "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Mactan",          "lat": 10.3060, "lng": 123.9720},
    {"name": "Basak Lapu-Lapu",         "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Basak",           "lat": 10.3020, "lng": 123.9870},
    {"name": "Pajo",                    "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Pajo",            "lat": 10.3090, "lng": 123.9820},
    {"name": "Agus",                    "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Agus",            "lat": 10.3150, "lng": 123.9960},
    {"name": "Pusok",                   "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Pusok",           "lat": 10.3110, "lng": 123.9910},
    {"name": "Gun-ob",                  "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Gun-ob",          "lat": 10.3010, "lng": 124.0020},
    {"name": "Ibo",                     "type": "barangay",  "city": "Lapu-Lapu City", "barangay": "Ibo",             "lat": 10.3200, "lng": 123.9690},

    # ── Talisay City ───────────────────────────────────────────────────────
    {"name": "Tabunok",                 "type": "barangay",  "city": "Talisay City",   "barangay": "Tabunok",         "lat": 10.2420, "lng": 123.8470},
    {"name": "Tangke",                  "type": "barangay",  "city": "Talisay City",   "barangay": "Tangke",          "lat": 10.2570, "lng": 123.8600},
    {"name": "Biasong",                 "type": "barangay",  "city": "Talisay City",   "barangay": "Biasong",         "lat": 10.2490, "lng": 123.8530},
    {"name": "Lawaan",                  "type": "barangay",  "city": "Talisay City",   "barangay": "Lawaan",          "lat": 10.2330, "lng": 123.8390},
    {"name": "Pooc",                    "type": "barangay",  "city": "Talisay City",   "barangay": "Pooc",            "lat": 10.2380, "lng": 123.8430},
    {"name": "San Isidro",              "type": "barangay",  "city": "Talisay City",   "barangay": "San Isidro",      "lat": 10.2460, "lng": 123.8510},
    {"name": "Bulacao",                 "type": "barangay",  "city": "Talisay City",   "barangay": "Bulacao",         "lat": 10.2620, "lng": 123.8640},
    {"name": "Maghaway",                "type": "barangay",  "city": "Talisay City",   "barangay": "Maghaway",        "lat": 10.2520, "lng": 123.8560},

    # ── Minglanilla ────────────────────────────────────────────────────────
    {"name": "Minglanilla Public Market","type": "landmark", "city": "Minglanilla",    "barangay": "Poblacion",       "lat": 10.2380, "lng": 123.8000},
    {"name": "Poblacion Minglanilla",   "type": "barangay",  "city": "Minglanilla",    "barangay": "Poblacion",       "lat": 10.2370, "lng": 123.7990},
    {"name": "Linao",                   "type": "barangay",  "city": "Minglanilla",    "barangay": "Linao",           "lat": 10.2440, "lng": 123.8060},
    {"name": "Tubod",                   "type": "barangay",  "city": "Minglanilla",    "barangay": "Tubod",           "lat": 10.2280, "lng": 123.7930},
    {"name": "Calajo-an",               "type": "barangay",  "city": "Minglanilla",    "barangay": "Calajo-an",       "lat": 10.2320, "lng": 123.7970},
    {"name": "Pakigne",                 "type": "barangay",  "city": "Minglanilla",    "barangay": "Pakigne",         "lat": 10.2200, "lng": 123.7870},
    {"name": "Guindaruhan",             "type": "barangay",  "city": "Minglanilla",    "barangay": "Guindaruhan",     "lat": 10.2260, "lng": 123.7920},
]


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
    q     = (request.args.get("q") or "").strip().lower()
    limit = min(int(request.args.get("limit", 10)), 30)

    if not q:
        # Return a default set when no query — useful for showing suggestions
        results = LOCATIONS[:limit]
    else:
        results = [
            loc for loc in LOCATIONS
            if q in loc["name"].lower()
            or q in loc["barangay"].lower()
            or q in loc["city"].lower()
        ][:limit]

    return jsonify({"ok": True, "results": results})


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
