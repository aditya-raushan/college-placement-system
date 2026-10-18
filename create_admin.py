"""Create the FIRST admin account securely.

Run:  python create_admin.py
The password is typed in the terminal (hidden), validated, hashed and stored.
"""
import re
import sys
from getpass import getpass

import mysql.connector
from werkzeug.security import generate_password_hash

from config import Config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main():
    name = " ".join(input("Admin full name: ").split())
    email = input("Admin email: ").strip().lower()
    if not (2 <= len(name) <= 100):
        sys.exit("Name must be 2-100 characters.")
    if not EMAIL_RE.match(email) or len(email) > 120:
        sys.exit("Invalid email address.")

    password = getpass("Admin password (hidden, min 12 chars): ")
    again = getpass("Repeat password: ")
    if password != again:
        sys.exit("Passwords do not match.")
    if len(password) < 12 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        sys.exit("Use at least 12 characters with letters and digits.")

    try:
        conn = mysql.connector.connect(**Config.DB_CONFIG)
    except mysql.connector.Error as exc:
        sys.exit(f"Cannot connect to MySQL: {exc}")
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        print(f"Admin account created for {email}.")
    except mysql.connector.IntegrityError:
        conn.rollback()
        sys.exit("A user with this email already exists.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()