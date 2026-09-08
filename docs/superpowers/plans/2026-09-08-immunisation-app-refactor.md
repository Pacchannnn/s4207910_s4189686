# Immunisation Lens Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor all six Flask pages into a requirements-traceable, accessible, responsive academic application while preserving the working SQLite and SQL foundation.

**Architecture:** Keep the existing Flask blueprint and route paths. Requests are parsed and validated in `views.py`, calculations and ordering stay in parameterized SQL in `queries.py`, and Jinja renders semantic server-generated HTML using a small shared component set and one documented CSS system.

**Tech Stack:** Python 3, Flask 3.1.2, SQLite, Jinja, HTML, CSS, standard-library `unittest`, optional vanilla JavaScript for non-critical enhancement only.

## Global Constraints

- Implement all six pages described in the supplied COSC3106 requirements PDF.
- Preserve Flask and SQLite; do not introduce a client-side framework or external API.
- Treat PDF example figures as illustrative only; all displayed application data must come from the supplied database.
- Keep requirement-critical navigation, filtering, and results usable without JavaScript.
- Perform joins, calculations, aggregation, sorting, threshold filtering, and limiting in SQL where appropriate.
- Use parameterized SQL for values and whitelist every user-controlled SQL ordering expression.
- Do not cap reported coverage values above 100%; identify them as anomalies.
- Do not invent team-member names or student-number mappings.
- Run tests with `python -m unittest discover -s tests -v`.
- Make each task a separate commit after its focused and full test suites pass.

---

## File Map

### New files

- `docs/REQUIREMENTS_MATRIX.md`: authoritative requirement-to-code-to-test traceability and current implementation audit.
- `tests/test_validation.py`: unit coverage for strict request parsing and scalar-choice validation.
- `immunisation_app/templates/components/validation_notice.html`: shared accessible validation summary.
- `immunisation_app/templates/components/methodology_note.html`: shared methodology/data-quality panel.

### Existing files to modify

- `immunisation_app/validation.py`: strict integer parsing and scalar whitelist helpers.
- `immunisation_app/views.py`: explicit malformed-input errors and consistent template contexts.
- `immunisation_app/queries.py`: targeted query outputs and threshold/no-data corrections.
- `immunisation_app/db.py`: final team records only after the user supplies exact identity data.
- `immunisation_app/templates/base.html`: semantic shared shell and navigation that works without JavaScript.
- `immunisation_app/templates/home.html`: four traceable facts and exploration paths.
- `immunisation_app/templates/mission.html`: mission, usage, database personas, and database team presentation.
- `immunisation_app/templates/vaccinations.html`: 90%-threshold country table, regional summary, and data-quality context.
- `immunisation_app/templates/infections.html`: economy selection, sortable country results, and cross-economy summary.
- `immunisation_app/templates/vaccination_improvement.html`: two-year comparison and ranking output.
- `immunisation_app/templates/infection_benchmark.html`: global-first benchmark table and empty state.
- `immunisation_app/templates/404.html`: shared-shell consistency.
- `immunisation_app/static/css/styles.css`: documented tokens, layout, components, accessibility, and responsive rules.
- `immunisation_app/static/js/app.js`: remove navigation dependency; retain only enhancement that is safe when absent, or delete the file if no enhancement remains.
- `tests/test_queries.py`: SQL behavior, anomaly, threshold, aggregation, and no-data coverage.
- `tests/test_routes.py`: all-page, validation, semantics, empty-state, and required-output coverage.

---

### Task 1: Requirements and Current-State Matrix

**Files:**
- Create: `docs/REQUIREMENTS_MATRIX.md`
- Reference: `docs/superpowers/specs/2026-09-08-immunisation-app-refactor-design.md`
- Reference: `immunisation_app/views.py`
- Reference: `immunisation_app/queries.py`
- Reference: `tests/test_queries.py`
- Reference: `tests/test_routes.py`

**Interfaces:**
- Consumes: the six PDF page requirements and current source evidence.
- Produces: stable IDs `L1-A-01` through `L3-B-04` used by later task notes and final acceptance checks.

- [ ] **Step 1: Create the matrix structure and current-state audit**

Write tables with these columns:

```markdown
| ID | Requirement | Route | Query/template evidence | Test evidence | Current | Target |
|---|---|---|---|---|---|---|
```

Cover these mandatory groups explicitly:

```text
L1-A: attention, topics, dataset snapshot, four facts
L1-B: social-challenge perspective, usage guidance, DB personas, DB team
L2: SQL selection/filter/sort/join/aggregation and anomaly handling
L2-A: country/region/year/antigen controls, >=90% country results, regional summary
L2-B: one economy, infection, year, resultant-column ordering, country rates, economy aggregation
L3: sub-dataset query design, selected sorting, minimal Python post-processing
L3-A: start year, end year, antigen, count, population-based improvement ranking
L3-B: year, infection, weighted global rate, above-global countries, global row first
```

Add separate route, template, query, and test inventory tables below the requirement table. Record team identity as `Blocked: exact names and student-number mapping not supplied`; do not mark it met merely because placeholder rows exist.

- [ ] **Step 2: Verify every required group and all six routes appear**

Run:

```powershell
rg -n "L1-A|L1-B|L2-A|L2-B|L3-A|L3-B|/mission|/vaccinations|/infections|/vaccination-improvement|/infection-benchmark" docs/REQUIREMENTS_MATRIX.md
```

Expected: matches for all six requirement groups and all six route paths.

- [ ] **Step 3: Run the untouched baseline suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: 15 tests pass.

- [ ] **Step 4: Commit the audit**

```powershell
git add docs/REQUIREMENTS_MATRIX.md
git commit -m "docs: map application requirements"
```

---

### Task 2: Strict Request Validation

**Files:**
- Create: `tests/test_validation.py`
- Modify: `immunisation_app/validation.py`
- Modify: `immunisation_app/views.py`
- Modify: `tests/test_routes.py`

**Interfaces:**
- Consumes: raw query-string values and database-derived choices.
- Produces: `parse_int(value: str | None, default: int, label: str) -> tuple[int, str | None]` and `valid_scalar(value: str, allowed: set[str]) -> bool`.

- [ ] **Step 1: Write failing parsing unit tests**

Create `tests/test_validation.py` with focused cases:

```python
import unittest

from immunisation_app.validation import parse_int, valid_scalar


class ValidationTests(unittest.TestCase):
    def test_parse_int_uses_default_only_when_value_is_missing(self):
        self.assertEqual(parse_int(None, 2024, "Year"), (2024, None))

    def test_parse_int_reports_malformed_value(self):
        self.assertEqual(
            parse_int("twenty", 2024, "Year"),
            (2024, "Year must be a whole number."),
        )

    def test_valid_scalar_uses_an_explicit_whitelist(self):
        self.assertTrue(valid_scalar("rate", {"rate", "country"}))
        self.assertFalse(valid_scalar("rate; DROP TABLE Country;", {"rate", "country"}))
```

- [ ] **Step 2: Run the focused tests and confirm import failure**

Run:

```powershell
python -m unittest tests.test_validation -v
```

Expected: FAIL because `parse_int` and `valid_scalar` do not exist.

- [ ] **Step 3: Implement minimal parsing helpers**

Add to `immunisation_app/validation.py`:

```python
def parse_int(
    value: str | None, default: int, label: str
) -> tuple[int, str | None]:
    if value is None or not value.strip():
        return default, None
    try:
        return int(value), None
    except (TypeError, ValueError):
        return default, f"{label} must be a whole number."


def valid_scalar(value: str, allowed: set[str]) -> bool:
    return value in allowed
```

Retain `valid_choice`. Remove `as_int` after all callers move to `parse_int`.

- [ ] **Step 4: Add failing route assertions for malformed numeric and sort inputs**

Add route tests equivalent to:

```python
def test_malformed_year_and_sort_show_validation_messages(self):
    response = self.client.get(
        "/infections?economy=3&infection=MEA&year=twenty&sort=unknown&direction=sideways"
    )
    self.assertEqual(response.status_code, 200)
    self.assertIn(b"Year must be a whole number", response.data)
    self.assertIn(b"Choose a valid sort field", response.data)
    self.assertIn(b"Choose a valid sort direction", response.data)
```

- [ ] **Step 5: Update every analytical route to collect parser and whitelist errors**

Use this pattern in `views.py`:

```python
raw_year = request.args.get("year")
year, year_error = parse_int(raw_year, reference["years"][0]["value"], "Year")
if year_error:
    errors.append(year_error)
if not valid_scalar(sort_by, {"country", "cases", "population", "rate"}):
    errors.append("Choose a valid sort field.")
if not valid_scalar(direction, {"asc", "desc"}):
    errors.append("Choose a valid sort direction.")
```

Apply page-specific allowed sort sets and numeric labels to vaccination, infection, improvement, and benchmark routes. When errors exist, pass empty result structures with every template key present.

- [ ] **Step 6: Run validation and full tests**

Run:

```powershell
python -m unittest tests.test_validation tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit strict validation**

```powershell
git add immunisation_app/validation.py immunisation_app/views.py tests/test_validation.py tests/test_routes.py
git commit -m "fix: report invalid filter values"
```

---

### Task 3: Shared Semantic Shell and Interface Components

**Files:**
- Create: `immunisation_app/templates/components/validation_notice.html`
- Create: `immunisation_app/templates/components/methodology_note.html`
- Modify: `immunisation_app/templates/base.html`
- Modify: `immunisation_app/static/css/styles.css`
- Modify or delete: `immunisation_app/static/js/app.js`
- Modify: `tests/test_routes.py`

**Interfaces:**
- Consumes: `active_page`, `errors`, and page-specific methodology copy.
- Produces: a shared shell whose navigation and main content work without JavaScript, plus two includes used by analytical pages.

- [ ] **Step 1: Write failing shared-shell route tests**

Add tests that parse response text without requiring a browser:

```python
def test_shared_shell_has_accessible_navigation_and_no_js_dependency(self):
    response = self.client.get("/")
    self.assertIn(b'href="#main-content"', response.data)
    self.assertIn(b'aria-label="Primary navigation"', response.data)
    self.assertNotIn(b'class="nav-toggle"', response.data)
    self.assertNotIn(b"js/app.js", response.data)
```

Add a validation include assertion using an invalid route request and check for `role="alert"`.

- [ ] **Step 2: Run the focused route tests and confirm failure**

Run:

```powershell
python -m unittest tests.test_routes.RouteTests.test_shared_shell_has_accessible_navigation_and_no_js_dependency -v
```

Expected: FAIL because the current shell contains the JavaScript-dependent mobile toggle and script reference.

- [ ] **Step 3: Create the shared validation include**

Create `components/validation_notice.html`:

```jinja2
{% if errors %}
<div class="notice error-notice" role="alert" aria-labelledby="filter-errors-title">
  <strong id="filter-errors-title">{{ error_title|default('Check the filters') }}</strong>
  <ul>
    {% for error in errors %}<li>{{ error }}</li>{% endfor %}
  </ul>
</div>
{% endif %}
```

Create `components/methodology_note.html` with parameters `methodology_title` and `methodology_text`, rendered as a labelled `<aside>`.

- [ ] **Step 4: Make navigation independent of JavaScript**

Remove the toggle button and script reference from `base.html`. Keep all six navigation links inside a semantic `<nav>`. At widths below 860px, style `.site-nav` as an always-visible wrapping or horizontally scrollable list. Delete `app.js` if no enhancement remains; otherwise leave it unreferenced until an enhancement has a verified accessible fallback.

- [ ] **Step 5: Reorganize the stylesheet without changing page meaning**

Keep `styles.css` as the single delivered file and add section comments in this order:

```css
/* 1. Tokens */
/* 2. Reset and base elements */
/* 3. Shared layout */
/* 4. Navigation and footer */
/* 5. Content components */
/* 6. Forms and validation */
/* 7. Tables and data states */
/* 8. Page-specific components */
/* 9. Responsive rules */
```

Add `:focus-visible` styles, `caption` styling, a usable `.table-shell:focus-visible`, and a `@media (prefers-reduced-motion: reduce)` rule. Preserve the existing named color variables and ensure error/success meaning is also expressed in text.

- [ ] **Step 6: Replace repeated inline error blocks in all analytical templates**

Use:

```jinja2
{% set error_title = "Check the filters" %}
{% include "components/validation_notice.html" %}
```

Use `Check the comparison` on the improvement page.

- [ ] **Step 7: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit the shared interface foundation**

```powershell
git add immunisation_app/templates immunisation_app/static tests/test_routes.py
git commit -m "refactor: establish accessible interface shell"
```

---

### Task 4: Landing and Mission Requirements

**Files:**
- Modify: `immunisation_app/queries.py`
- Modify: `immunisation_app/templates/home.html`
- Modify: `immunisation_app/templates/mission.html`
- Modify: `tests/test_queries.py`
- Modify: `tests/test_routes.py`
- Modify after identity confirmation: `immunisation_app/db.py`
- Modify after identity confirmation: `database/immunisation.db`
- Modify: `docs/REQUIREMENTS_MATRIX.md`

**Interfaces:**
- Consumes: `get_snapshot`, `get_latest_infection_totals`, `get_personas`, and `get_team_members`.
- Produces: four database-derived landing facts and complete database-derived mission/persona/team content.

- [ ] **Step 1: Write failing Level 1 tests**

Extend query and route tests:

```python
def test_snapshot_contains_four_presented_fact_groups(self):
    snapshot = get_snapshot(self.db)
    self.assertEqual(snapshot["first_year"], 2000)
    self.assertEqual(snapshot["last_year"], 2024)
    self.assertEqual(snapshot["country_count"], 217)
    self.assertEqual(snapshot["antigen_count"], 5)
    self.assertEqual(snapshot["infection_count"], 3)

def test_home_renders_exactly_four_database_fact_cards(self):
    response = self.client.get("/")
    self.assertEqual(response.data.count(b'class="fact-card '), 4)
    for value in (b"2000", b"2024", b"217", b"5", b"3"):
        self.assertIn(value, response.data)
```

Add mission assertions for mission perspective, usage guidance, every persona returned by `get_personas`, and every non-placeholder team record returned by `get_team_members`.

- [ ] **Step 2: Run focused tests and record which assertions fail**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_snapshot_contains_four_presented_fact_groups tests.test_routes.RouteTests.test_home_renders_exactly_four_database_fact_cards -v
```

Expected: fact tests pass or expose only markup differences; the team-content acceptance check remains pending exact identity data.

- [ ] **Step 3: Refine Level 1 content and semantics**

Keep exactly four `.fact-card` articles: reporting period, countries/areas, antigens, and infection types. Ensure the hero names vaccination coverage and preventable infections; ensure the exploration section links to both Level 2 pages and both Level 3 pages. Add section headings and neutral methodology copy without hardcoded analytical values.

On the mission page, retain the three database personas and three-layer usage explanation. Present the database team records in a semantic list or articles with visible names and student numbers.

- [ ] **Step 4: Update exact team identities after the user supplies them**

Require two exact `(name, student_number, responsibility)` records and an explicit mapping to member IDs 1 and 2. Update both `TEAM_MEMBERS` in `db.py` and the tracked `ProjectTeamMember` rows using a parameterized migration executed against `database/immunisation.db`:

```python
connection.executemany(
    """
    UPDATE ProjectTeamMember
    SET name = ?, student_number = ?, responsibility = ?
    WHERE member_id = ?
    """,
    [(name_1, sid_1, responsibility_1, 1), (name_2, sid_2, responsibility_2, 2)],
)
```

Do not guess which person owns `s4207910` or `s4189686`. If exact names/mapping have not been supplied, keep `L1-B-04` blocked and continue Tasks 5-9 without claiming final completion.

- [ ] **Step 5: Run Level 1 and full tests**

Run:

```powershell
python -m unittest tests.test_queries tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all implementable tests pass; the identity assertion is enabled only after exact data is installed.

- [ ] **Step 6: Update Level 1 matrix rows and commit**

```powershell
git add immunisation_app/queries.py immunisation_app/db.py immunisation_app/templates/home.html immunisation_app/templates/mission.html database/immunisation.db tests docs/REQUIREMENTS_MATRIX.md
git commit -m "feat: align overview and mission requirements"
```

Omit unchanged or unavailable identity files from `git add` when the external identity checkpoint is still open.

---

### Task 5: Vaccination Country and Region View

**Files:**
- Modify: `immunisation_app/queries.py`
- Modify: `immunisation_app/views.py`
- Modify: `immunisation_app/templates/vaccinations.html`
- Modify: `tests/test_queries.py`
- Modify: `tests/test_routes.py`
- Modify: `docs/REQUIREMENTS_MATRIX.md`

**Interfaces:**
- Consumes: `get_vaccination_view(db, *, antigen, year, country, region, sort_by, direction)`.
- Produces: `{"rows": list[dict], "summary": list[dict], "metrics": dict}` where `rows` contains only usable coverage values at or above 90.

- [ ] **Step 1: Write failing SQL behavior tests**

Add assertions:

```python
def test_vaccination_country_rows_only_include_countries_meeting_target(self):
    result = get_vaccination_view(
        self.db,
        antigen="MCV2",
        year=2010,
        country="",
        region="",
        sort_by="coverage",
        direction="desc",
    )
    self.assertGreater(len(result["rows"]), 0)
    self.assertTrue(all(row["coverage"] >= 90 for row in result["rows"]))
    self.assertGreater(result["metrics"]["countries_with_data"], 0)
    self.assertEqual(
        result["metrics"]["countries_meeting_target"], len(result["rows"])
    )
```

Retain the existing test proving values above 100 are labelled rather than capped.

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_vaccination_country_rows_only_include_countries_meeting_target -v
```

Expected: FAIL because the current detail query returns below-target rows and has no `metrics` key.

- [ ] **Step 3: Refactor vaccination SQL around one normalized CTE definition**

Keep the existing fallback expression:

```sql
COALESCE(
    CAST(NULLIF(TRIM(CAST(v.coverage AS TEXT)), '') AS REAL),
    v.doses * 100.0 / NULLIF(v.target_num, 0)
)
```

Filter the detail result with `WHERE coverage >= 90`. Add a metrics query over the same filtered input:

```sql
SELECT
    COUNT(DISTINCT CASE WHEN coverage IS NOT NULL THEN country_id END) AS countries_with_data,
    COUNT(DISTINCT CASE WHEN coverage >= 90 THEN country_id END) AS countries_meeting_target,
    COUNT(DISTINCT CASE WHEN coverage > 100 THEN country_id END) AS anomalous_coverage_count,
    ROUND(AVG(coverage), 2) AS average_coverage
FROM filtered
```

Return all three result parts. Keep SQL ordering whitelisted and retain the 500-row safety limit.

- [ ] **Step 4: Update route defaults and template output**

Use an empty metrics dictionary with explicit zero/`None` values when validation fails. Render:

- selected antigen/year context;
- metric strip for countries with data, countries meeting target, average coverage, and anomalies;
- regional summary table with antigen, year, region, countries with data, countries meeting 90%, and average coverage;
- country table with only countries meeting 90%;
- a data-quality note explaining missing fallback, invalid targets, and above-100 flags.

Add `<caption>` text to both tables and `tabindex="0"` to table wrappers.

- [ ] **Step 5: Add route tests for threshold output and combined filters**

Test `country` and `region` separately and together. Assert the response contains `Countries meeting 90% target`, `Regional target summary`, and `Reported above 100%` for a fixture selection known to contain anomalies.

- [ ] **Step 6: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_vaccination_country_rows_only_include_countries_meeting_target tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Update L2-A matrix rows and commit**

```powershell
git add immunisation_app/queries.py immunisation_app/views.py immunisation_app/templates/vaccinations.html tests docs/REQUIREMENTS_MATRIX.md
git commit -m "feat: align vaccination target analysis"
```

---

### Task 6: Infection View by Economic Status

**Files:**
- Modify: `immunisation_app/queries.py`
- Modify: `immunisation_app/templates/infections.html`
- Modify: `tests/test_queries.py`
- Modify: `tests/test_routes.py`
- Modify: `docs/REQUIREMENTS_MATRIX.md`

**Interfaces:**
- Consumes: `get_infection_by_economy(db, *, economy_id, infection_id, year, search, sort_by, direction)`.
- Produces: country rows for exactly one economy, an all-economy aggregate, and the selected economy summary.

- [ ] **Step 1: Write failing completeness and aggregation assertions**

Add to the existing infection query test:

```python
self.assertTrue(all(row["economy_id"] == 3 for row in result["rows"]))
self.assertTrue(all(row["infection"] == "Measles" for row in result["rows"]))
self.assertTrue(all(row["year"] == 2022 for row in result["rows"]))
for item in result["summary"]:
    expected_rate = item["total_cases"] / item["represented_population"] * 100000
    self.assertAlmostEqual(item["cases_per_100k"], expected_rate, places=6)
```

Add a search-filter test proving the filter is applied in SQL and a sort test for each meaningful varying result column: country, cases, population, and rate.

- [ ] **Step 2: Run focused query tests**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_infection_view_calculates_rate_and_all_economy_summary -v
```

Expected: current core assertions pass; new search/sort cases reveal any ordering or filter gap before markup changes.

- [ ] **Step 3: Tighten SQL output and deterministic ordering**

Keep country rates as:

```sql
id.cases * 100000.0 / NULLIF(cp.population, 0)
```

Keep the economy summary weighted by `SUM(cases) / SUM(population)`. Select only columns rendered by the page. Add deterministic secondary ordering by country for all sort modes. Keep search as a bound `LIKE` parameter.

- [ ] **Step 4: Refactor infection template semantics**

Render selected-economy metrics, followed by an all-economy summary table and country-detail table. Include infection, economy, year, cases, population, and cases per 100,000. Add captions, scoped headers, focusable table wrappers, retained filter selections, and the shared methodology note.

- [ ] **Step 5: Add route tests for all controls and empty search**

Exercise economy, infection, year, country search, sort field, and direction in one valid request. Exercise a search string that matches no country and assert the page-specific empty state appears with HTTP 200.

- [ ] **Step 6: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_queries tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Update L2-B matrix rows and commit**

```powershell
git add immunisation_app/queries.py immunisation_app/templates/infections.html tests docs/REQUIREMENTS_MATRIX.md
git commit -m "feat: strengthen infection economy analysis"
```

---

### Task 7: Population-Based Vaccination Improvement

**Files:**
- Modify: `immunisation_app/queries.py`
- Modify: `immunisation_app/templates/vaccination_improvement.html`
- Modify: `tests/test_queries.py`
- Modify: `tests/test_routes.py`
- Modify: `docs/REQUIREMENTS_MATRIX.md`

**Interfaces:**
- Consumes: `get_vaccination_improvements(db, *, antigen, start_year, end_year, limit, sort_by, direction)`.
- Produces: rows containing `country_id`, `country`, `antigen`, `start_year`, `end_year`, `start_rate`, `end_rate`, and `improvement`.

- [ ] **Step 1: Write failing output-shape and boundary tests**

Extend the query test:

```python
for row in rows:
    self.assertEqual(row["antigen"], "MCV1")
    self.assertEqual(row["start_year"], 2000)
    self.assertEqual(row["end_year"], 2024)
    self.assertAlmostEqual(
        row["improvement"], row["end_rate"] - row["start_rate"], places=6
    )
```

Add route cases for limit 3, limit 50, limit 2, limit 51, equal years, reversed years, and malformed year/limit values.

- [ ] **Step 2: Run the focused test and confirm output-shape failure**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_vaccination_improvement_uses_two_year_datasets -v
```

Expected: FAIL because the current rows do not contain antigen or year fields.

- [ ] **Step 3: Return complete comparison rows directly from SQL**

Carry antigen and the selected years into the final projection:

```sql
SELECT
    country_id,
    country,
    ? AS antigen,
    ? AS start_year,
    ? AS end_year,
    start_rate,
    end_rate,
    improvement
FROM improvements
ORDER BY ...
LIMIT ?
```

Keep rates based on doses divided by each country's population for the same year. Exclude non-positive populations, missing endpoint data, and non-positive improvements in SQL. Bind all values including the limit.

- [ ] **Step 4: Refactor the improvement result presentation**

Render all required fields from each row rather than reconstructing year/antigen values in Jinja. Add a concise calculation note, a results count, rank numbers derived from loop order, a table caption, and a no-positive-improvement state.

- [ ] **Step 5: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_vaccination_improvement_uses_two_year_datasets tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Update L3-A matrix rows and commit**

```powershell
git add immunisation_app/queries.py immunisation_app/templates/vaccination_improvement.html tests docs/REQUIREMENTS_MATRIX.md
git commit -m "feat: complete vaccination improvement ranking"
```

---

### Task 8: Global Infection Benchmark

**Files:**
- Modify: `immunisation_app/queries.py`
- Modify: `immunisation_app/templates/infection_benchmark.html`
- Modify: `tests/test_queries.py`
- Modify: `tests/test_routes.py`
- Modify: `docs/REQUIREMENTS_MATRIX.md`

**Interfaces:**
- Consumes: `get_above_global_infections(db, *, infection_id, year)`.
- Produces: an empty list when no valid benchmark exists, otherwise one `row_type == "global"` row followed by strictly above-global country rows.

- [ ] **Step 1: Write a failing no-data benchmark test**

Use the temporary database already created in `QueryTests.setUp`:

```python
def test_benchmark_returns_no_global_row_without_source_data(self):
    self.db.execute(
        "DELETE FROM InfectionData WHERE inf_type = ? AND year = ?",
        ("MEA", 2020),
    )
    self.db.commit()
    rows = get_above_global_infections(self.db, infection_id="MEA", year=2020)
    self.assertEqual(rows, [])
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_benchmark_returns_no_global_row_without_source_data -v
```

Expected: FAIL because the current aggregate emits a global row containing null values.

- [ ] **Step 3: Suppress invalid global rows in SQL**

In the global branch of the `combined` CTE, add:

```sql
FROM global_rate
WHERE cases_per_100k IS NOT NULL
```

Retain the weighted global calculation and `cr.cases_per_100k > gr.cases_per_100k`. Keep final ordering by global row first, then descending rate, then country.

- [ ] **Step 4: Refactor the benchmark template**

Keep a prominent benchmark summary, but ensure the comparison table itself repeats the global row first. Use the exact denominator label `per 100,000 people`, add a caption, scope headers, focusable wrapper, country count, weighted-calculation note, and no-benchmark empty state.

- [ ] **Step 5: Extend route ordering and empty-state tests**

Assert the global row's HTML appears before the first country row. Create a route-test database state with the selected source rows removed and assert `No benchmark available` is displayed without rendering `No data` as a global rate.

- [ ] **Step 6: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_queries.QueryTests.test_benchmark_returns_no_global_row_without_source_data tests.test_routes -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Update L3-B matrix rows and commit**

```powershell
git add immunisation_app/queries.py immunisation_app/templates/infection_benchmark.html tests docs/REQUIREMENTS_MATRIX.md
git commit -m "feat: harden global infection benchmark"
```

---

### Task 9: Responsive, Accessibility, and Visual Verification

**Files:**
- Modify: `immunisation_app/static/css/styles.css`
- Modify as defects require: `immunisation_app/templates/base.html`
- Modify as defects require: `immunisation_app/templates/*.html`
- Modify: `tests/test_routes.py`
- Modify: `docs/REQUIREMENTS_MATRIX.md`
- Create: `docs/VERIFICATION.md`

**Interfaces:**
- Consumes: completed six-page HTML and CSS.
- Produces: verified desktop/mobile/keyboard behavior and an evidence record for repeatable final checks.

- [ ] **Step 1: Add automated semantic checks before visual changes**

Add route tests for all six pages that assert one `<h1`, a non-empty `<title>`, the shared navigation, and the main landmark. Add page-specific assertions for form labels, table captions, `role="alert"`, and empty-state headings.

- [ ] **Step 2: Run semantic tests and confirm failures identify concrete gaps**

Run:

```powershell
python -m unittest tests.test_routes -v
```

Expected: any remaining missing caption, label, heading, or landmark assertion fails before correction.

- [ ] **Step 3: Correct responsive and accessibility defects**

At minimum verify and correct:

```text
1440px: navigation, content width, hero, filters, summary cards, and wide tables
768px: wrapped navigation, two-column collapse, form grid, and table overflow
375px: no page-level horizontal overflow, visible navigation, single-column forms/cards
Keyboard: skip link, navigation, every control, submit button, and table wrapper
Motion: reduced-motion preference removes nonessential smooth scrolling/transitions
No JavaScript: all links and GET forms remain usable
```

Never remove result columns at narrow widths; keep horizontal scrolling inside `.table-shell`.

- [ ] **Step 4: Run the app for browser verification**

Run:

```powershell
python app.py
```

Open each route using representative valid parameters:

```text
/
/mission
/vaccinations?antigen=MCV2&year=2010&sort=coverage&direction=desc
/infections?economy=3&infection=MEA&year=2022&sort=rate&direction=desc
/vaccination-improvement?antigen=MCV1&start_year=2000&end_year=2024&limit=10&sort=improvement&direction=desc
/infection-benchmark?infection=MEA&year=2020
```

Inspect at 1440x900, 768x1024, and 375x812. Record each pass or concrete correction in `docs/VERIFICATION.md`.

- [ ] **Step 5: Verify invalid and empty states in the browser**

Open malformed year, invalid sort, reversed-year, impossible search, and no-benchmark cases. Confirm visible neutral guidance, retained user input where safe, no traceback, and no layout overflow.

- [ ] **Step 6: Run full automated verification**

Run:

```powershell
python -m unittest discover -s tests -v
git diff --check
git status --short
```

Expected: all tests pass, `git diff --check` prints nothing, and only intended files are modified.

- [ ] **Step 7: Update the matrix and verification record**

Mark a requirement `Met` only when its implementation and test/manual evidence columns are populated. Keep the team identity row `Blocked` until exact values are installed. Include the database anomaly counts and tested viewport sizes in `docs/VERIFICATION.md`.

- [ ] **Step 8: Commit UI verification corrections**

```powershell
git add immunisation_app/static/css/styles.css immunisation_app/templates tests/test_routes.py docs/REQUIREMENTS_MATRIX.md docs/VERIFICATION.md
git commit -m "test: verify responsive requirements experience"
```

---

### Task 10: Final Requirements Audit and Submission Readiness

**Files:**
- Modify: `docs/REQUIREMENTS_MATRIX.md`
- Modify: `docs/VERIFICATION.md`
- Modify only for confirmed identity data: `immunisation_app/db.py`
- Modify only for confirmed identity data: `database/immunisation.db`

**Interfaces:**
- Consumes: all task outputs and the exact two team identity records.
- Produces: a clean branch where every non-blocked requirement has evidence and the full test suite passes.

- [ ] **Step 1: Resolve the team identity checkpoint**

Obtain both exact names and explicit student-number mapping for `s4207910` and `s4189686`. Apply the parameterized update described in Task 4, update `TEAM_MEMBERS`, and add this test:

```python
def test_team_data_contains_submission_identities(self):
    members = get_team_members(self.db)
    self.assertEqual(
        {member["student_number"] for member in members},
        {"s4207910", "s4189686"},
    )
    self.assertTrue(
        all("replace in database" not in member["name"].lower() for member in members)
    )
```

Run the focused query and mission route tests and mark `L1-B-04` met only after they pass.

- [ ] **Step 2: Audit every matrix row against real evidence**

For each row, open the named route/query/template/test and verify the evidence exists. Do not change `Partial` or `Blocked` to `Met` based on intent or prose alone.

- [ ] **Step 3: Run final test and cleanliness commands**

Run:

```powershell
python -m unittest discover -s tests -v
git diff --check
git status --short --branch
git log --oneline --decorate -12
```

Expected: all tests pass, no whitespace errors, no generated QA files are tracked, and the branch contains one reviewable commit per task.

- [ ] **Step 4: Perform final six-route smoke check**

Request every route once with defaults and once with representative valid filters. Confirm HTTP 200, branded shell, no server traceback, and requirement-specific content.

- [ ] **Step 5: Commit final evidence**

```powershell
git add immunisation_app/db.py database/immunisation.db tests/test_queries.py docs/REQUIREMENTS_MATRIX.md docs/VERIFICATION.md
git commit -m "docs: complete requirements verification"
```

Omit unchanged identity files if they were committed in Task 4. Do not create this final commit while any mandatory matrix row remains blocked.
