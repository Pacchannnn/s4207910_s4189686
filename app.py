"""
app.py  -  COSC3106 Python Programming Studio, Studio Project
=============================================================
"Investigating Preventable Infectious Diseases"

SUB-TASK B  (Levels 1, 2 and 3)
-------------------------------
  Level 1B  /mission        Mission Statement - purpose, how to use the site,
                            personas and team members, all read from the
                            database.
  Level 2B  /economy        Focused view of infection data by economic status.
  Level 3B  /above-average  Countries whose reported infection rate exceeds the
                            global rate.

Run with:
    python app.py
then open http://127.0.0.1:5000/

All SQL lives in db.py.  This module is only routing, input validation and
presentation.
"""

from flask import Flask, render_template, request, redirect, url_for

import db

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------
def _as_int(value, default):
    """Query strings are user-controlled; coerce or fall back, never crash."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _valid(value, allowed, default):
    """Constrain a value to a known-good set."""
    return value if value in allowed else default


@app.context_processor
def inject_globals():
    """Make the team available to every template (used in the page footer)."""
    return {"team": db.get_team_members()}


@app.template_filter("num")
def format_number(value, places=0):
    """Thousands separators, and an em dash for anything missing."""
    if value is None:
        return "—"
    try:
        return "{:,.{p}f}".format(float(value), p=places)
    except (TypeError, ValueError):
        return str(value)


# ===========================================================================
# LEVEL 1 - SUB-TASK B : Mission Statement
# ===========================================================================
@app.route("/")
def index():
    return redirect(url_for("mission"))


@app.route("/mission")
def mission():
    return render_template(
        "mission.html",
        personas=db.get_personas(),
        members=db.get_team_members(),
        scope=db.get_scope_summary(),
        diseases=db.get_infection_types(),
        economies=db.get_economies(),
        quality=db.get_data_quality_notes(),
    )


# ===========================================================================
# LEVEL 2 - SUB-TASK B : Infection data by economic status
# ===========================================================================
@app.route("/economy")
def economy():
    economies = db.get_economies()
    diseases = db.get_infection_types()
    years = db.get_years()

    economy_ids = [r["economyID"] for r in economies]
    disease_ids = [r["id"] for r in diseases]

    # Defaults chosen so the page is never empty on first load.
    economy_id = _valid(_as_int(request.args.get("economy"), economy_ids[-1]),
                        economy_ids, economy_ids[-1])
    inf_type = _valid(request.args.get("disease"), disease_ids, "MEA")
    year = _valid(_as_int(request.args.get("year"), years[0]), years, years[0])

    sort = _valid(request.args.get("sort"), db.L2_SORT, "cases_per_100k")
    direction = _valid(request.args.get("dir"), ("asc", "desc"), "desc")

    s_sort = _valid(request.args.get("ssort"), db.L2_SUMMARY_SORT, "cases")
    s_dir = _valid(request.args.get("sdir"), ("asc", "desc"), "desc")

    rows = db.get_infections_by_economy(economy_id, inf_type, year,
                                        sort=sort, direction=direction)
    summary = db.get_economy_comparison(inf_type, year,
                                        sort=s_sort, direction=s_dir)

    selected_economy = next(r["phase"] for r in economies
                            if r["economyID"] == economy_id)
    selected_disease = next(r["description"] for r in diseases
                            if r["id"] == inf_type)

    # Totals for the selected economic phase, taken from the summary table so
    # the two tables can never disagree with each other.
    phase_total = next((r for r in summary
                        if r["economic_phase"] == selected_economy), None)

    return render_template(
        "economy.html",
        economies=economies, diseases=diseases, years=years,
        economy_id=economy_id, inf_type=inf_type, year=year,
        selected_economy=selected_economy, selected_disease=selected_disease,
        sort=sort, direction=direction, s_sort=s_sort, s_dir=s_dir,
        rows=rows, summary=summary, phase_total=phase_total,
    )


# ===========================================================================
# LEVEL 3 - SUB-TASK B : Above-average infection rate
# ===========================================================================
LIMIT_CHOICES = (10, 25, 50, 0)  # 0 == show every qualifying country


@app.route("/above-average")
def above_average():
    diseases = db.get_infection_types()
    years = db.get_years()
    disease_ids = [r["id"] for r in diseases]

    inf_type = _valid(request.args.get("disease"), disease_ids, "MEA")
    year = _valid(_as_int(request.args.get("year"), years[0]), years, years[0])

    # The antigen list depends on the disease, so it is resolved after the
    # disease is known.  If the user switches disease while an antigen from the
    # previous one is still in the query string, fall back to the first valid
    # antigen rather than returning an empty comparison column.
    antigens = db.get_antigens_for_disease(inf_type)
    antigen_ids = [r["AntigenID"] for r in antigens]
    antigen = _valid(request.args.get("antigen"), antigen_ids, antigen_ids[0])

    sort = _valid(request.args.get("sort"), db.L3_SORT, "cases_per_100k")
    direction = _valid(request.args.get("dir"), ("asc", "desc"), "desc")
    limit = _valid(_as_int(request.args.get("limit"), 25), LIMIT_CHOICES, 25)

    rows = db.get_above_average_infections(inf_type, year, antigen,
                                           sort=sort, direction=direction,
                                           limit=limit or None)
    context = db.get_global_rate_context(inf_type, year, antigen)

    selected_disease = next(r["description"] for r in diseases
                            if r["id"] == inf_type)
    selected_antigen = next(r["name"] for r in antigens
                            if r["AntigenID"] == antigen)

    return render_template(
        "above_average.html",
        diseases=diseases, years=years, antigens=antigens,
        limit_choices=LIMIT_CHOICES,
        inf_type=inf_type, year=year, antigen=antigen,
        sort=sort, direction=direction, limit=limit,
        rows=rows, context=context,
        selected_disease=selected_disease, selected_antigen=selected_antigen,
    )


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
