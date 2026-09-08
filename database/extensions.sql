-- Additions only: the nine supplied tables and their records are preserved.
CREATE TABLE IF NOT EXISTS Persona (
    persona_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    profile TEXT NOT NULL,
    goal TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Unvalidated draft',
    provenance TEXT NOT NULL DEFAULT 'Supplied by the student; not based on interviews'
);
CREATE TABLE IF NOT EXISTS TeamMember (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS astra_vaccination_filter
    ON Vaccination(antigen, year, country);
CREATE INDEX IF NOT EXISTS astra_infection_filter
    ON InfectionData(inf_type, year, country);

-- Rebuild derived views only. Original tables and values are never updated.
DROP VIEW IF EXISTS v_vaccination;
CREATE VIEW v_vaccination AS
WITH grouped AS (
    SELECT antigen, country, year,
        SUM(CASE WHEN typeof(doses) IN ('integer','real')
            AND doses >= 0 AND doses < 1e300 THEN doses END) AS doses,
        SUM(CASE WHEN typeof(target_num) IN ('integer','real')
            AND target_num > 0 AND target_num < 1e300 THEN target_num END) AS target_num,
        AVG(CASE WHEN typeof(coverage) IN ('integer','real')
            AND coverage >= 0 AND coverage < 1e300 THEN coverage END) AS reported,
        SUM(CASE WHEN typeof(doses) IN ('integer','real') AND doses >= 0 AND doses < 1e300
                  AND typeof(target_num) IN ('integer','real') AND target_num > 0 AND target_num < 1e300
                 THEN doses END) AS paired_doses,
        SUM(CASE WHEN typeof(doses) IN ('integer','real') AND doses >= 0 AND doses < 1e300
                  AND typeof(target_num) IN ('integer','real') AND target_num > 0 AND target_num < 1e300
                 THEN target_num END) AS paired_target,
        SUM(CASE WHEN typeof(coverage) IN ('integer','real') AND coverage > 100 THEN 1 ELSE 0 END) AS reported_anomalies,
        COUNT(*) AS source_rows
    FROM Vaccination GROUP BY antigen, country, year
), resolved AS (
    SELECT *, COALESCE(reported, paired_doses / paired_target * 100.0) AS coverage
    FROM grouped
)
SELECT *,
    CASE WHEN reported IS NOT NULL THEN 'Reported'
         WHEN coverage IS NOT NULL THEN 'Calculated'
         ELSE 'Not available' END AS coverage_source,
    CASE WHEN coverage > 100 OR reported_anomalies > 0 THEN 1 ELSE 0 END AS anomaly
FROM resolved;

DROP VIEW IF EXISTS v_infection;
CREATE VIEW v_infection AS
SELECT i.inf_type, t.description AS infection, i.year,
       c.CountryID AS country_id, c.name AS country,
       e.economyID AS economy_id, e.phase AS economy,
       CASE WHEN typeof(i.cases) IN ('integer','real')
            AND i.cases BETWEEN 0 AND 1e300 THEN i.cases END AS cases,
       CASE WHEN typeof(p.population) IN ('integer','real')
            AND p.population > 0 AND p.population < 1e300 THEN p.population END AS population,
       CASE WHEN typeof(i.cases) IN ('integer','real')
                 AND i.cases BETWEEN 0 AND 1e300
                 AND typeof(p.population) IN ('integer','real')
                 AND p.population > 0 AND p.population < 1e300
            THEN i.cases / p.population * 100000.0 END AS rate
FROM InfectionData i
JOIN Country c ON c.CountryID = i.country
JOIN Infection_Type t ON t.id = i.inf_type
LEFT JOIN Economy e ON e.economyID = c.economy
LEFT JOIN CountryPopulation p ON p.country = i.country AND p.year = i.year;
