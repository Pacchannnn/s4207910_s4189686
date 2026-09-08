"""Six distinct subtask pages. Forms work entirely through HTTP GET."""
from flask import Blueprint, render_template, request
from .db import get_db
from .queries import Queries, VACCINATION_SORTS, INFECTION_SORTS, IMPROVEMENT_SORTS, BENCHMARK_SORTS
from .validation import Filters, InvalidFilters

bp = Blueprint("pages", __name__)

def repository():
    return Queries(get_db())

def ids(options):
    return [str(row["value"]) for row in options]

def default_id(options, preferred):
    available = ids(options)
    return preferred if preferred in available else (available[0] if available else "")

def simple_page(template, title, **context):
    try:
        Filters(request.args, set())
    except InvalidFilters as error:
        return render_template("error.html",title="Check your filters",message=str(error)),400
    return render_template(template,title=title,**context)

@bp.get("/")
def home():
    q = repository()
    return simple_page("home.html","Vaccination and Disease Data",facts=q.facts(),diseases=q.disease_totals())

@bp.get("/mission")
def mission():
    q = repository()
    return simple_page("mission.html","Website Mission",**q.mission(),quality=q.quality())

def form_page(template, title, defaults, sorts, runner):
    q = repository()
    options = q.choices()
    years = ids(options["years"])
    defaults = {**defaults,
                "year":years[0] if years else "",
                "antigen":default_id(options["antigens"],"DTPCV1"),
                "infection":default_id(options["infections"],"MEA"),
                "economy":default_id(options["economies"],"3"),
                "start":years[-1] if years else "",
                "end":years[0] if years else ""}
    values = dict(defaults)
    values.update({k:v[:200] for k,v in request.args.items() if k in defaults})
    result, error, status = None, None, 200
    try:
        if not years:
            raise InvalidFilters("No selectable years are available in the database.")
        result = runner(q,options,defaults,values)
    except InvalidFilters as problem:
        error, status = str(problem), 400
    return render_template(template,title=title,options=options,values=values,sorts=sorts,
                           result=result,error=error),status

def sorting(f, sorts, defaults, values):
    values["sort"] = f.choice("sort",sorts,defaults["sort"])
    values["direction"] = f.choice("direction",("asc","desc"),defaults["direction"])
    return values["sort"],values["direction"]

@bp.get("/vaccinations")
def vaccinations():
    def run(q,o,d,v):
        f = Filters(request.args,{"year","antigen","country","region","minimum","threshold","sort","direction"})
        year = int(f.choice("year",ids(o["years"]),d["year"]))
        antigen = f.choice("antigen",ids(o["antigens"]),d["antigen"])
        country = f.choice("country",[""]+ids(o["countries"]),"")
        region = f.choice("region",[""]+ids(o["regions"]),"")
        minimum = f.number("minimum",90,0,100)
        threshold = f.number("threshold",90,0,100)
        v.update(minimum=f"{minimum:g}", threshold=f"{threshold:g}")
        sort,direction = sorting(f,VACCINATION_SORTS,d,v)
        return q.vaccinations(year,antigen,country,region,minimum,threshold,sort,direction)
    return form_page("vaccinations.html","Vaccination coverage",
                     {"country":"","region":"","minimum":90,"threshold":90,"sort":"country","direction":"asc"},
                     VACCINATION_SORTS,run)

@bp.get("/infections")
def infections():
    bounds_keys = {f"{prefix}_{column}" for prefix in ("min","max") for column in ("cases","population","rate")}
    def run(q,o,d,v):
        f = Filters(request.args,{"year","infection","economy","country","sort","direction"}|bounds_keys)
        year = int(f.choice("year",ids(o["years"]),d["year"]))
        infection = f.choice("infection",ids(o["infections"]),d["infection"])
        economy = f.choice("economy",ids(o["economies"]),d["economy"])
        country = f.text("country")
        bounds = {}
        for column in ("cases","population","rate"):
            bounds.update(f.range(column))
        sort,direction = sorting(f,INFECTION_SORTS,d,v)
        return q.infections(year,infection,economy,country,bounds,sort,direction)
    return form_page("infections.html","Infections by economic status",
                     {"country":"","sort":"rate","direction":"desc",**{key:"" for key in bounds_keys}},
                     INFECTION_SORTS,run)

@bp.get("/improvements")
def improvements():
    def run(q,o,d,v):
        f = Filters(request.args,{"start","end","antigen","limit","sort","direction"})
        start = int(f.choice("start",ids(o["years"]),d["start"]))
        end = int(f.choice("end",ids(o["years"]),d["end"]))
        if start>=end:
            raise InvalidFilters("Start year must be earlier than end year.")
        antigen = f.choice("antigen",ids(o["antigens"]),d["antigen"])
        limit = f.integer("limit",10,1,len(o["countries"]))
        sort,direction = sorting(f,IMPROVEMENT_SORTS,d,v)
        return q.improvements(start,end,antigen,limit,sort,direction)
    return form_page("improvements.html","Largest vaccination-rate improvements",
                     {"limit":10,"sort":"increase","direction":"desc"},IMPROVEMENT_SORTS,run)

@bp.get("/benchmark")
def benchmark():
    def run(q,o,d,v):
        f = Filters(request.args,{"year","infection","sort","direction"})
        year = int(f.choice("year",ids(o["years"]),d["year"]))
        infection = f.choice("infection",ids(o["infections"]),d["infection"])
        sort,direction = sorting(f,BENCHMARK_SORTS,d,v)
        return q.benchmark(year,infection,sort,direction)
    return form_page("benchmark.html","Countries above the global infection rate",
                     {"sort":"rate","direction":"desc"},BENCHMARK_SORTS,run)
