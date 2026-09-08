from __future__ import annotations

from flask import Blueprint, render_template, request

from .db import get_db
from .queries import (
    get_above_global_infections,
    get_infection_by_economy,
    get_latest_infection_totals,
    get_personas,
    get_reference_data,
    get_snapshot,
    get_team_members,
    get_vaccination_improvements,
    get_vaccination_view,
)
from .validation import parse_int, valid_choice, valid_scalar


pages = Blueprint("pages", __name__)


@pages.get("/")
def home():
    database = get_db()
    snapshot = get_snapshot(database)
    infection_totals = get_latest_infection_totals(database)
    return render_template(
        "home.html",
        active_page="home",
        snapshot=snapshot,
        infection_totals=infection_totals,
    )


@pages.get("/mission")
def mission():
    database = get_db()
    return render_template(
        "mission.html",
        active_page="mission",
        personas=get_personas(database),
        members=get_team_members(database),
    )


@pages.get("/vaccinations")
def vaccinations():
    database = get_db()
    reference = get_reference_data(database)
    antigen = request.args.get("antigen", "MCV1")
    year, year_error = parse_int(
        request.args.get("year"), reference["years"][0]["value"], "Year"
    )
    country = request.args.get("country", "")
    region = request.args.get("region", "")
    sort_by = request.args.get("sort", "coverage")
    direction = request.args.get("direction", "desc")
    errors: list[str] = []

    if year_error:
        errors.append(year_error)
    if not valid_choice(antigen, reference["antigens"]):
        errors.append("Choose a valid antigen.")
    if not valid_choice(year, reference["years"], "value"):
        errors.append("Choose a valid year.")
    if country and not valid_choice(country, reference["countries"]):
        errors.append("Choose a valid country.")
    if region and not valid_choice(region, reference["regions"]):
        errors.append("Choose a valid region.")
    if not valid_scalar(
        sort_by, {"coverage", "country", "region", "doses", "target"}
    ):
        errors.append("Choose a valid sort field.")
    if not valid_scalar(direction, {"asc", "desc"}):
        errors.append("Choose a valid sort direction.")

    result = {"rows": [], "summary": []}
    if not errors:
        result = get_vaccination_view(
            database,
            antigen=antigen,
            year=year,
            country=country,
            region=region,
            sort_by=sort_by,
            direction=direction,
        )

    return render_template(
        "vaccinations.html",
        active_page="vaccinations",
        reference=reference,
        filters={
            "antigen": antigen,
            "year": year,
            "country": country,
            "region": region,
            "sort": sort_by,
            "direction": direction,
        },
        errors=errors,
        rows=result["rows"],
        summary=result["summary"],
    )


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
    errors: list[str] = []

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
            "sort": sort_by,
            "direction": direction,
        },
        infection_name=selected_infection["name"] if selected_infection else infection,
        errors=errors,
        rows=result["rows"],
        summary=result["summary"],
        selected_summary=result["selected_summary"],
    )


@pages.get("/vaccination-improvement")
def vaccination_improvement():
    database = get_db()
    reference = get_reference_data(database)
    antigen = request.args.get("antigen", "MCV1")
    start_year, start_year_error = parse_int(
        request.args.get("start_year"), 2000, "Start year"
    )
    end_year, end_year_error = parse_int(
        request.args.get("end_year"), 2024, "End year"
    )
    limit, limit_error = parse_int(
        request.args.get("limit"), 10, "Number of countries"
    )
    sort_by = request.args.get("sort", "improvement")
    direction = request.args.get("direction", "desc")
    errors: list[str] = []

    if start_year_error:
        errors.append(start_year_error)
    if end_year_error:
        errors.append(end_year_error)
    if limit_error:
        errors.append(limit_error)
    if not valid_choice(antigen, reference["antigens"]):
        errors.append("Choose a valid antigen.")
    if not valid_choice(start_year, reference["years"], "value"):
        errors.append("Choose a valid start year.")
    if not valid_choice(end_year, reference["years"], "value"):
        errors.append("Choose a valid end year.")
    if end_year <= start_year:
        errors.append("End year must be later than start year.")
    if limit < 3 or limit > 50:
        errors.append("Number of countries must be between 3 and 50.")
    if not valid_scalar(
        sort_by, {"improvement", "end_rate", "start_rate", "country"}
    ):
        errors.append("Choose a valid sort field.")
    if not valid_scalar(direction, {"asc", "desc"}):
        errors.append("Choose a valid sort direction.")

    rows = []
    if not errors:
        rows = get_vaccination_improvements(
            database,
            antigen=antigen,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            sort_by=sort_by,
            direction=direction,
        )

    return render_template(
        "vaccination_improvement.html",
        active_page="vaccination_improvement",
        reference=reference,
        filters={
            "antigen": antigen,
            "start_year": start_year,
            "end_year": end_year,
            "limit": limit,
            "sort": sort_by,
            "direction": direction,
        },
        errors=errors,
        rows=rows,
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

    if year_error:
        errors.append(year_error)
    if not valid_choice(infection, reference["infections"]):
        errors.append("Choose a valid infection type.")
    if not valid_choice(year, reference["years"], "value"):
        errors.append("Choose a valid year.")

    rows = []
    if not errors:
        rows = get_above_global_infections(
            database, infection_id=infection, year=year
        )

    global_row = rows[0] if rows else None
    country_rows = rows[1:] if len(rows) > 1 else []
    return render_template(
        "infection_benchmark.html",
        active_page="infection_benchmark",
        reference=reference,
        filters={"infection": infection, "year": year},
        errors=errors,
        global_row=global_row,
        country_rows=country_rows,
    )

