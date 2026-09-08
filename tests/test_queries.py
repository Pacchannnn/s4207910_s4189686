from __future__ import annotations

import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from immunisation_app.db import connect_database, initialise_project_tables
from immunisation_app.queries import (
    get_above_global_infections,
    get_infection_by_economy,
    get_personas,
    get_snapshot,
    get_team_members,
    get_vaccination_improvements,
    get_vaccination_view,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = PROJECT_ROOT / "database" / "immunisation.db"


class QueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.db"
        shutil.copy2(SOURCE_DB, self.database_path)
        initialise_project_tables(self.database_path)
        self.db = connect_database(self.database_path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_snapshot_contains_four_presented_fact_groups(self) -> None:
        snapshot = get_snapshot(self.db)

        self.assertEqual(snapshot["first_year"], 2000)
        self.assertEqual(snapshot["last_year"], 2024)
        self.assertEqual(snapshot["country_count"], 217)
        self.assertEqual(snapshot["antigen_count"], 5)
        self.assertEqual(snapshot["infection_count"], 3)

    def test_project_table_initialisation_is_idempotent(self) -> None:
        self.db.close()
        before = hashlib.sha256(self.database_path.read_bytes()).hexdigest()

        initialise_project_tables(self.database_path)

        after = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.db = connect_database(self.database_path)

    def test_mission_data_is_retrieved_from_database(self) -> None:
        personas = get_personas(self.db)
        members = get_team_members(self.db)

        self.assertGreaterEqual(len(personas), 3)
        self.assertEqual(len(members), 2)
        self.assertTrue(all(row["student_number"] for row in members))

    def test_vaccination_view_filters_and_summarises_in_sql(self) -> None:
        result = get_vaccination_view(
            self.db,
            antigen="MCV2",
            year=2010,
            country="",
            region="",
            sort_by="coverage",
            direction="desc",
        )

        self.assertGreater(len(result["rows"]), 0)
        self.assertGreater(len(result["summary"]), 0)
        self.assertTrue(all(row["antigen"] == "MCV2" for row in result["rows"]))
        self.assertTrue(all(row["year"] == 2010 for row in result["rows"]))
        coverages = [row["coverage"] for row in result["rows"] if row["coverage"] is not None]
        self.assertEqual(coverages, sorted(coverages, reverse=True))
        self.assertTrue(all(row["met_target_count"] >= 0 for row in result["summary"]))

    def test_vaccination_values_above_100_are_flagged_not_silently_capped(self) -> None:
        result = get_vaccination_view(
            self.db,
            antigen="MCV2",
            year=2010,
            country="",
            region="",
            sort_by="coverage",
            direction="desc",
        )

        anomalous_rows = [
            row
            for row in result["rows"]
            if row["coverage"] is not None and row["coverage"] > 100
        ]
        self.assertGreater(len(anomalous_rows), 0)
        self.assertTrue(
            all(row["target_status"] == "Reported above 100%" for row in anomalous_rows)
        )

    def test_infection_view_calculates_rate_and_all_economy_summary(self) -> None:
        result = get_infection_by_economy(
            self.db,
            economy_id=3,
            infection_id="MEA",
            year=2022,
            search="",
            sort_by="rate",
            direction="desc",
        )

        self.assertGreater(len(result["rows"]), 0)
        self.assertEqual(len(result["summary"]), 4)
        rates = [row["cases_per_100k"] for row in result["rows"]]
        self.assertEqual(rates, sorted(rates, reverse=True))
        sample = result["rows"][0]
        expected = sample["cases"] / sample["population"] * 100000
        self.assertAlmostEqual(sample["cases_per_100k"], expected, places=6)

    def test_vaccination_improvement_uses_two_year_datasets(self) -> None:
        rows = get_vaccination_improvements(
            self.db,
            antigen="MCV1",
            start_year=2000,
            end_year=2024,
            limit=10,
            sort_by="improvement",
            direction="desc",
        )

        self.assertGreater(len(rows), 0)
        self.assertLessEqual(len(rows), 10)
        self.assertTrue(all(row["improvement"] > 0 for row in rows))
        improvements = [row["improvement"] for row in rows]
        self.assertEqual(improvements, sorted(improvements, reverse=True))
        for row in rows:
            self.assertAlmostEqual(
                row["improvement"], row["end_rate"] - row["start_rate"], places=6
            )

    def test_above_global_query_puts_global_row_first(self) -> None:
        rows = get_above_global_infections(self.db, infection_id="MEA", year=2020)

        self.assertGreater(len(rows), 1)
        self.assertEqual(rows[0]["row_type"], "global")
        global_rate = rows[0]["cases_per_100k"]
        country_rates = [row["cases_per_100k"] for row in rows[1:]]
        self.assertTrue(all(rate > global_rate for rate in country_rates))
        self.assertEqual(country_rates, sorted(country_rates, reverse=True))

    def test_sort_inputs_are_whitelisted(self) -> None:
        result = get_vaccination_view(
            self.db,
            antigen="MCV2",
            year=2010,
            country="",
            region="",
            sort_by="coverage; DROP TABLE Country;",
            direction="sideways",
        )

        self.assertGreater(len(result["rows"]), 0)
        country_count = self.db.execute("SELECT COUNT(*) FROM Country").fetchone()[0]
        self.assertEqual(country_count, 217)


if __name__ == "__main__":
    unittest.main()
