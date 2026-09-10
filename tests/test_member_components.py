from __future__ import annotations

import shutil
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from flask import template_rendered
from immunisation_app import create_app


class ComponentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}
        self.headers = []
        self.row_headers = 0
        self.details_depth = 0
        self.visible_text = []
        self.hidden_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "data-sort-key" in attrs:
            self.links[attrs["data-sort-key"]] = attrs["href"]
        if tag == "th":
            self.headers.append(attrs)
            self.row_headers += attrs.get("scope") == "row"
        if tag == "details":
            self.details_depth += 1

    def handle_endtag(self, tag):
        if tag == "details":
            self.details_depth -= 1

    def handle_data(self, data):
        (self.hidden_text if self.details_depth else self.visible_text).append(data)


class MemberComponentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "test.db"
        shutil.copy2(Path(__file__).resolve().parents[1] / "database/immunisation.db", path)
        self.app = create_app({"TESTING": True, "DATABASE": str(path)})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def render(self, url, query=None):
        contexts = []
        def capture(sender, template, context, **kwargs):
            contexts.append(context)
        with template_rendered.connected_to(capture, self.app):
            response = self.client.get(url, query_string=query)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        parser = ComponentParser()
        parser.feed(html)
        return html, parser, contexts[-1]

    def test_header_links_preserve_filters_and_toggle_direction(self):
        args = [("economy", "3"), ("infection", "MEA"), ("year", "2022"),
                ("search", "Zimbabwe"), ("numeric_column", "cases"),
                ("numeric_operator", "gte"), ("numeric_value", "5532"),
                ("sort", "cases"), ("direction", "desc"), ("tag", "a"), ("tag", "b")]
        _, parser, initial = self.render("/infections", args)
        self.assertEqual(set(parser.links), {"country", "cases", "population", "rate"})
        for key, url in parser.links.items():
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(urlsplit(url).path, "/infections")
            for field in ("economy", "infection", "year", "search", "numeric_column", "numeric_operator", "numeric_value", "tag"):
                self.assertEqual(query[field], [v for k, v in args if k == field])
            self.assertEqual(query["sort"], [key])
            self.assertEqual(query["direction"], ["asc" if key in ("cases", "country") else "desc"])
            _, clicked, result = self.render(url)
            self.assertEqual(result["rows"], initial["rows"])
            self.assertEqual(result["summary"], initial["summary"])
            self.assertEqual(result["selected_summary"], initial["selected_summary"])
            if key == "cases":
                self.assertEqual(parse_qs(urlsplit(clicked.links[key]).query)["direction"], ["desc"])

    def test_header_results_equal_dropdown_and_expose_one_active_sort(self):
        _, parser, initial = self.render("/infections", {"economy": 3, "infection": "MEA", "year": 2022})
        self.assertEqual(len(parser.links), 4)
        for key, link in parser.links.items():
            html, clicked, result = self.render(link)
            query = {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}
            _, _, dropdown = self.render("/infections", query)
            self.assertEqual(result["rows"], dropdown["rows"])
            field = "cases_per_100k" if key == "rate" else key
            values = [row[field] for row in result["rows"]]
            self.assertEqual(values, sorted(values, reverse=query["direction"] == "desc"))
            self.assertEqual(result["summary"], initial["summary"])
            active = [h for h in clicked.headers if "aria-sort" in h]
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["aria-sort"], "ascending" if query["direction"] == "asc" else "descending")
            self.assertIn('name="sort"', html)
            self.assertIn('name="direction"', html)

    def test_country_and_economy_labels_are_row_headers(self):
        _, parser, ctx = self.render("/infections")
        self.assertEqual(parser.row_headers, len(ctx["rows"]) + len(ctx["summary"]))

    def test_critical_methodology_stays_outside_collapsed_details(self):
        html, parser, _ = self.render("/infections")
        self.assertIn("<details", html)
        visible = " ".join(parser.visible_text)
        for text in (
            "Records without a positive population are excluded.",
            "Blank or unmatched economic groups are excluded, not reassigned.",
            "Records must match a country",
            "The denominator covers represented records, not every country in the world.",
            "No matching result does not mean zero cases.",
            "Numeric comparisons use unrounded values",
        ):
            self.assertIn(text, visible)
        self.assertIn("Economy rates use total cases divided by total represented population", " ".join(parser.hidden_text))
        self.assertNotRegex(html, r"<script\b")
