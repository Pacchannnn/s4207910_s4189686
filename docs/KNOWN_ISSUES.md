# Known issues and resolution history

## Current audit status — 10 September 2026

| Item | Status | Evidence / remaining scope |
|---|---|---|
| CHANGE 1: blank doses in coverage fallback | Resolved | Fallback requires numeric doses, numeric target and target > 0. Missing input is excluded, not zero-filled. Reported coverage remains preferred. |
| CHANGE 2: fictitious vaccination improvement | Resolved | Both endpoint datasets require numeric doses; blank start/end doses cannot create an improvement. Population joins, sorting and limits are unchanged. |
| CHANGE 6: regional summary scope | Resolved, wording only | Description and caption explain that selected filters apply; a selected country is not the whole region. |
| CHANGE 8, 9, 10, 11 | Completed within their approved scope | Three audit documents updated; main README added; development/private ignore rules added without ignoring the database; unused hero image removed after dependency checks. |
| CHANGE 3, 4, 5 | Resolved within approved scope | Benchmark user-selected sorting preserves the global row and membership; Improvement selects largest N before presentation sorting; numeric filtering applies to Infections detail only, with safe validation. |
| CHANGE 7 | Completed | Missing-data and denominator explanations were added without changing queries or source data. |
| CHANGE 12 | Completed within approved scope | Safe cache cleanup and Git archive exclusions applied. Development history retained; four ignored `.pyc` files remain under `tests/__pycache__`. No claim that the local folder is artifact-free. |
| CONTRIBUTION 1, 2, 3, 5 | Integrated | Infections header links preserve filters and expose sort state; country/economy labels are row headers; optional methodology detail collapses while warnings remain visible; README attribution is limited to adapted UI components. |
| CHANGE 1–12 | Completed within approved scopes | Historical facts and source anomalies below are not erased by this status. |
| CHANGE 13, 14 | Not performed | No implementation or cleanup under these changes. |

Current suite: **73/73 tests pass**, including four tests in `tests/test_member_components.py`. Historical CHANGE 1/2 evidence remains 57/57 tests and independent coverage 125/125 / improvement 1500/1500 checks. The contribution integration did not change database, query, validation or calculation logic. See `VERIFICATION.md` for scope and history; passing tests are not proof of absence of all possible defects.

The historical BUG-01 wording fix below preceded CHANGE 4. The later Top N query-contract concern is now resolved by selecting largest N before presentation sorting. Historical examples and test totals below continue to describe earlier versions, not current numerical results.

### Remaining source-data and packaging notes

- Source data still contains blank vaccination fields, coverage above 100%, nine unmatched vaccination country codes, and blank economy mappings for Ethiopia and Venezuela. The two Country-to-Economy foreign-key findings have not been repaired. These are handled/explained rather than silently rewritten.
- `docs/superpowers/plans/2026-09-08-immunisation-app-refactor.md` and `docs/superpowers/specs/2026-09-08-immunisation-app-refactor-design.md` remain tracked. Archive exclusion does not untrack them or prevent a Git push. Changing their tracking requires the user's action/approval.
- `.superpowers/` and the remaining test bytecode are ignored. No additional cleanup or Git-index change was performed during the final documentation audit.

## Historical review

Original review: `c0d9332`. The user subsequently requested fixes. All five recorded items below are now resolved; historical reproduction details are retained for traceability.

## Confirmed application issue

### BUG-01 — Improvement sort can misrepresent display positions as improvement ranks (P2)

- Location: `immunisation_app/templates/vaccination_improvement.html:6` and `:38`; selected sorting and limiting in `get_vaccination_improvements` in `immunisation_app/queries.py`.
- Reproduce: open `/vaccination-improvement?antigen=MCV1&start_year=2000&end_year=2024&limit=3&sort=country&direction=asc`.
- Actual: Afghanistan, Algeria, Angola appear as ranks 1–3 beneath “Largest vaccination-rate improvements”. With improvement/descending, the three countries are Sierra Leone, South Sudan, Libya instead.
- Impact: readers can mistake alphabetical display positions for the largest improvements.
- Later fix: make the heading and position label accurately reflect selected sorting, or explicitly choose a contract that selects the largest N improvements before sorting their display.
- Note: selected sort before LIMIT is explicitly required by Task 7; this finding concerns presentation, not a proven violation of that SQL plan.
- Status: resolved. The page now says “Positive vaccination-rate improvements”, explains selected sorting before limiting, and labels display order “Position”. All eight sort/direction combinations are covered by a route regression. SQL selection semantics are preserved.

## Test coverage gaps (not confirmed application bugs)

| ID | Gap | Location / later check |
|---|---|---|
| TEST-01 | Invalid-input tests do not directly prove query bypass and malformed-input handling across every analytical route. | `tests/test_routes.py`; verify analytical query functions are not called on invalid requests. Current views contain `if not errors` guards. |
| TEST-02 | Home fact mutation test changes only the first year. | `tests/test_routes.py`, `test_home_fact_cards_follow_snapshot_database_changes`; vary other displayed facts too. Current template reads their database fields. |
| TEST-03 | Hero-topic test searches the whole response. | `tests/test_routes.py`, `test_home_hero_names_vaccination_coverage_and_preventable_infections`; scope the assertion to the hero. Current hero contains the required topics. |

Resolved: TEST-01 now asserts an alert and zero analytical-query calls for invalid numeric and choice fields on all four analytical routes. TEST-02 now mutates both year endpoints and country/antigen/infection counts in temporary SQLite, then checks each fact value. TEST-03 now inspects only the hero section.

## Robustness concern

ROBUST-01: vaccination fallback divides by `NULLIF(v.target_num, 0)`, so negative targets are not explicitly excluded although documentation describes a positive-target rule (`immunisation_app/queries.py`, `get_vaccination_view`). No negative targets were found in the tracked database during review. Add a negative-target fixture and align calculation/documentation in a later data-quality change. This is not a demonstrated failure on the shipped dataset.

Resolved: fallback now uses `CASE WHEN v.target_num > 0`. Regression cases cover negative, zero, missing and positive targets, including usable-country counts and average coverage. Reported coverage retains priority.

## Completed review and verification

- Task 10 identity review: source bootstrap, tracked SQLite, query tests and Mission output agree on Le Chi Bach / s4207910 and Nguyen Tran Ba Trong / s4189686.
- Fresh final run: `python -m unittest discover -s tests -q` — 51 tests passed.
- Read-only SQLite check: `PRAGMA integrity_check` — `ok`; exact two identities verified.
- Prior Task 1 route-inventory and Task 5 stale-matrix notes are resolved by final smoke evidence/current documentation.
- Final review used source, documentation, tests and targeted database inspection. It did not repeat Task 9's browser sweep; that evidence remains in `VERIFICATION.md`.
- Fix verification: 54/54 tests pass; `git diff --check` passes. Both behavior regressions were observed failing before the fixes.
- Broader Flask test-client sweep: 623 requests across all vaccination antigen/year combinations, all infection/year/economy combinations, all benchmark infection/year combinations, and improvement antigen/end-year combinations from 2000, plus overview/Mission/404. All returned expected status codes.
- This historical review covered only its original inventory. The later pending audit items are listed above. No new browser viewport sweep was performed for the data-fix pass.
