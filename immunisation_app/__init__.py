from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template

from . import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    project_root = Path(__file__).resolve().parents[1]
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "DATABASE_PATH", str(project_root / "database" / "immunisation.db")
        ),
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "development-key-change-before-public-deployment"
        ),
    )

    if test_config:
        app.config.update(test_config)

    db.initialise_project_tables(Path(app.config["DATABASE"]))
    db.init_app(app)

    from .views import pages

    app.register_blueprint(pages)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html", active_page=""), 404

    @app.template_filter("number")
    def format_number(value: object, decimals: int = 0) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "No data"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "No data"
        return f"{number:,.{decimals}f}"

    return app
