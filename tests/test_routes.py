from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from html import escape
from pathlib import Path

from immunisation_app import create_app
from immunisation_app.db import get_db
from immunisation_app.queries import get_personas, get_team_members


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

        self.assertIn(b"vaccination coverage", response.data)
        self.assertIn(b"preventable infections", response.data)

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
        self.assertEqual(response.data.count(b'<div class="table-shell" tabindex="0">'), 2)
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
        self.assertNotIn(b"No data", response.data)
        self.assertNotIn(b'class="global-benchmark"', response.data)

    def test_unknown_route_returns_branded_404(self) -> None:
        response = self.client.get("/not-a-real-page")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)
        self.assertIn(b"Immunisation Lens", response.data)


if __name__ == "__main__":
    unittest.main()
