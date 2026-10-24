"""
app.py  —  Biyahero Flask Backend
===================================
Serves all HTML pages and exposes API endpoints that store
signup / login data in the SQLite database (database/biyahero.db).

Run:
    pip install flask werkzeug
    python app.py
"""

import os
import sqlite3
from flask import (
    Flask, request, jsonify, send_from_directory, session, redirect, url_for
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
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024  # 10 MB upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Return a new SQLite connection with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Use DELETE journal mode instead of WAL — avoids lock contention
    # when multiple connections open the file concurrently (e.g. tests).
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA busy_timeout=8000")
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


def save_upload(file_field_name):
    """
    Save an uploaded file and return its relative path.
    Returns None if the field is missing or empty.
    """
    f = request.files.get(file_field_name)
    if not f or f.filename == "":
        return None
    if not allowed_file(f.filename):
        return None
    filename = secure_filename(f.filename)
    dest = os.path.join(UPLOAD_FOLDER, filename)
    f.save(dest)
    return os.path.join("uploads", filename).replace("\\", "/")


# ---------------------------------------------------------------------------
# Static file serving  (HTML, CSS, JS, images)
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


@app.route("/api/<path:filename>")
def serve_api_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, "api"), filename)


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

    # Basic validation
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
#
#   Step 1  POST /api/driver/signup/step1   personal info   → stores in session
#   Step 2  POST /api/driver/signup/step2   vehicle & route → stores in session
#   Step 3  POST /api/driver/signup/step3   documents       → saves to DB
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

    # Check if email already registered
    db = get_db()
    existing = db.execute("SELECT id FROM drivers WHERE email = ?", (email,)).fetchone()
    db.close()
    if existing:
        return jsonify({"ok": False, "error": "An account with that email already exists."}), 409

    # Persist step data in server-side session
    session["driver_step1"] = {
        "fullname":     fullname,
        "contact":      contact,
        "email":        email,
        "password":     password,   # will be hashed at final insert
        "municipality": municipality,
    }
    return jsonify({"ok": True, "message": "Step 1 saved. Proceed to step 2."})


@app.route("/api/driver/signup/step2", methods=["POST"])
def driver_signup_step2():
    if "driver_step1" not in session:
        return jsonify({"ok": False, "error": "Step 1 not completed. Please start from the beginning."}), 400

    data = request.get_json(silent=True) or request.form

    vehicle_type         = (data.get("vehicle-type")          or "").strip()
    plate_number         = (data.get("plate-number")          or "").strip()
    franchise_number     = (data.get("franchise-number")      or "").strip() or None
    route                = (data.get("route")                 or "").strip()
    terminal             = (data.get("terminal")              or "").strip()
    seats                = data.get("seats", "").strip() if hasattr(data.get("seats", ""), "strip") else str(data.get("seats", ""))
    hours_from           = (data.get("hours-from")            or "").strip()
    hours_to             = (data.get("hours-to")              or "").strip()
    # operating days can be multi-value (checkboxes) or comma-separated from JSON
    days_raw             = request.form.getlist("days") or []
    if not days_raw:
        days_raw = data.get("days") or []
    if isinstance(days_raw, str):
        days_raw = [d.strip() for d in days_raw.split(",") if d.strip()]
    operating_days       = ",".join(days_raw)
    wheelchair           = 1 if data.get("wheelchair-accessible") in ("on", "true", "1", True) else 0

    if not all([vehicle_type, plate_number, route, terminal, seats, hours_from, hours_to, operating_days]):
        return jsonify({"ok": False, "error": "All required fields must be filled."}), 400

    try:
        seats = int(seats)
    except ValueError:
        return jsonify({"ok": False, "error": "Seats must be a number."}), 400

    session["driver_step2"] = {
        "vehicle_type":          vehicle_type,
        "plate_number":          plate_number,
        "franchise_number":      franchise_number,
        "route":                 route,
        "terminal":              terminal,
        "seats":                 seats,
        "operating_hours_from":  hours_from,
        "operating_hours_to":    hours_to,
        "operating_days":        operating_days,
        "wheelchair_accessible": wheelchair,
    }
    return jsonify({"ok": True, "message": "Step 2 saved. Proceed to step 3."})


@app.route("/api/driver/signup/step3", methods=["POST"])
def driver_signup_step3():
    if "driver_step1" not in session or "driver_step2" not in session:
        return jsonify({"ok": False, "error": "Previous steps not completed. Please start from the beginning."}), 400

    data = request.form   # step 3 has file uploads, must use multipart form

    id_type   = (data.get("id-type")   or "").strip()
    id_number = (data.get("id-number") or "").strip()

    if not id_type or not id_number:
        return jsonify({"ok": False, "error": "ID type and ID number are required."}), 400

    # Save uploaded files
    id_front_path    = save_upload("id-front")
    id_back_path     = save_upload("id-back")
    or_cr_path       = save_upload("or-cr")
    selfie_path      = save_upload("selfie")
    vehicle_photo    = save_upload("vehicle-photo")   # optional

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
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                'pending'
            )
        """, (
            s1["fullname"], s1["contact"], s1["email"], pw_hash, s1["municipality"],
            s2["vehicle_type"], s2["plate_number"], s2["franchise_number"],
            s2["route"], s2["terminal"], s2["seats"],
            s2["operating_hours_from"], s2["operating_hours_to"], s2["operating_days"], s2["wheelchair_accessible"],
            id_type, id_number,
            id_front_path, id_back_path, or_cr_path, selfie_path, vehicle_photo,
        ))
        db.commit()
        db.close()
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "An account with that email already exists."}), 409

    # Clear wizard session data
    session.pop("driver_step1", None)
    session.pop("driver_step2", None)

    return jsonify({"ok": True, "message": "Application submitted! Redirecting to login…"})


# ---------------------------------------------------------------------------
# LOGIN  —  POST /api/login
# Checks commuters, drivers, and operators tables in order.
# ---------------------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or request.form
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password are required."}), 400

    db = get_db()

    # 1. Check commuters
    row = db.execute("SELECT id, password_hash FROM commuters WHERE email = ?", (email,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        db.close()
        return jsonify({"ok": True, "role": "commuter", "redirect": "/html/dashboard.html"})

    # 2. Check drivers
    row = db.execute(
        "SELECT id, password_hash, approval_status FROM drivers WHERE email = ?", (email,)
    ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        db.close()
        status = row["approval_status"]
        if status == "pending":
            return jsonify({"ok": True, "role": "driver", "redirect": "/html/pending-approval.html"})
        if status == "declined":
            return jsonify({"ok": True, "role": "driver", "redirect": "/html/declined.html"})
        return jsonify({"ok": True, "role": "driver", "redirect": "/html/driver-dashboard.html"})

    # 3. Check operators
    row = db.execute("SELECT id, password_hash FROM operators WHERE email = ?", (email,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        db.close()
        return jsonify({"ok": True, "role": "operator", "redirect": "/html/operator-dashboard.html"})

    db.close()
    return jsonify({"ok": False, "error": "Email address or password is incorrect."}), 401


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, port=5000)
