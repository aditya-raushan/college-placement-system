"""MySQL connection helpers. Every query uses %s placeholders (parameterized)."""
from contextlib import contextmanager

import mysql.connector
from flask import current_app, g


def get_db():
    """Return the MySQL connection for the current request (opened on first use)."""
    if "db" not in g:
        g.db = mysql.connector.connect(**current_app.config["DB_CONFIG"])
    return g.db


def close_db(exception=None):
    """Close the connection at the end of the request (registered in app.py)."""
    db = g.pop("db", None)
    if db is not None and db.is_connected():
        db.close()


def fetch_all(sql, params=()):
    """Run a SELECT and return all rows as a list of dictionaries."""
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row as a dictionary (or None)."""
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()


def execute(sql, params=()):
    """Run one INSERT/UPDATE/DELETE, commit it, and return the new row id.

    On failure the change is rolled back and the error is raised again.
    """
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(sql, params)
        db.commit()
        return cur.lastrowid
    except mysql.connector.Error:
        db.rollback()
        raise
    finally:
        cur.close()


@contextmanager
def transaction():
    """Group several statements: all succeed (commit) or all fail (rollback).

    Usage:
        with transaction() as cur:
            cur.execute(...)
            cur.execute(...)
    """
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        yield cur
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()


def check_connection():
    """Used by /health. Returns basic information about the database."""
    info = fetch_one("SELECT VERSION() AS version, DATABASE() AS db_name")
    count = fetch_one(
        "SELECT COUNT(*) AS n FROM information_schema.tables "
        "WHERE table_schema = DATABASE()"
    )
    return {
        "mysql_version": info["version"],
        "database": info["db_name"],
        "table_count": count["n"],
    }