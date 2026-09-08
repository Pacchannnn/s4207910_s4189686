"""Independent reference arithmetic over raw tables, never application views."""
import hashlib
import json
import math
import sqlite3
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from immunisation_app import create_app
from immunisation_app.queries import Queries

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("Antigen", "Country", "CountryPopulation", "Economy", "InfectionData",
          "Infection_Type", "Region", "Vaccination", "YearDate")


class OracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect((ROOT / "database/immunisation.db").as_uri() + "?mode=ro", uri=True)
        cls.db.row_factory = sqlite3.Row
        cls.q = Queries(cls.db)
        cls.countries = {r["CountryID"]: dict(r) for r in cls.db.execute("SELECT * FROM Country")}
        cls.pop = {(r["country"], r["year"]): r["population"]
                   for r in cls.db.execute("SELECT * FROM CountryPopulation")}
        cls.vaccinations = [dict(r) for r in cls.db.execute("SELECT * FROM Vaccination")]
        cls.infections = [dict(r) for r in cls.db.execute("SELECT * FROM InfectionData")]
        cls.years = [r[0] for r in cls.db.execute("SELECT YearID FROM YearDate ORDER BY YearID")]
        cls.antigens = [r[0] for r in cls.db.execute("SELECT AntigenID FROM Antigen")]
        cls.types = [r[0] for r in cls.db.execute("SELECT id FROM Infection_Type")]

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @staticmethod
    def numeric(value):
        return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0

    def assert_number(self, actual, expected):
        if expected is None:
            self.assertIsNone(actual)
        else:
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-9),
                            (actual, expected))

    def valid_infections(self, year, infection):
        return [r for r in self.infections if r["year"] == year and r["inf_type"] == infection
                and r["country"] in self.countries and self.numeric(r["cases"])
                and self.numeric(self.pop.get((r["country"], year)))
                and self.pop[(r["country"], year)] > 0]

    def test_required_home_values(self):
        f = self.q.facts()
        for field, value in {"countries": 217, "antigens": 5, "vaccination_records": 24211,
                             "first_year": 2000, "last_year": 2024, "infections": 3,
                             "infection_records": 15525, "total_cases": 19232497}.items():
            self.assertEqual(f[field], value, field)
        self.assert_number(f["total_doses"], 10622256489.44529)

    def test_2a_rcv1_sample_and_regional_denominators(self):
        result = self.q.vaccinations(2000, "RCV1", "", "", 90, 90, "coverage", "desc")
        self.assertEqual([(r["country"], r["coverage"]) for r in result["rows"]],
                         [("Singapore", 93.5), ("Malta", 92.7)])
        self.assertEqual(sum(r["available"] for r in result["regions"]), 3)
        self.assertEqual(sum(r["meeting"] for r in result["regions"]), 2)

    def test_2a_every_antigen_year_against_raw_records(self):
        # This supplied dataset has one source row per antigen/country/year.
        keys = [(r["antigen"], r["country"], r["year"]) for r in self.vaccinations]
        self.assertEqual(len(keys), len(set(keys)))
        for antigen in self.antigens:
            for year in self.years:
                with self.subTest(antigen=antigen, year=year):
                    expected = {}
                    for row in self.vaccinations:
                        if row["antigen"] != antigen or row["year"] != year or row["country"] not in self.countries:
                            continue
                        coverage = row["coverage"] if self.numeric(row["coverage"]) else None
                        if coverage is None and self.numeric(row["doses"]) and self.numeric(row["target_num"]) and row["target_num"] > 0:
                            coverage = row["doses"] / row["target_num"] * 100
                        if coverage is not None:
                            expected[row["country"]] = coverage
                    result = self.q.vaccinations(year, antigen, "", "", 0, 90, "country", "asc")
                    self.assertEqual(set(expected), {r["country_id"] for r in result["rows"]})
                    for row in result["rows"]:
                        self.assert_number(row["coverage"], expected[row["country_id"]])
                    self.assertEqual(sum(r["available"] for r in result["regions"]), len(expected))
                    self.assertEqual(sum(r["total"] for r in result["regions"]), len(self.countries))
                    self.assertEqual(sum(r["meeting"] for r in result["regions"]),
                                     sum(v >= 90 for v in expected.values()))

    def test_2b_low_income_sample(self):
        result = self.q.infections(2022, "MEA", "4", "", {}, "rate", "desc")
        group = next(r for r in result["summary"] if r["economy"] == "Low Income")
        self.assertEqual(len(result["rows"]), 25)
        self.assertEqual(group["cases"], 83977)
        self.assertEqual(group["population"], 591481496)
        self.assert_number(group["rate"], 14.197739163086178)

    def test_2b_and_3b_every_infection_year_against_weighted_reference(self):
        economies = dict(self.db.execute("SELECT economyID,phase FROM Economy"))
        for infection in self.types:
            for year in self.years:
                with self.subTest(infection=infection, year=year):
                    valid = self.valid_infections(year, infection)
                    cases = math.fsum(r["cases"] for r in valid)
                    population = math.fsum(self.pop[(r["country"], year)] for r in valid)
                    expected_rate = cases / population * 100000 if population else None
                    result = self.q.benchmark(year, infection, "rate", "desc")
                    self.assertEqual(result["global"]["countries"], len(valid))
                    self.assert_number(result["global"]["rate"], expected_rate)
                    above = {self.countries[r["country"]]["name"] for r in valid
                             if r["cases"] / self.pop[(r["country"], year)] * 100000 > expected_rate}
                    self.assertEqual(above, {r["country"] for r in result["rows"]})
                    summary = self.q.infections(year, infection, "4", "", {}, "country", "asc")["summary"]
                    for code, name in economies.items():
                        matched = [r for r in valid if self.countries[r["country"]]["economy"] == code]
                        pop = math.fsum(self.pop[(r["country"], year)] for r in matched)
                        rate = math.fsum(r["cases"] for r in matched) / pop * 100000 if pop else None
                        self.assert_number(next(r["rate"] for r in summary if r["economy"] == name), rate)

    def test_3a_endpoints_and_intermediate_periods_from_raw_doses(self):
        doses = defaultdict(list)
        for row in self.vaccinations:
            if self.numeric(row["doses"]):
                doses[(row["antigen"], row["country"], row["year"])].append(row["doses"])
        for antigen in self.antigens:
            for start, end in [(2000, 2024), (2000, 2001), (2010, 2020), (2020, 2024), (2023, 2024)]:
                with self.subTest(antigen=antigen, start=start, end=end):
                    expected = []
                    for country, meta in self.countries.items():
                        d0, d1 = doses[(antigen, country, start)], doses[(antigen, country, end)]
                        p0, p1 = self.pop.get((country, start)), self.pop.get((country, end))
                        if not d0 or not d1 or not self.numeric(p0) or not self.numeric(p1) or p0 <= 0 or p1 <= 0:
                            continue
                        s, e = math.fsum(d0) / p0 * 100, math.fsum(d1) / p1 * 100
                        expected.append((meta["name"], s, e, e-s))
                    result = self.q.improvements(start, end, antigen, 10, "increase", "desc")
                    self.assertEqual(result["eligible"], len(expected))
                    top = sorted((r for r in expected if r[3] > 0), key=lambda r: (-r[3], r[0]))[:10]
                    self.assertEqual([r["country"] for r in result["rows"]], [r[0] for r in top])
                    for actual, ref in zip(result["rows"], top):
                        for field, val in zip(("start_rate", "end_rate", "increase"), ref[1:]):
                            self.assert_number(actual[field], val)

    def test_3a_chad_sample(self):
        result = self.q.improvements(2000, 2024, "DTPCV1", 3, "increase", "desc")
        self.assertEqual(result["eligible"], 123)
        self.assertEqual([r["country"] for r in result["rows"]],
                         ["Chad", "Congo, Dem. Rep.", "Central African Republic"])
        self.assert_number(result["rows"][0]["start_rate"], 1.4216714972451547)
        self.assert_number(result["rows"][0]["end_rate"], 4.788280754789259)
        self.assert_number(result["rows"][0]["increase"], 3.3666092575441042)

    def test_3b_measles_sample(self):
        result = self.q.benchmark(2020, "MEA", "rate", "desc")
        self.assertEqual(result["global"]["countries"], 207)
        self.assert_number(result["global"]["rate"], 2.0473104062008067)
        self.assertEqual(len(result["rows"]), 28)
        self.assertEqual(result["rows"][0]["country"], "Congo, Dem. Rep.")
        self.assert_number(result["rows"][0]["rate"], 85.72768175284263)

    def test_original_table_hashes_and_integrity(self):
        manifest = json.loads((ROOT / "docs/source_manifest.json").read_text())
        for table in TABLES:
            rows = [tuple(r) for r in self.db.execute(f'SELECT * FROM "{table}"')]
            encoded = sorted(json.dumps(row, ensure_ascii=True, separators=(",", ":")) for row in rows)
            digest = hashlib.sha256("\n".join(encoded).encode()).hexdigest()
            self.assertEqual(digest, manifest["tables"][table]["sha256"], table)
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_custom_500_and_empty_database_states(self):
        app = create_app({"TESTING": False, "PROPAGATE_EXCEPTIONS": False})
        with patch("immunisation_app.routes.repository", side_effect=RuntimeError("private secret")):
            with self.assertLogs(app.logger, level="ERROR"):
                response = app.test_client().get("/")
            self.assertEqual(response.status_code, 500)
            self.assertNotIn(b"private secret", response.data)
        blank = sqlite3.connect(":memory:")
        blank.row_factory = sqlite3.Row
        for row in self.db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            blank.execute(row[0])
        blank.executescript((ROOT / "database/extensions.sql").read_text())
        for path in ("/", "/mission", "/vaccinations", "/improvements", "/benchmark"):
            with patch("immunisation_app.routes.repository", return_value=Queries(blank)):
                response = app.test_client().get(path)
            self.assertIn(response.status_code, (200, 400))
            self.assertNotIn(b"Traceback", response.data)
        blank.close()


if __name__ == "__main__":
    unittest.main()
