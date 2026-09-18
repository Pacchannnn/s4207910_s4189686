import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from immunisation_app import create_app


class AnalysisStateTests(unittest.TestCase):
    pages = {
        "/vaccinations": ("get_vaccination_view", "vaccination-context-title"),
        "/infections": ("get_infection_by_economy", "selected-economy-title"),
        "/vaccination-improvement": ("get_vaccination_improvements", "comparison-context-title"),
        "/infection-benchmark": ("get_above_global_infections", "global-title"),
    }

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        database = Path(temp.name) / "test.db"
        shutil.copy2(Path(__file__).resolve().parents[1] / "database/immunisation.db", database)
        self.client = create_app({"TESTING": True, "DATABASE": str(database)}).test_client()

    def test_initial_state_has_guide_and_never_runs_result_query(self):
        for route, (query, heading) in self.pages.items():
            for suffix in ("", "?year=2020", "?run=0"):
                with self.subTest(route=route, suffix=suffix), patch("immunisation_app.views." + query) as call:
                    response = self.client.get(route + suffix)
                    html = response.get_data(as_text=True)
                    self.assertEqual(response.status_code, 200)
                    call.assert_not_called()
                    self.assertIn('<section class="analysis-guide"', html)
                    self.assertNotIn("<table", html)
                    self.assertNotIn('id="' + heading + '"', html)
                    self.assertNotIn('class="metric-strip"', html)
                    self.assertNotIn("countries returned", html)
                    self.assertNotIn("<script", html)
                    self.assertIn('name="run" value="1"', html)

    def test_submit_shows_results_and_native_help(self):
        for route, (_, heading) in self.pages.items():
            with self.subTest(route=route):
                response = self.client.get(route, query_string={"run": "1"})
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('id="' + heading + '"', html)
                self.assertIn("<table", html)
                self.assertIn('<details class="analysis-guide">', html)
                self.assertNotIn("<script", html)

    def test_reset_removes_submission_and_returns_to_analysis_guide(self):
        for route in self.pages:
            with self.subTest(route=route):
                html = self.client.get(route + "?run=1&direction=asc").get_data(as_text=True)
                self.assertIn('href="' + route + '#analysis"', html)
                reset = self.client.get(route + "#analysis").get_data(as_text=True)
                self.assertIn('id="analysis"', reset)
                self.assertIn('<section class="analysis-guide"', reset)
                self.assertNotIn("<table", reset)
