from __future__ import annotations

import operator
from html import unescape
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import template_rendered

from immunisation_app import create_app
from immunisation_app.db import connect_database
from immunisation_app.queries import (
    get_above_global_infections,
    get_infection_by_economy,
)


class ApprovedChangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        shutil.copy2(Path(__file__).resolve().parents[1] / "database/immunisation.db", self.path)
        self.app = create_app({"TESTING": True, "DATABASE": str(self.path)})
        self.client = self.app.test_client()
        self.db = connect_database(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def render(self, path, query):
        contexts = []
        def capture(sender, template, context, **extra):
            contexts.append(context)
        with template_rendered.connected_to(capture, self.app):
            response = self.client.get(path, query_string=query)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True), contexts[-1]

    def test_benchmark_all_sorts_preserve_global_and_membership(self):
        baseline = get_above_global_infections(self.db, infection_id="MEA", year=2020)
        for column, field in (("country", "country"), ("cases", "cases"),
                              ("population", "population"), ("rate", "cases_per_100k")):
            for direction in ("asc", "desc"):
                with self.subTest(column=column, direction=direction):
                    rows = get_above_global_infections(
                        self.db, infection_id="MEA", year=2020,
                        sort_by=column, direction=direction,
                    )
                    self.assertEqual(rows[0], baseline[0])
                    self.assertEqual({r["country_id"] for r in rows[1:]},
                                     {r["country_id"] for r in baseline[1:]})
                    values = [r[field] for r in rows[1:]]
                    self.assertEqual(values, sorted(values, reverse=direction == "desc"))

    def test_benchmark_sort_injection_falls_back_safely(self):
        expected = get_above_global_infections(self.db, infection_id="MEA", year=2020)
        actual = get_above_global_infections(
            self.db, infection_id="MEA", year=2020,
            sort_by="cases; DROP TABLE Country", direction="DESC; DROP TABLE Country",
        )
        self.assertEqual(actual, expected)

    def test_benchmark_sort_routes_render_controls_and_global_first(self):
        for column in ("country", "cases", "population", "rate"):
            for direction in ("asc", "desc"):
                html, ctx = self.render("/infection-benchmark", {
                    "infection": "MEA", "year": 2020, "sort": column, "direction": direction,
                })
                self.assertIn('name="sort"', html)
                self.assertEqual(ctx["filters"]["sort"], column)
                self.assertEqual(ctx["filters"]["direction"], direction)
                rendered = unescape(html)
                self.assertLess(rendered.index('class="global-row"'),
                                rendered.index('<th scope="row"><strong>' + ctx["country_rows"][0]["country"]))

    def test_benchmark_invalid_sort_bypasses_query(self):
        for args in ({"sort": "not-a-column"}, {"direction": "DROP TABLE Country"}):
            with patch("immunisation_app.views.get_above_global_infections") as query:
                response = self.client.get("/infection-benchmark", query_string=args)
                self.assertIn(b'role="alert"', response.data)
                query.assert_not_called()

    def infection_fixture(self):
        self.db.execute("DELETE FROM InfectionData WHERE inf_type='MEA' AND year=2022")
        for country, cases, population in (("AFG", 10, 100000), ("ALB", 20, 200000), ("AGO", 40, 100000)):
            self.db.execute("UPDATE Country SET economy=3 WHERE CountryID=?", (country,))
            self.db.execute("UPDATE CountryPopulation SET population=? WHERE country=? AND year=2022", (population, country))
            self.db.execute("INSERT INTO InfectionData VALUES ('MEA',?,2022,?)", (country, cases))
        self.db.commit()
        return dict(economy_id=3, infection_id="MEA", year=2022,
                    search="", sort_by="country", direction="asc")

    def test_numeric_filters_all_columns_operators_leave_summaries_unchanged(self):
        args = self.infection_fixture()
        baseline = get_infection_by_economy(self.db, **args)
        values = {"cases": [10, 20, 40], "population": [100000, 200000, 100000], "rate": [10, 10, 40]}
        for column, threshold in (("cases", 20), ("population", 100000), ("rate", 10)):
            for op, compare in (("gt", operator.gt), ("gte", operator.ge), ("lt", operator.lt), ("lte", operator.le), ("eq", operator.eq)):
                with self.subTest(column=column, op=op):
                    result = get_infection_by_economy(self.db, **args,
                        numeric_column=column, numeric_operator=op, numeric_value=threshold)
                    expected = [name for name, value in zip(("Afghanistan", "Albania", "Angola"), values[column]) if compare(value, threshold)]
                    self.assertEqual([r["country"] for r in result["rows"]], expected)
                    self.assertEqual(result["summary"], baseline["summary"])
                    self.assertEqual(result["selected_summary"], baseline["selected_summary"])

    def test_numeric_filter_combines_with_country_and_renders_sql_results(self):
        self.infection_fixture()
        html, ctx = self.render("/infections", {
            "economy": 3, "infection": "MEA", "year": 2022, "search": "Angola",
            "numeric_column": "rate", "numeric_operator": "gte", "numeric_value": "40",
        })
        self.assertEqual([r["country"] for r in ctx["rows"]], ["Angola"])
        self.assertIn('name="numeric_column"', html)
        self.assertIn('value="40"', html)
        self.assertIn("40.00", html)
        self.assertEqual(ctx["selected_summary"]["total_cases"], 70)
        self.assertEqual(ctx["selected_summary"]["represented_population"], 400000)
        _, empty = self.render("/infections", {
            "economy": 3, "infection": "MEA", "year": 2022, "search": "Angola",
            "numeric_column": "rate", "numeric_operator": "gt", "numeric_value": "40",
        })
        self.assertEqual(empty["rows"], [])
        self.assertEqual(empty["summary"], ctx["summary"])

    def test_invalid_numeric_inputs_bypass_query(self):
        invalid = [
            {"numeric_column": "cases; DROP TABLE Country", "numeric_value": "1"},
            {"numeric_column": "cases", "numeric_operator": "OR 1=1", "numeric_value": "1"},
            {"numeric_value": "1"},
        ] + [{"numeric_column": "cases", "numeric_value": v} for v in ("", "abc", "NaN", "inf", "1e999", "-1", "1 OR 1=1")]
        for args in invalid:
            with self.subTest(args=args), patch("immunisation_app.views.get_infection_by_economy") as query:
                response = self.client.get("/infections", query_string=args)
                self.assertIn(b'role="alert"', response.data)
                query.assert_not_called()

    def test_numeric_query_rejects_unwhitelisted_and_nonfinite_inputs(self):
        args = self.infection_fixture()
        for column, op, value in (("cases; DROP TABLE Country", "gte", 1),
                                  ("cases", "OR 1=1", 1), ("cases", "gte", float("nan")),
                                  ("cases", "gte", float("inf")), ("cases", "gte", -1)):
            with self.subTest(column=column, op=op, value=value):
                with self.assertRaises(ValueError):
                    get_infection_by_economy(self.db, **args, numeric_column=column,
                                            numeric_operator=op, numeric_value=value)
        self.assertGreater(self.db.execute("SELECT COUNT(*) FROM Country").fetchone()[0], 0)

    def test_numeric_routes_retain_all_columns_and_operators(self):
        args = self.infection_fixture()
        for column, value in (("cases", "20"), ("population", "100000"), ("rate", "10")):
            for op in ("gt", "gte", "lt", "lte", "eq"):
                html, ctx = self.render("/infections", {
                    "economy": 3, "infection": "MEA", "year": 2022,
                    "sort": "country", "direction": "asc",
                    "numeric_column": column, "numeric_operator": op, "numeric_value": value,
                })
                expected = get_infection_by_economy(self.db, **args, numeric_column=column,
                    numeric_operator=op, numeric_value=float(value))
                self.assertEqual(ctx["rows"], expected["rows"])
                self.assertEqual(ctx["summary"], expected["summary"])
                self.assertEqual(ctx["filters"]["numeric_column"], column)
                self.assertEqual(ctx["filters"]["numeric_operator"], op)
                self.assertNotIn('role="alert"', html)

    def test_numeric_filter_accepts_zero_and_decimal_scientific_values(self):
        self.infection_fixture()
        for value in ("0", "20.5", "2e1"):
            html, ctx = self.render("/infections", {
                "economy": 3, "infection": "MEA", "year": 2022,
                "numeric_column": "cases", "numeric_operator": "gte", "numeric_value": value,
            })
            self.assertNotIn('role="alert"', html)
            self.assertTrue(all(row["cases"] >= float(value) for row in ctx["rows"]))
