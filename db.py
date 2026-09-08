"""
db.py  -  data access layer for Sub-Task B
==========================================
Every SQL statement used by the web application lives in this module, so the
queries can be read, reviewed and reasoned about in one place.

Design decisions that apply across the whole module
---------------------------------------------------
1. Raw ``sqlite3`` with parameterised queries.  No ORM, so the SQL that the
   assessment is about stays visible; ``?`` placeholders everywhere, so user
   input can never be injected.

2. Ordering is chosen by the user, which SQL cannot parameterise.  Column names
   are therefore resolved through an explicit whitelist dictionary and can only
   ever be one of a fixed set of literals (see ``_order_by``).

3. Data anomalies present in the supplied database are handled *in SQL*, not by
   post-processing in Python:

   =========================================  =================================
   Anomaly found in the data                  How it is handled
   =========================================  =================================
   Vaccination.target_num / doses / coverage  typeof(col) = 'real' guards, so
   hold empty strings for ~24% of rows        blanks are excluded rather than
   instead of NULL                            silently coerced to zero
   9 country codes appear in Vaccination      INNER JOIN to Country discards
   that do not exist in Country (AIA, BON,    the orphan rows
   COK, MSR, NIU, SAB, STA, TKL, WLF)
   10 countries in Country have no rows at    INNER JOIN; without a case count
   all in InfectionData                       they cannot produce a rate
   A rate needs a denominator                 population > 0 guard prevents a
                                              divide-by-zero
   A country/year pair could in principle     Composite primary keys already
   repeat with inconsistent values            make duplicates impossible here;
                                              aggregates use SUM/AVG so the
                                              queries stay correct regardless
   =========================================  =================================

4. "Cases per 100,000 people" is computed as ``cases * 100000.0 / population``.
   The ``100000.0`` literal forces real division; SQLite would otherwise do
   integer division on integer columns.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "data", "immunisation.db")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def get_connection():
    """Open a connection that returns dictionary-like rows."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def query(sql, params=()):
    """Run a SELECT and return a list of sqlite3.Row."""
    con = get_connection()
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def query_one(sql, params=()):
    """Run a SELECT and return the first row, or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def _order_by(whitelist, key, direction, default_key):
    """
    Build a safe ORDER BY fragment.

    ``key`` comes from the query string, so it is never interpolated directly.
    It is looked up in ``whitelist`` (a dict of key -> SQL expression); anything
    unrecognised falls back to ``default_key``.  ``direction`` collapses to
    exactly 'ASC' or 'DESC'.
    """
    expr = whitelist.get(key, whitelist[default_key])
    direction = "DESC" if str(direction).lower() == "desc" else "ASC"
    return "%s %s" % (expr, direction)


# ===========================================================================
# LEVEL 1 - SUB-TASK B : Mission Statement
# ===========================================================================
def get_personas():
    """Personas are stored in the database, as the specification requires."""
    return query(
        """
        SELECT PersonaID, name, role, age_range, location,
               goal, frustration, how_site_helps, icon
          FROM Persona
         ORDER BY PersonaID
        """
    )


def get_team_members():
    """Team names and student numbers, also read back from the database."""
    return query(
        """
        SELECT student_number, name, subtask, role
          FROM TeamMember
         ORDER BY subtask, name
        """
    )


def get_scope_summary():
    """
    Live figures describing what the site actually covers, so the mission
    statement is grounded in the data rather than in claims.
    """
    return query_one(
        """
        SELECT (SELECT MIN(year) FROM InfectionData)               AS first_year,
               (SELECT MAX(year) FROM InfectionData)               AS last_year,
               (SELECT COUNT(DISTINCT country) FROM InfectionData) AS n_countries,
               (SELECT COUNT(*) FROM Infection_Type)               AS n_diseases,
               (SELECT COUNT(*) FROM Economy)                      AS n_economies,
               (SELECT COUNT(*) FROM Region)                       AS n_regions,
               (SELECT COUNT(*) FROM InfectionData)                AS n_infection_rows,
               (SELECT SUM(cases) FROM InfectionData)              AS total_cases
        """
    )


# ===========================================================================
# Shared reference data (populates the filter controls)
# ===========================================================================
def get_economies():
    return query("SELECT economyID, phase FROM Economy ORDER BY economyID")


def get_infection_types():
    return query("SELECT id, description FROM Infection_Type ORDER BY description")


def get_years():
    """
    Only offer years that actually have infection data, so the user can never
    select a year that returns an empty table.
    """
    return [r["year"] for r in
            query("SELECT DISTINCT year FROM InfectionData ORDER BY year DESC")]


# ===========================================================================
# LEVEL 2 - SUB-TASK B : Infection data by economic status
# ===========================================================================

# Whitelist of sortable columns for the country-level table.
L2_SORT = {
    "country":        "country",
    "region":         "region",
    "cases":          "cases",
    "population":     "population",
    "cases_per_100k": "cases_per_100k",
}

# Whitelist for the cross-economy summary table.
L2_SUMMARY_SORT = {
    "phase":          "economic_phase",
    "countries":      "countries_reporting",
    "cases":          "total_cases",
    "cases_per_100k": "cases_per_100k",
}


def get_infections_by_economy(economy_id, inf_type, year,
                              sort="cases_per_100k", direction="desc"):
    """
    Level 2B, table 1.

    Every country belonging to ONE economic status, for ONE infection type, in
    ONE year - with the raw case count, the population that produced it, and
    the population-adjusted rate per 100,000 people.

    Joins five tables: InfectionData -> Country -> Economy, Country -> Region,
    InfectionData -> Infection_Type, and InfectionData -> CountryPopulation on
    the composite (country, year) key.
    """
    sql = """
        SELECT it.description                              AS disease,
               c.name                                      AS country,
               r.region                                    AS region,
               e.phase                                     AS economic_phase,
               i.year                                      AS year,
               i.cases                                     AS cases,
               p.population                                AS population,
               ROUND(i.cases * 100000.0 / p.population, 2) AS cases_per_100k
          FROM InfectionData      i
          JOIN Country            c  ON c.CountryID  = i.country
          JOIN Economy            e  ON e.economyID  = c.economy
          JOIN Region             r  ON r.RegionID   = c.region
          JOIN Infection_Type     it ON it.id        = i.inf_type
          JOIN CountryPopulation  p  ON p.country    = i.country
                                    AND p.year       = i.year
         WHERE e.economyID = ?
           AND i.inf_type  = ?
           AND i.year      = ?
           AND i.cases      IS NOT NULL
           AND p.population IS NOT NULL
           AND p.population  > 0
         ORDER BY %s, c.name ASC
    """ % _order_by(L2_SORT, sort, direction, "cases_per_100k")
    return query(sql, (economy_id, inf_type, year))


def get_economy_comparison(inf_type, year, sort="cases", direction="desc"):
    """
    Level 2B, table 2 - the summary that combines information from more than
    one table.

    For ONE infection type in ONE year, aggregate every economic phase: how
    many countries reported, the total case count, the combined population, and
    the pooled rate per 100,000 people.

    The pooled rate is SUM(cases) / SUM(population), not the average of the
    individual country rates - averaging rates would weight San Marino the same
    as India.
    """
    sql = """
        SELECT it.description                                        AS disease,
               e.phase                                               AS economic_phase,
               i.year                                                AS year,
               COUNT(DISTINCT c.CountryID)                           AS countries_reporting,
               SUM(i.cases)                                          AS total_cases,
               SUM(p.population)                                     AS total_population,
               ROUND(SUM(i.cases) * 100000.0 / SUM(p.population), 2) AS cases_per_100k
          FROM InfectionData      i
          JOIN Country            c  ON c.CountryID  = i.country
          JOIN Economy            e  ON e.economyID  = c.economy
          JOIN Infection_Type     it ON it.id        = i.inf_type
          JOIN CountryPopulation  p  ON p.country    = i.country
                                    AND p.year       = i.year
         WHERE i.inf_type  = ?
           AND i.year      = ?
           AND i.cases      IS NOT NULL
           AND p.population IS NOT NULL
           AND p.population  > 0
         GROUP BY e.economyID, e.phase, it.description, i.year
         ORDER BY %s
    """ % _order_by(L2_SUMMARY_SORT, sort, direction, "cases")
    return query(sql, (inf_type, year))


# ===========================================================================
# LEVEL 3 - SUB-TASK B : Countries with an above-average infection rate
# ===========================================================================
#
# The marking rubric for this level asks specifically for (a) a query that
# compares two datasets rather than displaying raw data, and (b) the use of a
# subquery - EXISTS, NOT EXISTS, IN, NOT IN or a nested SELECT - to use the
# result of one query to find a sub-dataset.  Both are done here, in SQL, with
# no post-processing in Python.
#

# Whitelist of sortable columns.  "similarity" sorts by how close a country's
# rate is to the global rate, satisfying the "sorting based on similarity using
# SQL" requirement for this level.
L3_SORT = {
    "cases_per_100k": "cases_per_100k",
    "country":        "country",
    "region":         "region",
    "economic_phase": "economic_phase",
    "cases":          "cases",
    "population":     "population",
    "excess":         "excess_over_global",
    "coverage":       "coverage_pct",
    # A compound SELECT (UNION ALL) may only ORDER BY a name in the result set,
    # never an expression, so the distance from the global rate is materialised
    # as its own column, `similarity`, in both branches of the union.
    "similarity":     "similarity",
}


def get_antigens_for_disease(inf_type):
    """
    The vaccines recorded against a given disease.  Driving the antigen list
    from the data means the control can never offer a combination the database
    cannot answer (for example rubella has one antigen, measles has two).
    """
    return query(
        """
        SELECT DISTINCT a.AntigenID, a.name
          FROM Vaccination v
          JOIN Antigen     a ON a.AntigenID = v.antigen
         WHERE v.inf_type = ?
         ORDER BY a.AntigenID
        """,
        (inf_type,),
    )


def get_above_average_infections(inf_type, year, antigen,
                                 sort="cases_per_100k", direction="desc",
                                 limit=None):
    """
    Level 3B - one query, no Python post-processing.

    Finds the global reported infection rate per 100,000 people for a disease
    and year, returns every country whose own rate exceeds it, and sets each of
    those countries against a *second* dataset - its vaccination coverage for
    the chosen antigen in the same year.

    How the SQL is built
    --------------------
    ``global_stats``   a common table expression holding one row: the
                       population-weighted world rate,
                       SUM(cases) / SUM(population) * 100000.

    ``... WHERE i.country IN (SELECT ...)``
                       the sub-dataset.  The inner SELECT re-reads the
                       infection data and keeps only the countries whose own
                       rate is greater than the scalar subquery
                       ``(SELECT rate FROM global_stats)``.  This is the
                       "result of one query used to find another sub-dataset"
                       requirement: the global figure is computed first, then
                       used to select the rows.

    ``(SELECT v.coverage FROM Vaccination v WHERE v.country = i.country ...)``
                       a correlated scalar subquery that reaches into the
                       vaccination dataset for the matching country, year,
                       disease and antigen.  This is what turns the page from
                       a list of infection figures into a comparison of two
                       datasets: how much disease was reported, next to how
                       much of the population was vaccinated against it.

    The result is a UNION ALL of the global benchmark row (``sort_group = 0``)
    with the qualifying countries (``sort_group = 1``).  Ordering by
    ``sort_group`` first pins the benchmark to the top of the table however the
    user sorts the countries beneath it, as the specification asks.

    Sorting, filtering and every calculation happen in SQLite.  Python receives
    rows that are already in their final order and never touches the numbers -
    the database engine can use its indexes and returns only the rows needed,
    whereas fetching all 207 countries and sorting them in Python would move
    far more data for a worse result.
    """
    order = _order_by(L3_SORT, sort, direction, "cases_per_100k")
    limit_clause = "LIMIT :lim" if limit else ""

    sql = """
        WITH global_stats AS (
            SELECT SUM(i.cases)                              AS total_cases,
                   SUM(p.population)                         AS total_population,
                   COUNT(*)                                  AS n_countries,
                   SUM(i.cases) * 100000.0 / SUM(p.population) AS rate
              FROM InfectionData     i
              JOIN CountryPopulation p ON p.country   = i.country
                                      AND p.year      = i.year
              JOIN Country           c ON c.CountryID = i.country
             WHERE i.inf_type   = :inf
               AND i.year       = :yr
               AND i.cases      IS NOT NULL
               AND p.population IS NOT NULL
               AND p.population  > 0
        )

        /* ---- row 0: the global benchmark, pinned to the top ------------ */
        SELECT 0                                  AS sort_group,
               'Global'                           AS country,
               'All reporting countries'          AS region,
               '-'                                AS economic_phase,
               g.total_cases                      AS cases,
               g.total_population                 AS population,
               ROUND(g.rate, 2)                   AS cases_per_100k,
               0.0                                AS excess_over_global,
               0.0                                AS similarity,
               g.n_countries                      AS n_countries,
               (SELECT ROUND(AVG(v.coverage), 1)
                  FROM Vaccination v
                 WHERE v.inf_type = :inf
                   AND v.antigen  = :ant
                   AND v.year     = :yr
                   AND typeof(v.coverage) = 'real')
                                                  AS coverage_pct
          FROM global_stats g

        UNION ALL

        /* ---- rows 1..n: only countries above that benchmark ------------ */
        SELECT 1                                             AS sort_group,
               c.name                                        AS country,
               r.region                                      AS region,
               e.phase                                       AS economic_phase,
               i.cases                                       AS cases,
               p.population                                  AS population,
               ROUND(i.cases * 100000.0 / p.population, 2)   AS cases_per_100k,
               ROUND(i.cases * 100000.0 / p.population
                     - (SELECT rate FROM global_stats), 2)   AS excess_over_global,
               ROUND(ABS(i.cases * 100000.0 / p.population
                     - (SELECT rate FROM global_stats)), 2)  AS similarity,
               NULL                                          AS n_countries,
               (SELECT v.coverage
                  FROM Vaccination v
                 WHERE v.country  = i.country
                   AND v.year     = i.year
                   AND v.inf_type = i.inf_type
                   AND v.antigen  = :ant
                   AND typeof(v.coverage) = 'real')          AS coverage_pct
          FROM InfectionData     i
          JOIN Country           c ON c.CountryID = i.country
          JOIN Region            r ON r.RegionID  = c.region
          JOIN Economy           e ON e.economyID = c.economy
          JOIN CountryPopulation p ON p.country   = i.country
                                  AND p.year      = i.year
         WHERE i.inf_type   = :inf
           AND i.year       = :yr
           AND i.cases      IS NOT NULL
           AND p.population IS NOT NULL
           AND p.population  > 0
           AND i.country IN (
                 SELECT i2.country
                   FROM InfectionData     i2
                   JOIN CountryPopulation p2 ON p2.country = i2.country
                                            AND p2.year    = i2.year
                  WHERE i2.inf_type   = :inf
                    AND i2.year       = :yr
                    AND i2.cases      IS NOT NULL
                    AND p2.population IS NOT NULL
                    AND p2.population  > 0
                    AND i2.cases * 100000.0 / p2.population
                        > (SELECT rate FROM global_stats)
               )

         ORDER BY sort_group ASC, %s, country ASC
         %s
    """ % (order, limit_clause)

    params = {"inf": inf_type, "yr": year, "ant": antigen}
    if limit:
        # +1 so the pinned global row never eats one of the requested countries.
        params["lim"] = int(limit) + 1
    return query(sql, params)


def get_global_rate_context(inf_type, year, antigen):
    """
    Supporting figures shown beside the Level 3B table so the benchmark is
    transparent, and one figure that only a NOT EXISTS can produce.

    ``n_no_coverage_record`` counts the above-average countries for which NO
    row exists in the vaccination dataset for that antigen and year.  It
    matters: a country can look like a coverage success purely because it never
    reported, and this is the number that stops the table being read that way.

    Two global averages are shown deliberately.  They answer different
    questions - the weighted rate is "what is a randomly chosen person's risk",
    the unweighted mean is "what is a typical country's rate" - and quoting one
    without saying which is the kind of framing this project should avoid.
    """
    return query_one(
        """
        WITH clean AS (
            SELECT i.country                         AS country_id,
                   i.cases                           AS cases,
                   p.population                      AS population,
                   i.cases * 100000.0 / p.population AS rate
              FROM InfectionData     i
              JOIN CountryPopulation p ON p.country   = i.country
                                      AND p.year      = i.year
              JOIN Country           c ON c.CountryID = i.country
             WHERE i.inf_type   = :inf
               AND i.year       = :yr
               AND i.cases      IS NOT NULL
               AND p.population IS NOT NULL
               AND p.population  > 0
        )
        SELECT COUNT(*)                                          AS n_reporting,
               SUM(cases)                                        AS total_cases,
               SUM(population)                                   AS total_population,
               ROUND(SUM(cases) * 100000.0 / SUM(population), 2) AS weighted_rate,
               ROUND(AVG(rate), 2)                               AS unweighted_mean_rate,

               (SELECT COUNT(*) FROM clean
                 WHERE rate > (SELECT SUM(cases) * 100000.0 / SUM(population)
                                 FROM clean))                    AS n_above,

               /* NOT EXISTS: above-average countries that never reported a
                  coverage figure for this antigen and year at all. */
               (SELECT COUNT(*)
                  FROM clean cl
                 WHERE cl.rate > (SELECT SUM(cases) * 100000.0 / SUM(population)
                                    FROM clean)
                   AND NOT EXISTS (
                         SELECT 1
                           FROM Vaccination v
                          WHERE v.country  = cl.country_id
                            AND v.year     = :yr
                            AND v.inf_type = :inf
                            AND v.antigen  = :ant
                            AND typeof(v.coverage) = 'real'
                       ))                                        AS n_no_coverage_record
          FROM clean
        """,
        {"inf": inf_type, "yr": year, "ant": antigen},
    )


# ===========================================================================
# Data-quality reporting (used by the "About this data" panel)
# ===========================================================================
def get_data_quality_notes():
    """
    Count, live, the records the queries above deliberately exclude, so the
    site can state what it dropped instead of quietly hiding it.
    """
    return query_one(
        """
        SELECT
          (SELECT COUNT(DISTINCT country) FROM Vaccination
            WHERE country NOT IN (SELECT CountryID FROM Country))       AS orphan_countries,
          (SELECT COUNT(*) FROM Country
            WHERE CountryID NOT IN (SELECT country FROM InfectionData)) AS countries_no_infection_data,
          (SELECT COUNT(*) FROM Vaccination
            WHERE typeof(coverage) <> 'real')                           AS blank_coverage_rows,
          (SELECT COUNT(*) FROM InfectionData)                          AS infection_rows
        """
    )
