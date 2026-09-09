# Final review: issues deferred for later

Reviewed application commit: `c0d9332`. User requested recording issues without fixing them in this pass.

## Confirmed application issue

### BUG-01 — Improvement sort can misrepresent display positions as improvement ranks (P2)

- Location: `immunisation_app/templates/vaccination_improvement.html:6` and `:38`; selected sorting and limiting in `get_vaccination_improvements` in `immunisation_app/queries.py`.
- Reproduce: open `/vaccination-improvement?antigen=MCV1&start_year=2000&end_year=2024&limit=3&sort=country&direction=asc`.
- Actual: Afghanistan, Algeria, Angola appear as ranks 1–3 beneath “Largest vaccination-rate improvements”. With improvement/descending, the three countries are Sierra Leone, South Sudan, Libya instead.
- Impact: readers can mistake alphabetical display positions for the largest improvements.
- Later fix: make the heading and position label accurately reflect selected sorting, or explicitly choose a contract that selects the largest N improvements before sorting their display.
- Note: selected sort before LIMIT is explicitly required by Task 7; this finding concerns presentation, not a proven violation of that SQL plan.
- Status: open, intentionally deferred.

## Test coverage gaps (not confirmed application bugs)

| ID | Gap | Location / later check |
|---|---|---|
| TEST-01 | Invalid-input tests do not directly prove query bypass and malformed-input handling across every analytical route. | `tests/test_routes.py`; verify analytical query functions are not called on invalid requests. Current views contain `if not errors` guards. |
| TEST-02 | Home fact mutation test changes only the first year. | `tests/test_routes.py`, `test_home_fact_cards_follow_snapshot_database_changes`; vary other displayed facts too. Current template reads their database fields. |
| TEST-03 | Hero-topic test searches the whole response. | `tests/test_routes.py`, `test_home_hero_names_vaccination_coverage_and_preventable_infections`; scope the assertion to the hero. Current hero contains the required topics. |

## Robustness concern

ROBUST-01: vaccination fallback divides by `NULLIF(v.target_num, 0)`, so negative targets are not explicitly excluded although documentation describes a positive-target rule (`immunisation_app/queries.py`, `get_vaccination_view`). No negative targets were found in the tracked database during review. Add a negative-target fixture and align calculation/documentation in a later data-quality change. This is not a demonstrated failure on the shipped dataset.

## Completed review and verification

- Task 10 identity review: source bootstrap, tracked SQLite, query tests and Mission output agree on Le Chi Bach / s4207910 and Nguyen Tran Ba Trong / s4189686.
- Fresh final run: `python -m unittest discover -s tests -q` — 51 tests passed.
- Read-only SQLite check: `PRAGMA integrity_check` — `ok`; exact two identities verified.
- Prior Task 1 route-inventory and Task 5 stale-matrix notes are resolved by final smoke evidence/current documentation.
- Final review used source, documentation, tests and targeted database inspection. It did not repeat Task 9's browser sweep; that evidence remains in `VERIFICATION.md`.
- All implementation tasks are delivered. The earlier matrix's `Met` statuses describe requirement coverage, not a claim that the application is bug-free. BUG-01 and the gaps above remain open by user request.
