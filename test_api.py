"""
test_api.py  -  Smoke test for the Biyahero API
Run:  python test_api.py
Requires the Flask server to be running: python app.py
"""
import time
import requests

BASE = "http://127.0.0.1:5000"
PASS = []
FAIL = []

# Unique emails per run so re-runs never collide with existing rows
TS             = int(time.time())
COMMUTER_EMAIL = f"ana_{TS}@biyahero.com"
DRIVER_EMAIL   = f"pedro_{TS}@biyahero.com"

def check(label, condition, detail=""):
    if condition:
        PASS.append(label)
        print(f"  PASS  {label}")
    else:
        FAIL.append(label)
        print(f"  FAIL  {label}  --  {detail}")

s = requests.Session()

# ------------------------------------------------------------------
print("\n=== Commuter signup ===")
r = s.post(f"{BASE}/api/commuter/signup",
           json={"fullname": "Ana Test", "email": COMMUTER_EMAIL, "password": "test1234"})
check("Commuter signup 200",     r.status_code == 200, r.text)
check("Commuter signup ok=true", r.json().get("ok") is True, r.text)

r2 = s.post(f"{BASE}/api/commuter/signup",
            json={"fullname": "Ana Test", "email": COMMUTER_EMAIL, "password": "test1234"})
check("Duplicate email -> 409",  r2.status_code == 409, r2.text)

# ------------------------------------------------------------------
print("\n=== Login ===")
r = s.post(f"{BASE}/api/login",
           json={"email": COMMUTER_EMAIL, "password": "test1234"})
check("Commuter login 200",    r.status_code == 200, r.text)
check("Commuter login role",   r.json().get("role") == "commuter", r.text)
check("Commuter redirect",     "/dashboard" in r.json().get("redirect", ""), r.text)

r = s.post(f"{BASE}/api/login",
           json={"email": COMMUTER_EMAIL, "password": "wrongpass"})
check("Wrong password -> 401",   r.status_code == 401, r.text)
check("Wrong password ok=false", r.json().get("ok") is False, r.text)

# ------------------------------------------------------------------
print("\n=== Driver signup (3 steps) ===")
ds = requests.Session()
r = ds.post(f"{BASE}/api/driver/signup/step1",
            json={"fullname": "Pedro Test", "contact": "+63 917 111 9999",
                  "email": DRIVER_EMAIL, "password": "driver123",
                  "municipality": "Cebu City"})
check("Driver step1 200", r.status_code == 200, r.text)

r = ds.post(f"{BASE}/api/driver/signup/step2",
            json={"vehicle-type": "Traditional Jeepney", "plate-number": f"GAB{TS % 9999:04d}",
                  "route": "Lahug - Carbon Market", "terminal": "Lahug Terminal",
                  "seats": "20", "hours-from": "06:00 AM", "hours-to": "09:00 PM",
                  "days": ["Monday", "Tuesday", "Wednesday"],
                  "wheelchair-accessible": "false"})
check("Driver step2 200", r.status_code == 200, r.text)

dummy = b"fake-image-data"
files = {
    "id-front": ("id_front.jpg", dummy, "image/jpeg"),
    "id-back":  ("id_back.jpg",  dummy, "image/jpeg"),
    "or-cr":    ("or_cr.jpg",    dummy, "image/jpeg"),
    "selfie":   ("selfie.jpg",   dummy, "image/jpeg"),
}
r = ds.post(f"{BASE}/api/driver/signup/step3",
            files=files,
            data={"id-type": "Driver's License", "id-number": f"N01-{TS}"})
check("Driver step3 200",        r.status_code == 200, r.text)
check("Driver step3 ok=true",    r.json().get("ok") is True, r.text)

r = ds.post(f"{BASE}/api/login",
            json={"email": DRIVER_EMAIL, "password": "driver123"})
check("Driver login 200",        r.status_code == 200, r.text)
check("Driver login role",       r.json().get("role") == "driver", r.text)
check("Driver pending redirect", "pending" in r.json().get("redirect", ""), r.text)

# ------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("Failed tests:", FAIL)
