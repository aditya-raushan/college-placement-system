"""
One-time database setup script.

What it does:
  1. Asks for your MySQL ROOT password (typed in the terminal, never saved).
  2. Runs schema.sql (WARNING: drops and recreates all tables).
  3. Creates/updates the app user from DB_USER / DB_PASSWORD in .env.
  4. Connects as the app user and runs constraint tests (rolled back).
"""
import os
import re
import sys
from getpass import getpass
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "placement_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "college_placement_db")

if DB_NAME != "college_placement_db":
    sys.exit("DB_NAME in .env must be college_placement_db (it is fixed in schema.sql).")
if not DB_PASSWORD or DB_PASSWORD.startswith("replace-with"):
    sys.exit("Set a real DB_PASSWORD in .env, save the file, and run again.")


def load_statements(path):
    """Read an SQL file and return a list of individual statements."""
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    cleaned = "\n".join(lines)
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def step_schema_and_user():
    root_pw = getpass("Enter your MySQL ROOT password (typing is hidden): ")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user="root", password=root_pw
        )
    except Error as e:
        sys.exit(f"Could not connect as root: {e}")

    cur = conn.cursor()

    cur.execute("SELECT VERSION()")
    version = cur.fetchone()[0]
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    parsed = tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    print(f"MySQL version: {version}")
    if parsed < (8, 0, 16):
        sys.exit("MySQL 8.0.16 or newer is required (CHECK constraints). Please upgrade.")

    statements = load_statements(BASE_DIR / "schema.sql")
    for stmt in statements:
        cur.execute(stmt)
    print(f"schema.sql executed ({len(statements)} statements).")

    cur.execute("CREATE USER IF NOT EXISTS %s@'localhost' IDENTIFIED BY %s",
                (DB_USER, DB_PASSWORD))
    cur.execute("ALTER USER %s@'localhost' IDENTIFIED BY %s", (DB_USER, DB_PASSWORD))
    cur.execute("GRANT ALL PRIVILEGES ON `college_placement_db`.* TO %s@'localhost'",
                (DB_USER,))
    cur.execute("FLUSH PRIVILEGES")
    conn.commit()
    print(f"App user '{DB_USER}' is ready.")
    cur.close()
    conn.close()


def step_constraint_tests():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASSWORD, database=DB_NAME,
        )
    except Error as e:
        sys.exit(f"Could not connect as {DB_USER}: {e}")

    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = sorted(r[0] for r in cur.fetchall())
    print(f"\nConnected as {DB_USER}. Tables found: {len(tables)}")
    print(tables)

    results = []

    def expect_fail(label, sql, params=()):
        try:
            cur.execute(sql, params)
            results.append(False)
            print(f"  FAIL  {label} -> was accepted but should be rejected")
        except Error as e:
            results.append(True)
            print(f"  PASS  {label} -> rejected (error {e.errno})")

    print("\nConstraint tests (everything is rolled back at the end):")
    cur.execute("INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Test Student', 'test1@example.com', 'x', 'student')")
    u1 = cur.lastrowid
    cur.execute("INSERT INTO students (user_id, usn, branch, semester, cgpa, backlogs, graduation_year) "
                "VALUES (%s, '1XX22CS001', 'CSE', 5, 8.50, 0, 2026)", (u1,))
    s1 = cur.lastrowid
    cur.execute("INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Test Two', 'test2@example.com', 'x', 'student')")
    u2 = cur.lastrowid

    expect_fail("Duplicate email",
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Dup', 'test1@example.com', 'x', 'student')")
    expect_fail("CGPA = 11 (out of range)",
                "INSERT INTO students (user_id, usn, branch, semester, cgpa, backlogs, graduation_year) "
                "VALUES (%s, '1XX22CS002', 'CSE', 5, 11.00, 0, 2026)", (u2,))
    expect_fail("Duplicate USN",
                "INSERT INTO students (user_id, usn, branch, semester, cgpa, backlogs, graduation_year) "
                "VALUES (%s, '1XX22CS001', 'CSE', 5, 7.00, 0, 2026)", (u2,))
    expect_fail("Application to a missing drive (foreign key)",
                "INSERT INTO applications (student_id, drive_id) VALUES (%s, 9999)", (s1,))
    expect_fail("Invalid role 'superadmin'",
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Hacker', 'h@example.com', 'x', 'superadmin')")

    conn.rollback()
    cur.execute("SELECT COUNT(*) FROM users")
    left = cur.fetchone()[0]
    print(f"\nUsers left after rollback: {left} (expected 0)")
    cur.close()
    conn.close()

    if all(results) and left == 0 and len(tables) == 8:
        print("\nPHASE 1 CHECKPOINT: ALL GOOD. You can say 'continue'.")
    else:
        print("\nSomething failed. Copy the output above and send it to me.")


if __name__ == "__main__":
    step_schema_and_user()
    step_constraint_tests()