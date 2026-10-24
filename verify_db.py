"""
verify_db.py
Directly tests the database INSERT/SELECT logic without needing Flask.
Run: python verify_db.py
"""
import sqlite3
import os
import time
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "biyahero.db")
PASS = []
FAIL = []
TS   = int(time.time())

def check(label, condition, detail=""):
    if condition:
        PASS.append(label)
        print(f"  PASS  {label}")
    else:
        FAIL.append(label)
        print(f"  FAIL  {label}  -- {detail}")

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row

print("\n=== Commuter INSERT ===")
email_c = f"verify_c_{TS}@biyahero.com"
db.execute(
    "INSERT INTO commuters (fullname, email, password_hash) VALUES (?, ?, ?)",
    ("Verify Commuter", email_c, generate_password_hash("pass1234"))
)
db.commit()
row = db.execute("SELECT * FROM commuters WHERE email=?", (email_c,)).fetchone()
check("Commuter row exists",       row is not None)
check("Commuter fullname correct", row and row["fullname"] == "Verify Commuter")
check("Commuter password hashed",  row and row["password_hash"].startswith("scrypt:") or (row and "pbkdf2" in row["password_hash"]))
check("Commuter password verifies", row and check_password_hash(row["password_hash"], "pass1234"))

print("\n=== Driver INSERT ===")
email_d = f"verify_d_{TS}@biyahero.com"
db.execute("""
    INSERT INTO drivers (
        fullname, contact, email, password_hash, municipality,
        vehicle_type, plate_number, franchise_number,
        route, terminal, seats,
        operating_hours_from, operating_hours_to, operating_days, wheelchair_accessible,
        id_type, id_number,
        id_front_path, id_back_path, or_cr_path, selfie_path, vehicle_photo_path,
        approval_status
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (
    "Verify Driver", "+63 917 000 0000", email_d, generate_password_hash("drv1234"), "Cebu City",
    "Traditional Jeepney", "TST 0001", None,
    "Lahug - Carbon Market", "Lahug Terminal", 20,
    "06:00 AM", "09:00 PM", "Monday,Tuesday,Wednesday,Thursday,Friday", 0,
    "Driver's License", "N01-00-000001",
    "uploads/id_front.jpg", "uploads/id_back.jpg", "uploads/or_cr.jpg", "uploads/selfie.jpg", None,
    "pending"
))
db.commit()
row = db.execute("SELECT * FROM drivers WHERE email=?", (email_d,)).fetchone()
check("Driver row exists",            row is not None)
check("Driver fullname correct",      row and row["fullname"] == "Verify Driver")
check("Driver vehicle_type correct",  row and row["vehicle_type"] == "Traditional Jeepney")
check("Driver route correct",         row and row["route"] == "Lahug - Carbon Market")
check("Driver operating_days stored", row and "Monday" in row["operating_days"])
check("Driver approval pending",      row and row["approval_status"] == "pending")
check("Driver password verifies",     row and check_password_hash(row["password_hash"], "drv1234"))

print("\n=== Operator INSERT ===")
email_o = f"verify_o_{TS}@biyahero.com"
db.execute(
    "INSERT INTO operators (fullname, email, password_hash, company_name) VALUES (?,?,?,?)",
    ("Verify Operator", email_o, generate_password_hash("op12345"), "Cebu Metro Transit")
)
db.commit()
row = db.execute("SELECT * FROM operators WHERE email=?", (email_o,)).fetchone()
check("Operator row exists",      row is not None)
check("Operator is_active=1",     row and row["is_active"] == 1)
check("Operator company stored",  row and row["company_name"] == "Cebu Metro Transit")

print("\n=== Cleanup ===")
db.execute("DELETE FROM commuters WHERE email LIKE 'verify_%'")
db.execute("DELETE FROM drivers   WHERE email LIKE 'verify_%'")
db.execute("DELETE FROM operators WHERE email LIKE 'verify_%'")
db.commit()
db.close()
print("  Test rows removed.")

print(f"\n{'='*40}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("Failed:", FAIL)
else:
    print("All checks passed. Database is working correctly.")
