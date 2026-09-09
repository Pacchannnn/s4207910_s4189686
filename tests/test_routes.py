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
from immunisation_app.queries import get_personas, get_team_members


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

    def test_all_six_pages_have_one_named_document_shell(self) -> None:
        paths = (
            "/",
            "/mission",
            "/vaccinations?antigen=MCV2&year=2010",
            "/infections?economy=3&infection=MEA&year=2022",
            "/vaccination-improvement"
            "?antigen=MCV1&start_year=2000&end_year=2024&limit=10",
            "/infection-benchmark?infection=MEA&year=2020",
        )

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                document = SemanticDocumentParser()
                document.feed(response.get_data(as_text=True))

                self.assertEqual(response.status_code, 200)
                self.assertTrue(document.title)
                self.assertEqual(len(document.tag_attributes.get("h1", [])), 1)
                self.assertEqual(
                    document.tag_attributes.get("nav"),
                    [{
                        "class": "site-nav",
                        "id": "site-navigation",
                        "aria-label": "Primary navigation",
                    }],
                )
                self.assertEqual(
                    document.tag_attributes.get("main"),
                    [{"id": "main-content"}],
                )

    def test_analytical_controls_and_tables_have_accessible_names(self) -> None:
        cases = (
            (
                "/vaccinations?antigen=MCV2&year=2010",
                ("antigen", "year", "country", "region", "sort", "direction"),
                2,
            ),
            (
                "/infections?economy=3&infection=MEA&year=2022",
                ("economy", "infection", "year", "search", "sort", "direction"),
                2,
            ),
            (
                "/vaccination-improvement"
                "?antigen=MCV1&start_year=2000&end_year=2024&limit=10",
                (
                    "antigen",
                    "start_year",
                    "end_year",
                    "limit",
                    "sort",
                    "direction",
                ),
                1,
            ),
            (
                "/infection-benchmark?infection=MEA&year=2020",
                ("infection", "year"),
                1,
            ),
        )

        for path, expected_controls, expected_table_count in cases:
            with self.subTest(path=path):
                response = self.client.get(path)
                document = SemanticDocumentParser()
                document.feed(response.get_data(as_text=True))

                self.assertEqual(document.control_names(), expected_controls)
                self.assertEqual(document.unlabelled_controls(), [])
                self.assertEqual(len(document.tables), expected_table_count)
                for table in document.tables:
                    self.assertTrue("".join(table["caption"]).strip())
                    self.assertTrue(table["column_header_scopes"])
                    self.assertTrue(
                        all(
                            scope == "col"
                            for scope in table["column_header_scopes"]
                        )
                    )
                    wrapper = table["wrapper"]
                    self.assertEqual(wrapper.get("tabindex"), "0")
                    self.assertEqual(wrapper.get("role"), "region")
                    self.assertTrue((wrapper.get("aria-label") or "").strip())

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

    def test_empty_results_use_descriptive_headings(self) -> None:
        cases = (
            (
                "/vaccinations"
                "?antigen=MCV2&year=2010&country=KNA&region=TEA",
                {"No regional data", "No matching records"},
            ),
            (
                "/infections"
                "?economy=3&infection=MEA&year=2022&search=no-such-country",
                {"No matching countries"},
            ),
        )

        for path, expected_headings in cases:
            with self.subTest(path=path):
                response = self.client.get(path)
                document = SemanticDocumentParser()
                document.feed(response.get_data(as_text=True))

                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    expected_headings.issubset(set(document.empty_state_headings))
                )

        with self.app.app_context():
            database = get_db()
            database.execute(
                "DELETE FROM Vaccination WHERE antigen = ? AND year IN (?, ?)",
                ("MCV1", 2000, 2024),
            )
            database.execute(
                "DELETE FROM InfectionData WHERE inf_type = ? AND year = ?",
                ("MEA", 2020),
            )
            database.commit()

        for path, expected_heading in (
            (
                "/vaccination-improvement"
                "?antigen=MCV1&start_year=2000&end_year=2024&limit=10",
                "No positive improvement found",
            ),
            (
                "/infection-benchmark?infection=MEA&year=2020",
                "No benchmark available",
            ),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                document = SemanticDocumentParser()
                document.feed(response.get_data(as_text=True))

                self.assertEqual(response.status_code, 200)
                self.assertIn(expected_heading, document.empty_state_headings)

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

    def test_invalid_analytical_inputs_bypass_queries(self) -> None:
        for route, query, fields in (
            ("/vaccinations", "get_vaccination_view", ("year", "antigen", "country", "region", "sort", "direction")),
            ("/infections", "get_infection_by_economy", ("year", "economy", "infection", "sort", "direction")),
            ("/vaccination-improvement", "get_vaccination_improvements", ("start_year", "end_year", "limit", "antigen", "sort", "direction")),
            ("/infection-benchmark", "get_above_global_infections", ("year", "infection")),
        ):
            for field in fields:
                with self.subTest(route=route, field=field), patch("immunisation_app.views." + query) as analytical_query:
                    response = self.client.get(route, query_string={field: "invalid-value"})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b'role="alert"', response.data)
                    analytical_query.assert_not_called()

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

    def test_home_links_to_both_explorers_and_both_analyses(self) -> None:
        response = self.client.get("/")

        for path in (
            b"/vaccinations",
            b"/infections",
            b"/vaccination-improvement",
            b"/infection-benchmark",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    b'<a class="path-item" href="' + path + b'">',
                    response.data,
                )

    def test_mission_presents_perspective_guidance_and_database_content(self) -> None:
        with self.app.app_context():
            database = get_db()
            persona_ids = [
                row[0]
                for row in database.execute(
                    "SELECT persona_id FROM ProjectPersona ORDER BY persona_id"
                )
            ]
            database.executemany(
                """
                UPDATE ProjectPersona
                SET name = ?, role = ?, goal = ?, need = ?, app_feature = ?
                WHERE persona_id = ?
                """,
                [
                    (
                        f"Test persona & {index}",
                        f"Test role {index}",
                        f"Test goal {index}",
                        f"Test need {index}",
                        f"Test feature {index}",
                        persona_id,
                    )
                    for index, persona_id in enumerate(persona_ids, start=1)
                ],
            )
            database.executemany(
                """
                UPDATE ProjectTeamMember
                SET name = ?, student_number = ?, responsibility = ?
                WHERE member_id = ?
                """,
                [
                    ("Test member 1", "test-sid-1", "Test responsibility 1", 1),
                    ("Test member 2", "test-sid-2", "Test responsibility 2", 2),
                ],
            )
            database.commit()
            personas = get_personas(database)
            members = get_team_members(database)

        response = self.client.get("/mission")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"respectfully presented data", response.data)
        self.assertIn(b"without presenting association as causation", response.data)
        for layer in (b"Orient", b"Focus", b"Deepen"):
            self.assertIn(layer, response.data)
        for persona in personas:
            for value in persona.values():
                self.assertIn(escape(str(value)).encode(), response.data)

        non_placeholder_members = [
            member
            for member in members
            if "replace" not in member["name"].lower()
            and not member["student_number"].lower().startswith("sid")
        ]
        for member in non_placeholder_members:
            for value in member.values():
                self.assertIn(escape(str(value)).encode(), response.data)

    def test_mission_renders_exact_database_backed_submission_identities(self) -> None:
        response = self.client.get("/mission")

        self.assertEqual(response.status_code, 200)
        for name, student_number in (
            ("Le Chi Bach", "s4207910"),
            ("Nguyen Tran Ba Trong", "s4189686"),
        ):
            self.assertIn(escape(name).encode(), response.data)
            self.assertIn(student_number.encode(), response.data)
        for placeholder in (b"replace in database", b"sID1", b"sID2"):
            self.assertNotIn(placeholder, response.data)

    def test_invalid_filters_render_a_labelled_alert(self) -> None:
        response = self.client.get(
            "/infections?economy=3&infection=MEA&year=twenty"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'role="alert"', response.data)
        self.assertIn(b'aria-labelledby="filter-errors-title"', response.data)
        self.assertIn(
            b'<strong id="filter-errors-title">Check the filters</strong>',
            response.data,
        )

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

    def test_infection_page_accepts_filters(self) -> None:
        response = self.client.get(
            "/infections?economy=3&infection=MEA&year=2022&search=Zimbabwe&sort=cases&direction=asc"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cases per 100,000", response.data)
        self.assertIn(b"Measles", response.data)
        self.assertIn(b'value="3" selected', response.data)
        self.assertIn(b'value="MEA" selected', response.data)
        self.assertIn(b'value="2022" selected', response.data)
        self.assertIn(b'value="Zimbabwe"', response.data)
        self.assertIn(b'value="cases" selected', response.data)
        self.assertIn(b'value="asc" selected', response.data)
        self.assertIn(b"Selected economy metrics", response.data)
        self.assertIn(
            b"Selected economy metrics: Lower Middle Income - Measles in 2022",
            response.data,
        )
        self.assertIn(b"All-economy infection summary", response.data)
        self.assertIn(b"Country infection detail", response.data)
        self.assertIn(b"How to read this view", response.data)
        self.assertEqual(response.data.count(b"<caption>"), 2)
        self.assertGreaterEqual(response.data.count(b'scope="col"'), 12)

    def test_infection_page_shows_an_empty_state_for_a_nonmatching_search(self) -> None:
        response = self.client.get(
            "/infections?economy=3&infection=MEA&year=2022&search=no-such-country"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No matching countries", response.data)

    def test_malformed_year_and_sort_show_validation_messages(self) -> None:
        response = self.client.get(
            "/infections?economy=3&infection=MEA&year=twenty&sort=unknown&direction=sideways"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Year must be a whole number", response.data)
        self.assertIn(b"Choose a valid sort field", response.data)
        self.assertIn(b"Choose a valid sort direction", response.data)

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

    def test_benchmark_page_includes_accessible_global_row_first(self) -> None:
        response = self.client.get("/infection-benchmark?infection=MEA&year=2020")

        self.assertEqual(response.status_code, 200)
        table_start = response.data.index(b"<tbody>")
        accessible_global_row = (
            b'<tr class="global-row"><th scope="row"><strong>Global benchmark'
        )
        self.assertIn(accessible_global_row, response.data)
        global_index = response.data.index(b'<tr class="global-row">', table_start)
        country_index = response.data.index(b"Congo, Dem. Rep.", global_index)
        self.assertLess(global_index, country_index)
        self.assertIn(b"28 countries above the global rate", response.data)
        self.assertIn(b"<caption>", response.data)
        self.assertIn(b"Global benchmark and countries above it", response.data)
        self.assertEqual(response.data.count(b'scope="col"'), 6)
        self.assertIn(b'tabindex="0"', response.data)
        self.assertIn(b"per 100,000 people", response.data)
        self.assertIn(
            b"Weighted global rate = total reported cases / total represented "
            b"population x 100,000",
            response.data,
        )

    def test_benchmark_page_explains_when_no_benchmark_is_available(self) -> None:
        with self.app.app_context():
            database = get_db()
            database.execute(
                "DELETE FROM InfectionData WHERE inf_type = ? AND year = ?",
                ("MEA", 2020),
            )
            database.commit()

        response = self.client.get(
            "/infection-benchmark?infection=MEA&year=2020"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No benchmark available", response.data)
        self.assertNotIn(b"0 countries above the global rate", response.data)
        self.assertNotIn(b"No data", response.data)
        self.assertNotIn(b'class="global-benchmark"', response.data)

    def test_unknown_route_returns_branded_404(self) -> None:
        response = self.client.get("/not-a-real-page")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)
        self.assertIn(b"Immunisation Lens", response.data)


if __name__ == "__main__":
    unittest.main()
