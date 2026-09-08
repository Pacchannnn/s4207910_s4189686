# Immunisation Lens Controlled Refactor Design

**Date:** 2026-09-08
**Status:** Approved direction
**Scope:** All six pages required by the COSC3106 Studio Project requirements

## 1. Context

The existing Flask application is a working prototype with six routes, a SQLite database, Jinja templates, shared styling, validation helpers, SQL query functions, and 15 passing `unittest` tests. The refactor will preserve that foundation and bring the application into explicit alignment with the supplied requirements document.

The application must help varied users explore global immunisation and preventable-infection data in an informative, respectful, and unbiased way. It must provide a progression from high-level context to filtered summaries and deeper analysis. The six required pages are:

1. Landing page
2. Mission statement
3. Vaccination rates by country and region
4. Infection data by economic status
5. Countries with the biggest improvement in vaccination rates
6. Countries with above-average infection rates

## 2. Goals

- Preserve the existing database, Flask route structure, and correct SQL behavior.
- Make every requirement traceable to a page, route, query, and test where applicable.
- Provide a coherent visual and interaction system across all six pages.
- Keep data filtering and analytical calculations server-side.
- Make handling of missing, invalid, and anomalous data explicit and testable.
- Improve accessibility, responsive behavior, empty states, and validation feedback.
- Maintain clear separation between Level 1, Level 2, and Level 3 experiences.
- Finish with automated and manual verification against the requirements matrix.

## 3. Non-goals

- Replacing Flask or SQLite.
- Introducing a JavaScript framework or client-side data-processing layer.
- Adding authentication, user accounts, editing workflows, or external APIs.
- Changing the supplied source dataset to manufacture cleaner results.
- Introducing abstractions or template components that are used only once without a clarity benefit.

## 4. Chosen Approach

Use a controlled in-place refactor.

The public route paths and main query function responsibilities remain stable. Work proceeds in small vertical slices so each page remains runnable. Frontend structure and design are standardized first, followed by targeted query and validation changes found through the requirements audit. Existing behavior is protected by tests before it is changed.

This approach is preferred over a frontend replacement because it retains functioning Jinja integrations and empty/error states. It is preferred over a full application-layer rewrite because the current route-query-template boundaries are already suitable for the assignment.

## 5. Application Architecture

The application keeps the following dependency flow:

```text
HTTP GET request
    -> Flask route in views.py
    -> reference-data and input validation
    -> parameterized SQL query in queries.py
    -> plain row dictionaries
    -> Jinja page template and shared partials
    -> semantic HTML styled by the shared CSS system
```

Responsibilities remain explicit:

- `views.py`: request parsing, validation orchestration, query selection, and template context.
- `validation.py`: reusable parsing and allowed-choice checks.
- `queries.py`: parameterized selection, joining, aggregation, calculation, sorting, and limiting.
- `db.py`: connection lifecycle and project-specific database tables.
- templates: semantic presentation without analytical calculations.
- CSS: tokens, layout, components, page-specific refinements, and responsive rules.
- JavaScript: optional progressive enhancement only; no requirement-critical behavior.

## 6. Requirements Traceability

A requirements matrix will be maintained at `docs/REQUIREMENTS_MATRIX.md`. Each row will include:

- a stable requirement ID;
- the source section and concise requirement statement;
- the responsible page and route;
- current implementation evidence;
- target implementation evidence;
- automated test evidence;
- status: met, partial, missing, or blocked.

The matrix is the acceptance checklist for the refactor. Example figures in the PDF are treated only as examples; actual output must be derived from the supplied database.

## 7. Page Designs

### 7.1 Landing Page

The landing page captures attention, identifies the website's topics, explains the exploration paths, and presents exactly four database-derived facts relevant to the target personas. Facts will use clear labels and context rather than presenting isolated large numbers. The page will also introduce the progression from overview to focused exploration and deep analysis.

### 7.2 Mission Statement

The mission page explains the site's perspective on the social challenge, how the site can be used, the target personas, and the team. Personas and team details remain stored in and retrieved from SQLite.

Identity data will never be invented. The current placeholder team records are treated as a content blocker for final submission and will be replaced only with user-provided names and student numbers. Until supplied, the requirements matrix will mark that requirement partial while continuing all other implementation work.

### 7.3 Vaccination Rates by Country and Region

The page provides antigen, year, country, region, sort-field, and direction controls using a server-side GET form. Country and region filters can be used independently or together.

The result area contains:

- concise selection and data-quality context;
- a table limited to countries meeting at least 90% of the selected antigen target;
- a regional summary showing countries with data, countries meeting the 90% target, and a clearly defined regional coverage statistic;
- an empty state when no rows match.

The UI will distinguish coverage values above 100% as reported anomalies rather than silently capping them.

### 7.4 Infection Data by Economic Status

The page provides one economic-status selection, infection type, year, country-name filter, sort-field, and direction controls. The country table displays all required resulting columns, including cases per 100,000 people. The summary table aggregates the selected infection and year across all economic phases, combining infection, country, economy, and population data.

### 7.5 Vaccination Improvement

The page provides starting year, ending year, antigen, result count, sort-field, and direction controls. The result table contains country, start rate, end rate, rate increase, start year, and end year.

Vaccination rates are calculated from doses and country population for each selected year. Only countries with valid positive population and values for both endpoints are comparable. The improvement and ordering remain in SQL, with a parameterized result limit.

### 7.6 Infection Benchmark

The page provides year and infection-type controls. A single SQL operation derives country rates, the weighted global rate, and countries exceeding that rate. The global benchmark is displayed first, followed by the above-average countries sorted by rate. An empty state explains when a valid benchmark cannot be calculated.

## 8. Shared Interface System

Shared layout remains in `base.html`. Repeated fragments will be extracted only when at least two pages use the same structure or behavior. Candidate shared components are:

- page header;
- validation notice;
- filter-panel structure;
- table wrapper and empty state;
- methodology/data-quality note.

Jinja macros or includes will accept explicit data and presentation parameters. Page templates remain responsible for page-specific column definitions and content so the abstraction does not hide requirements.

The CSS will be organized into documented sections within one delivered stylesheet unless file splitting materially improves maintenance. Sections will cover reset, tokens, base elements, layout, components, pages, utilities, and responsive rules. Existing visual tokens may be retained when they fit the approved direction, but conflicting legacy overrides will be removed during migration.

## 9. Interaction and Accessibility

- All analytical filters submit with method `GET`, producing shareable URLs.
- Core navigation and every data task work without JavaScript.
- JavaScript may enhance the narrow-screen navigation and submit feedback, but its absence must not hide navigation or prevent form use.
- Every form control has a visible label.
- Error summaries use appropriate alert semantics and remain close to their forms.
- Tables use captions or nearby programmatic headings, scoped headers, and responsive overflow without removing columns.
- Focus states, keyboard navigation, skip navigation, color contrast, and reduced-motion preferences are verified.
- Empty, invalid, loading-enhanced, and no-data states use plain, neutral language.

## 10. Data Quality Rules

The source database audit found:

- 24,211 vaccination rows;
- 5,415 rows with missing or blank reported coverage;
- 153 rows with missing or non-positive target values;
- 1,312 rows with reported coverage above 100%;
- no duplicate `(country, antigen, year)` vaccination keys;
- no duplicate `(country, infection type, year)` infection keys;
- no duplicate `(country, year)` population keys;
- no null or non-positive population rows;
- data years spanning 2000 through 2024.

The application therefore applies these rules:

1. Prefer a valid reported coverage value on Level 2 vaccination views.
2. When reported coverage is missing, calculate coverage from doses divided by a valid positive target.
3. If neither value supports a calculation, display `No data` and exclude that row from aggregate rate calculations.
4. Do not cap values above 100%; label them as reported anomalies.
5. Calculate population-based Level 3 rates only when population is positive.
6. Calculate global infection rate as total cases divided by total represented population, not as an unweighted average of country rates.
7. Preserve parameterized SQL and whitelist all user-selectable sort expressions.
8. Document the absence of current duplicate natural keys and keep duplicate-detection checks in tests or audit tooling so the assumption remains visible.

## 11. Validation and Error Handling

All select values are checked against database-derived choices. Integer inputs fall back only for missing values; explicitly malformed input must produce a visible validation error rather than silently selecting a default. Start year must precede end year. Result count remains within a documented safe range. Sort keys and directions are whitelisted.

Valid requests with zero matches produce page-specific empty states. Database errors are not exposed to the browser. The branded 404 behavior remains covered by tests.

## 12. Testing Strategy

The existing 15 `unittest` tests form the baseline. The implementation will extend them in four layers:

1. Query tests for calculations, joins, aggregation, anomaly handling, sorting, limiting, and no-data behavior.
2. Route tests for all six pages, valid filters, malformed values, boundaries, empty results, and retained selections.
3. Requirements tests for database-derived landing facts, database-derived mission content, threshold filtering, global-row ordering, and required output columns.
4. Manual UI verification for common desktop and mobile widths, keyboard operation, focus visibility, overflow tables, contrast, and JavaScript-disabled core flows.

Tests will continue to run with the standard library command `python -m unittest discover -s tests -v`. `pytest` may be added only if it provides a concrete benefit; it is not required by the current project.

## 13. Delivery Sequence

1. Create the requirements, route, template, SQL, and test audit matrices.
2. Add characterization tests around behavior that must remain stable.
3. Refactor the shared base template and interface system.
4. Refactor pages in order: landing, mission, vaccination, infection, improvement, benchmark.
5. Make targeted query and validation changes identified by the matrix.
6. Extend automated tests for normal, invalid, boundary, missing-data, and empty-result cases.
7. Perform responsive and accessibility verification.
8. Run the final requirements audit and remove obsolete code and styles.

Each page slice must render and pass relevant tests before the next page begins.

## 14. Acceptance Criteria

The refactor is complete when:

- all six required pages are accessible through the shared navigation;
- every mandatory PDF requirement is marked met with implementation evidence;
- displayed facts, personas, team details, filters, rates, summaries, and rankings are database-derived where required;
- analytical calculations, aggregation, sorting, and limiting occur in SQL where appropriate;
- missing and anomalous values follow the documented rules;
- no requirement-critical interaction depends on JavaScript;
- automated tests pass from a clean checkout;
- manual desktop, mobile, keyboard, and empty/error-state checks pass;
- no placeholder team identity data remains in the submission database.
