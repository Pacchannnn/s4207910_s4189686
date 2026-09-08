"""Request-scoped, read-only SQLite connections. No source database writes."""
import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db():
    if "db" not in g:
        path = Path(current_app.config["DATABASE"]).resolve()
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA query_only = ON")
        g.db = connection
    return g.db

def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
