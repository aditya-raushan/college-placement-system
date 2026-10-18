"""Student dashboard, profile and the eligibility-aware drive listing."""
from datetime import datetime

from datetime import datetime

import mysql.connector
from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

from database.db_connection import fetch_all, fetch_one, transaction
from routes.helpers import (check_eligibility, clean_student_form,
                            current_student, role_required)

bp = Blueprint("student", __name__, url_prefix="/student")


def _skills_of(student_id):
    rows = fetch_all(
        "SELECT skill_name FROM student_skills WHERE student_id = %s ORDER BY skill_name",
        (student_id,),
    )
    return [r["skill_name"] for r in rows]


def load_drives_for(student, search="", only_eligible=False):
    """Open drives with eligibility info for ONE student."""
    sql = (
        "SELECT d.drive_id, d.job_role, d.job_description, d.minimum_cgpa, "
        "d.maximum_backlogs, d.package_lpa, d.deadline, d.status, "
        "c.company_name, c.industry, (d.deadline < NOW()) AS expired, "
        "(SELECT GROUP_CONCAT(ds.skill_name ORDER BY ds.skill_name SEPARATOR ', ') "
        " FROM drive_skills ds WHERE ds.drive_id = d.drive_id) AS skills, "
        "a.status AS my_status "
        "FROM placement_drives d "
        "JOIN companies c ON c.company_id = d.company_id "
        "LEFT JOIN applications a ON a.drive_id = d.drive_id AND a.student_id = %s "
        "WHERE d.status = 'open' "
    )
    params = [student["student_id"]]
    if search:
        sql += "AND (c.company_name LIKE %s OR d.job_role LIKE %s) "
        like = f"%{search}%"
        params += [like, like]
    sql += "ORDER BY d.deadline ASC"
    drives = fetch_all(sql, tuple(params))

    my_skills = {s.lower() for s in _skills_of(student["student_id"])}
    result = []
    for d in drives:
        d["expired"] = bool(d["expired"])
        delta = d["deadline"] - datetime.now()
        d["days_left"] = delta.days if delta.total_seconds() > 0 else 0
        ok, reasons = check_eligibility(student, d)
        d["eligible"], d["reasons"] = ok, reasons
        needed = [s.strip() for s in (d["skills"] or "").split(",") if s.strip()]
        d["missing_skills"] = [s for s in needed if s.lower() not in my_skills]
        d["can_apply"] = ok and d["my_status"] is None
        if only_eligible and not ok:
            continue
        result.append(d)
    return result


@bp.route("/dashboard")
@role_required("student")
def dashboard():
    student = current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("index"))
    counts = fetch_one(
        "SELECT COUNT(*) AS total, "
        "COALESCE(SUM(status = 'shortlisted'), 0) AS shortlisted, "
        "COALESCE(SUM(status = 'selected'), 0) AS selected, "
        "COALESCE(SUM(status = 'rejected'), 0) AS rejected "
        "FROM applications WHERE student_id = %s",
        (student["student_id"],),
    )
    drives = load_drives_for(student)
    eligible_open = sum(1 for d in drives if d["can_apply"])
    upcoming = [d for d in drives if d["can_apply"]][:3]   # already sorted by deadline
    recent = fetch_all(
        "SELECT a.application_id, a.status, a.applied_at, d.job_role, c.company_name "
        "FROM applications a "
        "JOIN placement_drives d ON d.drive_id = a.drive_id "
        "JOIN companies c ON c.company_id = d.company_id "
        "WHERE a.student_id = %s ORDER BY a.applied_at DESC LIMIT 5",
        (student["student_id"],),
    )
    return render_template("student/dashboard.html", student=student, counts=counts,
                           eligible_open=eligible_open, recent=recent,
                           upcoming=upcoming)


@bp.route("/profile", methods=["GET", "POST"])
@role_required("student")
def profile():
    student = current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, errors = clean_student_form(request.form)
        name = " ".join((request.form.get("name") or "").split())
        if not (2 <= len(name) <= 100):
            errors.append("Name must be 2-100 characters.")
        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("student/profile.html", student=student,
                                   skills=request.form.get("skills", ""),
                                   form=request.form), 400
        try:
            with transaction() as cur:
                # Always updates the rows that belong to the logged-in user
                cur.execute("UPDATE users SET name = %s WHERE user_id = %s",
                            (name, session["user_id"]))
                cur.execute(
                    "UPDATE students SET usn=%s, branch=%s, semester=%s, cgpa=%s, "
                    "backlogs=%s, graduation_year=%s WHERE student_id=%s",
                    (data["usn"], data["branch"], data["semester"], data["cgpa"],
                     data["backlogs"], data["graduation_year"], student["student_id"]),
                )
                cur.execute("DELETE FROM student_skills WHERE student_id = %s",
                            (student["student_id"],))
                if data["skills"]:
                    cur.executemany(
                        "INSERT INTO student_skills (student_id, skill_name) VALUES (%s, %s)",
                        [(student["student_id"], s) for s in data["skills"]],
                    )
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                flash("This USN is already used by another student.", "danger")
            else:
                flash("Some of the data was rejected by the database.", "danger")
            return render_template("student/profile.html", student=student,
                                   skills=request.form.get("skills", ""),
                                   form=request.form), 400
        session["name"] = name
        flash("Profile updated.", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", student=student,
                           skills=", ".join(_skills_of(student["student_id"])), form=None)


@bp.route("/drives")
@role_required("student")
def drives():
    student = current_student()
    search = (request.args.get("q") or "").strip()[:60]
    only_eligible = request.args.get("eligible") == "1"
    drive_list = load_drives_for(student, search, only_eligible)
    return render_template("student/drives.html", drives=drive_list, student=student,
                           q=search, only_eligible=only_eligible)