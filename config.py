"""Application configuration. All secrets come from the .env file."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _flag(name, default="0"):
    """Read an on/off setting such as FLASK_DEBUG=1 from the environment."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = _flag("FLASK_DEBUG")

    # Session cookie security
    SESSION_COOKIE_HTTPONLY = True        # JavaScript cannot read the cookie
    SESSION_COOKIE_SAMESITE = "Lax"       # helps against cross-site requests
    SESSION_COOKIE_SECURE = _flag("SESSION_COOKIE_SECURE")  # set 1 only on HTTPS
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # CSRF tokens stay valid for 2 hours
    WTF_CSRF_TIME_LIMIT = 7200

    # MySQL connection settings (used by database/db_connection.py)
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME", "college_placement_db"),
        "charset": "utf8mb4",
        "connection_timeout": 5,
    }