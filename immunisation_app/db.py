from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g


PERSONAS = (
    (
        "Public health student",
        "Learner",
        "Understand how reported infection rates differ between countries and economic groups.",
        "Clear definitions, comparable units and guided filters.",
        "Economy comparison and the weighted global infection benchmark.",
    ),
    (
        "Policy researcher",
        "Analyst",
        "Identify economic and geographic patterns that may warrant closer investigation.",
        "Traceable calculations, flexible sorting and transparent data-quality handling.",
        "Economy comparison, sortable detail tables and above-benchmark country lists.",
    ),
    (
        "Community educator",
        "Communicator",
        "Find reliable, neutral evidence to support public conversations about immunisation.",
        "Plain language, respectful framing and concise evidence summaries.",
        "Mission page and labelled rates per 100,000 people.",
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
