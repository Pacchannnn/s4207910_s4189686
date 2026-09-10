from __future__ import annotations

import sqlite3
import math
from typing import Any


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def _safe_order(
    requested_column: str,
    requested_direction: str,
    columns: dict[str, str],
    default_column: str,
) -> tuple[str, str]:
    column = columns.get(requested_column, columns[default_column])
    direction = "ASC" if requested_direction.lower() == "asc" else "DESC"
    return column, direction


def get_reference_data(db: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    return {
        "economies": _rows(
            db.execute("SELECT economyID AS id, phase AS name FROM Economy ORDER BY economyID")
        ),
        "infections": _rows(
            db.execute("SELECT id, description AS name FROM Infection_Type ORDER BY description")
        ),
        "years": _rows(
            db.execute("SELECT YearID AS value FROM YearDate ORDER BY YearID DESC")
        ),
    }


def get_personas(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        db.execute(
            """
            SELECT name, role, goal, need, app_feature
            FROM ProjectPersona
            ORDER BY persona_id
            """
        )
    )


def get_team_members(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        db.execute(
            """
            SELECT name, student_number, responsibility
            FROM ProjectTeamMember
            ORDER BY member_id
            """
        )
    )


def get_infection_by_economy(
    db: sqlite3.Connection,
    *,
    economy_id: int,
    infection_id: str,
    year: int,
    search: str,
    sort_by: str,
    direction: str,
    numeric_column: str = "",
    numeric_operator: str = "gte",
    numeric_value: float | None = None,
) -> dict[str, Any]:
    order_column, order_direction = _safe_order(
        sort_by,
        direction,
        {
            "country": "country",
            "cases": "cases",
            "population": "population",
            "rate": "cases_per_100k",
        },
        "rate",
    )
    search_filter = ""
    parameters: list[Any] = [infection_id, year, economy_id]
    if search:
        search_filter = "AND c.name LIKE ?"
        parameters.append(f"%{search}%")

    numeric_filter = ""
    if numeric_column or numeric_value is not None:
        columns = {"cases": "cases", "population": "population", "rate": "cases_per_100k"}
        operators = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "eq": "="}
        if (numeric_column not in columns or numeric_operator not in operators
                or not isinstance(numeric_value, (int, float))
                or not math.isfinite(numeric_value) or numeric_value < 0):
            raise ValueError("Invalid numeric filter.")
        numeric_filter = f"WHERE {columns[numeric_column]} {operators[numeric_operator]} ?"
        parameters.append(numeric_value)

    detail_sql = f"""
        WITH rates AS (
            SELECT
                c.name AS country,
                e.economyID AS economy_id,
                e.phase AS economy,
                it.description AS infection,
                id.year,
                id.cases,
                cp.population,
                id.cases * 100000.0 / NULLIF(cp.population, 0) AS cases_per_100k
            FROM InfectionData AS id
            JOIN Infection_Type AS it ON it.id = id.inf_type
            JOIN Country AS c ON c.CountryID = id.country
            JOIN Economy AS e ON e.economyID = c.economy
            JOIN CountryPopulation AS cp
                ON cp.country = id.country AND cp.year = id.year
            WHERE id.inf_type = ?
              AND id.year = ?
              AND e.economyID = ?
              AND cp.population > 0
              {search_filter}
        )
        SELECT
            country,
            economy_id,
            economy,
            infection,
            year,
            cases,
            population,
            cases_per_100k
        FROM rates
        {numeric_filter}
        ORDER BY {order_column} {order_direction}, country ASC
        LIMIT 500
    """
    summary_sql = """
        SELECT
            e.economyID AS economy_id,
            e.phase AS economy,
            SUM(id.cases) AS total_cases,
            SUM(cp.population) AS represented_population,
            SUM(id.cases) * 100000.0 / NULLIF(SUM(cp.population), 0) AS cases_per_100k,
            COUNT(DISTINCT c.CountryID) AS country_count
        FROM InfectionData AS id
        JOIN Country AS c ON c.CountryID = id.country
        JOIN Economy AS e ON e.economyID = c.economy
        JOIN CountryPopulation AS cp
            ON cp.country = id.country AND cp.year = id.year
        WHERE id.inf_type = ?
          AND id.year = ?
          AND cp.population > 0
        GROUP BY e.economyID, e.phase
        ORDER BY total_cases DESC
    """
    rows = _rows(db.execute(detail_sql, parameters))
    summary = _rows(db.execute(summary_sql, (infection_id, year)))
    selected_summary = next(
        (row for row in summary if row["economy_id"] == economy_id), None
    )
    return {"rows": rows, "summary": summary, "selected_summary": selected_summary}


def get_above_global_infections(
    db: sqlite3.Connection, *, infection_id: str, year: int,
    sort_by: str = "rate", direction: str = "desc",
) -> list[dict[str, Any]]:
    order_column, order_direction = _safe_order(
        sort_by, direction,
        {"country": "country", "cases": "cases", "population": "population",
         "rate": "cases_per_100k"}, "rate",
    )
    sql = f"""
        WITH country_rates AS (
            SELECT
                c.CountryID AS country_id,
                c.name AS country,
                it.description AS infection,
                id.year,
                id.cases,
                cp.population,
                id.cases * 100000.0 / NULLIF(cp.population, 0) AS cases_per_100k
            FROM InfectionData AS id
            JOIN Infection_Type AS it ON it.id = id.inf_type
            JOIN Country AS c ON c.CountryID = id.country
            JOIN CountryPopulation AS cp
                ON cp.country = id.country AND cp.year = id.year
            WHERE id.inf_type = ?
              AND id.year = ?
              AND cp.population > 0
        ),
        global_rate AS (
            SELECT
                SUM(cases) AS cases,
                SUM(population) AS population,
                SUM(cases) * 100000.0 / NULLIF(SUM(population), 0) AS cases_per_100k
            FROM country_rates
        ),
        combined AS (
            SELECT
                0 AS row_order,
                'global' AS row_type,
                NULL AS country_id,
                'Global benchmark' AS country,
                (SELECT infection FROM country_rates LIMIT 1) AS infection,
                ? AS year,
                cases,
                population,
                cases_per_100k
            FROM global_rate
            WHERE cases_per_100k IS NOT NULL

            UNION ALL

            SELECT
                1 AS row_order,
                'country' AS row_type,
                cr.country_id,
                cr.country,
                cr.infection,
                cr.year,
                cr.cases,
                cr.population,
                cr.cases_per_100k
            FROM country_rates AS cr
            CROSS JOIN global_rate AS gr
            WHERE cr.cases_per_100k > gr.cases_per_100k
        )
        SELECT
            row_order,
            row_type,
            country_id,
            country,
            infection,
            year,
            cases,
            population,
            cases_per_100k
        FROM combined
        ORDER BY row_order ASC, {order_column} {order_direction}, country ASC
    """
    return _rows(db.execute(sql, (infection_id, year, year)))
