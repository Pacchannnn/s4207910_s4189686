from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g


PERSONAS = (
    (
        "Dr Amara Okonkwo",
        "Regional Public Health Analyst",
        "Identify countries falling behind in infection control to prioritise outbreak-response funding.",
        "Comparable infection rates per 100,000 rather than raw case counts.",
        "Infection explorer and global benchmark.",
    ),
    (
        "Liem Tran",
        "Public Health Student",
        "Explore disease burden and economic conditions using reliable figures.",
        "The year, population, case count and rate shown together.",
        "Economy comparison and country results.",
    ),
    (
        "Sofia Mascherano",
        "Health Journalist",
        "Check claims about measles resurgence under a tight deadline.",
        "Clear country rates, not raw totals alone.",
        "Sortable country data and the global benchmark.",
    ),
)

TEAM_MEMBERS = (
    (1, "Le Chi Bach", "s4207910", "Vaccination stream"),
    (2, "Nguyen Tran Ba Trong", "s4189686", "Infection stream"),
)


def connect_database(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialise_project_tables(path: str | Path) -> None:
    connection = connect_database(path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        changed = False

        if "ProjectPersona" not in tables:
            connection.execute(
                """
            CREATE TABLE IF NOT EXISTS ProjectPersona (
                persona_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                goal TEXT NOT NULL,
                need TEXT NOT NULL,
                app_feature TEXT NOT NULL
            )
            """
            )
            changed = True
        if "ProjectTeamMember" not in tables:
            connection.execute(
                """
            CREATE TABLE IF NOT EXISTS ProjectTeamMember (
                member_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                student_number TEXT NOT NULL UNIQUE,
                responsibility TEXT NOT NULL
            )
            """
            )
            changed = True

        existing_personas = {
            row[0] for row in connection.execute("SELECT name FROM ProjectPersona")
        }
        missing_personas = [row for row in PERSONAS if row[0] not in existing_personas]
        if missing_personas:
            connection.executemany(
                """
            INSERT OR IGNORE INTO ProjectPersona
                (name, role, goal, need, app_feature)
            VALUES (?, ?, ?, ?, ?)
            """,
                missing_personas,
            )
            changed = True

        existing_member_ids = {
            row[0]
            for row in connection.execute("SELECT member_id FROM ProjectTeamMember")
        }
        missing_members = [row for row in TEAM_MEMBERS if row[0] not in existing_member_ids]
        if missing_members:
            connection.executemany(
                """
            INSERT OR IGNORE INTO ProjectTeamMember
                (member_id, name, student_number, responsibility)
            VALUES (?, ?, ?, ?)
            """,
                missing_members,
            )
            changed = True

        if changed:
            connection.commit()
    finally:
        connection.close()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_database(current_app.config["DATABASE"])
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
