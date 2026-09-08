"""Integration tests run against the real copied course database."""
import hashlib
import sqlite3
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
PATHS = ["/", "/mission", "/vaccinations", "/infections", "/improvements", "/benchmark"]

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
        self.facts = 0
        self.titles = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "script" or any(k.lower().startswith("on") for k in a):
            self.scripts.append(tag)
        if "fact-card" in a.get("class", "").split():
            self.facts += 1
        if tag == "title":
            self.titles += 1

class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from immunisation_app import create_app
        cls.app = create_app({"TESTING": True})
        cls.client = cls.app.test_client()

    def test_all_six_pages_render_with_shared_navigation_and_no_script(self):
        for path in PATHS:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                parser = PageParser()
                parser.feed(response.get_data(as_text=True))
                self.assertEqual(parser.titles, 1)
                self.assertEqual(parser.scripts, [])
                for target in PATHS:
                    self.assertIn(target, parser.links)
                self.assertIn("script-src 'none'", response.headers["Content-Security-Policy"])

    def test_home_has_exactly_four_dynamic_facts(self):
        r = self.client.get("/")
        parser = PageParser()
        parser.feed(r.get_data(as_text=True))
        self.assertEqual(parser.facts, 4)
        self.assertIn(b"Vaccination and Disease Data", r.data)

    def test_mission_reads_supplied_personas_and_team(self):
        r = self.client.get("/mission")
        for text in ["Dr Amara Okonkwo", "Liem Tran", "Sofia Mascherano", "Grace Lil", "s4207910", "s4189686", "Example user profiles"]:
            self.assertIn(text, r.get_data(as_text=True))

    def test_valid_filters_render_results(self):
        urls = [
            "/vaccinations?year=2024&antigen=MCV2&country=VNM&region=TEA&minimum=0&threshold=90&sort=coverage&direction=desc",
            "/infections?year=2022&infection=MEA&economy=3&country=&sort=rate&direction=desc",
            "/improvements?start=2000&end=2024&antigen=MCV1&limit=10&sort=increase&direction=desc",
            "/benchmark?year=2024&infection=MEA&sort=rate&direction=desc"
        ]
        for url in urls:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                self.assertIn(b"<tbody>", r.data)

    def test_every_sort_choice_works_in_both_directions(self):
        from immunisation_app.queries import VACCINATION_SORTS, INFECTION_SORTS, IMPROVEMENT_SORTS, BENCHMARK_SORTS
        for path, sorts in [('/vaccinations', VACCINATION_SORTS), ('/infections', INFECTION_SORTS),
                            ('/improvements', IMPROVEMENT_SORTS), ('/benchmark', BENCHMARK_SORTS)]:
            for sort in sorts:
                for direction in ['asc', 'desc']:
                    with self.subTest(path=path, sort=sort, direction=direction):
                        self.assertEqual(self.client.get(path, query_string={'sort':sort, 'direction':direction}).status_code, 200)

    def test_blank_coverage_filter_displays_the_actual_default_used(self):
        r = self.client.get('/vaccinations?minimum=&threshold=')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Minimum: 90%', r.data)
        self.assertIn(b'at least 90% coverage', r.data)

    def test_invalid_parameters_are_400_without_traceback(self):
        urls = [
            "/?unexpected=1", "/mission?x=1",
            "/vaccinations?year=banana", "/vaccinations?year=2025",
            "/vaccinations?country=NOPE", "/vaccinations?region=NOPE",
            "/vaccinations?minimum=-1", "/vaccinations?minimum=101",
            "/vaccinations?threshold=nan", "/vaccinations?antigen=NOPE",
            "/vaccinations?year=2024&year=2023", "/vaccinations?year=",
            "/infections?economy=99", "/infections?infection=DROP",
            "/infections?min_rate=inf", "/infections?min_cases=20&max_cases=10",
            "/infections?min_population=-2", "/infections?sort=DROP%20TABLE",
            "/infections?direction=sideways", "/infections?country=" + "x"*81,
            "/improvements?start=2024&end=2000", "/improvements?start=2020&end=2020",
            "/improvements?limit=0", "/improvements?limit=999999",
            "/improvements?limit=2.5", "/benchmark?infection=%27%20OR%201=1--",
            "/benchmark?year=" + "9"*500, "/benchmark?foo=bar"
        ]
        for url in urls:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 400)
                self.assertNotIn(b"Traceback", r.data)
                self.assertIn(b"Check your filters", r.data)

    def test_empty_results_are_not_errors(self):
        for url in ["/infections?country=zzzznonexistent", "/vaccinations?country=VNM&region=NAC"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertIn(b"No matching", r.data)

    def test_search_is_literal_bound_and_html_escaped(self):
        for value in ["' OR 1=1 --", "%", "_", "<script>alert(1)</script>"]:
            r = self.client.get("/infections", query_string={"country": value})
            self.assertEqual(r.status_code, 200)
            self.assertIn(b"No matching", r.data)
            self.assertNotIn(b"<script>", r.data)

    def test_static_css_and_custom_errors(self):
        r = self.client.get("/static/style.css")
        self.assertEqual(r.status_code, 200)
        r.close()
        r = self.client.get("/does-not-exist")
        self.assertEqual(r.status_code, 404)
        self.assertIn(b"Page not found", r.data)
        self.assertEqual(self.client.post("/infections", data={"year":"wrong"}).status_code, 405)

    def test_requests_do_not_change_database(self):
        path = ROOT / "database/immunisation.db"
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        for route in PATHS:
            self.client.get(route)
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_connection_readonly_and_closed_after_context(self):
        from immunisation_app.db import get_db
        with self.app.app_context():
            connection = get_db()
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("CREATE TABLE forbidden(id)")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_missing_database_and_oversized_query_are_sanitized(self):
        from immunisation_app import create_app
        app = create_app({"TESTING": True, "DATABASE": ROOT / "missing-test-database.db"})
        with self.assertLogs(app.logger, level="ERROR"):
            response = app.test_client().get("/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"missing-test-database", response.data)
        self.assertEqual(self.client.get("/?x=" + "a" * 9000).status_code, 400)

    def test_assets_templates_and_styles_contain_no_javascript(self):
        for file in (ROOT / "immunisation_app").rglob("*"):
            if not file.is_file() or "__pycache__" in file.parts:
                continue
            self.assertNotIn(file.suffix.lower(), (".js", ".mjs", ".cjs"))
            if file.suffix in (".html", ".css"):
                text = file.read_text(encoding="utf-8").lower()
                for forbidden in ("<script", "javascript:", "onclick=", "onload=", "onerror="):
                    self.assertNotIn(forbidden, text, str(file))

if __name__ == "__main__":
    unittest.main()
