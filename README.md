# Vaccination & Disease Data

Six Flask pages for exploring the supplied vaccination and infectious-disease database.
The entry point is **app.py**. Open the website through Flask, not by opening an HTML template.

## Run on Windows

Open CMD or PowerShell in this directory:

```text
cd "C:\Users\Dell G15\OneDrive\Documents\RMIT\Sem 2 - 2026\Python\Final Asm\Final Optimized"
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

The virtual environment and packages are already installed on the current machine.
On subsequent runs, only the last command is needed.

Open **http://127.0.0.1:5067/** and leave the server terminal running.
Press Ctrl+C in that terminal to stop a server you started there.
VS Code is optional.
If this port is occupied, use a different port without stopping unrelated servers:

PowerShell:
```powershell
$env:PORT = "5068"
.venv\Scripts\python.exe app.py
```

CMD:
```bat
set PORT=5068
.venv\Scripts\python.exe app.py
```

## Structure

```text
Final Optimized/
  app.py                         Local entry point, port 5067
  requirements.txt               Flask runtime dependency
  requirements-test.txt          Optional browser-test dependency
  README.md
  database/
    immunisation.db              Supplied data copy + personas/team + derived SQL views
    extensions.sql               Reproducible additional schema
  immunisation_app/
    __init__.py                  Application factory, errors and security headers
    db.py                        Request-scoped read-only connections
    queries.py                   Parameterized SQL for all six pages
    routes.py                    Routes and GET forms
    validation.py                Input validation and sort validation
    templates/
      base.html                  Shared navigation/footer
      home.html                  1A
      mission.html               1B
      vaccinations.html          2A
      infections.html            2B
      improvements.html          3A
      benchmark.html             3B
      macros.html                Shared form/table helpers
      error.html                 Error page
    static/
      style.css                  Shared responsive styling
      icons/                     Local SVG icons and license
      fonts/                     Local Roboto font and license
  tests/
    test_app.py                  HTTP, validation, security and link checks
    test_queries.py              Synthetic arithmetic and missing-data regressions
    test_oracles.py              Raw-table numerical cross-checks
  tools/
    prepare_database.py          Rebuild additions; preserves source records and student edits
    audit_source.py              Compare original table hashes
    browser_check.py             Real-browser checks with JavaScript disabled
  docs/
    REQUIREMENTS.md              Requirement-to-implementation matrix
    VERIFICATION.md              Numerical policy, checks and limitations
    source_manifest.json         Original source-table fingerprints
    browser-results.json         Generated browser results (ignored; recreate with tool)
    screenshots/                 Generated screenshots (ignored; recreate with tool)
```

The .venv directory is machine-local and is not application source. Recreate it on another machine.
There is no application JavaScript or CDN dependency. Fonts and icons are served locally.
The language menu supports English, Vietnamese, Spanish, French, German and simplified Chinese.
Interface translations do not translate all source descriptions or country names.

## Reproduce the checks

```text
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tools/audit_source.py --source "C:\Users\Dell G15\OneDrive\Documents\RMIT\Sem 2 - 2026\Python\Final\immunisation-2.db"
```

Optional real-browser checks require Microsoft Edge and the local server on port 5067:

```text
.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.venv\Scripts\python.exe tools/browser_check.py
```

## Sample views

- 2A: http://127.0.0.1:5067/vaccinations?antigen=RCV1&year=2000&minimum=90
- 2B: http://127.0.0.1:5067/infections?economy=4&infection=MEA&year=2022
- 3A: http://127.0.0.1:5067/improvements?antigen=DTPCV1&start=2000&end=2024&limit=10
- 3B: http://127.0.0.1:5067/benchmark?infection=MEA&year=2020

## Database preparation

The delivered database is ready to use. Only run the following if rebuilding derived views
or adding the supplied personas/team to a fresh copy of the course database:

```text
.venv\Scripts\python.exe tools/prepare_database.py
```

Preparation uses INSERT OR IGNORE for personas/team and does not overwrite edited values.
The original nine source tables are never updated. Runtime connections are read-only.

## Provenance

Technical implementation is AI-assisted, adapted from the supplied Framework Final and astra references.
The mission personas are supplied draft examples, not validated interview participants.
No project log, survey, Teams history, contribution record or submission evidence is fabricated.
The PDF defines website requirements; this folder does not assert completion of separate presentation
or submission requirements outside that PDF.

## Git and packaging

The local working folder stays named Final Optimized. The supplied six-page PDF does not
specify a submission archive name. Confirm the current Canvas upload instructions before packaging.
The GitHub repository is named s4207910_s4189686 and uses immunisation_app as its package.
The remote version is older: its templates, routes, dependencies and JavaScript must not be
mixed into this version without integration and tests. This folder has no Git history.
Do not represent this already-complete AI-assisted reference as incremental student authorship.
Commit actual reviewed changes from the present onward, with accurate messages and attribution.

Keep requirements-test.txt, tests, tools, and docs/source_manifest.json: they support reproducible
verification. Exclude .venv, caches, logs and generated browser outputs using .gitignore.
Run tests with PYTHONDONTWRITEBYTECODE=1 to avoid creating new local bytecode caches.
