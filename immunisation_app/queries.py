"""All retrieval, filtering, joining, ranking and aggregation are performed in SQL."""
VACCINATION_SORTS = {
    "country": "Country", "region": "Region", "coverage": "Coverage (%)",
    "antigen": "Antigen", "year": "Year", "coverage_source": "Coverage source"
}
INFECTION_SORTS = {
    "country": "Country", "infection": "Infection type", "economy": "Economic status",
    "year": "Year", "cases": "Reported cases", "population": "Population",
    "rate": "Cases per 100,000"
}
IMPROVEMENT_SORTS = {
    "increase": "Rate increase", "country": "Country",
    "start_rate": "Start rate", "end_rate": "End rate",
    "start_doses": "Start doses", "end_doses": "End doses",
    "start_population": "Start population", "end_population": "End population"
}
BENCHMARK_SORTS = {
    "rate": "Infection rate", "country": "Country", "excess": "Excess above benchmark",
    "cases": "Reported cases", "population": "Population"
}

def order_by(sort, direction, allowed):
    # SQL identifiers cannot be bound. Only fixed identifiers from this whitelist
    # reach SQL; all actual filter values use parameter binding.
    if sort not in allowed or direction not in ("asc", "desc"):
        raise ValueError("Invalid sort choice.")
    return f"{sort} IS NULL ASC, {sort} {direction.upper()}, country ASC"

class Queries:
    def __init__(self, connection):
        self.db = connection

    def all(self, sql, parameters=()):
        return self.db.execute(sql, parameters).fetchall()

    def one(self, sql, parameters=()):
        return self.db.execute(sql, parameters).fetchone()

    def choices(self):
        return {
            "years": self.all("SELECT year AS value, year AS label FROM (SELECT year FROM Vaccination UNION SELECT year FROM InfectionData) ORDER BY year DESC"),
            "countries": self.all("SELECT CountryID AS value,name AS label FROM Country ORDER BY name"),
            "regions": self.all("SELECT RegionID AS value,region AS label FROM Region ORDER BY region"),
            "economies": self.all("SELECT economyID AS value,phase AS label FROM Economy ORDER BY economyID"),
            "antigens": self.all("SELECT AntigenID AS value,AntigenID || ' - ' || name AS label FROM Antigen ORDER BY AntigenID"),
            "infections": self.all("SELECT id AS value,description AS label FROM Infection_Type ORDER BY description")
        }

    def facts(self):
        return self.one("""
            SELECT
             (SELECT MIN(YearID) FROM YearDate) AS first_year,
             (SELECT MAX(YearID) FROM YearDate) AS last_year,
             (SELECT COUNT(*) FROM Country) AS countries,
             (SELECT COUNT(*) FROM Infection_Type) AS infections,
             (SELECT COUNT(*) FROM Antigen) AS antigens,
             (SELECT COUNT(*) FROM Vaccination) AS vaccination_records,
             (SELECT COUNT(*) FROM InfectionData) AS infection_records,
             (SELECT SUM(doses) FROM Vaccination WHERE typeof(doses) IN ('integer','real')) AS total_doses,
             (SELECT SUM(cases) FROM InfectionData WHERE typeof(cases) IN ('integer','real')) AS total_cases
        """)

    def disease_totals(self):
        return self.all("""
            SELECT t.description AS disease, SUM(i.cases) AS cases,
                   MIN(i.year) AS first_year, MAX(i.year) AS last_year
            FROM Infection_Type t LEFT JOIN InfectionData i ON i.inf_type=t.id
                AND typeof(i.cases) IN ('integer','real')
            GROUP BY t.id,t.description ORDER BY cases DESC,t.description
        """)

    def mission(self):
        return {
            "personas": self.all("SELECT name,profile,goal,difficulty,status,provenance FROM Persona ORDER BY persona_id"),
            "team": self.all("SELECT name,student_id FROM TeamMember ORDER BY student_id DESC")
        }

    def quality(self):
        return self.one("""
            SELECT
            (SELECT COUNT(*) FROM Vaccination WHERE typeof(doses) NOT IN ('real','integer')) AS missing_doses,
            (SELECT COUNT(*) FROM Vaccination WHERE typeof(coverage) NOT IN ('real','integer')) AS missing_coverage,
            (SELECT COUNT(*) FROM Vaccination WHERE typeof(coverage) IN ('real','integer') AND (coverage<0 OR coverage>100)) AS invalid_coverage,
            (SELECT COUNT(*) FROM Vaccination v WHERE NOT EXISTS
                (SELECT 1 FROM Country c WHERE c.CountryID=v.country)) AS orphan_vaccinations,
            (SELECT COUNT(*) FROM Country c WHERE NOT EXISTS
                (SELECT 1 FROM Economy e WHERE e.economyID=c.economy)) AS unknown_economies
        """)

    def vaccinations(self, year, antigen, country, region, minimum, threshold, sort, direction):
        params = {"year":year, "antigen":antigen, "country":country, "region":region,
                  "minimum":minimum, "threshold":threshold}
        rows = self.all(f"""
            SELECT country,country_id,region,antigen,year,coverage,coverage_source,anomaly,source_rows FROM (
            SELECT c.name AS country, c.CountryID AS country_id, r.region,
                   v.antigen, v.year, v.coverage, v.coverage_source, v.anomaly, v.source_rows
            FROM v_vaccination v
            JOIN Country c ON c.CountryID=v.country
            JOIN Region r ON r.RegionID=c.region
            WHERE v.year=:year AND v.antigen=:antigen
              AND (:country='' OR c.CountryID=:country)
              AND (:region='' OR c.region=:region)
              AND v.coverage >= :minimum
            )
            ORDER BY {order_by(sort, direction, VACCINATION_SORTS)}
        """, params)
        # Region summaries intentionally include every country of a chosen region,
        # including countries with missing records, regardless of detail minimum.
        regions = self.all("""
            SELECT r.region, :antigen AS antigen, :year AS year,
                   COUNT(c.CountryID) AS total,
                   COUNT(v.coverage) AS available,
                   COUNT(c.CountryID)-COUNT(v.coverage) AS missing,
                   COALESCE(SUM(v.coverage >= :threshold),0) AS meeting,
                   AVG(v.coverage) AS mean_coverage,
                   COALESCE(SUM(v.anomaly),0) AS anomalies,
                   COALESCE(SUM(v.coverage_source='Calculated'),0) AS calculated,
                   100.0*SUM(v.coverage >= :threshold)/NULLIF(COUNT(v.coverage),0) AS meeting_percent
            FROM Region r JOIN Country c ON c.region=r.RegionID
            LEFT JOIN v_vaccination v ON v.country=c.CountryID
                AND v.antigen=:antigen AND v.year=:year
            WHERE (:region='' OR r.RegionID=:region)
            GROUP BY r.RegionID,r.region
            ORDER BY r.region
        """, params)
        excluded = self.one("""
            SELECT COUNT(*) AS count FROM Vaccination v
            WHERE v.antigen=:antigen AND v.year=:year AND NOT EXISTS
            (SELECT 1 FROM Country c WHERE c.CountryID=v.country)
        """, params)["count"]
        return {"rows":rows, "regions":regions, "excluded":excluded}

    def infections(self, year, infection, economy, country, bounds, sort, direction):
        params = {"year":year,"infection":infection,"economy":economy,"country":country}
        clauses = []
        for column in ("cases", "population", "rate"):
            for prefix, operator in (("min", ">="), ("max", "<=")):
                key = prefix + "_" + column
                if bounds.get(key) is not None:
                    clauses.append(f"{column} {operator} :{key}")
                    params[key] = bounds[key]
        # instr makes %, _ and quotes literal substring characters.
        extra = "".join(" AND " + clause for clause in clauses)
        rows = self.all(f"""
            SELECT country, infection, economy, year, cases, population, rate
            FROM v_infection
            WHERE year=:year AND inf_type=:infection AND economy_id=:economy
              AND instr(lower(country),lower(:country))>0 {extra}
            ORDER BY {order_by(sort,direction,INFECTION_SORTS)}
        """, params)
        summary = self.all("""
            SELECT e.phase AS economy,:year AS year,
                   t.description AS infection,
                   COUNT(i.country_id) AS countries,
                   COUNT(i.cases) AS reporting,
                   SUM(i.cases) AS cases,
                   SUM(CASE WHEN i.rate IS NOT NULL THEN i.cases END) AS matched_cases,
                   SUM(CASE WHEN i.rate IS NOT NULL THEN i.population END) AS population,
                   SUM(CASE WHEN i.rate IS NOT NULL THEN i.cases END) /
                   NULLIF(SUM(CASE WHEN i.rate IS NOT NULL THEN i.population END),0)*100000.0 AS rate
            FROM Economy e CROSS JOIN Infection_Type t
            LEFT JOIN v_infection i ON i.economy_id=e.economyID AND i.year=:year AND i.inf_type=:infection
            WHERE t.id=:infection
            GROUP BY e.economyID,e.phase,t.description ORDER BY e.economyID
        """,params)
        unknown = self.one("""
            SELECT COUNT(*) AS count FROM v_infection
            WHERE year=:year AND inf_type=:infection AND economy_id IS NULL
        """,params)["count"]
        return {"rows":rows,"summary":summary,"unknown_economy":unknown}

    def improvements(self, start, end, antigen, limit, sort, direction):
        params = {"start":start,"end":end,"antigen":antigen,"limit":limit}
        cte = """
            WITH eligible AS (
                SELECT c.name AS country, c.CountryID AS country_id,
                       s.doses AS start_doses, e.doses AS end_doses,
                       ps.population AS start_population, pe.population AS end_population,
                       s.doses/ps.population*100.0 AS start_rate,
                       e.doses/pe.population*100.0 AS end_rate,
                       (e.doses/pe.population-s.doses/ps.population)*100.0 AS increase
                FROM Country c
                JOIN v_vaccination s ON s.country=c.CountryID AND s.year=:start AND s.antigen=:antigen
                JOIN v_vaccination e ON e.country=c.CountryID AND e.year=:end AND e.antigen=:antigen
                JOIN CountryPopulation ps ON ps.country=c.CountryID AND ps.year=:start
                JOIN CountryPopulation pe ON pe.country=c.CountryID AND pe.year=:end
                WHERE s.doses IS NOT NULL AND e.doses IS NOT NULL
                  AND typeof(ps.population) IN ('real','integer') AND ps.population>0 AND ps.population<1e300
                  AND typeof(pe.population) IN ('real','integer') AND pe.population>0 AND pe.population<1e300
                  AND EXISTS (SELECT 1 FROM Antigen a WHERE a.AntigenID=s.antigen)
            )
        """
        rows = self.all(cte + f"""
            SELECT country,start_doses,end_doses,start_population,end_population,
                   start_rate,end_rate,increase,:start AS start_year,:end AS end_year,:antigen AS antigen
            FROM (SELECT * FROM eligible WHERE increase>0 ORDER BY increase DESC,country ASC LIMIT :limit)
            ORDER BY {order_by(sort,direction,IMPROVEMENT_SORTS)}
        """,params)
        stats = self.one(cte + """
            SELECT COUNT(*) AS eligible,
                   COALESCE(SUM(increase>0),0) AS improving,
                   COALESCE(SUM(increase<0),0) AS declining,
                   COALESCE(SUM(increase=0),0) AS unchanged,
                   MAX(increase) AS max_increase,
                   (SELECT COUNT(*) FROM Country)-COUNT(*) AS excluded
            FROM eligible
        """,params)
        return {"rows":rows, **dict(stats)}

    def benchmark(self, year, infection, sort, direction):
        params = {"year":year,"infection":infection}
        cte = """
            WITH valid AS (
                SELECT country, cases, population, rate, infection, year
                FROM v_infection
                WHERE year=:year AND inf_type=:infection AND rate IS NOT NULL
            ), global_rate AS (
                SELECT SUM(cases) AS cases,SUM(population) AS population,
                       SUM(cases)/NULLIF(SUM(population),0)*100000.0 AS rate,
                       COUNT(*) AS countries FROM valid
            )
        """
        benchmark = self.one(cte + "SELECT cases,population,rate,countries FROM global_rate",params)
        rows = self.all(cte + f"""
            SELECT country,infection,year,cases,population,rate,
                   rate-(SELECT rate FROM global_rate) AS excess
            FROM valid WHERE rate>(SELECT rate FROM global_rate)
            ORDER BY {order_by(sort,direction,BENCHMARK_SORTS)}
        """,params)
        source_count = self.one("""
            SELECT COUNT(*) AS count FROM InfectionData WHERE year=:year AND inf_type=:infection
        """,params)["count"]
        return {"global":benchmark,"rows":rows,"excluded":source_count-benchmark["countries"]}
