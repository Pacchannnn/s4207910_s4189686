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
    get_team_members,
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

    def test_project_table_initialisation_is_idempotent(self) -> None:
        self.db.close()
        before = hashlib.sha256(self.database_path.read_bytes()).hexdigest()

        initialise_project_tables(self.database_path)

        after = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.db = connect_database(self.database_path)

    def test_project_table_initialisation_installs_submission_identities(self) -> None:
        self.db.execute("DELETE FROM ProjectTeamMember")
        self.db.commit()
        self.db.close()

        initialise_project_tables(self.database_path)

        self.db = connect_database(self.database_path)
        self.assertEqual(
            [
                (member["name"], member["student_number"])
                for member in get_team_members(self.db)
            ],
            [
                ("Le Chi Bach", "s4207910"),
                ("Nguyen Tran Ba Trong", "s4189686"),
            ],
        )

    def test_mission_data_is_retrieved_from_database(self) -> None:
        personas = get_personas(self.db)
        members = get_team_members(self.db)

        self.assertGreaterEqual(len(personas), 3)
        self.assertEqual(len(members), 2)
        self.assertTrue(all(row["student_number"] for row in members))

    def test_team_data_contains_submission_identities(self) -> None:
        members = get_team_members(self.db)

        self.assertEqual(
            {member["student_number"] for member in members},
            {"s4207910", "s4189686"},
        )
        self.assertTrue(
            all("replace in database" not in member["name"].lower() for member in members)
        )
        self.assertEqual(
            [
                (member["name"], member["student_number"])
                for member in members
            ],
            [
                ("Le Chi Bach", "s4207910"),
                ("Nguyen Tran Ba Trong", "s4189686"),
            ],
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
        self.assertTrue(all(row["economy_id"] == 3 for row in result["rows"]))
        self.assertTrue(all(row["infection"] == "Measles" for row in result["rows"]))
        self.assertTrue(all(row["year"] == 2022 for row in result["rows"]))
        self.assertEqual(
            set(result["rows"][0]),
            {
                "country",
                "economy_id",
                "economy",
                "infection",
                "year",
                "cases",
                "population",
                "cases_per_100k",
            },
        )
        rates = [row["cases_per_100k"] for row in result["rows"]]
        self.assertEqual(rates, sorted(rates, reverse=True))
        sample = result["rows"][0]
        expected = sample["cases"] / sample["population"] * 100000
        self.assertAlmostEqual(sample["cases_per_100k"], expected, places=6)
        for item in result["summary"]:
            expected_rate = item["total_cases"] / item["represented_population"] * 100000
            self.assertAlmostEqual(item["cases_per_100k"], expected_rate, places=6)

    def test_infection_view_applies_country_search_and_all_sort_modes(self) -> None:
        # This catches a removed SQL search predicate or an unwhitelisted sort mapping.
        filtered = get_infection_by_economy(
            self.db,
            economy_id=3,
            infection_id="MEA",
            year=2022,
            search="Zimbabwe",
            sort_by="country",
            direction="asc",
        )

        self.assertEqual([row["country"] for row in filtered["rows"]], ["Zimbabwe"])

        for sort_by, direction in (
            ("country", "asc"),
            ("cases", "desc"),
            ("population", "asc"),
            ("rate", "desc"),
        ):
            with self.subTest(sort_by=sort_by, direction=direction):
                result = get_infection_by_economy(
                    self.db,
                    economy_id=3,
                    infection_id="MEA",
                    year=2022,
                    search="",
                    sort_by=sort_by,
                    direction=direction,
                )
                rows = result["rows"]
                if sort_by == "country":
                    self.assertEqual(
                        [row["country"] for row in rows],
                        sorted(
                            (row["country"] for row in rows),
                            reverse=direction == "desc",
                        ),
                    )
                    continue

                expected_rows = sorted(
                    rows,
                    key=lambda row: (row[sort_by if sort_by != "rate" else "cases_per_100k"], row["country"]),
                    reverse=False,
                )
                if direction == "desc":
                    expected_rows = sorted(
                        rows,
                        key=lambda row: (-row[sort_by if sort_by != "rate" else "cases_per_100k"], row["country"]),
                    )
                self.assertEqual(rows, expected_rows)

    def test_above_global_query_puts_global_row_first(self) -> None:
        rows = get_above_global_infections(self.db, infection_id="MEA", year=2020)

        self.assertGreater(len(rows), 1)
        self.assertEqual(rows[0]["row_type"], "global")
        global_rate = rows[0]["cases_per_100k"]
        country_rates = [row["cases_per_100k"] for row in rows[1:]]
        self.assertTrue(all(rate > global_rate for rate in country_rates))
        self.assertEqual(country_rates, sorted(country_rates, reverse=True))

    def test_benchmark_is_weighted_strict_and_deterministic(self) -> None:
        self.db.execute(
            "DELETE FROM InfectionData WHERE inf_type = ? AND year = ?",
            ("MEA", 2020),
        )
        self.db.executemany(
            "UPDATE CountryPopulation SET population = ? "
            "WHERE country = ? AND year = ?",
            (
                (400_000, "AFG", 2020),
                (100_000, "DZA", 2020),
                (100_000, "AGO", 2020),
                (100_000, "ALB", 2020),
            ),
        )
        self.db.executemany(
            "INSERT INTO InfectionData (inf_type, country, year, cases) "
            "VALUES (?, ?, ?, ?)",
            (
                ("MEA", "AFG", 2020, 60),
                ("MEA", "DZA", 2020, 20),
                ("MEA", "AGO", 2020, 30),
                ("MEA", "ALB", 2020, 30),
            ),
        )
        self.db.commit()

        rows = get_above_global_infections(self.db, infection_id="MEA", year=2020)

        self.assertEqual(
            [row["country"] for row in rows],
            ["Global benchmark", "Albania", "Angola"],
        )
        self.assertEqual(rows[0]["cases"], 140)
        self.assertEqual(rows[0]["population"], 700_000)
        self.assertAlmostEqual(rows[0]["cases_per_100k"], 20.0)

    def test_benchmark_returns_no_global_row_without_source_data(self) -> None:
        self.db.execute(
            "DELETE FROM InfectionData WHERE inf_type = ? AND year = ?",
            ("MEA", 2020),
        )
        self.db.commit()

        rows = get_above_global_infections(self.db, infection_id="MEA", year=2020)

        self.assertEqual(rows, [])

    def test_sort_inputs_are_whitelisted(self) -> None:
        result = get_infection_by_economy(
            self.db,
            economy_id=3,
            infection_id="MEA",
            year=2022,
            search="",
            sort_by="cases_per_100k; DROP TABLE Country;",
            direction="sideways",
        )

        self.assertGreater(len(result["rows"]), 0)
        country_count = self.db.execute("SELECT COUNT(*) FROM Country").fetchone()[0]
        self.assertEqual(country_count, 217)


if __name__ == "__main__":
    unittest.main()
