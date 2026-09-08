"""
setup_db.py  -  COSC3106 Studio Project, Sub-Task B
====================================================
Extends the supplied immunisation database with the two tables that Level 1
Sub-Task B (Mission Statement) requires:

    * Persona     - the user groups this website is designed for
    * TeamMember  - the names and student numbers of the team

The specification states that personas and team members "must be stored in and
retrieved from your database", so they are modelled as proper relations rather
than hard-coded in the templates.  Every page reads them back out with SQL.

This script is idempotent: run it as many times as you like.

    python setup_db.py

>>> EDIT THE `TEAM` LIST BELOW WITH YOUR REAL NAMES AND STUDENT NUMBERS <<<
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "data", "immunisation.db")

# ---------------------------------------------------------------------------
# >>> EDIT ME <<<  Team members - Level 1 Sub-Task B requires these in the DB.
# subtask is 'A' or 'B' (which set of three pages that student built).
# ---------------------------------------------------------------------------
TEAM = [
    # (student_number, full_name, subtask, role)
    ("s4189686", "Nguyen Tran Ba Trong", "B",
     "Mission Statement, Infection by Economic Status, Above-Average Infection Rate"),
    # >>> EDIT ME <<< your teammate's real name and student number.
    ("sYYYYYYY", "PLACEHOLDER - teammate name", "A",
     "Landing Page, Vaccination Rates by Country & Region, Biggest Improvement"),
]

# ---------------------------------------------------------------------------
# Personas - the target user groups for this website.
# ---------------------------------------------------------------------------
PERSONAS = [
    (
        1,
        "Dr Amara Okonkwo",
        "Regional Public Health Analyst",
        "35-45",
        "Sub-Saharan Africa",
        "Work out which countries in her region are falling behind on preventable "
        "disease control this year, so limited outbreak-response funding goes where "
        "the burden is genuinely highest.",
        "The published surveillance spreadsheets give raw case counts only. Comparing "
        "a country of 2 million with one of 200 million means rebuilding population "
        "adjustments by hand every single time.",
        "The Above-Average Infection Rate page computes the global rate per 100,000 "
        "people and lists exactly which countries exceed it, in one query, for the "
        "year and disease she picks.",
        "analyst",
    ),
    (
        2,
        "Liam Tran",
        "Second-year Public Health student",
        "18-24",
        "Melbourne, Australia",
        "Find credible, citable figures showing how the burden of preventable disease "
        "relates to a country's income level, for an assessed literature review.",
        "News articles quote dramatic numbers with no year, no source and no "
        "denominator, and he cannot tell whether a figure is a raw count or a rate.",
        "The Infection by Economic Status page states the disease, the year, the raw "
        "case count, the population and the derived rate side by side, so every number "
        "he cites can be reproduced and referenced.",
        "student",
    ),
    (
        3,
        "Sofia Marchetti",
        "Health Journalist",
        "30-40",
        "Rome, Italy",
        "Verify a claim about measles resurgence and get one defensible, checkable "
        "figure before a same-day deadline.",
        "Different outlets report different totals for the same year, and she has no "
        "fast way to see whether a country is genuinely an outlier or simply large.",
        "Both data pages let her sort any column and see the global benchmark on the "
        "same screen, so an outlier claim can be checked in under a minute.",
        "journalist",
    ),
    (
        4,
        "Grace Whitmore",
        "Parent and community volunteer",
        "40-55",
        "Regional Victoria, Australia",
        "Understand whether diseases like measles and whooping cough are still a real "
        "risk today, and how her country compares with the rest of the world.",
        "Health dashboards assume she already knows what an 'antigen' or 'coverage "
        "target' is, and drop her into charts with no explanation.",
        "The Mission Statement explains the site in plain language, diseases are named "
        "rather than coded, and every table says in words what it is showing.",
        "community",
    ),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS Persona (
    PersonaID      INTEGER   PRIMARY KEY,
    name           TEXT (60) NOT NULL,
    role           TEXT (80) NOT NULL,
    age_range      TEXT (10),
    location       TEXT (60),
    goal           TEXT      NOT NULL,
    frustration    TEXT      NOT NULL,
    how_site_helps TEXT      NOT NULL,
    icon           TEXT (20)
);

CREATE TABLE IF NOT EXISTS TeamMember (
    student_number TEXT (10) PRIMARY KEY
                             UNIQUE
                             NOT NULL,
    name           TEXT (60) NOT NULL,
    subtask        TEXT (1)  NOT NULL
                             CHECK (subtask IN ('A', 'B')),
    role           TEXT (120)
);
"""


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(
            "Database not found at %s\n"
            "Copy immunisation-2.db into the data/ folder as immunisation.db."
            % DB_PATH
        )

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()
    cur.executescript(SCHEMA)

    # Clear first, then re-seed.  INSERT OR REPLACE alone would leave behind
    # any row that has since been deleted from the lists above, so the tables
    # are emptied to make the Python lists the single source of truth.
    cur.execute("DELETE FROM Persona")
    cur.execute("DELETE FROM TeamMember")

    cur.executemany(
        "INSERT OR REPLACE INTO Persona "
        "(PersonaID, name, role, age_range, location, goal, frustration, "
        " how_site_helps, icon) VALUES (?,?,?,?,?,?,?,?,?)",
        PERSONAS,
    )
    cur.executemany(
        "INSERT OR REPLACE INTO TeamMember "
        "(student_number, name, subtask, role) VALUES (?,?,?,?)",
        TEAM,
    )

    con.commit()
    n_p = cur.execute("SELECT COUNT(*) FROM Persona").fetchone()[0]
    n_t = cur.execute("SELECT COUNT(*) FROM TeamMember").fetchone()[0]
    con.close()

    print("Database ready: %s" % DB_PATH)
    print("  Persona rows    : %d" % n_p)
    print("  TeamMember rows : %d" % n_t)
    if any(sn.startswith("sYYY") for sn, *_ in TEAM):
        print("\n  !! TEAM still contains a placeholder - edit TEAM in setup_db.py "
              "and re-run.")


if __name__ == "__main__":
    main()
