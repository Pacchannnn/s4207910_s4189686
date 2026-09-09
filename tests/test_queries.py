from __future__ import annotations

import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from immunisation_app.db import connect_database, initialise_project_tables
from immunisation_app.queries import (
    get_snapshot,
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

    def test_vaccination_fallback_requires_positive_target(self) -> None:
        for target in (-100, 0, None, 100):
            with self.subTest(target=target):
                self.db.execute("UPDATE Vaccination SET coverage = NULL, doses = 95, target_num = ? WHERE antigen = 'MCV1' AND year = 2024", (target,))
                result = get_vaccination_view(self.db, antigen="MCV1", year=2024,
                    country="", region="", sort_by="coverage", direction="desc")
                if target == 100:
                    self.assertGreater(result["metrics"]["countries_with_data"], 0)
                    self.assertEqual(result["metrics"]["average_coverage"], 95)
                else:
                    self.assertEqual(result["rows"], [])
                    self.assertEqual(result["metrics"]["countries_with_data"], 0)
                    self.assertIsNone(result["metrics"]["average_coverage"])

    def test_project_table_initialisation_is_idempotent(self) -> None:
        self.db.close()
        before = hashlib.sha256(self.database_path.read_bytes()).hexdigest()

        initialise_project_tables(self.database_path)

        after = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.db = connect_database(self.database_path)

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

    def test_vaccination_country_rows_only_include_countries_meeting_target(self) -> None:
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
        self.assertTrue(all(row["coverage"] >= 90 for row in result["rows"]))
        self.assertGreater(result["metrics"]["countries_with_data"], 0)
        self.assertEqual(
            result["metrics"]["countries_meeting_target"], len(result["rows"])
        )

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
            self.assertEqual(
                set(row),
                {
                    "country_id",
                    "country",
                    "antigen",
                    "start_year",
                    "end_year",
                    "start_rate",
                    "end_rate",
                    "improvement",
                },
            )
            self.assertEqual(row["antigen"], "MCV1")
            self.assertEqual(row["start_year"], 2000)
            self.assertEqual(row["end_year"], 2024)
            self.assertAlmostEqual(
                row["improvement"], row["end_rate"] - row["start_rate"], places=6
            )

    def test_vaccination_improvement_uses_matching_endpoint_populations_and_exclusions(
        self,
    ) -> None:
        self.db.execute(
            "UPDATE Vaccination SET doses = ? WHERE antigen = ? AND country = ? AND year = ?",
            (50, "MCV1", "AFG", 2000),
        )
        self.db.execute(
            "UPDATE CountryPopulation SET population = ? WHERE country = ? AND year = ?",
            (100, "AFG", 2000),
        )
        self.db.execute(
            "UPDATE Vaccination SET doses = ? WHERE antigen = ? AND country = ? AND year = ?",
            (150, "MCV1", "AFG", 2024),
        )
        self.db.execute(
            "UPDATE CountryPopulation SET population = ? WHERE country = ? AND year = ?",
            (200, "AFG", 2024),
        )
        self.db.execute(
            "UPDATE CountryPopulation SET population = 0 WHERE country = ? AND year = ?",
            ("AGO", 2000),
        )
        self.db.execute(
            "DELETE FROM Vaccination WHERE antigen = ? AND country = ? AND year = ?",
            ("MCV1", "AIA", 2024),
        )
        self.db.execute(
            "UPDATE Vaccination SET doses = 0 WHERE antigen = ? AND country = ? AND year = ?",
            ("MCV1", "ALB", 2024),
        )
        self.db.commit()

        rows = get_vaccination_improvements(
            self.db,
            antigen="MCV1",
            start_year=2000,
            end_year=2024,
            limit=50,
            sort_by="country",
            direction="asc",
        )

        rows_by_country = {row["country_id"]: row for row in rows}
        self.assertIn("AFG", rows_by_country)
        self.assertAlmostEqual(rows_by_country["AFG"]["start_rate"], 50.0)
        self.assertAlmostEqual(rows_by_country["AFG"]["end_rate"], 75.0)
        self.assertAlmostEqual(rows_by_country["AFG"]["improvement"], 25.0)
        self.assertNotIn("AGO", rows_by_country)
        self.assertNotIn("AIA", rows_by_country)
        self.assertNotIn("ALB", rows_by_country)

    def test_vaccination_improvement_applies_all_sort_modes_and_limit(self) -> None:
        sort_fields = {
            "country": "country",
            "start_rate": "start_rate",
            "end_rate": "end_rate",
            "improvement": "improvement",
        }

        for sort_by, field in sort_fields.items():
            for direction in ("asc", "desc"):
                with self.subTest(sort_by=sort_by, direction=direction):
                    rows = get_vaccination_improvements(
                        self.db,
                        antigen="MCV1",
                        start_year=2000,
                        end_year=2024,
                        limit=3,
                        sort_by=sort_by,
                        direction=direction,
                    )

                    self.assertEqual(len(rows), 3)
                    if field == "country":
                        expected = sorted(
                            rows,
                            key=lambda row: row[field],
                            reverse=direction == "desc",
                        )
                    elif direction == "asc":
                        expected = sorted(rows, key=lambda row: (row[field], row["country"]))
                    else:
                        expected = sorted(rows, key=lambda row: (-row[field], row["country"]))
                    self.assertEqual(rows, expected)

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
