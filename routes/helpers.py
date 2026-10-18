"""Shared helpers: access-control decorators, eligibility, and validation."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, redirect, request, session, url_for

from database.db_connection import fetch_one

BRANCHES = ["CSE", "ISE", "ECE", "EEE", "ME", "CE", "AIML"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USN_RE = re.compile(r"^[A-Za-z0-9]{5,20}$")


# ---------------------------------------------------------------- access control
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Server-side role check. Not logged in -> login page. Wrong role -> 403."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def home_for_role(role):
    return url_for("admin.dashboard") if role == "admin" else url_for("student.dashboard")


def current_student():
    """Student row of the logged-in user (always looked up by the SESSION user id)."""
    return fetch_one(
        "SELECT s.student_id, s.usn, s.branch, s.semester, s.cgpa, s.backlogs, "
        "s.graduation_year, u.name, u.email "
        "FROM students s JOIN users u ON u.user_id = s.user_id "
        "WHERE s.user_id = %s",
        (session["user_id"],),
    )


def safe_next(default_endpoint, **values):
    """Redirect target from a form's 'next' field; only same-site paths allowed."""
    target = request.form.get("next") or request.args.get("next") or ""
    parsed = urlparse(target)
    if target.startswith("/") and not target.startswith("//") and not parsed.netloc:
        return target
    return url_for(default_endpoint, **values)


# ---------------------------------------------------------------- eligibility
def check_eligibility(student, drive):
    """Return (is_eligible, list_of_reasons_if_not)."""
    reasons = []
    if drive["status"] != "open":
        reasons.append("Drive is closed")
    if drive.get("expired"):
        reasons.append("Deadline has passed")
    if Decimal(str(student["cgpa"])) < Decimal(str(drive["minimum_cgpa"])):
        reasons.append(f"CGPA below {drive['minimum_cgpa']}")
    if int(student["backlogs"]) > int(drive["maximum_backlogs"]):
        reasons.append(f"Backlogs above {drive['maximum_backlogs']}")
    return (len(reasons) == 0), reasons


# ---------------------------------------------------------------- validation
def parse_skills(raw):
    """'Python, SQL, python' -> ['Python', 'SQL'] (deduplicated, max 20)."""
    seen, result = set(), []
    for part in (raw or "").split(","):
        skill = " ".join(part.split())
        if skill and len(skill) <= 50 and skill.lower() not in seen:
            seen.add(skill.lower())
            result.append(skill)
    return result[:20]


def _to_decimal(value, label, low, high, errors):
    try:
        number = Decimal((value or "").strip())
    except InvalidOperation:
        errors.append(f"{label} must be a number.")
        return None
    if not (low <= number <= high):
        errors.append(f"{label} must be between {low} and {high}.")
        return None
    return number.quantize(Decimal("0.01"))


def _to_int(value, label, low, high, errors):
    try:
        number = int((value or "").strip())
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if not (low <= number <= high):
        errors.append(f"{label} must be between {low} and {high}.")
        return None
    return number


def clean_student_form(form):
    """Validate academic fields (used by registration and profile edit)."""
    errors = []
    data = {}
    usn = (form.get("usn") or "").strip().upper()
    if not USN_RE.match(usn):
        errors.append("USN must be 5-20 letters/digits with no spaces.")
    data["usn"] = usn
    branch = (form.get("branch") or "").strip()
    if branch not in BRANCHES:
        errors.append("Please choose a valid branch.")
    data["branch"] = branch
    data["semester"] = _to_int(form.get("semester"), "Semester", 1, 8, errors)
    data["cgpa"] = _to_decimal(form.get("cgpa"), "CGPA", Decimal("0"), Decimal("10"), errors)
    data["backlogs"] = _to_int(form.get("backlogs"), "Backlogs", 0, 50, errors)
    data["graduation_year"] = _to_int(form.get("graduation_year"), "Graduation year", 2000, 2100, errors)
    data["skills"] = parse_skills(form.get("skills"))
    return data, errors


def clean_password(password, confirm):
    errors = []
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors.append("Password must be at least 8 characters and contain a letter and a digit.")
    if len(password) > 128:
        errors.append("Password is too long.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors


def clean_drive_form(form, require_future_deadline):
    """Validate the placement drive form."""
    errors = []
    data = {}
    data["company_id"] = _to_int(form.get("company_id"), "Company", 1, 2**31, errors)
    role = " ".join((form.get("job_role") or "").split())
    if not (2 <= len(role) <= 100):
        errors.append("Job role must be 2-100 characters.")
    data["job_role"] = role
    data["job_description"] = (form.get("job_description") or "").strip()[:5000]
    data["minimum_cgpa"] = _to_decimal(form.get("minimum_cgpa"), "Minimum CGPA", Decimal("0"), Decimal("10"), errors)
    data["maximum_backlogs"] = _to_int(form.get("maximum_backlogs"), "Maximum backlogs", 0, 50, errors)
    data["package_lpa"] = _to_decimal(form.get("package_lpa"), "Package (LPA)", Decimal("0"), Decimal("9999"), errors)
    deadline = None
    try:
        deadline = datetime.strptime((form.get("deadline") or "").strip(), "%Y-%m-%dT%H:%M")
        if require_future_deadline and deadline <= datetime.now():
            errors.append("Deadline must be in the future.")
    except ValueError:
        errors.append("Please enter a valid deadline.")
    data["deadline"] = deadline
    status = form.get("status", "open")
    if status not in ("open", "closed"):
        errors.append("Invalid status.")
    data["status"] = status
    data["skills"] = parse_skills(form.get("skills"))
    return data, errors


def clean_company_form(form):
    errors = []
    data = {
        "company_name": " ".join((form.get("company_name") or "").split()),
        "industry": " ".join((form.get("industry") or "").split()),
        "website": (form.get("website") or "").strip(),
        "description": (form.get("description") or "").strip()[:5000],
    }
    if not (2 <= len(data["company_name"]) <= 120):
        errors.append("Company name must be 2-120 characters.")
    if not (2 <= len(data["industry"]) <= 80):
        errors.append("Industry must be 2-80 characters.")
    if data["website"]:
        if len(data["website"]) > 200 or not re.match(r"^https?://[^\s]+\.[^\s]+$", data["website"]):
            errors.append("Website must start with http:// or https:// and be a valid URL.")
    data["website"] = data["website"] or None
    data["description"] = data["description"] or None
    return data, errors