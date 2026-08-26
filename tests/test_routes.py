from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from immunisation_app import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = PROJECT_ROOT / "database" / "immunisation.db"


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.db"
        shutil.copy2(SOURCE_DB, self.database_path)
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.database_path),
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_all_six_required_pages_render(self) -> None:
        paths = (
            "/",
            "/mission",
            "/vaccinations",
            "/infections",
            "/vaccination-improvement",
            "/infection-benchmark",
        )

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Immunisation Lens", response.data)

    def test_vaccination_page_accepts_filters(self) -> None:
        response = self.client.get(
            "/vaccinations?antigen=MCV2&year=2010&sort=coverage&direction=desc"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MCV2", response.data)
        self.assertIn(b"Regional target summary", response.data)

    def test_infection_page_accepts_filters(self) -> None:
        response = self.client.get(
            "/infections?economy=3&infection=MEA&year=2022&sort=rate&direction=desc"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cases per 100,000", response.data)
        self.assertIn(b"Measles", response.data)

    def test_invalid_improvement_years_show_validation_message(self) -> None:
        response = self.client.get(
            "/vaccination-improvement?antigen=MCV1&start_year=2024&end_year=2000&limit=10"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"End year must be later than start year", response.data)

    def test_benchmark_page_includes_global_row_first(self) -> None:
        response = self.client.get("/infection-benchmark?infection=MEA&year=2020")

        self.assertEqual(response.status_code, 200)
        global_index = response.data.index(b"Global benchmark")
        country_index = response.data.index(b"Countries above global rate")
        self.assertLess(global_index, country_index)

    def test_unknown_route_returns_branded_404(self) -> None:
        response = self.client.get("/not-a-real-page")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)
        self.assertIn(b"Immunisation Lens", response.data)


if __name__ == "__main__":
    unittest.main()
