"""Flask application factory."""
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request
from .db import close_db

NAVIGATION = [
    ("pages.home", "Overview"), ("pages.mission", "Mission"),
    ("pages.vaccinations", "Vaccination"), ("pages.infections", "Infections"),
    ("pages.improvements", "Improvement"), ("pages.benchmark", "Benchmark")
]

def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=Path(__file__).resolve().parents[1] / "database/immunisation.db",
        MAX_CONTENT_LENGTH=16384,
    )
    if config:
        app.config.update(config)
    app.teardown_appcontext(close_db)
    from .i18n import init_app
    init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    @app.context_processor
    def common():
        return {"navigation":NAVIGATION}

    @app.template_filter("num")
    def number(value, decimals=0):
        if value is None:
            return "Not available"
        return f"{value:,.{decimals}f}"

    @app.before_request
    def limit_query():
        if len(request.query_string)>8192:
            return render_template("error.html",title="Check your filters",
                                   message="The filter address is too long. Reset the form and try again."),400

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; style-src 'self'; "
            "img-src 'self'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html",title="Page not found",
                               message="This address does not match a page. Choose a destination below to keep exploring."),404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return render_template("error.html",title="Method not allowed",
                               message="Use the page's search form to explore the data."),405

    @app.errorhandler(413)
    def too_large(error):
        return render_template("error.html",title="Request too large",
                               message="The request is too large. Return to the form and try again."),413

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        app.logger.error("Database unavailable: %s",error)
        return render_template("error.html",title="Data temporarily unavailable",
                               message="The project database could not be read. Check the database setup described in README.md."),503

    @app.errorhandler(500)
    def server_error(error):
        return render_template("error.html",title="Unable to display this page",
                               message="Please return to the overview and try again."),500

    return app
