from __future__ import annotations

from flask import Blueprint, render_template, request

from .db import get_db
from .queries import (
    get_latest_infection_totals,
    get_reference_data,
    get_snapshot,
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

    result = {
        "rows": [],
        "summary": [],
        "metrics": {
            "countries_with_data": 0,
            "countries_meeting_target": 0,
            "average_coverage": None,
            "anomalous_coverage_count": 0,
        },
    }
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
        metrics=result["metrics"],
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
