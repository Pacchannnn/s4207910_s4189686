import re
import shutil
import tempfile
import unittest
from pathlib import Path

from immunisation_app import create_app


class FilterHelpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        database = Path(self.temp.name) / "test.db"
        shutil.copy2(Path(__file__).resolve().parents[1] / "database/immunisation.db", database)
        self.client = create_app({"TESTING": True, "DATABASE": str(database)}).test_client()

    def test_reset_is_clean_link_to_initial_analysis(self):
        for route in ("/vaccinations", "/infections", "/vaccination-improvement", "/infection-benchmark"):
            with self.subTest(route=route):
                html = self.client.get(route + "?direction=asc").get_data(as_text=True)
                self.assertIn('href="' + route + '#analysis" class="reset-filters"', html)
                self.assertNotIn('<script', html)
                self.assertEqual(self.client.get(route).status_code, 200)
                self.assertNotIn('type="reset"', html)

    def test_summary_precedes_sidebar(self):
        for route, heading in (("/vaccinations", "vaccination-context-title"),
                               ("/infections", "selected-economy-title"),
                               ("/vaccination-improvement", "comparison-context-title"),
                               ("/infection-benchmark", "global-title")):
            html = self.client.get(route + "?run=1").get_data(as_text=True)
            self.assertLess(html.index('id="' + heading + '"'), html.index('<aside class="analysis-sidebar"'))

    def test_analysis_guide_collapses_for_results_and_opens_for_invalid_settings(self):
        for route in ("/vaccinations", "/infections", "/vaccination-improvement", "/infection-benchmark"):
            html = self.client.get(route + "?run=1").get_data(as_text=True)
            self.assertIn('<details class="analysis-guide">', html)
            self.assertIn("How to read this analysis", html)
            invalid = self.client.get(route + "?run=1&year=bad&start_year=bad").get_data(as_text=True)
            self.assertIn('<section class="analysis-guide"', invalid)
            self.assertIn("Choose your analysis settings", invalid)

    def test_numeric_disclosure_closed_by_default_open_for_zero_and_errors(self):
        cases = [
            ({}, False),
            ({"numeric_column": "cases", "numeric_operator": "gte", "numeric_value": "0"}, True),
            ({"numeric_column": "cases", "numeric_value": "invalid"}, True),
            ({"numeric_column": "cases", "numeric_value": ""}, True),
            ({"numeric_operator": "invalid"}, True),
        ]
        for query, opened in cases:
            with self.subTest(query=query):
                response = self.client.get("/infections", query_string={**query, "run": "1"})
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                match = re.search(r'<details class="advanced-filters"([^>]*)>(.*?)</details>', html, re.S)
                self.assertIsNotNone(match)
                self.assertEqual("open" in match[1], opened)
                for name in ("numeric_column", "numeric_operator", "numeric_value"):
                    self.assertIn(f'name="{name}"', match[2])
                self.assertNotIn('name="economy"', match[2])
                if query.get("numeric_value") == "0":
                    self.assertIn('name="numeric_value" value="0"', match[2])

    def test_data_note_links_resolve_to_mission_glossary(self):
        mission = self.client.get("/mission")
        self.assertEqual(mission.status_code, 200)
        self.assertIn('id="data-notes"', mission.get_data(as_text=True))
        for route in ("/vaccinations", "/infections", "/vaccination-improvement", "/infection-benchmark"):
            html = self.client.get(route + "?run=1").get_data(as_text=True)
            self.assertIn('href="/mission#data-notes"', html)
