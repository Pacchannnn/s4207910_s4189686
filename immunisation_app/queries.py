from __future__ import annotations

import sqlite3
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


def get_snapshot(db: sqlite3.Connection) -> dict[str, int]:
    row = db.execute(
        """
        SELECT
            (SELECT MIN(YearID) FROM YearDate) AS first_year,
            (SELECT MAX(YearID) FROM YearDate) AS last_year,
            (SELECT COUNT(*) FROM Country) AS country_count,
            (SELECT COUNT(*) FROM Antigen) AS antigen_count,
            (SELECT COUNT(*) FROM Infection_Type) AS infection_count
        """
    ).fetchone()
    return dict(row)


def get_latest_infection_totals(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        db.execute(
            """
            WITH totals AS (
                SELECT
                    it.id,
                    it.description,
                    SUM(id.cases) AS total_cases
                FROM InfectionData AS id
                JOIN Infection_Type AS it ON it.id = id.inf_type
                WHERE id.year = (SELECT MAX(YearID) FROM YearDate)
                GROUP BY it.id, it.description
            )
            SELECT
                id,
                description,
                total_cases,
                ROUND(
                    total_cases * 100.0 / NULLIF(MAX(total_cases) OVER (), 0),
                    2
                ) AS relative_width
            FROM totals
            ORDER BY total_cases DESC
            """
        )
    )


def get_reference_data(db: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    return {
        "antigens": _rows(
            db.execute("SELECT AntigenID AS id, name FROM Antigen ORDER BY name")
        ),
        "countries": _rows(
            db.execute("SELECT CountryID AS id, name FROM Country ORDER BY name")
        ),
        "regions": _rows(
            db.execute("SELECT RegionID AS id, region AS name FROM Region ORDER BY region")
        ),
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


def get_vaccination_view(
    db: sqlite3.Connection,
    *,
    antigen: str,
    year: int,
    country: str,
    region: str,
    sort_by: str,
    direction: str,
) -> dict[str, Any]:
    order_column, order_direction = _safe_order(
        sort_by,
        direction,
        {
            "country": "country",
            "region": "region_name",
            "coverage": "coverage",
            "doses": "doses",
            "target": "target_num",
        },
        "coverage",
    )
    filters = ["v.antigen = ?", "v.year = ?"]
    parameters: list[Any] = [antigen, year]
    if country:
        filters.append("c.CountryID = ?")
        parameters.append(country)
    if region:
        filters.append("r.RegionID = ?")
        parameters.append(region)
    where_clause = " AND ".join(filters)
    coverage_expression = """
        COALESCE(
            CAST(NULLIF(TRIM(CAST(v.coverage AS TEXT)), '') AS REAL),
            CASE WHEN v.target_num > 0
                THEN v.doses * 100.0 / v.target_num END
        )
    """

    filtered_cte = f"""
        WITH filtered AS (
            SELECT
                v.antigen,
                v.year,
                c.CountryID AS country_id,
                c.name AS country,
                r.RegionID AS region_id,
                r.region AS region_name,
                v.doses,
                v.target_num,
                {coverage_expression} AS coverage
            FROM Vaccination AS v
            JOIN Country AS c ON c.CountryID = v.country
            JOIN Region AS r ON r.RegionID = c.region
            WHERE {where_clause}
        )
    """
    detail_sql = f"""
        {filtered_cte}
        SELECT
            antigen,
            year,
            country_id,
            country,
            region_id,
            region_name,
            doses,
            target_num,
            ROUND(coverage, 2) AS coverage,
            CASE
                WHEN coverage IS NULL THEN 'No data'
                WHEN coverage > 100 THEN 'Reported above 100%'
                WHEN coverage >= 90 THEN 'Met target'
                ELSE 'Below target'
            END AS target_status
        FROM filtered
        WHERE coverage >= 90
        ORDER BY {order_column} {order_direction}, country ASC
        LIMIT 500
    """
    summary_sql = f"""
        {filtered_cte}
        SELECT
            antigen,
            year,
            region_id,
            region_name,
            COUNT(DISTINCT CASE WHEN coverage IS NOT NULL THEN country_id END)
                AS countries_with_data,
            COUNT(DISTINCT CASE WHEN coverage >= 90 THEN country_id END) AS met_target_count,
            ROUND(AVG(coverage), 2) AS average_coverage
        FROM filtered
        GROUP BY antigen, year, region_id, region_name
        ORDER BY met_target_count DESC, region_name ASC
    """
    metrics_sql = f"""
        {filtered_cte}
        SELECT
            COUNT(DISTINCT CASE WHEN coverage IS NOT NULL THEN country_id END)
                AS countries_with_data,
            COUNT(DISTINCT CASE WHEN coverage >= 90 THEN country_id END)
                AS countries_meeting_target,
            COUNT(DISTINCT CASE WHEN coverage > 100 THEN country_id END)
                AS anomalous_coverage_count,
            ROUND(AVG(coverage), 2) AS average_coverage
        FROM filtered
    """
    return {
        "rows": _rows(db.execute(detail_sql, parameters)),
        "summary": _rows(db.execute(summary_sql, parameters)),
        "metrics": dict(db.execute(metrics_sql, parameters).fetchone()),
    }


def get_vaccination_improvements(
    db: sqlite3.Connection,
    *,
    antigen: str,
    start_year: int,
    end_year: int,
    limit: int,
    sort_by: str,
    direction: str,
) -> list[dict[str, Any]]:
    order_column, order_direction = _safe_order(
        sort_by,
        direction,
        {
            "country": "country",
            "start_rate": "start_rate",
            "end_rate": "end_rate",
            "improvement": "improvement",
        },
        "improvement",
    )
    sql = f"""
        WITH start_rates AS (
            SELECT
                c.CountryID AS country_id,
                c.name AS country,
                SUM(v.doses) * 100.0 / NULLIF(MAX(cp.population), 0) AS start_rate
            FROM Vaccination AS v
            JOIN Country AS c ON c.CountryID = v.country
            JOIN CountryPopulation AS cp
                ON cp.country = v.country AND cp.year = v.year
            WHERE v.antigen = ?
              AND v.year = ?
              AND v.doses IS NOT NULL
              AND cp.population > 0
            GROUP BY c.CountryID, c.name
        ),
        end_rates AS (
            SELECT
                c.CountryID AS country_id,
                SUM(v.doses) * 100.0 / NULLIF(MAX(cp.population), 0) AS end_rate
            FROM Vaccination AS v
            JOIN Country AS c ON c.CountryID = v.country
            JOIN CountryPopulation AS cp
                ON cp.country = v.country AND cp.year = v.year
            WHERE v.antigen = ?
              AND v.year = ?
              AND v.doses IS NOT NULL
              AND cp.population > 0
            GROUP BY c.CountryID
        ),
        improvements AS (
            SELECT
                s.country_id,
                s.country,
                s.start_rate,
                e.end_rate,
                e.end_rate - s.start_rate AS improvement
            FROM start_rates AS s
            JOIN end_rates AS e ON e.country_id = s.country_id
            WHERE e.end_rate - s.start_rate > 0
        )
        SELECT
            country_id,
            country,
            ? AS antigen,
            ? AS start_year,
            ? AS end_year,
            start_rate,
            end_rate,
            improvement
        FROM improvements
        ORDER BY {order_column} {order_direction}, country ASC
        LIMIT ?
    """
    return _rows(
        db.execute(
            sql,
            (
                antigen,
                start_year,
                antigen,
                end_year,
                antigen,
                start_year,
                end_year,
                limit,
            ),
        )
    )
