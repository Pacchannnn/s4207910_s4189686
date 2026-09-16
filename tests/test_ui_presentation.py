from html.parser import HTMLParser
import shutil
import tempfile
import unittest
from pathlib import Path

from immunisation_app import create_app


class UIParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.details_depth = 0
        self.details_text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "details":
            self.details_depth += 1

    def handle_endtag(self, tag):
        if tag == "details":
            self.details_depth -= 1

    def handle_data(self, data):
        if self.details_depth:
            self.details_text.append(data)


class ApprovedUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        database = Path(self.temp.name) / "test.db"
        shutil.copy2(Path(__file__).resolve().parents[1] / "database/immunisation.db", database)
        self.client = create_app({"TESTING": True, "DATABASE": str(database)}).test_client()

    def parse(self, path, query=None):
        response = self.client.get(path, query_string={**(query or {}), 'run': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.get_data(as_text=True), r"<title>[^<]+</title>")
        parser = UIParser()
        parser.feed(response.get_data(as_text=True))
        return parser

    def test_direction_radios_preserve_selected_get_value(self):
        for path in ("/vaccinations", "/infections", "/vaccination-improvement", "/infection-benchmark"):
            for direction in ("asc", "desc"):
                with self.subTest(path=path, direction=direction):
                    parser = self.parse(path, {"direction": direction})
                    radios = [a for tag, a in parser.tags if tag == "input" and a.get("name") == "direction"]
                    self.assertEqual({a.get("value") for a in radios}, {"asc", "desc"})
                    self.assertTrue(all(a.get("type") == "radio" for a in radios))
                    self.assertEqual([a["value"] for a in radios if "checked" in a], [direction])
                    self.assertTrue(any(tag == "legend" for tag, _ in parser.tags))
                    self.assertTrue(any(tag == "form" and a.get("method") == "get" for tag, a in parser.tags))
                    self.assertTrue(any(tag == "select" and a.get("name") == "sort" for tag, a in parser.tags))
                    self.assertTrue(any(tag == "button" and a.get("type") == "submit" for tag, a in parser.tags))

    def test_only_current_page_link_is_marked(self):
        for path in ("/", "/mission", "/vaccinations", "/infections", "/vaccination-improvement", "/infection-benchmark"):
            with self.subTest(path=path):
                parser = self.parse(path)
                current = [a["href"] for tag, a in parser.tags if tag == "a" and a.get("aria-current") == "page"]
                self.assertEqual(current, [path])

    def test_improvement_full_method_is_available_in_disclosure(self):
        parser = self.parse("/vaccination-improvement")
        self.assertTrue(any(tag == "summary" for tag, _ in parser.tags))
        details = " ".join(parser.details_text)
        self.assertIn("administered doses / population x 100", details)
        self.assertIn("matching country and same-year population record", details)
        self.assertIn("Blank doses are missing, not zero", details)
