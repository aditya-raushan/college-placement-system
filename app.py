"""Flask application entry point."""
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, session
from flask_wtf.csrf import CSRFError, CSRFProtect
from mysql.connector import Error as MySQLError

from config import Config
from database.db_connection import check_connection, close_db, fetch_one
from routes.helpers import BRANCHES, home_for_role

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    secret = app.config.get("SECRET_KEY")
    if not secret or secret.startswith("replace-with"):
        raise RuntimeError("SECRET_KEY is missing. Put a long random value in your .env file.")

    csrf.init_app(app)
    app.teardown_appcontext(close_db)

    # ---- blueprints (Phases 5 and 6 will add companies and applications here)
       # ---- blueprints (Phase 6 will add applications here)
        # ---- blueprints
    from routes import admin, applications, auth, companies, student
    for module in (auth, student, companies, applications, admin):
        app.register_blueprint(module.bp)
        # ---- template helpers
    @app.template_filter("first_name")
    def first_name(value):
        return (value or "").split(" ")[0]

    @app.template_filter("initials")
    def initials(value):
        parts = (value or "?").split()
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

    @app.context_processor
    def inject_globals():
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
        return {"BRANCHES": BRANCHES, "current_year": datetime.now().year,
                "greeting": greeting}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    # ---- pages
    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(home_for_role(session.get("role")))
        try:   # real numbers from the database (hidden if the DB is unreachable)
            stats = fetch_one(
                "SELECT (SELECT COUNT(*) FROM companies) AS companies, "
                "(SELECT COUNT(*) FROM placement_drives "
                " WHERE status = 'open' AND deadline > NOW()) AS open_drives, "
                "(SELECT COUNT(*) FROM students) AS students, "
                "(SELECT COUNT(*) FROM applications WHERE status = 'selected') AS offers")
        except MySQLError:
            stats = None
        return render_template("index.html", stats=stats)

    @app.route("/health")
    def health():
        try:
            details = check_connection()
            return jsonify(status="ok", database_connection="connected", **details)
        except MySQLError as exc:
            app.logger.error("Database health check failed: %s", exc)
            return jsonify(status="error", database_connection="failed"), 503

    # ---- error pages
    def _error(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return _error(400, "Form expired", "Your form session expired or was invalid. Go back, refresh the page and try again.")

    @app.errorhandler(400)
    def bad_request(_e):
        return _error(400, "Bad request", "The request could not be understood.")

    @app.errorhandler(403)
    def forbidden(_e):
        return _error(403, "Access denied", "You do not have permission to view this page.")

    @app.errorhandler(404)
    def not_found(_e):
        return _error(404, "Page not found", "The page you are looking for does not exist.")

    @app.errorhandler(405)
    def not_allowed(_e):
        return _error(405, "Method not allowed", "This action is not allowed here.")

    @app.errorhandler(MySQLError)
    def database_error(exc):
        app.logger.error("Database error: %s", exc)
        return _error(500, "Database error", "A database problem occurred. Please try again.")

    @app.errorhandler(500)
    def server_error(_e):
        return _error(500, "Server error", "Something went wrong on the server.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])