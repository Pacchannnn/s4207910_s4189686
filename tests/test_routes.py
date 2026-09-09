from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from immunisation_app import create_app
from immunisation_app.db import get_db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = PROJECT_ROOT / "database" / "immunisation.db"


class SemanticDocumentParser(HTMLParser):
    """Collect browser-facing document semantics without third-party parsers."""

    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict[str, str | None]]] = []
        self.tag_attributes: dict[str, list[dict[str, str | None]]] = {}
        self.title_parts: list[str] = []
        self.controls: list[dict[str, object]] = []
        self.labels: list[dict[str, object]] = []
        self._open_labels: list[dict[str, object]] = []
        self.tables: list[dict[str, object]] = []
        self._open_table: dict[str, object] | None = None
        self._open_caption: list[str] | None = None
        self._thead_depth = 0
        self.empty_state_headings: list[str] = []
        self._empty_state_depth = 0
        self._open_empty_heading: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        self.tag_attributes.setdefault(tag, []).append(attributes)

        if tag == "label":
            label: dict[str, object] = {
                "text": [],
                "controls": [],
                "for": attributes.get("for"),
            }
            self.labels.append(label)
            self._open_labels.append(label)

        if tag in {"input", "select", "textarea"}:
            control: dict[str, object] = {
                "attributes": attributes,
                "wrapping_label": self._open_labels[-1]
                if self._open_labels
                else None,
            }
            self.controls.append(control)
            if self._open_labels:
                self._open_labels[-1]["controls"].append(control)

        if tag == "thead":
            self._thead_depth += 1

        if tag == "table":
            wrapper = next(
                (
                    item_attrs
                    for item_tag, item_attrs in reversed(self.stack)
                    if item_tag == "div"
                    and "table-shell" in (item_attrs.get("class") or "").split()
                ),
                {},
            )
            self._open_table = {
                "caption": [],
                "column_header_scopes": [],
                "wrapper": wrapper,
            }
            self.tables.append(self._open_table)
        elif tag == "caption" and self._open_table is not None:
            self._open_caption = self._open_table["caption"]
        elif tag == "th" and self._open_table is not None and self._thead_depth:
            self._open_table["column_header_scopes"].append(attributes.get("scope"))

        classes = (attributes.get("class") or "").split()
        if "empty-state" in classes:
            self._empty_state_depth += 1
        elif self._empty_state_depth and tag in {"h2", "h3"}:
            self._open_empty_heading = []

        if tag not in self.VOID_ELEMENTS:
            self.stack.append((tag, attributes))

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self._open_labels:
            self._open_labels.pop()
        elif tag == "thead":
            self._thead_depth -= 1
        elif tag == "caption":
            self._open_caption = None
        elif tag == "table":
            self._open_table = None
        elif tag in {"h2", "h3"} and self._open_empty_heading is not None:
            heading = "".join(self._open_empty_heading).strip()
            if heading:
                self.empty_state_headings.append(heading)
            self._open_empty_heading = None

        if self.stack:
            for index in range(len(self.stack) - 1, -1, -1):
                open_tag, attributes = self.stack[index]
                if open_tag == tag:
                    self.stack = self.stack[:index]
                    if "empty-state" in (
                        attributes.get("class") or ""
                    ).split():
                        self._empty_state_depth -= 1
                    break

    def handle_data(self, data: str) -> None:
        if any(tag == "title" for tag, _ in self.stack):
            self.title_parts.append(data)
        inside_form_control = any(
            tag in {"input", "select", "textarea", "option"}
            for tag, _ in self.stack
        )
        if not inside_form_control:
            for label in self._open_labels:
                label["text"].append(data)
        if self._open_caption is not None:
            self._open_caption.append(data)
        if self._open_empty_heading is not None:
            self._open_empty_heading.append(data)

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()

    def control_names(self) -> tuple[str | None, ...]:
        return tuple(
            control["attributes"].get("name") for control in self.controls
        )

    def unlabelled_controls(self) -> list[dict[str, object]]:
        document_ids = (
            attributes.get("id")
            for attributes_by_tag in self.tag_attributes.values()
            for attributes in attributes_by_tag
        )
        id_counts = Counter(document_id for document_id in document_ids if document_id)
        explicitly_labelled_ids = {
            label["for"]
            for label in self.labels
            if label["for"] and "".join(label["text"]).strip()
        }
        unlabelled: list[dict[str, object]] = []

        for control in self.controls:
            wrapping_label = control["wrapping_label"]
            has_visible_wrapping_label = bool(
                wrapping_label
                and "".join(wrapping_label["text"]).strip()
            )
            control_id = control["attributes"].get("id")
            has_explicit_label = bool(
                control_id
                and id_counts[control_id] == 1
                and control_id in explicitly_labelled_ids
            )
            if not has_visible_wrapping_label and not has_explicit_label:
                unlabelled.append(control)

        return unlabelled


class RouteTests(unittest.TestCase):
    def test_task_a_pages_and_navigation(self):
        for path in ("/", "/vaccinations", "/vaccination-improvement"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            document = SemanticDocumentParser()
            document.feed(response.get_data(as_text=True))
            self.assertEqual(len(document.tag_attributes.get("h1", [])), 1)
        for path in ("/mission", "/infections", "/infection-benchmark"):
            self.assertEqual(self.client.get(path).status_code, 404)

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

    def test_semantic_parser_checks_each_control_instance_for_a_label(self) -> None:
        document = SemanticDocumentParser()
        document.feed(
            '<label>Year<select name="year"><option>2024</option></select></label>'
            '<input name="year"><input>'
        )

        self.assertEqual(document.control_names(), ("year", "year", None))
        self.assertEqual(
            [
                control["attributes"].get("name")
                for control in document.unlabelled_controls()
            ],
            ["year", None],
        )

    def test_semantic_parser_requires_document_wide_unique_label_target(self) -> None:
        document = SemanticDocumentParser()
        document.feed(
            '<label for="shared">Year</label>'
            '<div id="shared"></div>'
            '<input id="shared" name="year">'
            '<label for="unique">Country</label>'
            '<input id="unique" name="country">'
        )

        self.assertEqual(document.control_names(), ("year", "country"))
        self.assertEqual(document.unlabelled_controls(), [document.controls[0]])

    def test_phone_styles_stack_every_filter_control_in_one_column(self) -> None:
        response = self.client.get("/static/css/styles.css")
        stylesheet = response.get_data(as_text=True)
        status_code = response.status_code
        response.close()
        phone_rules = stylesheet[stylesheet.index("@media (max-width: 640px)") :]

        self.assertEqual(status_code, 200)
        self.assertRegex(
            phone_rules,
            r"\.sort-pair\s*\{\s*grid-template-columns:\s*1fr;\s*\}",
        )

    def test_shared_shell_has_accessible_navigation_and_no_js_dependency(self) -> None:
        response = self.client.get("/")

        self.assertIn(b'href="#main-content"', response.data)
        self.assertIn(b'aria-label="Primary navigation"', response.data)
        self.assertNotIn(b'class="nav-toggle"', response.data)
        self.assertNotIn(b"js/app.js", response.data)

    def test_home_renders_exactly_four_database_fact_cards(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.data.count(b'class="fact-card '), 4)
        for value in (b"2000", b"2024", b"217", b"5", b"3"):
            self.assertIn(value, response.data)

    def test_home_hero_names_vaccination_coverage_and_preventable_infections(
        self,
    ) -> None:
        response = self.client.get("/")

        hero = re.search(rb'<section class="hero">(.*?)</section>', response.data, re.DOTALL)
        self.assertIsNotNone(hero)
        self.assertIn(b"vaccination coverage", hero.group(1))
        self.assertIn(b"preventable infections", hero.group(1))

    def test_home_fact_cards_follow_snapshot_database_changes(self) -> None:
        with self.app.app_context():
            database = get_db()
            database.execute("INSERT INTO YearDate (YearID) VALUES (?)", (1999,))
            database.commit()

        response = self.client.get("/")
        fact_cards = re.findall(
            rb'<article class="fact-card [^"]+">(.*?)</article>',
            response.data,
            re.DOTALL,
        )

        self.assertEqual(len(fact_cards), 4)
        self.assertIn(b"1999-2024", b"".join(fact_cards))

        with self.app.app_context():
            database = get_db()
            database.execute("INSERT INTO YearDate (YearID) VALUES (2031)")
            database.execute("INSERT INTO Country (CountryID, name) VALUES ('ZZZ', 'Fixture country')")
            database.execute("INSERT INTO Antigen (AntigenID, name) VALUES ('TEST', 'Fixture antigen')")
            database.execute("INSERT INTO Infection_Type (id, description) VALUES ('TST', 'Fixture')")
            database.commit()
        changed = self.client.get("/").data
        values = re.findall(rb'<span class="fact-value">(.*?)</span>', changed)
        self.assertEqual(values, [b"1999-2031", b"218", b"6", b"4"])

    def test_improvement_alternate_sorts_do_not_claim_largest_ranks(self) -> None:
        for sort in ("country", "start_rate", "end_rate", "improvement"):
            for direction in ("asc", "desc"):
                with self.subTest(sort=sort, direction=direction):
                    response = self.client.get("/vaccination-improvement", query_string={
                        "antigen": "MCV1", "start_year": 2000, "end_year": 2024,
                        "limit": 3, "sort": sort, "direction": direction,
                    })
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b"Positive vaccination-rate improvements", response.data)
                    self.assertIn(b'<th scope="col">Position</th>', response.data)
                    self.assertNotIn(b"Largest vaccination-rate improvements", response.data)

    def test_analytical_page_renders_a_labelled_methodology_note(self) -> None:
        response = self.client.get("/vaccination-improvement")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<aside class="methodology-band" aria-labelledby="methodology-title">',
            response.data,
        )
        self.assertIn(
            b'<h2 id="methodology-title">Doses relative to population</h2>',
            response.data,
        )

    def test_vaccination_page_accepts_filters(self) -> None:
        response = self.client.get(
            "/vaccinations?antigen=MCV2&year=2010&sort=coverage&direction=desc"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MCV2", response.data)
        self.assertIn(b"Regional target summary", response.data)

    def test_vaccination_country_filter_shows_target_metrics_and_anomaly(self) -> None:
        response = self.client.get(
            "/vaccinations?antigen=MCV2&year=2010&country=KNA"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 country meeting target", response.data)
        self.assertIn(b"Countries meeting 90% target", response.data)
        self.assertIn(b"Reported above 100%", response.data)

    def test_vaccination_region_filter_limits_country_results(self) -> None:
        response = self.client.get(
            "/vaccinations?antigen=MCV2&year=2010&region=TLA"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"9 countries meeting target", response.data)
        self.assertIn(b"Regional target summary", response.data)
        self.assertIn(b"Reported above 100%", response.data)

    def test_vaccination_country_and_region_filters_work_together(self) -> None:
        response = self.client.get(
            "/vaccinations?antigen=MCV2&year=2010&country=KNA&region=TLA"
        )
        incompatible_response = self.client.get(
            "/vaccinations?antigen=MCV2&year=2010&country=KNA&region=TEA"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MCV2 in 2010", response.data)
        self.assertIn(b"1 country meeting target", response.data)
        self.assertIn(b"Regional target summary", response.data)
        self.assertEqual(response.data.count(b'class="table-shell"'), 2)
        self.assertIn(b"Regional coverage target results", response.data)
        self.assertIn(b"Countries meeting the 90% coverage target", response.data)
        self.assertEqual(incompatible_response.status_code, 200)
        self.assertIn(b"0 countries meeting target", incompatible_response.data)
        self.assertIn(b"No regional data", incompatible_response.data)

    def test_invalid_improvement_years_show_validation_message(self) -> None:
        response = self.client.get(
            "/vaccination-improvement?antigen=MCV1&start_year=2024&end_year=2000&limit=10"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"End year must be later than start year", response.data)

    def test_improvement_limit_boundaries_are_accepted_and_retained(self) -> None:
        for limit in (3, 50):
            with self.subTest(limit=limit):
                response = self.client.get(
                    "/vaccination-improvement"
                    f"?antigen=MCV1&start_year=2000&end_year=2024&limit={limit}"
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(f'value="{limit}"'.encode(), response.data)
                self.assertNotIn(b"Number of countries must be between", response.data)
                self.assertLessEqual(response.data.count(b'class="rank-number"'), limit)

    def test_improvement_rejects_out_of_range_equal_reversed_and_malformed_values(
        self,
    ) -> None:
        cases = (
            (
                "start_year=2000&end_year=2024&limit=2",
                b"Number of countries must be between 3 and 50",
            ),
            (
                "start_year=2000&end_year=2024&limit=51",
                b"Number of countries must be between 3 and 50",
            ),
            (
                "start_year=2024&end_year=2024&limit=10",
                b"End year must be later than start year",
            ),
            (
                "start_year=2024&end_year=2000&limit=10",
                b"End year must be later than start year",
            ),
            (
                "start_year=twenty&end_year=2024&limit=10",
                b"Start year must be a whole number",
            ),
            (
                "start_year=2000&end_year=twenty&limit=10",
                b"End year must be a whole number",
            ),
            (
                "start_year=2000&end_year=2024&limit=many",
                b"Number of countries must be a whole number",
            ),
        )

        for query, message in cases:
            with self.subTest(query=query):
                response = self.client.get(
                    f"/vaccination-improvement?antigen=MCV1&{query}"
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(message, response.data)
                self.assertIn(b'role="alert"', response.data)

    def test_improvement_results_render_complete_ranked_comparison_rows(self) -> None:
        response = self.client.get(
            "/vaccination-improvement"
            "?antigen=MCV1&start_year=2000&end_year=2024&limit=3"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"3 countries returned", response.data)
        self.assertEqual(response.data.count(b'class="rank-number"'), 3)
        self.assertIn(b"<caption>", response.data)
        self.assertIn(b"Positive vaccination-rate improvements", response.data)
        for heading in (
            b"Antigen",
            b"Start year",
            b"End year",
            b"Start rate",
            b"End rate",
            b"Improvement",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, response.data)
        self.assertGreaterEqual(response.data.count(b">MCV1<"), 3)
        self.assertGreaterEqual(response.data.count(b">2000<"), 3)
        self.assertGreaterEqual(response.data.count(b">2024<"), 3)
        self.assertIn(b"rate = administered doses / population x 100", response.data)
        self.assertIn(b"Improvement = end rate - start rate", response.data)

    def test_improvement_page_explains_when_no_positive_rows_exist(self) -> None:
        with self.app.app_context():
            database = get_db()
            database.execute(
                "DELETE FROM Vaccination WHERE antigen = ? AND year IN (?, ?)",
                ("MCV1", 2000, 2024),
            )
            database.commit()

        response = self.client.get(
            "/vaccination-improvement"
            "?antigen=MCV1&start_year=2000&end_year=2024&limit=10"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"0 countries returned", response.data)
        self.assertIn(b"No positive improvement found", response.data)
        self.assertIn(b"Only countries with data for both years", response.data)

    def test_unknown_route_returns_branded_404(self) -> None:
        response = self.client.get("/not-a-real-page")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)
        self.assertIn(b"Immunisation Lens", response.data)


if __name__ == "__main__":
    unittest.main()
