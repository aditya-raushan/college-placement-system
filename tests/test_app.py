"""Automated tests. They use your REAL MySQL database (from .env) and clean up
everything they create (emails 'pytest_*@example.com', companies 'PyTest Co *').

Run from the project root with (venv) active:   pytest -v
"""
import uuid
from decimal import Decimal

import mysql.connector
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database import db_connection as dbc
from routes.admin import dashboard_stats
from routes.helpers import check_eligibility

PASSWORD = "Test@12345"


@pytest.fixture(scope="session")
def app():
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                              "SESSION_COOKIE_SECURE": False})
    yield application
    _cleanup(application)


def _cleanup(application):
    with application.app_context():
        dbc.execute("DELETE FROM users WHERE email LIKE %s", ("pytest\\_%@example.com",))
        pattern = ("PyTest Co %",)
        dbc.execute("DELETE FROM placement_drives WHERE company_id IN "
                    "(SELECT company_id FROM companies WHERE company_name LIKE %s)", pattern)
        dbc.execute("DELETE FROM companies WHERE company_name LIKE %s", pattern)


@pytest.fixture()
def client(app):
    return app.test_client()


def uid():
    return uuid.uuid4().hex[:8]


def make_user(app, role="student", cgpa="8.00", backlogs=0):
    token = uid()
    email = f"pytest_{token}@example.com"
    with app.app_context():
        user_id = dbc.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,%s)",
            (f"Test {token}", email, generate_password_hash(PASSWORD), role))
        student_id = None
        if role == "student":
            student_id = dbc.execute(
                "INSERT INTO students (user_id, usn, branch, semester, cgpa, backlogs, graduation_year) "
                "VALUES (%s,%s,'CSE',7,%s,%s,2027)", (user_id, f"PT{token}".upper(), cgpa, backlogs))
    return {"user_id": user_id, "student_id": student_id, "email": email}


def make_drive(app, min_cgpa="7.00", max_backlogs=0, status="open", days=5):
    with app.app_context():
        company_id = dbc.execute(
            "INSERT INTO companies (company_name, industry) VALUES (%s, 'Testing')",
            (f"PyTest Co {uid()}",))
        return dbc.execute(
            "INSERT INTO placement_drives (company_id, job_role, minimum_cgpa, maximum_backlogs, "
            "package_lpa, deadline, status) VALUES (%s,'Tester',%s,%s,5.00,"
            "DATE_ADD(NOW(), INTERVAL %s DAY),%s)",
            (company_id, min_cgpa, max_backlogs, days, status))


def login(client, email, password=PASSWORD):
    return client.post("/auth/login", data={"email": email, "password": password},
                       follow_redirects=False)


def query_one(app, sql, params=()):
    with app.app_context():
        return dbc.fetch_one(sql, params)


# ------------------------------------------------------------ registration / login
def test_register_and_login(app, client):
    token = uid()
    email = f"pytest_{token}@example.com"
    data = {"name": "Reg Student", "email": email, "password": PASSWORD,
            "confirm_password": PASSWORD, "usn": f"RG{token}", "branch": "CSE",
            "semester": "5", "cgpa": "8.2", "backlogs": "0", "graduation_year": "2027",
            "skills": "Python, SQL"}
    assert client.post("/auth/register", data=data).status_code == 302
    assert login(client, email).status_code == 302


def test_register_cannot_choose_admin_role(app, client):
    token = uid()
    email = f"pytest_{token}@example.com"
    data = {"name": "Sneaky", "email": email, "password": PASSWORD, "confirm_password": PASSWORD,
            "usn": f"SN{token}", "branch": "CSE", "semester": "5", "cgpa": "8", "backlogs": "0",
            "graduation_year": "2027", "role": "admin"}
    client.post("/auth/register", data=data)
    assert query_one(app, "SELECT role FROM users WHERE email=%s", (email,))["role"] == "student"


def test_register_invalid_cgpa_rejected(client):
    token = uid()
    data = {"name": "Bad Cgpa", "email": f"pytest_{token}@example.com", "password": PASSWORD,
            "confirm_password": PASSWORD, "usn": f"BC{token}", "branch": "CSE", "semester": "5",
            "cgpa": "11", "backlogs": "0", "graduation_year": "2027"}
    assert client.post("/auth/register", data=data).status_code == 400


def test_duplicate_email_and_usn_prevented(app, client):
    existing = make_user(app)
    row = query_one(app, "SELECT usn FROM students WHERE user_id=%s", (existing["user_id"],))
    base = {"name": "Dup", "password": PASSWORD, "confirm_password": PASSWORD, "branch": "CSE",
            "semester": "5", "cgpa": "8", "backlogs": "0", "graduation_year": "2027"}
    dup_email = dict(base, email=existing["email"], usn=f"X{uid()}")
    assert client.post("/auth/register", data=dup_email).status_code == 400
    dup_usn = dict(base, email=f"pytest_{uid()}@example.com", usn=row["usn"])
    assert client.post("/auth/register", data=dup_usn).status_code == 400


def test_invalid_credentials(app, client):
    user = make_user(app)
    assert login(client, user["email"], "wrong-password").status_code == 401
    assert login(client, "nobody@example.com").status_code == 401


# ------------------------------------------------------------ access control
def test_anonymous_redirected_from_admin(client):
    assert client.get("/admin/dashboard").status_code == 302


def test_student_forbidden_from_admin_pages(app, client):
    user = make_user(app)
    login(client, user["email"])
    for path in ("/admin/dashboard", "/admin/students", "/admin/companies",
                 "/admin/drives", "/admin/reports", "/applications/manage"):
        assert client.get(path).status_code == 403, path


def test_admin_can_login_and_open_dashboard(app, client):
    admin = make_user(app, role="admin")
    assert login(client, admin["email"]).status_code == 302
    assert client.get("/admin/dashboard").status_code == 200


# ------------------------------------------------------------ eligibility
def test_check_eligibility_rules():
    drive = {"minimum_cgpa": Decimal("7.5"), "maximum_backlogs": 1, "status": "open", "expired": False}
    assert check_eligibility({"cgpa": Decimal("8.0"), "backlogs": 1}, drive)[0] is True
    assert check_eligibility({"cgpa": Decimal("7.0"), "backlogs": 0}, drive)[0] is False
    assert check_eligibility({"cgpa": Decimal("9.0"), "backlogs": 2}, drive)[0] is False
    assert check_eligibility({"cgpa": Decimal("9.0"), "backlogs": 0}, dict(drive, status="closed"))[0] is False
    assert check_eligibility({"cgpa": Decimal("9.0"), "backlogs": 0}, dict(drive, expired=True))[0] is False


# ------------------------------------------------------------ applications
def test_apply_success_and_duplicate_blocked(app, client):
    user = make_user(app, cgpa="8.50")
    drive_id = make_drive(app, min_cgpa="7.00")
    login(client, user["email"])
    assert client.post(f"/applications/apply/{drive_id}").status_code == 302
    client.post(f"/applications/apply/{drive_id}")          # second attempt
    count = query_one(app, "SELECT COUNT(*) AS n FROM applications WHERE student_id=%s AND drive_id=%s",
                      (user["student_id"], drive_id))["n"]
    assert count == 1


def test_ineligible_student_cannot_apply(app, client):
    user = make_user(app, cgpa="6.00")
    drive_id = make_drive(app, min_cgpa="8.00")
    login(client, user["email"])
    client.post(f"/applications/apply/{drive_id}")
    assert query_one(app, "SELECT COUNT(*) AS n FROM applications WHERE student_id=%s",
                     (user["student_id"],))["n"] == 0


def test_closed_and_expired_drives_blocked(app, client):
    user = make_user(app)
    closed = make_drive(app, status="closed")
    expired = make_drive(app, days=-2)
    login(client, user["email"])
    client.post(f"/applications/apply/{closed}")
    client.post(f"/applications/apply/{expired}")
    assert query_one(app, "SELECT COUNT(*) AS n FROM applications WHERE student_id=%s",
                     (user["student_id"],))["n"] == 0


def test_student_cannot_update_status(app, client):
    user = make_user(app)
    drive_id = make_drive(app)
    login(client, user["email"])
    client.post(f"/applications/apply/{drive_id}")
    app_id = query_one(app, "SELECT application_id FROM applications WHERE student_id=%s",
                       (user["student_id"],))["application_id"]
    assert client.post(f"/applications/{app_id}/status", data={"status": "selected"}).status_code == 403


def test_admin_status_change_updates_results_table(app, client):
    student = make_user(app)
    admin = make_user(app, role="admin")
    drive_id = make_drive(app)
    with app.app_context():
        app_id = dbc.execute("INSERT INTO applications (student_id, drive_id) VALUES (%s,%s)",
                             (student["student_id"], drive_id))
    login(client, admin["email"])
    client.post(f"/applications/{app_id}/status", data={"status": "selected"})
    assert query_one(app, "SELECT status FROM applications WHERE application_id=%s", (app_id,))["status"] == "selected"
    assert query_one(app, "SELECT result_status FROM selection_results WHERE application_id=%s", (app_id,))["result_status"] == "selected"
    client.post(f"/applications/{app_id}/status", data={"status": "shortlisted"})
    assert query_one(app, "SELECT COUNT(*) AS n FROM selection_results WHERE application_id=%s", (app_id,))["n"] == 0
    assert client.post(f"/applications/{app_id}/status", data={"status": "bogus"}).status_code == 400


# ------------------------------------------------------------ dashboard numbers
def test_dashboard_stats_match_database(app, client):
    admin = make_user(app, role="admin")
    login(client, admin["email"])
    with app.app_context():
        stats = dashboard_stats()
        assert stats["students"] == dbc.fetch_one("SELECT COUNT(*) AS n FROM students")["n"]
        assert stats["applications"] == dbc.fetch_one("SELECT COUNT(*) AS n FROM applications")["n"]
        assert stats["companies"] == dbc.fetch_one("SELECT COUNT(*) AS n FROM companies")["n"]
    assert client.get("/admin/dashboard").status_code == 200


# ------------------------------------------------------------ SQL constraints
def test_database_constraints(app):
    user = make_user(app)
    drive_id = make_drive(app)
    with app.app_context():
        dbc.execute("INSERT INTO applications (student_id, drive_id) VALUES (%s,%s)",
                    (user["student_id"], drive_id))
        with pytest.raises(mysql.connector.Error):          # UNIQUE (student, drive)
            dbc.execute("INSERT INTO applications (student_id, drive_id) VALUES (%s,%s)",
                        (user["student_id"], drive_id))
        with pytest.raises(mysql.connector.Error):          # foreign key
            dbc.execute("INSERT INTO applications (student_id, drive_id) VALUES (%s, 999999)",
                        (user["student_id"],))
        with pytest.raises(mysql.connector.Error):          # CHECK cgpa 0..10
            dbc.execute("UPDATE students SET cgpa = 11 WHERE student_id = %s", (user["student_id"],))
        with pytest.raises(mysql.connector.Error):          # RESTRICT: drive has applications
            dbc.execute("DELETE FROM placement_drives WHERE drive_id = %s", (drive_id,))


# ------------------------------------------------------------ pages and errors
def test_landing_and_login_pages_load(client):
    assert client.get("/").status_code == 200
    assert client.get("/auth/login").status_code == 200
    assert client.get("/auth/register").status_code == 200


def test_student_pages_load(app, client):
    user = make_user(app)
    login(client, user["email"])
    for path in ("/student/dashboard", "/student/profile", "/student/drives",
                 "/applications/mine"):
        assert client.get(path).status_code == 200, path


def test_error_pages(client):
    assert client.get("/does-not-exist").status_code == 404
    assert client.get("/health").status_code in (200, 503)