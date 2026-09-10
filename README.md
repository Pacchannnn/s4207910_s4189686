# Immunisation Lens

A Python/Flask application for exploring reported preventable infections using
SQLite. This is the **Sub-Task B** submission: three pages provide the mission,
personas and team (`/`), infection data by economic status (`/infections`), and
the countries reporting above the weighted global infection rate
(`/infection-benchmark`).

## Requirements

- Python with `pip` and `venv` (tested with Python 3.14).
- Flask and Waitress, pinned in `requirements.txt`.
- The supplied `database/immunisation.db`. Keep this file in the project: it
  contains the source data needed to run the application. SQLite support is
  included with Python; no separate database server is required.

## Setup and run

Open a terminal in this directory. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Using the environment's Python directly does not require activation. On macOS or
Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

Open http://localhost:5000. The application runs through Waitress on port **5000**
by default; the `PORT` environment variable can override it. Stop with Ctrl+C.

## Tests

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -q
```

Tests use temporary database copies. Current verification and remaining review
items are recorded in `docs/VERIFICATION.md` and `docs/KNOWN_ISSUES.md`.

## Selected UI contributions

The Infections page's sortable table headers, row-header semantics and native
methodology disclosure were adapted from the member-supplied
`demo_complete_project` templates (`_macros.html` and `economy.html`). They use
this project's existing filter parameters and styling. The main project's Flask
architecture, SQL calculations and database remain the foundation; this note
does not attribute the backend or integration tests to the member.

## Main structure

```text
app.py                 Application entry point
wsgi.py                WSGI entry point
requirements.txt       Python dependencies
database/immunisation.db
immunisation_app/
  __init__.py          Flask application factory
  db.py                Database connections and project-table initialization
  queries.py           SQL queries and calculations
  views.py             Routes and form handling
  validation.py        Input validation
  templates/           Jinja pages and shared components
  static/              Styles and static resources
tests/                 Query, route and validation tests
docs/                  Requirements, verification and known issues
```

## Scope

The Sub-Task A pages (landing page, vaccination coverage explorer and
vaccination improvement ranking) were removed from this submission, along with
their queries, templates, styles and tests. The Mission page is now served at
`/`, and the previous `/mission` address redirects there. The supplied database
is unchanged apart from the project persona rows, which describe the pages that
remain. `docs/REQUIREMENTS_MATRIX.md` records the removal in full.
