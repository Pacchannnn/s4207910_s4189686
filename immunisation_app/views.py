from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from .db import get_db
from .queries import (
    get_above_global_infections,
    get_infection_by_economy,
    get_personas,
    get_reference_data,
    get_team_members,
)
from .validation import parse_int, parse_nonnegative_number, valid_choice, valid_scalar


pages = Blueprint("pages", __name__)


@pages.get("/")
def mission():
    database = get_db()
    return render_template(
        "mission.html",
        active_page="mission",
        personas=get_personas(database),
        members=get_team_members(database),
    )


@pages.get("/mission")
def mission_alias():
    return redirect(url_for("pages.mission"), code=301)


@pages.get("/infections")
def infections():
    database = get_db()
    reference = get_reference_data(database)
    economy, economy_error = parse_int(
        request.args.get("economy"),
        reference["economies"][0]["id"],
        "Economic status",
    )
    infection = request.args.get("infection", "MEA")
    year, year_error = parse_int(
        request.args.get("year"), reference["years"][0]["value"], "Year"
    )
    search = request.args.get("search", "").strip()[:80]
    sort_by = request.args.get("sort", "rate")
    direction = request.args.get("direction", "desc")
    numeric_column = request.args.get("numeric_column", "")
    numeric_operator = request.args.get("numeric_operator", "gte")
    numeric_text = request.args.get("numeric_value", "").strip()
    numeric_value = None
    errors: list[str] = []

    if numeric_column not in {"", "cases", "population", "rate"}:
        errors.append("Choose a valid numeric filter column.")
    if numeric_operator not in {"gt", "gte", "lt", "lte", "eq"}:
        errors.append("Choose a valid numeric comparison.")
    if numeric_column:
        numeric_value, numeric_error = parse_nonnegative_number(numeric_text)
        if numeric_error:
            errors.append(numeric_error)
    elif numeric_text:
        errors.append("Choose a numeric filter column or clear its value.")

    if economy_error:
        errors.append(economy_error)
    if year_error:
        errors.append(year_error)
    if not valid_choice(economy, reference["economies"]):
        errors.append("Choose a valid economic status.")
    if not valid_choice(infection, reference["infections"]):
        errors.append("Choose a valid infection type.")
    if not valid_choice(year, reference["years"], "value"):
        errors.append("Choose a valid year.")
    if not valid_scalar(sort_by, {"country", "cases", "population", "rate"}):
        errors.append("Choose a valid sort field.")
    if not valid_scalar(direction, {"asc", "desc"}):
        errors.append("Choose a valid sort direction.")

    result = {"rows": [], "summary": [], "selected_summary": None}
    if not errors:
        result = get_infection_by_economy(
            database,
            economy_id=economy,
            infection_id=infection,
            year=year,
            search=search,
            sort_by=sort_by,
            direction=direction,
            numeric_column=numeric_column,
            numeric_operator=numeric_operator,
            numeric_value=numeric_value,
        )

    selected_infection = next(
        (item for item in reference["infections"] if item["id"] == infection), None
    )
    return render_template(
        "infections.html",
        active_page="infections",
        reference=reference,
        filters={
            "economy": economy,
            "infection": infection,
            "year": year,
            "search": search,
            "numeric_column": numeric_column,
            "numeric_operator": numeric_operator,
            "numeric_value": numeric_text,
            "sort": sort_by,
            "direction": direction,
        },
        infection_name=selected_infection["name"] if selected_infection else infection,
        errors=errors,
        rows=result["rows"],
        summary=result["summary"],
        selected_summary=result["selected_summary"],
    )


@pages.get("/infection-benchmark")
def infection_benchmark():
    database = get_db()
    reference = get_reference_data(database)
    infection = request.args.get("infection", "MEA")
    year, year_error = parse_int(
        request.args.get("year"), reference["years"][0]["value"], "Year"
    )
    errors: list[str] = []
    sort_by = request.args.get("sort", "rate")
    direction = request.args.get("direction", "desc")
    if not valid_scalar(sort_by, {"country", "cases", "population", "rate"}):
        errors.append("Choose a valid sort field.")
    if not valid_scalar(direction, {"asc", "desc"}):
        errors.append("Choose a valid sort direction.")

    if year_error:
        errors.append(year_error)
    if not valid_choice(infection, reference["infections"]):
        errors.append("Choose a valid infection type.")
    if not valid_choice(year, reference["years"], "value"):
        errors.append("Choose a valid year.")

    rows = []
    if not errors:
        rows = get_above_global_infections(
            database, infection_id=infection, year=year,
            sort_by=sort_by, direction=direction,
        )

    global_row = rows[0] if rows else None
    country_rows = rows[1:] if len(rows) > 1 else []
    return render_template(
        "infection_benchmark.html",
        active_page="infection_benchmark",
        reference=reference,
        filters={"infection": infection, "year": year, "sort": sort_by, "direction": direction},
        errors=errors,
        global_row=global_row,
        country_rows=country_rows,
    )
