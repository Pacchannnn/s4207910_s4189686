# Responsive, Accessibility, and Visual Verification

**Date:** 9 September 2026
**Task baseline:** `e4c1068`
**Application:** Flask/Waitress application served locally from `python app.py`

This record covers the six required routes, validation and empty states, semantic HTML, keyboard operation, reduced motion, and layouts at the three required viewport sizes. Screenshots were generated in an isolated temporary directory and deliberately not added to the repository.

## Automated semantic verification

The route suite renders real Flask responses and parses the returned HTML with the standard-library `HTMLParser`. The Task 9 checks verify:

- exactly one `<h1>`, a non-empty `<title>`, one labelled primary `<nav>`, and one `#main-content` landmark on every required page;
- visible wrapping labels for every analytical control;
- a non-empty caption, `scope="col"` column headers, and a focusable, named `role="region"` wrapper for every rendered result table;
- a labelled `role="alert"` for invalid filters; and
- descriptive headings for vaccination, infection, improvement, and benchmark empty states.

TDD evidence:

1. RED: the new cross-page shell and empty-state checks passed, while the analytical-table test failed for vaccination because its headers lacked `scope="col"`, and for vaccination/infection/improvement because wrappers lacked an accessible region name.
2. GREEN: the vaccination headers were scoped and the previously unnamed table wrappers received specific `role="region"`/`aria-label` values. The focused three-test run passed, followed by all 27 route tests.
3. An older vaccination test was loosened from an exact attribute-order fragment to counting `.table-shell` instances, so it continues testing the two-table behavior without rejecting added accessibility attributes.
4. Review RED/GREEN: the prior label parser collapsed duplicate control names and discarded unnamed controls. The adversarial fragment containing one labelled `year` select, an extra unlabelled `year` input, and an unnamed input failed against commit `8b7e34a`; the instance-based parser identifies both unlabelled inputs and the focused regression passes. A second adversarial fragment proved that uniqueness must include every document element: a non-control element sharing the target ID now invalidates the explicit label association. Visible wrapping-label text excludes option content, while explicit labels require a unique document-wide matching control ID.

## Browser method

The Codex in-app browser was initially reported, but after the interrupted run its required reset and rediscovery returned `browsers: []`. The fallback used the installed Chrome 152.0.7977.77 in headless mode with an isolated temporary profile and the Chrome DevTools Protocol against the live localhost application. This provided exact viewport emulation, screenshots, computed layout measurements, keyboard input, focus styles, and reduced-motion emulation without touching the user's normal browser profile.

All screenshots listed below were personally inspected. Automated DOM measurements accompanied each capture and checked viewport width, document scroll width, grid columns, control bounds, table-wrapper bounds/scroll width, page scripts, form method, alert text, and empty-state headings.

## Required route sweep

| Route | Representative query | 1440x900 | 768x1024 | 375x812 | Evidence observed |
|---|---|---|---|---|---|
| `/` | none | Pass | Pass | Pass | Hero remains legible; four cards move from four to two to one column; exploration and latest-year layouts collapse without overlap. |
| `/mission` | none | Pass | Pass | Pass | Intro changes from two columns to one; usage steps and persona content stack cleanly; navigation remains available. |
| `/vaccinations` | `antigen=MCV2&year=2010&sort=coverage&direction=desc` | Pass | Pass | Pass | Six controls render in one row, then three columns, then one column; metric strip changes 4/2/1 columns; both complete tables scroll only inside their wrappers. |
| `/infections` | `economy=3&infection=MEA&year=2022&sort=rate&direction=desc` | Pass | Pass | Pass | Filter and metric grids collapse correctly; both complete tables retain all columns and use local horizontal overflow. |
| `/vaccination-improvement` | `antigen=MCV1&start_year=2000&end_year=2024&limit=10&sort=improvement&direction=desc` | Pass | Pass | Pass | Comparison controls and methodology panel collapse cleanly; all eight ranked-result columns remain in the scrollable table. |
| `/infection-benchmark` | `infection=MEA&year=2020` | Pass | Pass | Pass | Benchmark summary changes from three columns to one; the global-first comparison preserves all six columns inside local overflow. |

Measured responsive evidence:

- No tested route had page-level horizontal overflow. Desktop document width was 1425px inside the 1440px viewport (the remaining width is the vertical scrollbar); tablet and phone document widths were exactly 768px and 375px.
- At 375px, content and controls stayed between 14px and 361px. At 768px they stayed between 20px and 748px.
- At 375px, result wrappers measured 345px client width while complete tables measured at least 760px (up to 790px for vaccination detail). At 768px, wrappers measured 726px and tables remained locally scrollable where wider. No columns were hidden or removed.
- The narrow primary navigation is always rendered and horizontally scrollable (347px client width, 533px content width at 375px). Keyboard focus automatically exposed the off-screen Improvement and Benchmark links.

## Validation and empty-state sweep

Each state was captured and measured at 1440x900, 768x1024, and 375x812.

| State | Route/query | Result |
|---|---|---|
| Malformed year and invalid sort/direction | `/infections?economy=3&infection=MEA&year=twenty&sort=unknown&direction=sideways` | Pass: HTTP page remained branded with no traceback; labelled alert showed all three neutral instructions; safe database defaults were selected; no overflow. |
| Reversed years | `/vaccination-improvement?antigen=MCV1&start_year=2024&end_year=2000&limit=10` | Pass: both user-selected years and count were retained; labelled `Check the comparison` alert explained the order requirement; no result calculation or overflow. |
| Impossible country search | `/infections?economy=3&infection=MEA&year=2022&search=no-such-country` | Pass: search text was retained; economy summary remained available; `No matching countries` heading and guidance replaced only the detail result; no overflow. |
| No benchmark source data | `/infection-benchmark?infection=MEA&year=2020` against a temporary database copy with those source rows removed | Pass: `No benchmark available` heading and neutral guidance rendered, no false global card or null rate appeared, and no overflow occurred. The tracked database was not changed. |

## Keyboard, motion, and no-JavaScript checks

- At 375x812 on the vaccination route, injected Tab events produced this order: skip link; brand; all six navigation links; antigen; year; country; region; sort; direction; submit button; regional table wrapper; country table wrapper. Every stop computed a solid focus outline.
- The first Tab made `Skip to content` visible at `(16, 16)`; the link targets the unique `#main-content` landmark.
- Focus reached both horizontally scrollable table regions. Each has `tabindex="0"`, `role="region"`, and a page-specific accessible name.
- With `prefers-reduced-motion: reduce`, the media query matched, computed HTML `scroll-behavior` was `auto`, and nonessential animation/transition durations computed to `0.01ms`.
- Every rendered page contained zero `<script>` elements. All four analytical forms computed `method="get"`, every navigation destination is an ordinary link, and representative query URLs returned complete server-rendered results.

## Contrast spot checks

WCAG relative-luminance calculations for the delivered solid-color pairs were:

| Pair | Contrast |
|---|---:|
| `--ink` on white | 17.30:1 |
| `--muted` on white | 5.67:1 |
| white on `--red` button | 5.19:1 |
| white on `--teal` | 6.08:1 |
| white on `--teal-dark` | 9.29:1 |
| success text/background | 5.26:1 |
| warning text/background | 5.69:1 |
| neutral status text/background | 5.88:1 |

These spot checks exceed the 4.5:1 normal-text threshold. Status meaning is also written in text rather than communicated by color alone.

## Database quality snapshot

The tracked SQLite database was queried directly during this verification:

| Check | Count/result |
|---|---:|
| Vaccination rows | 24,211 |
| Missing or blank reported coverage | 5,415 |
| Missing or non-positive target values | 153 |
| Reported coverage above 100% | 1,312 |
| Duplicate vaccination `(country, antigen, year)` groups | 0 |
| Duplicate infection `(country, infection, year)` groups | 0 |
| Duplicate population `(country, year)` groups | 0 |
| Null or non-positive population rows | 0 |
| Available year range | 2000-2024 |
| Project team identities | Le Chi Bach (`s4207910`); Nguyen Tran Ba Trong (`s4189686`) |

The vaccination page retains above-100% values and labels them; it does not cap them. During Task 9, the exact team-name/student-number checkpoint was still blocked and the placeholder rows were not altered; Task 10 resolves that checkpoint below.

## Final requirements and submission audit

Task 10 began from commit `e3f1fdc`. All 28 rows in `docs/REQUIREMENTS_MATRIX.md` were checked against their named view, query, template, and test evidence. Every mandatory row is Met; none remains Partial or Blocked.

Identity TDD evidence:

1. RED: the exact query and Mission-route regressions both failed against the tracked placeholder rows. The query returned `sID1` and `sID2`, and the rendered route did not contain Le Chi Bach.
2. GREEN: the tracked database was updated with a parameterized two-row statement and the bootstrap constants were aligned. The exact query mapping, route output, placeholder rejection, existing database-backed Mission behavior, and initialisation idempotence checks passed.
3. Bootstrap RED/GREEN: deleting both temporary team rows and re-running project-table initialisation failed with the old `TEAM_MEMBERS` constants, then passed after the exact identities were restored. This proves a newly populated project table receives the same submission mapping as the tracked database.

The final Flask test-client smoke requested each route with defaults and, where the route defines filters, one representative valid query. `/` and `/mission` have no filter controls, so their second checks repeated the canonical route with a second requirement-specific assertion.

| Route | Default check | Representative valid check | Requirement-specific evidence |
|---|---|---|---|
| `/` | HTTP 200 | Canonical route repeated; filters not applicable | Four database facts and the overview-to-analysis paths rendered. |
| `/mission` | HTTP 200 | Canonical route repeated; filters not applicable | Three usage layers and exact database-backed team identities rendered without placeholders. |
| `/vaccinations` | HTTP 200 | `antigen=MCV2&year=2010&sort=coverage&direction=desc` | Regional summary and 90%-target country result content rendered. |
| `/infections` | HTTP 200 | `economy=3&infection=MEA&year=2022&sort=rate&direction=desc` | All-economy summary and selected-economy metrics rendered. |
| `/vaccination-improvement` | HTTP 200 | `antigen=MCV1&start_year=2000&end_year=2024&limit=10&sort=improvement&direction=desc` | Complete positive-improvement comparison rendered. |
| `/infection-benchmark` | HTTP 200 | `infection=MEA&year=2020` | Global-first benchmark comparison rendered. |

All 12 smoke responses contained the branded shell and `#main-content`, omitted a server traceback, and included their requirement-specific marker.

Pre-commit verification results:

- `python -m unittest tests.test_queries tests.test_routes -v`: 48 tests passed.
- `python -m unittest discover -s tests -v`: 51 tests passed.
- `PRAGMA integrity_check`: `ok`; the tracked database returned exactly the two mapped team rows in member order.
- `git diff --check`: exit 0 with no whitespace errors (Git emitted only the expected Windows LF-to-CRLF working-copy notices).
- `git status --short --branch` showed only the six intended Task 10 files, and the 12-commit log confirmed the reviewed Task 5-9 history leading to the exact Task 10 baseline `e3f1fdc`.

## Repeatable final commands

```powershell
python -m unittest tests.test_routes -v
python -m unittest discover -s tests -v
git diff --check
git status --short --branch
```
