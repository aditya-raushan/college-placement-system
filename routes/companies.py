"""Admin: company management and placement drive management."""
import mysql.connector
from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)

from database.db_connection import execute, fetch_all, fetch_one, transaction
from routes.helpers import clean_company_form, clean_drive_form, role_required

bp = Blueprint("companies", __name__, url_prefix="/admin")


# ------------------------------------------------------------------ companies
@bp.route("/companies")
@role_required("admin")
def list_companies():
    q = (request.args.get("q") or "").strip()[:60]
    sql = (
        "SELECT c.company_id, c.company_name, c.industry, c.website, "
        "COUNT(d.drive_id) AS drive_count "
        "FROM companies c LEFT JOIN placement_drives d ON d.company_id = c.company_id "
    )
    params = ()
    if q:
        sql += "WHERE c.company_name LIKE %s OR c.industry LIKE %s "
        params = (f"%{q}%", f"%{q}%")
    sql += "GROUP BY c.company_id, c.company_name, c.industry, c.website ORDER BY c.company_name"
    return render_template("admin/companies.html", companies=fetch_all(sql, params), q=q)


@bp.route("/companies/add", methods=["GET", "POST"])
@role_required("admin")
def add_company():
    if request.method == "POST":
        data, errors = clean_company_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/company_form.html", company=request.form, mode="add"), 400
        try:
            execute(
                "INSERT INTO companies (company_name, industry, website, description) "
                "VALUES (%s, %s, %s, %s)",
                (data["company_name"], data["industry"], data["website"], data["description"]),
            )
        except mysql.connector.IntegrityError as exc:
            flash("A company with this name already exists." if exc.errno == 1062
                  else "The database rejected this data.", "danger")
            return render_template("admin/company_form.html", company=request.form, mode="add"), 400
        flash("Company added.", "success")
        return redirect(url_for("companies.list_companies"))
    return render_template("admin/company_form.html", company={}, mode="add")


@bp.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_company(company_id):
    company = fetch_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    if not company:
        abort(404)
    if request.method == "POST":
        data, errors = clean_company_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/company_form.html", company=request.form,
                                   mode="edit", company_id=company_id), 400
        try:
            execute(
                "UPDATE companies SET company_name=%s, industry=%s, website=%s, "
                "description=%s WHERE company_id=%s",
                (data["company_name"], data["industry"], data["website"],
                 data["description"], company_id),
            )
        except mysql.connector.IntegrityError as exc:
            flash("A company with this name already exists." if exc.errno == 1062
                  else "The database rejected this data.", "danger")
            return render_template("admin/company_form.html", company=request.form,
                                   mode="edit", company_id=company_id), 400
        flash("Company updated.", "success")
        return redirect(url_for("companies.list_companies"))
    return render_template("admin/company_form.html", company=company,
                           mode="edit", company_id=company_id)


@bp.route("/companies/<int:company_id>/delete", methods=["POST"])
@role_required("admin")
def delete_company(company_id):
    try:
        execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
        flash("Company deleted.", "success")
    except mysql.connector.IntegrityError:
        # ON DELETE RESTRICT: the company still has placement drives
        flash("Cannot delete: this company has placement drives. Delete/close them first.", "danger")
    return redirect(url_for("companies.list_companies"))


# --------------------------------------------------------------------- drives
def _company_choices():
    return fetch_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


@bp.route("/drives")
@role_required("admin")
def list_drives():
    q = (request.args.get("q") or "").strip()[:60]
    status = request.args.get("status", "")
    sql = (
        "SELECT d.drive_id, d.job_role, d.minimum_cgpa, d.maximum_backlogs, "
        "d.package_lpa, d.deadline, d.status, c.company_name, "
        "(d.deadline < NOW()) AS expired, "
        "(SELECT COUNT(*) FROM applications a WHERE a.drive_id = d.drive_id) AS applicants "
        "FROM placement_drives d JOIN companies c ON c.company_id = d.company_id WHERE 1=1 "
    )
    params = []
    if q:
        sql += "AND (c.company_name LIKE %s OR d.job_role LIKE %s) "
        params += [f"%{q}%", f"%{q}%"]
    if status in ("open", "closed"):
        sql += "AND d.status = %s "
        params.append(status)
    sql += "ORDER BY d.deadline DESC"
    return render_template("admin/drives.html", drives=fetch_all(sql, tuple(params)),
                           q=q, status=status)


def _save_skills(cur, drive_id, skills):
    cur.execute("DELETE FROM drive_skills WHERE drive_id = %s", (drive_id,))
    if skills:
        cur.executemany("INSERT INTO drive_skills (drive_id, skill_name) VALUES (%s, %s)",
                        [(drive_id, s) for s in skills])


@bp.route("/drives/add", methods=["GET", "POST"])
@role_required("admin")
def add_drive():
    companies = _company_choices()
    if request.method == "POST":
        data, errors = clean_drive_form(request.form, require_future_deadline=True)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/drive_form.html", drive=request.form,
                                   companies=companies, mode="add"), 400
        try:
            with transaction() as cur:
                cur.execute(
                    "INSERT INTO placement_drives (company_id, job_role, job_description, "
                    "minimum_cgpa, maximum_backlogs, package_lpa, deadline, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (data["company_id"], data["job_role"], data["job_description"],
                     data["minimum_cgpa"], data["maximum_backlogs"], data["package_lpa"],
                     data["deadline"], data["status"]),
                )
                _save_skills(cur, cur.lastrowid, data["skills"])
        except mysql.connector.IntegrityError:
            flash("The database rejected this data (is the company valid?).", "danger")
            return render_template("admin/drive_form.html", drive=request.form,
                                   companies=companies, mode="add"), 400
        flash("Placement drive created.", "success")
        return redirect(url_for("companies.list_drives"))
    return render_template("admin/drive_form.html", drive={"status": "open"},
                           companies=companies, mode="add")


@bp.route("/drives/<int:drive_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_drive(drive_id):
    drive = fetch_one("SELECT * FROM placement_drives WHERE drive_id = %s", (drive_id,))
    if not drive:
        abort(404)
    companies = _company_choices()
    if request.method == "POST":
        data, errors = clean_drive_form(request.form, require_future_deadline=False)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/drive_form.html", drive=request.form,
                                   companies=companies, mode="edit", drive_id=drive_id), 400
        try:
            with transaction() as cur:
                cur.execute(
                    "UPDATE placement_drives SET company_id=%s, job_role=%s, "
                    "job_description=%s, minimum_cgpa=%s, maximum_backlogs=%s, "
                    "package_lpa=%s, deadline=%s, status=%s WHERE drive_id=%s",
                    (data["company_id"], data["job_role"], data["job_description"],
                     data["minimum_cgpa"], data["maximum_backlogs"], data["package_lpa"],
                     data["deadline"], data["status"], drive_id),
                )
                _save_skills(cur, drive_id, data["skills"])
        except mysql.connector.IntegrityError:
            flash("The database rejected this data.", "danger")
            return render_template("admin/drive_form.html", drive=request.form,
                                   companies=companies, mode="edit", drive_id=drive_id), 400
        flash("Placement drive updated.", "success")
        return redirect(url_for("companies.list_drives"))

    skills = fetch_all("SELECT skill_name FROM drive_skills WHERE drive_id = %s "
                       "ORDER BY skill_name", (drive_id,))
    drive["skills"] = ", ".join(r["skill_name"] for r in skills)
    drive["deadline"] = drive["deadline"].strftime("%Y-%m-%dT%H:%M")
    return render_template("admin/drive_form.html", drive=drive, companies=companies,
                           mode="edit", drive_id=drive_id)


@bp.route("/drives/<int:drive_id>/close", methods=["POST"])
@role_required("admin")
def close_drive(drive_id):
    execute("UPDATE placement_drives SET status = 'closed' WHERE drive_id = %s", (drive_id,))
    flash("Drive closed. Students can no longer apply.", "success")
    return redirect(url_for("companies.list_drives"))


@bp.route("/drives/<int:drive_id>/delete", methods=["POST"])
@role_required("admin")
def delete_drive(drive_id):
    try:
        execute("DELETE FROM placement_drives WHERE drive_id = %s", (drive_id,))
        flash("Drive deleted.", "success")
    except mysql.connector.IntegrityError:
        flash("Cannot delete a drive that has applications. Close it instead.", "danger")
    return redirect(url_for("companies.list_drives"))