"""
create_sample_accounts.py
--------------------------
Creates sample driver, commuter, and operator accounts
directly in the database so you can log in immediately.

Run: python create_sample_accounts.py
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "biyahero.db")

accounts = [
    # (table, values_dict)
    ("driver", {
        "fullname":            "Juan Dela Cruz",
        "contact":             "+63 917 123 4567",
        "email":               "driver@biyahero.com",
        "password":            "Driver@123",
        "municipality":        "Cebu City",
        "vehicle_type":        "Traditional Jeepney",
        "plate_number":        "GAB 1234",
        "franchise_number":    "FR-2024-001",
        "route":               "Lahug - Carbon Market",
        "terminal":            "Lahug Terminal",
        "seats":               20,
        "operating_hours_from":"06:00 AM",
        "operating_hours_to":  "09:00 PM",
        "operating_days":      "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday",
        "wheelchair_accessible": 0,
        "id_type":             "Driver's License",
        "id_number":           "N01-23-456789",
        "approval_status":     "approved",
    }),
    ("commuter", {
        "fullname": "Maya Cruz",
        "email":    "commuter@biyahero.com",
        "password": "Commuter@123",
    }),
    ("operator", {
        "fullname":     "Alicia Reyes",
        "email":        "operator@biyahero.com",
        "password":     "Operator@123",
        "contact":      "+63 922 987 6543",
        "company_name": "Cebu City Transit Cooperative",
    }),
]

db = sqlite3.connect(DB_PATH)

# ── Driver ───────────────────────────────────────────────
d = accounts[0][1]
db.execute("""
    INSERT OR IGNORE INTO drivers (
        fullname, contact, email, password_hash, municipality,
        vehicle_type, plate_number, franchise_number,
        route, terminal, seats,
        operating_hours_from, operating_hours_to, operating_days, wheelchair_accessible,
        id_type, id_number,
        id_front_path, id_back_path, or_cr_path, selfie_path, vehicle_photo_path,
        approval_status
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (
    d["fullname"], d["contact"], d["email"], generate_password_hash(d["password"]),
    d["municipality"], d["vehicle_type"], d["plate_number"], d["franchise_number"],
    d["route"], d["terminal"], d["seats"],
    d["operating_hours_from"], d["operating_hours_to"], d["operating_days"],
    d["wheelchair_accessible"], d["id_type"], d["id_number"],
    "uploads/sample.jpg", "uploads/sample.jpg",
    "uploads/sample.jpg", "uploads/sample.jpg", None,
    d["approval_status"],
))

# ── Commuter ─────────────────────────────────────────────
c = accounts[1][1]
db.execute(
    "INSERT OR IGNORE INTO commuters (fullname, email, password_hash) VALUES (?,?,?)",
    (c["fullname"], c["email"], generate_password_hash(c["password"]))
)

# ── Operator ─────────────────────────────────────────────
o = accounts[2][1]
db.execute(
    "INSERT OR IGNORE INTO operators (fullname, email, password_hash, contact, company_name) VALUES (?,?,?,?,?)",
    (o["fullname"], o["email"], generate_password_hash(o["password"]), o["contact"], o["company_name"])
)

db.commit()
db.close()

print("\n========================================")
print("  Sample accounts created successfully!")
print("========================================")
print("\nDriver")
print("  Email    : driver@biyahero.com")
print("  Password : Driver@123")
print("  Status   : Approved — goes to Driver Dashboard")
print("\nCommuter")
print("  Email    : commuter@biyahero.com")
print("  Password : Commuter@123")
print("\nOperator")
print("  Email    : operator@biyahero.com")
print("  Password : Operator@123")
print("========================================\n")
