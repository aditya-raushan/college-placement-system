"""Registration, login and logout."""
import mysql.connector
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db_connection import fetch_one, transaction
from routes.helpers import (EMAIL_RE, clean_password, clean_student_form,
                            home_for_role)

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(home_for_role(session.get("role")))

    if request.method == "POST":
        name = " ".join((request.form.get("name") or "").split())
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        data, errors = clean_student_form(request.form)
        if not (2 <= len(name) <= 100):
            errors.append("Name must be 2-100 characters.")
        if not EMAIL_RE.match(email) or len(email) > 120:
            errors.append("Please enter a valid email address.")
        errors += clean_password(password, confirm)

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("register.html", form=request.form), 400

        try:
            # One transaction: user + student + skills are saved together or not at all.
            # The role is ALWAYS 'student' here; it is never read from the form.
            with transaction() as cur:
                cur.execute(
                    "INSERT INTO users (name, email, password_hash, role) "
                    "VALUES (%s, %s, %s, 'student')",
                    (name, email, generate_password_hash(password)),
                )
                user_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO students (user_id, usn, branch, semester, cgpa, "
                    "backlogs, graduation_year) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (user_id, data["usn"], data["branch"], data["semester"],
                     data["cgpa"], data["backlogs"], data["graduation_year"]),
                )
                student_id = cur.lastrowid
                if data["skills"]:
                    cur.executemany(
                        "INSERT INTO student_skills (student_id, skill_name) VALUES (%s, %s)",
                        [(student_id, s) for s in data["skills"]],
                    )
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062 and "usn" in str(exc.msg).lower():
                flash("This USN is already registered.", "danger")
            elif exc.errno == 1062:
                flash("This email is already registered.", "danger")
            else:
                flash("Some of the data was rejected by the database. Please check it.", "danger")
            return render_template("register.html", form=request.form), 400

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(home_for_role(session.get("role")))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = fetch_one(
            "SELECT user_id, name, password_hash, role FROM users WHERE email = %s",
            (email,),
        )
        # Same message for "no such user" and "wrong password" (no user enumeration)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email), 401
        if user["role"] not in ("admin", "student"):
            flash("The company portal is not enabled in this project.", "warning")
            return render_template("login.html", email=email), 403

        session.clear()                      # prevents session fixation
        session.permanent = True
        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        flash(f"Welcome, {user['name']}!", "success")
        return redirect(home_for_role(user["role"]))

    return render_template("login.html", email="")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))