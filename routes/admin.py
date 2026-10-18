"""Admin dashboard, student list, reports and CSV export."""
import csv
import io

from flask import Blueprint, Response, render_template, request

from database.db_connection import fetch_all, fetch_one
from routes.helpers import BRANCHES, role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def dashboard_stats():
    """All dashboard numbers come from the database (nothing is hardcoded)."""
    return fetch_one(
        "SELECT "
        "(SELECT COUNT(*) FROM students) AS students, "
        "(SELECT COUNT(*) FROM companies) AS companies, "
        "(SELECT COUNT(*) FROM placement_drives) AS drives, "
        "(SELECT COUNT(*) FROM placement_drives "
        " WHERE status = 'open' AND deadline > NOW()) AS open_drives, "
        "(SELECT COUNT(*) FROM applications) AS applications, "
        "(SELECT COUNT(DISTINCT student_id) FROM applications "
        " WHERE status = 'selected') AS selected_students"
    )


@bp.route("/dashboard")
@role_required("admin")
def dashboard():
    stats = dashboard_stats()
    by_status = fetch_all(
        "SELECT status, COUNT(*) AS n FROM applications GROUP BY status ORDER BY n DESC")
    recent = fetch_all(
        "SELECT a.application_id, a.status, a.applied_at, u.name AS student_name, "
        "d.job_role, c.company_name FROM applications a "
        "JOIN students s ON s.student_id = a.student_id "
        "JOIN users u ON u.user_id = s.user_id "
        "JOIN placement_drives d ON d.drive_id = a.drive_id "
        "JOIN companies c ON c.company_id = d.company_id "
        "ORDER BY a.applied_at DESC LIMIT 6")
    pct = round(100 * stats["selected_students"] / stats["students"], 1) if stats["students"] else 0
    pending = fetch_one("SELECT COUNT(*) AS n FROM applications WHERE status = 'applied'")["n"]
    closing_soon = fetch_all(
        "SELECT d.drive_id, d.job_role, d.deadline, c.company_name, "
        "(SELECT COUNT(*) FROM applications a WHERE a.drive_id = d.drive_id) AS applicants "
        "FROM placement_drives d JOIN companies c ON c.company_id = d.company_id "
        "WHERE d.status = 'open' AND d.deadline > NOW() "
        "AND d.deadline <= DATE_ADD(NOW(), INTERVAL 7 DAY) ORDER BY d.deadline LIMIT 5")
    return render_template("admin/dashboard.html", stats=stats, by_status=by_status,
                           recent=recent, placement_pct=pct, pending=pending,
                           closing_soon=closing_soon)


@bp.route("/students")
@role_required("admin")
def students():
    q = (request.args.get("q") or "").strip()[:60]
    branch = request.args.get("branch", "")
    sql = (
        "SELECT s.student_id, s.usn, u.name, u.email, s.branch, s.semester, s.cgpa, "
        "s.backlogs, s.graduation_year, "
        "(SELECT GROUP_CONCAT(k.skill_name ORDER BY k.skill_name SEPARATOR ', ') "
        " FROM student_skills k WHERE k.student_id = s.student_id) AS skills "
        "FROM students s JOIN users u ON u.user_id = s.user_id WHERE 1=1 "
    )
    params = []
    if q:
        sql += "AND (u.name LIKE %s OR s.usn LIKE %s OR u.email LIKE %s) "
        params += [f"%{q}%"] * 3
    if branch in BRANCHES:
        sql += "AND s.branch = %s "
        params.append(branch)
    sql += "ORDER BY s.usn"
    return render_template("admin/students.html", students=fetch_all(sql, tuple(params)),
                           q=q, branch=branch)


@bp.route("/reports")
@role_required("admin")
def reports():
    drive_id = request.args.get("drive_id", type=int)

    drives = fetch_all(
        "SELECT d.drive_id, d.job_role, c.company_name FROM placement_drives d "
        "JOIN companies c ON c.company_id = d.company_id ORDER BY c.company_name, d.job_role")

    # Q2: students eligible for one chosen drive (CGPA + backlog rules)
    eligible = []
    if drive_id:
        eligible = fetch_all(
            "SELECT s.usn, u.name, s.branch, s.cgpa, s.backlogs "
            "FROM students s JOIN users u ON u.user_id = s.user_id "
            "JOIN placement_drives d ON d.drive_id = %s "
            "WHERE s.cgpa >= d.minimum_cgpa AND s.backlogs <= d.maximum_backlogs "
            "ORDER BY s.cgpa DESC", (drive_id,))

    # Q4: applications per company (JOIN + COUNT + GROUP BY)
    per_company = fetch_all(
        "SELECT c.company_name, COUNT(a.application_id) AS applications "
        "FROM companies c LEFT JOIN placement_drives d ON d.company_id = c.company_id "
        "LEFT JOIN applications a ON a.drive_id = d.drive_id "
        "GROUP BY c.company_id, c.company_name ORDER BY applications DESC")

    # Q5: students above the average CGPA (subquery)
    above_avg = fetch_all(
        "SELECT s.usn, u.name, s.branch, s.cgpa FROM students s "
        "JOIN users u ON u.user_id = s.user_id "
        "WHERE s.cgpa > (SELECT AVG(cgpa) FROM students) ORDER BY s.cgpa DESC")
    avg_cgpa = fetch_one("SELECT ROUND(AVG(cgpa), 2) AS avg_cgpa FROM students")["avg_cgpa"]

    # Q8: drives with no applications (NOT EXISTS subquery)
    no_apps = fetch_all(
        "SELECT d.drive_id, c.company_name, d.job_role, d.deadline "
        "FROM placement_drives d JOIN companies c ON c.company_id = d.company_id "
        "WHERE NOT EXISTS (SELECT 1 FROM applications a WHERE a.drive_id = d.drive_id)")

    # Q7 + Q10: selected count and selection % per drive (uses a VIEW)
    selection = fetch_all(
        "SELECT * FROM v_drive_selection_report "
        "ORDER BY selection_percentage DESC, company_name")

    # Branch statistics: COUNT, AVG, MIN, MAX, GROUP BY, HAVING
    branch_stats = fetch_all(
        "SELECT branch, COUNT(*) AS students, ROUND(AVG(cgpa), 2) AS avg_cgpa, "
        "MIN(cgpa) AS min_cgpa, MAX(cgpa) AS max_cgpa "
        "FROM students GROUP BY branch HAVING COUNT(*) >= 2 ORDER BY avg_cgpa DESC")

    # Q9: student-wise placement status (VIEW)
    status_report = fetch_all("SELECT * FROM v_student_placement_status ORDER BY usn")

    return render_template("admin/reports.html", drives=drives, drive_id=drive_id,
                           eligible=eligible, per_company=per_company,
                           above_avg=above_avg, avg_cgpa=avg_cgpa, no_apps=no_apps,
                           selection=selection, branch_stats=branch_stats,
                           status_report=status_report)


@bp.route("/reports/export.csv")
@role_required("admin")
def export_csv():
    rows = fetch_all("SELECT usn, name, branch, cgpa, backlogs, total_applications, "
                     "selected_count, placement_status FROM v_student_placement_status "
                     "ORDER BY usn")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["USN", "Name", "Branch", "CGPA", "Backlogs", "Applications",
                     "Selections", "Placement status"])
    for r in rows:
        writer.writerow([r["usn"], r["name"], r["branch"], r["cgpa"], r["backlogs"],
                         r["total_applications"], r["selected_count"], r["placement_status"]])
    return Response(buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=placement_report.csv"})