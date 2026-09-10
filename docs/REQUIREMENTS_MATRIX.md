# Requirements and Current-State Matrix

This is the acceptance checklist for the **Sub-Task B** submission. Requirements are derived from the supplied page brief; example figures in that brief are illustrative only.

## Scope change — 10 September 2026

The application previously implemented all six pages (Sub-Task A and Sub-Task B). The Sub-Task A pages — the landing page (`/`), the vaccination coverage explorer (`/vaccinations`) and the vaccination improvement ranking (`/vaccination-improvement`) — were removed, together with their queries, templates, styles, tests and matrix rows.

What changed as a consequence:

- The Mission page is now served at `/`. The old `/mission` address returns a permanent redirect to `/`.
- `get_snapshot`, `get_latest_infection_totals`, `get_vaccination_view` and `get_vaccination_improvements` were deleted from `queries.py`.
- `get_reference_data` now returns only economies, infection types and years; the antigen, country and region lists had no remaining consumer.
- The persona rows in `ProjectPersona` were updated so the "supported by" text names features that still exist. The tracked database therefore has a new SHA-256; see `VERIFICATION.md`.
- The team member rows are unchanged: the brief requires the Mission page to list all team members.

Acceptance rows for the removed pages (L1-A-*, L2-A-*, L3-A-*) were removed rather than marked unmet. Verification records that only evidenced those pages were removed with them.

## Requirement matrix

| ID | Requirement | Route | Query/template evidence | Test evidence | Current | Target |
|---|---|---|---|---|---|---|
| L1-B-01 | Explain the site's respectful, informative, and unbiased perspective on the social challenge. | `/` | `views.mission`; `mission.html` explicitly describes transparent, comparable, respectfully presented data and cautions against presenting association as causation. | `RouteTests.test_mission_presents_perspective_guidance_and_database_content` | Met | Retain the plain, neutral framing. |
| L1-B-02 | Explain how users can use the site, including the orient/focus/deepen exploration guidance. | `/` | `mission.html` provides linked Orient, Focus, and Deepen steps spanning the mission page, the Level 2 explorer and the Level 3 analysis. | `RouteTests.test_mission_presents_perspective_guidance_and_database_content` | Met | Preserve the linked three-layer guidance. |
| L1-B-03 | Display target personas with their goals, needs, and supported features from SQLite. | `/` | `queries.get_personas` selects `ProjectPersona`; `mission.html` renders every returned role, name, goal, need, and app feature. | `QueryTests.test_mission_data_is_retrieved_from_database`; `RouteTests.test_mission_presents_perspective_guidance_and_database_content` | Met | Keep all persona content database-derived. |
| L1-B-04 | Display the project team with exact names and student-number mapping supplied for submission. | `/` | `TEAM_MEMBERS` and the tracked `ProjectTeamMember` rows map member 1 to Le Chi Bach (`s4207910`) and member 2 to Nguyen Tran Ba Trong (`s4189686`); `queries.get_team_members` retrieves them in member order and `mission.html` renders their names, student numbers, and responsibilities. | `QueryTests.test_team_data_contains_submission_identities`; `QueryTests.test_project_table_initialisation_installs_submission_identities`; `RouteTests.test_mission_renders_exact_database_backed_submission_identities` | Met | Preserve the exact mapping in both bootstrap data and the tracked SQLite database, with no placeholder output. |
| L2-01 | Use parameterized SQL for selection, filtering, sorting/whitelisted ordering, joining, aggregation, and explicit anomaly handling. | `/infections`, `/infection-benchmark` | `queries.py`: `_safe_order`; parameterized query values and limits in both analytical functions; SQL joins, CTE calculations, aggregation and deterministic ordering; captioned server-rendered result tables. | `QueryTests.test_sort_inputs_are_whitelisted`; query behaviour, all-sort-mode, weighted-rate and no-source tests; `RouteTests.test_analytical_controls_and_tables_have_accessible_names`; the route sweep in `docs/VERIFICATION.md`. | Met | Retain parameterized values, whitelisted ordering, SQL analytical work, and server-rendered GET experiences. |
| L2-02 | Handle missing, unmatched and non-positive values explicitly rather than silently substituting them. | `/infections`, `/infection-benchmark` | Both rate queries require a matching same-year `CountryPopulation` row with `population > 0`; unmatched or blank economy mappings are excluded, not reassigned; the methodology notes state that a missing record is not a zero. | `QueryTests.test_infection_view_calculates_rate_and_all_economy_summary`; `QueryTests.test_benchmark_is_weighted_strict_and_deterministic`; `QueryTests.test_benchmark_returns_no_global_row_without_source_data` | Met | Retain the explicit exclusion rules and the visible explanation of the denominator. |
| L2-B-01 | Provide economy, infection, year, country search, numeric detail filtering and sorting controls. | `/infections` | Numeric cases/population/rate and comparison inputs are validated; detail-only SQL predicates preserve summaries. Sortable headers and existing dropdowns share the same sort keys; header links preserve filters. | `ApprovedChangeTests.test_numeric_filters_all_columns_operators_leave_summaries_unchanged`; `test_invalid_numeric_inputs_bypass_query`; `MemberComponentTests.test_header_links_preserve_filters_and_toggle_direction`; existing route tests. | Met | Preserve numeric validation, summary scope, shareable GET parameters and accessible sort controls. |
| L2-B-02 | Show one economy's country-level infection results with infection, country, economy, year, cases, population, and cases per 100,000. | `/infections` | `get_infection_by_economy` projects the rendered country, economy, infection, year, cases, population, and rate fields after joining infection, country, economy, and population tables; `infections.html` presents them in a captioned, scoped-header table. | `QueryTests.test_infection_view_calculates_rate_and_all_economy_summary`; `RouteTests.test_infection_page_accepts_filters` | Met | Keep required columns and exclude non-positive populations explicitly. |
| L2-B-03 | Order country results by the selected resultant column and direction using a whitelist. | `/infections` | `_safe_order` maps country/cases/population/rate to SQL aliases; detail SQL orders by the chosen whitelisted value with a country tie-break. | `QueryTests.test_infection_view_applies_country_search_and_all_sort_modes`; `QueryTests.test_sort_inputs_are_whitelisted` | Met | Retain all four sort modes, direction handling, and deterministic ties. |
| L2-B-04 | Aggregate the selected infection and year across all economic phases using infection, country, economy, and population data. | `/infections` | `summary_sql` groups all economies and calculates weighted cases per 100,000 as `SUM(cases) / SUM(population)`; selected-economy metrics and a captioned all-economy table explain the method. | `QueryTests.test_infection_view_calculates_rate_and_all_economy_summary`; `RouteTests.test_infection_page_accepts_filters` | Met | Preserve weighted aggregation and the methodology note. |
| L3-01 | Design the analytical page around a sub-dataset SQL query and keep Python post-processing minimal. | `/infection-benchmark` | `get_above_global_infections` computes country rates, the weighted global rate and the strict above-global membership in one statement of CTEs; the view only splits the global row from the country rows for presentation. | `QueryTests.test_above_global_query_puts_global_row_first` | Met | Keep analytical logic in SQL and document any unavoidable presentation-only processing. |
| L3-02 | Ensure selected sorting is parameterized/whitelisted in analytical results. | `/infection-benchmark` | `_safe_order` handles country/cases/population/rate sort keys and both directions; the route rejects anything else before the query runs. | `ApprovedChangeTests.test_benchmark_sort_injection_falls_back_safely`; `test_benchmark_invalid_sort_bypasses_query` | Met | Retain the whitelisted sort modes and deterministic country ties. |
| L3-B-01 | Provide year, infection type and user-selected sorting controls. | `/infection-benchmark` | Route validates infection/year and country/cases/population/rate sorting in either direction. SQL pins the global row first. | `ApprovedChangeTests.test_benchmark_all_sorts_preserve_global_and_membership`; `test_benchmark_invalid_sort_bypasses_query`; existing route tests. | Met | Preserve global-first behaviour, membership, formula and whitelists. |
| L3-B-02 | Calculate the weighted global infection rate as total cases divided by total represented population. | `/infection-benchmark` | `global_rate` computes `SUM(cases)*100000/SUM(population)` over positive-population country rows and suppresses the global branch when that rate is null; the summary and methodology note state the denominator and weighted formula. | `QueryTests.test_benchmark_is_weighted_strict_and_deterministic`; `QueryTests.test_benchmark_returns_no_global_row_without_source_data`; benchmark route tests. | Met | Preserve the weighted calculation, positive-population rule, exact `per 100,000 people` label, and invalid-benchmark suppression. |
| L3-B-03 | Return countries whose infection rate is above the weighted global rate. | `/infection-benchmark` | Strict `cr.cases_per_100k > gr.cases_per_100k` membership; user-selected sorting changes only order. The template reports the returned country count. | `QueryTests.test_benchmark_is_weighted_strict_and_deterministic`; `ApprovedChangeTests.test_benchmark_all_sorts_preserve_global_and_membership` | Met | Retain strict SQL filtering, deterministic ties and the database-derived count. |
| L3-B-04 | Display the global benchmark row first, followed by user-sorted above-global countries. | `/infection-benchmark` | SQL orders by row group first, then the whitelisted user criterion; default is rate descending. Caption, scoped headers, labelled overflow wrapper and empty state remain. | Existing global-first/empty-state tests; `ApprovedChangeTests.test_benchmark_sort_routes_render_controls_and_global_first` | Met | Retain the global-first invariant across all sorts. |

## Route inventory

| Route | View function | Template | Primary requirement groups | Current evidence |
|---|---|---|---|---|
| `/` | `pages.mission` | `mission.html` | L1-B | Personas/team loaded from project tables. |
| `/mission` | `pages.mission_alias` | none | — | Permanent redirect to `/` for the pre-removal address. |
| `/infections` | `pages.infections` | `infections.html` | L2, L2-B | GET filters, country detail, all-economy summary. |
| `/infection-benchmark` | `pages.infection_benchmark` | `infection_benchmark.html` | L3, L3-B | Weighted global benchmark and above-global rows. |

## Template inventory

| Template | Route(s) | Relevant evidence |
|---|---|---|
| `base.html` | all | Shared navigation, visible-on-focus skip link, unique main landmark, stylesheet, branded shell, and no script dependency. |
| `mission.html` | `/` | Perspective, usage guidance, SQLite personas, team section. |
| `infections.html` | `/infections` | Labelled economy/infection/year/search/numeric/sort/direction GET form; scoped, captioned detail and all-economy tables in named focusable overflow regions. |
| `infection_benchmark.html` | `/infection-benchmark` | Infection/year/sort form, global benchmark first, above-global country table and methodology. |
| `404.html` | error handler | Branded not-found page linking back to the mission page. |

## Query inventory

| Query/function | SQL responsibilities | Used by |
|---|---|---|
| `get_reference_data` | Database-derived economy, infection and year choices. | `/infections`, `/infection-benchmark` |
| `get_personas` / `get_team_members` | Read project persona/team rows. | `/` |
| `get_infection_by_economy` | Parameterized joins, population-adjusted rate, country search/sort/numeric filter/limit, all-economy weighted summaries. | `/infections` |
| `get_above_global_infections` | Country rates, weighted global rate, strict-above filter, global-first ordering. | `/infection-benchmark` |

## Test inventory

| Test module | Coverage relevant to matrix |
|---|---|
| `tests/test_queries.py` | Idempotent project tables; exact bootstrap and tracked-database team identities; database-derived mission rows; infection rates, country search and all sort modes; economy summary; global benchmark ordering, weighting and no-source behaviour; sort whitelist/injection safety. |
| `tests/test_routes.py` | All three routes and the legacy redirect; one-h1/title/navigation/main shell semantics; visible labels for every analytical control; captions, column-header scopes, and named focusable table regions; alert and empty-state headings; Level 1 content including exact database-backed team identities and placeholder rejection; analytical valid/invalid/empty behaviour; branded 404. |
| `tests/test_approved_changes.py` | Benchmark sorting invariants and injection fallback; numeric detail filtering across every column/operator with unchanged summaries; invalid numeric input bypassing the query. |
| `tests/test_member_components.py` | Sortable header links, active sort state, row-header semantics and the collapsed-methodology contract on Infections. |
| `tests/test_validation.py` | Strict integer parsing and explicit scalar whitelisting. |

## Cross-page verification evidence

| Experience contract | Implementation evidence | Automated evidence | Status |
|---|---|---|---|
| Semantic page shell and keyboard entry | `base.html` primary navigation, skip link, and `#main-content`; one page-level heading in each route template. | `RouteTests.test_all_three_pages_have_one_named_document_shell` | Met |
| Visible labels, validation alerts, and empty-state headings | Analytical templates use wrapping labels and the shared labelled alert include; each no-data branch has a descriptive heading. | `RouteTests.test_analytical_controls_and_tables_have_accessible_names`, `test_invalid_filters_render_a_labelled_alert`, `test_empty_results_use_descriptive_headings` | Met |
| Responsive layouts without page overflow | `styles.css` 1100/860/640 breakpoints collapse grids/forms/cards; narrow navigation and `.table-shell` use local horizontal overflow. | `RouteTests.test_phone_styles_stack_every_filter_control_in_one_column`; browser check recorded in `docs/VERIFICATION.md`. | Met |
| Complete accessible data tables | Every analytical table has a caption and scoped headers inside a named `role="region"`, `tabindex="0"` wrapper; no responsive rule removes columns. | `RouteTests.test_analytical_controls_and_tables_have_accessible_names` | Met |
| Reduced motion and no JavaScript dependency | Reduced-motion media query disables smooth scrolling and shortens transitions/animations; navigation and GET forms are server-rendered. | `RouteTests.test_shared_shell_has_accessible_navigation_and_no_js_dependency`; zero `<script>` elements in the route sweep. | Met |

## Audit notes

- Exact team identities are consistent across `TEAM_MEMBERS`, the tracked SQLite rows, query output, and the Mission page: Le Chi Bach is mapped to `s4207910`, and Nguyen Tran Ba Trong is mapped to `s4189686`.
- Passing tests are not proof that every assignment requirement is satisfied, and source-data anomalies are handled and explained rather than repaired. See `docs/KNOWN_ISSUES.md`.
