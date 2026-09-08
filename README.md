# Immunisation Insight — Sub-Task B

COSC3107 / COSC3108 Python Programming Studio — Studio Project
*"Investigating Preventable Infectious Diseases"*

This repository holds the **Sub-Task B** pages: Levels 1, 2 and 3.

| Level | Page | Route | Requirement |
|-------|------|-------|-------------|
| 1B | Mission Statement | `/mission` | Purpose, how the site is used, personas and team members — personas and team read **from the database** |
| 2B | Infection & Economy | `/economy` | Infection data for one economic status, one disease, one year, filterable and sortable, plus a multi-table summary |
| 3B | Above the Global Rate | `/above-average` | Global infection rate per 100,000 and every country exceeding it, with the global row pinned to the top |

---

## Running it

Create the virtual environment (once):

```bash
python -m venv .venv
```

Install the dependencies:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Seed the Persona and TeamMember tables (once):

```bash
.venv\Scripts\python.exe setup_db.py
```

Run the server:

```bash
.venv\Scripts\python.exe app.py
```

In VS Code, select this interpreter with **Ctrl+Shift+P -> Python: Select
Interpreter -> .venv**. `.vscode/settings.json` already points at it, so the
`import flask` warning disappears once the window is reloaded.

Then open <http://127.0.0.1:5000/>.

`setup_db.py` only needs running once. It adds the `Persona` and `TeamMember`
tables to `data/immunisation.db` and seeds them. It is idempotent — running it
again refreshes the rows rather than duplicating them.

---

## Project structure

```
StudioProjectB/
├── app.py               Flask routes, input validation, presentation only
├── db.py                Every SQL statement in the project
├── setup_db.py          Creates + seeds Persona and TeamMember
├── requirements.txt
├── data/
│   └── immunisation.db  Supplied database + the two added tables
├── templates/
│   ├── base.html        Shared shell: header, nav, footer
│   ├── _macros.html     Sortable-column-heading macro
│   ├── mission.html     Level 1B
│   ├── economy.html     Level 2B
│   └── above_average.html   Level 3B
└── static/
    └── css/style.css    Hand-written CSS
```

**No JavaScript is used anywhere.** Every interaction — filtering, sorting,
the collapsible notes panel — is a plain HTML form, a link handled by Flask, or
a native `<details>` element. This is deliberate: the project brief restricts
the major components to HTML, CSS, Python and SQL.

---

## SQL features used, and where

| Feature | Where |
|---------|-------|
| Multi-table `JOIN` (5 tables) | `get_infections_by_economy` — `InfectionData` → `Country` → `Economy`, `Country` → `Region`, `Infection_Type`, `CountryPopulation` |
| `GROUP BY` with aggregates | `get_economy_comparison` — `COUNT(DISTINCT …)`, `SUM(…)` per economic phase |
| Common table expression | `get_above_average_infections` — `global_stats` computes the world rate once |
| **`IN` subquery** | `get_above_average_infections` — `WHERE i.country IN (SELECT …)` selects the sub-dataset of countries above the benchmark |
| **Scalar subquery** | `(SELECT rate FROM global_stats)` — the result of the first query is what filters the second |
| **Correlated subquery** | the `coverage_pct` column reaches into `Vaccination` for the matching country, year, disease and antigen |
| **`NOT EXISTS`** | `get_global_rate_context` — counts above-average countries that filed *no* coverage figure at all |
| `UNION ALL` + ordered groups | pins the global benchmark row to the top of the Level 3 table regardless of the user's chosen sort |
| Sorting by similarity | `ORDER BY similarity` — distance from the global rate, computed in SQL as `ABS(rate − global_rate)` |
| Parameterised queries | `?` and named `:params` throughout — no user value is ever concatenated into SQL |

### Why the work is done in SQL rather than Python

Filtering, aggregating, sorting and limiting all happen in SQLite. For the
Level 3 page that means the database evaluates the global rate, selects the
sub-dataset, joins the vaccination figures, orders the result and returns the
requested number of rows — Python receives rows that are already final.

Doing it in Python would mean pulling all 207 countries across the connection
to display ten of them, re-implementing the aggregation by hand, and losing
SQLite's ability to use its indexes and its composite primary keys.

Python is used for what it is better at: validating the query string, choosing
safe defaults, whitelisting sort keys, and formatting numbers for display.

---

## Data anomalies found, and how they are handled

The supplied database is not clean. These were found by profiling it, and each
is dealt with **in SQL** rather than by post-processing:

| Anomaly | Handling |
|---------|----------|
| `Vaccination.target_num`, `doses` and `coverage` hold empty strings `''` instead of `NULL` for ~24% of rows (5,415 blank coverage values) | `typeof(coverage) = 'real'` guards — blanks are excluded, never coerced to `0` |
| 9 country codes appear in `Vaccination` with no matching `Country` row (`AIA`, `BON`, `COK`, `MSR`, `NIU`, `SAB`, `STA`, `TKL`, `WLF`) | inner joins to `Country` discard them |
| 10 countries in `Country` have no `InfectionData` rows at all | inner joins exclude them; a country that did not report is *not* shown as zero |
| Coverage values above 100% (1,312 rows) | shown as published with a footnote, not silently capped — doses can exceed the estimated target cohort |
| A rate needs a non-zero denominator | `population > 0` guard prevents divide-by-zero |
| Possible duplicate country/year rows | composite primary keys already prevent them; the aggregates use `SUM`/`AVG` so the queries stay correct regardless |

The Level 3 page reports the exclusions to the user rather than hiding them —
the "no coverage figure reported" figure exists so a blank cell is never read
as "zero vaccination".

---

## Notes on the two averages

The Level 3 page shows two different global figures and names the difference:

- **Population-weighted rate** — `SUM(cases) / SUM(population) × 100000`.
  Answers *"what is a randomly chosen person's risk?"*. **This is what the
  table compares against.**
- **Unweighted mean** — `AVG(country rate)`. Answers *"what is a typical
  country's rate?"*.

They differ because the first weights each country by its population. Quoting
one without saying which is the kind of framing this project is meant to avoid.

---

## Before submitting

- [ ] Edit the `TEAM` list in `setup_db.py` with real names and student numbers, then re-run it
- [ ] Replace the seeded `PERSONAS` with the team's own personas from the UCD milestones
- [ ] Write the mission-statement prose in `templates/mission.html` in the team's own words
- [ ] Confirm with course staff that Flask is on the approved library list
- [ ] Check `data/immunisation.db` is committed — the app will not run without it
