"""
init_db.py
----------
Creates (or re-uses) the biyahero.db SQLite database and applies
the schema defined in schema.sql.

Run from the project root:
    python database/init_db.py
"""

import sqlite3
import os

# Resolve paths relative to this script's location
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "biyahero.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def init_database():
    print(f"Database path : {DB_PATH}")
    print(f"Schema path   : {SCHEMA_PATH}")

    # Read SQL schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Connect (creates the file if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Apply schema
    cursor.executescript(schema_sql)
    conn.commit()

    # Verify tables were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    conn.close()

    print("\nTables created successfully:")
    for table in tables:
        print(f"  ✓ {table}")
    print("\nbiyahero.db is ready.")


if __name__ == "__main__":
    init_database()
