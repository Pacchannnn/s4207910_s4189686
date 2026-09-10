# Verification

## Verification after Sub-Task A removal — 10 September 2026

The Sub-Task A pages were removed from this submission. Verification records that only evidenced those pages (the six-route browser sweep, the vaccination coverage and improvement numerical audits, and the earlier suite counts of 51/54/57/69/73 tests) were removed with them. The results below were produced after the removal and describe the current three-page application.

- Full suite: `python -B -m unittest discover -s tests -q` — **47/47 pass**. Twenty-six tests that covered only the removed pages were deleted; the mixed cross-page tests were narrowed to the remaining routes rather than dropped.
- Route sweep with the Flask test client: 379 requests returned HTTP 200 — every economy/infection/year combination on `/infections` (3 infection types x 25 years x 4 economic statuses), every infection/year combination on `/infection-benchmark`, the three default pages and the stylesheet. `/mission` returns 301 to `/`; `/vaccinations`, `/vaccination-improvement` and any unknown address return the branded 404.
- Rendered pages contain zero `<script>` elements; all filter forms compute `method="get"`, so results remain shareable through the URL.
- Spot check preserved from before the removal: `/infection-benchmark?infection=MEA&year=2020` still reports **28 countries above the global rate** with the global row first, confirming that no benchmark calculation changed.
- Browser check at desktop width against `python app.py`: the Mission, Infections and Benchmark pages render without page-level horizontal overflow after the unused Sub-Task A rules were deleted from `styles.css`. Every CSS class that remains in the stylesheet is still referenced by a template, and every class referenced by a template that had a rule still has one.
- `PRAGMA integrity_check` on the tracked database: `ok`.

### Database change in this pass

The `ProjectPersona` rows were updated so each persona's "supported by" text names features that still exist. No source data table was touched.

| | SHA-256 |
|---|---|
| Before the persona update | `B1BD2B9BD95E246906362AB71B272AADD861C2F66B0CED62EADAE9D42326A6BF` |
| Current | `5EF31AEC54ADD4C266197D17362BBB844636CBC849459974ECA8448A3E364E67` |

`immunisation_app/db.py` seeds the same persona text, so a database that has not yet been initialised receives the current wording.

## Database quality snapshot

The tracked SQLite database was queried directly during this verification. Only the tables the remaining pages read are listed.

| Check | Count/result |
|---|---:|
| Infection rows | 15,525 |
| Infection types | 3 (Measles, Rubella, Pertussis) |
| Economic statuses | 4 (High Income, Upper Middle Income, Lower Middle Income, Low Income) |
| Countries and areas | 217 |
| Countries with a blank economy mapping | 2 |
| Duplicate infection `(country, infection, year)` groups | 0 |
| Duplicate population `(country, year)` groups | 0 |
| Null or non-positive population rows | 0 |
| Infection rows with no matching same-year population row | 0 |
| Available year range | 2000-2024 |
| Project team identities | Le Chi Bach (`s4207910`); Nguyen Tran Ba Trong (`s4189686`) |

The two countries with a blank economy mapping (Ethiopia and Venezuela) are excluded from the economy view rather than reassigned to a group, and the methodology note on that page states this. They still appear in the global benchmark, which does not require an economy match.

## Scope of this verification

This is automated Flask and SQLite verification plus a desktop browser check. It is not a screen-reader audit, a multi-viewport sweep or a medical-validity review. Passing tests are not proof of the absence of all possible defects.

## Repeatable commands

```powershell
python -B -m unittest discover -s tests -q
python app.py
```
