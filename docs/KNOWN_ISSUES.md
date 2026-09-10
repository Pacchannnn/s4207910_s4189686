# Known issues and resolution history

## Status — 10 September 2026

| Item | Status | Evidence / remaining scope |
|---|---|---|
| Sub-Task A removal | Complete | The landing page, vaccination coverage explorer and vaccination improvement ranking were removed, together with their queries, templates, styles, tests and documentation rows. The Mission page moved to `/` and `/mission` now redirects there. See `REQUIREMENTS_MATRIX.md`. |
| Benchmark user-selected sorting | Resolved | Sorting uses a whitelist, preserves which countries exceed the benchmark and keeps the global row first. No similarity score or clustering was added. |
| Numeric filtering on Infections | Resolved | Cases, population and rate filters use validated values and whitelisted comparisons. They narrow the detail table only; economy summaries and denominators do not change. |
| Missing-data explanations | Resolved | Missing-record, unmatched-economy and represented-population explanations were added to the page methodology notes without changing source data or calculations. |
| Adapted UI components on Infections | Integrated | Sortable header links preserve filters and expose sort state; country and economy labels are row headers; the optional methodology detail collapses while the warnings stay visible. Four regressions in `tests/test_member_components.py`. See the attribution note in `README.md`. |

Current suite: **47/47 tests pass**. Passing tests are not proof of the absence of all possible defects; see `VERIFICATION.md` for what was and was not checked.

## Remaining source-data notes

These are handled and explained in the interface rather than silently rewritten:

- Two countries (Ethiopia and Venezuela) have a blank economy mapping. They are excluded from the economy view instead of being reassigned to a group, and the page says so. They still appear in the global benchmark, which does not require an economy match.
- Rates depend on a matching same-year population row with a positive population. Records without one are excluded from the denominator, so a rate describes represented records, not the whole world.
- A missing record is not treated as zero cases. "No matching result" does not mean "no cases".

## Test coverage gaps (not confirmed application bugs)

| ID | Gap | Later check |
|---|---|---|
| TEST-04 | The responsive assertion in `tests/test_routes.py` checks one phone rule (`.sort-pair`) rather than every collapsing grid. | Extend `test_phone_styles_stack_every_filter_control_in_one_column` to assert each single-column rule in the 640px block. |
| TEST-05 | Accessibility evidence is structural (labels, captions, header scopes, named regions). No assistive-technology run is automated. | Add a screen-reader or axe-style pass if the toolchain allows it. |

## Removed history

Issue records that described only the Sub-Task A pages — the improvement-ranking heading defect, the coverage fallback and endpoint data fixes, and the landing-page fact-card test gaps — were removed together with the pages they described. They are recoverable from the Git history of this repository.
