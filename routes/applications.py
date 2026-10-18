"""Applying to drives, application history, status updates and results."""
import mysql.connector
from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)

from database.db_connection import fetch_all, fetch_one, transaction
from routes.helpers import (check_eligibility, current_student, role_required,
                            safe_next)

bp = Blueprint("applications", __name__, url_prefix="/applications")

STATUSES = ("applied", "shortlisted", "selected", "rejected")


# ------------------------------------------------------------------- student
@bp.route("/apply/<int:drive_id>", methods=["POST"])
@role_required("student")
def apply(drive_id):
    student = current_student()
    drive = fetch_one(
        "SELECT drive_id, minimum_cgpa, maximum_backlogs, status, "
        "(deadline < NOW()) AS expired FROM placement_drives WHERE drive_id = %s",
        (drive_id,),
    )
    if not drive:
        abort(404)
    drive["expired"] = bool(drive["expired"])

    ok, reasons = check_eligibility(student, drive)
    if not ok:
        flash("You cannot apply: " + ", ".join(reasons) + ".", "danger")
        return redirect(url_for("student.drives"))

    try:
        with transaction() as cur:
            cur.execute("INSERT INTO applications (student_id, drive_id) VALUES (%s, %s)",
                        (student["student_id"], drive_id))
    except mysql.connector.IntegrityError as exc:
        # UNIQUE (student_id, drive_id) blocks duplicates even if two clicks race
        flash("You have already applied to this drive." if exc.errno == 1062
              else "Could not save your application.", "warning")
        return redirect(url_for("student.drives"))

    flash("Application submitted successfully.", "success")
    return redirect(url_for("applications.my_applications"))


@bp.route("/mine")
@role_required("student")
def my_applications():
    student = current_student()
    rows = fetch_all(
        "SELECT a.application_id, a.status, a.applied_at, d.job_role, d.package_lpa, "
        "c.company_name FROM applications a "
        "JOIN placement_drives d ON d.drive_id = a.drive_id "
        "JOIN companies c ON c.company_id = d.company_id "
        "WHERE a.student_id = %s ORDER BY a.applied_at DESC",
        (student["student_id"],),
    )
    return render_template("student/my_applications.html", applications=rows)


# --------------------------------------------------------------------- admin
@bp.route("/manage")
@role_required("admin")
def manage():
    drive_id = request.args.get("drive_id", type=int)
    status = request.args.get("status", "")
    q = (request.args.get("q") or "").strip()[:60]

    sql = (
        "SELECT a.application_id, a.status, a.applied_at, s.usn, u.name AS student_name, "
        "s.branch, s.cgpa, s.backlogs, d.drive_id, d.job_role, c.company_name "
        "FROM applications a "
        "JOIN students s ON s.student_id = a.student_id "
        "JOIN users u ON u.user_id = s.user_id "
        "JOIN placement_drives d ON d.drive_id = a.drive_id "
        "JOIN companies c ON c.company_id = d.company_id WHERE 1=1 "
    )
    params = []
    if drive_id:
        sql += "AND a.drive_id = %s "
        params.append(drive_id)
    if status in STATUSES:
        sql += "AND a.status = %s "
        params.append(status)
    if q:
        sql += "AND (u.name LIKE %s OR s.usn LIKE %s) "
        params += [f"%{q}%", f"%{q}%"]
    sql += "ORDER BY a.applied_at DESC"

    drives = fetch_all(
        "SELECT d.drive_id, d.job_role, c.company_name FROM placement_drives d "
        "JOIN companies c ON c.company_id = d.company_id ORDER BY c.company_name, d.job_role"
    )
    return render_template("admin/applications.html",
                           applications=fetch_all(sql, tuple(params)), drives=drives,
                           drive_id=drive_id, status=status, q=q, statuses=STATUSES)


@bp.route("/<int:application_id>/status", methods=["POST"])
@role_required("admin")
def update_status(application_id):
    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        abort(400)
    try:
        # Two related tables change together: applications + selection_results.
        with transaction() as cur:
            cur.execute("SELECT application_id FROM applications "
                        "WHERE application_id = %s FOR UPDATE", (application_id,))
            if cur.fetchone() is None:
                abort(404)
            cur.execute("UPDATE applications SET status = %s WHERE application_id = %s",
                        (new_status, application_id))
            if new_status in ("selected", "rejected"):
                cur.execute(
                    "INSERT INTO selection_results (application_id, result_status) "
                    "VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE result_status = VALUES(result_status)",
                    (application_id, new_status),
                )
            else:
                cur.execute("DELETE FROM selection_results WHERE application_id = %s",
                            (application_id,))
    except mysql.connector.Error:
        flash("Could not update the status. No changes were saved.", "danger")
        return redirect(safe_next("applications.manage"))
    flash(f"Application marked as {new_status}.", "success")
    return redirect(safe_next("applications.manage"))


@bp.route("/results")
@role_required("admin")
def results():
    result_status = request.args.get("result", "")
    sql = (
        "SELECT r.result_id, r.result_status, r.updated_at, s.usn, u.name AS student_name, "
        "s.branch, d.job_role, d.package_lpa, c.company_name "
        "FROM selection_results r "
        "JOIN applications a ON a.application_id = r.application_id "
        "JOIN students s ON s.student_id = a.student_id "
        "JOIN users u ON u.user_id = s.user_id "
        "JOIN placement_drives d ON d.drive_id = a.drive_id "
        "JOIN companies c ON c.company_id = d.company_id "
    )
    params = ()
    if result_status in ("selected", "rejected"):
        sql += "WHERE r.result_status = %s "
        params = (result_status,)
    sql += "ORDER BY r.updated_at DESC"
    per_drive = fetch_all(
        "SELECT c.company_name, d.job_role, "
        "COUNT(r.result_id) AS decided, "
        "COALESCE(SUM(r.result_status = 'selected'), 0) AS selected "
        "FROM placement_drives d JOIN companies c ON c.company_id = d.company_id "
        "LEFT JOIN applications a ON a.drive_id = d.drive_id "
        "LEFT JOIN selection_results r ON r.application_id = a.application_id "
        "GROUP BY d.drive_id, c.company_name, d.job_role "
        "HAVING COUNT(r.result_id) > 0 ORDER BY selected DESC"
    )
    return render_template("admin/results.html", results=fetch_all(sql, params),
                           per_drive=per_drive, result_status=result_status)