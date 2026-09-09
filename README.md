# Immunisation data explorer

Task A Flask and SQLite website by Le Chi Bach (s4207910):
Home (1A), Vaccinations (2A), and Vaccination improvement (3A).
This branch contains the shared infrastructure required by these three pages.
Task B pages are outside this build. The complete six-page refactor remains
available locally on the codex/refactor-v2 branch.

Team: Le Chi Bach (s4207910) and Nguyen Tran Ba Trong (s4189686).

## Run on Windows

Open a terminal in this project folder. Create a local Python environment:

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/. Stop the server with Ctrl+C.
On subsequent runs, use only the final command.
The virtual environment is machine-local and must not be committed.

## Verification

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Project files

- `immunisation_app/`: Flask routes, SQL, validation, templates and static assets.
- `database/immunisation.db`: application dataset and team/persona data.
- `tests/`: query, route and validation regression tests.
- `docs/`: requirements mapping, design decisions and verification records.
- `app.py`: local Waitress server; `wsgi.py` and `Procfile`: deployment entry points.

The interface uses server-rendered GET forms without application JavaScript.
Roboto is requested from Google Fonts, with system-font fallbacks when offline.
Set a private `SECRET_KEY` environment variable before public deployment.
