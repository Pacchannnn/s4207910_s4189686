# Verification and numerical decisions

## Completed checks

- 45 unittest tests passed using the project's isolated environment.
- 125 antigen/year combinations checked against raw source-record arithmetic for 2A.
- 75 infection/year combinations checked for 3B and all four economic summaries in 2B.
- 25 antigen/start/end combinations checked for 3A, including full-span and adjacent-year periods.
- 18 full-page screenshots: all six pages at 1440, 390 and 320 pixels.
- Real form submission, selection persistence, sorting, empty results, reset and invalid-year
  feedback passed in Chromium (Microsoft Edge), with page JavaScript disabled.
- No failed network requests in the browser checks.
- Source-table contents match the original for all nine tables.
- All six routes, sort choices/directions, parameter binding, repeated parameters, excessive
  query length, invalid values, HTML escaping, custom errors and missing database tested.
- Read-only connection lifecycle and request-time database immutability tested.
- Synthetic tests cover blank versus zero, zero population, calculated coverage, coverage above
  100, multiple antigen rows and top-N selection before display sorting.

## Known numeric anchors

| View | Selection | Verified result |
| --- | --- | --- |
| 1A | Full source | 217 countries; 5 antigens; 24,211 vaccination records; 2000-2024 |
| 1A | Supporting totals | 10,622,256,489.44529 source doses; 19,232,497 cases; 15,525 infection records; 3 diseases |
| 2A | RCV1 / 2000 / minimum 90 | Singapore 93.5%; Malta 92.7%; 3 countries have usable coverage across all regions |
| 2B | Low Income / Measles / 2022 | 25 countries; 83,977 cases; 591,481,496 population; rate 14.197739163086178 per 100,000 |
| 3A | DTPCV1 / 2000-2024 | 123 comparable; 34 improving; 89 declining; 0 unchanged; 94 excluded |
| 3A | Chad | 1.4216714972451547% to 4.788280754789259%; increase 3.3666092575441042 pp |
| 3B | Measles / 2020 | 207 valid countries; global 2.0473104062008067 per 100,000; 28 above |
| 3B | Congo, Dem. Rep. / Measles / 2020 | 85.72768175284263 per 100,000 |

## Definitions and scope

1. Homepage totals describe raw supplied rows. They can include countries without matching
   reference metadata. Country-level exploration requires matched metadata. The 217 headline
   is the reference-table count, not the count of countries reporting every indicator.
2. 2A uses nonnegative numeric reported coverage first. If unavailable, valid paired numeric
   doses and positive targets support a labelled calculated fallback. Above-100 values remain
   visible and enter the mean, with anomaly counts. No silent cap.
3. The regional summary covers every country in the selected region(s), independent of the
   detail country and minimum filters. Available countries have usable coverage. The mean is
   an equally weighted country mean, not a weighted population vaccination rate.
4. The real source has no duplicate antigen/country/year combinations. For future multiple
   source rows, numeric doses are summed, valid reported coverage is averaged, and fallback
   uses paired doses/targets. Multiple-source-row counts and anomaly flags are exposed.
5. 3A endpoint rates use the population for the same country and year. Empty doses do not become
   zero. A numeric zero is kept. Only positive changes enter top-N. The count of all comparable
   countries includes improving, equal and declining values. Difference units are percentage points.
6. 2B and 3B rates use summed cases over summed matched population. Missing population does not
   contribute cases to the rate numerator. Raw economic case totals are displayed separately.
   Countries without economic metadata can still enter the global benchmark.
7. Rate comparisons and sorting occur before rounding. Tables display six decimals for 3A/3B;
   infection tables show four decimals; coverage shows two. Bar labels are rounded summaries.
   SQLite REAL uses floating-point arithmetic; numerical tests allow 1e-10 relative or 1e-9
   absolute tolerance. Passing tests establishes consistency with the supplied data and stated
   formulas, not real-world correctness of anomalous source reports.

## Source limitations

The source includes blank numeric cells, coverage above 100%, unmatched vaccination country
codes and missing economic classifications. The original values remain intact. The website
explains these issues and does not substitute invented observations or treat coverage as
measured community immunity. Personas are presented as example user profiles; no interviews are claimed.

## Provenance and scope of this build

Source references: Framework Final and astra (read-only inputs), plus the original PDF and database.
Output: Final Optimized. The Demo project and step-by-step guide were not part of this build.

Tests do not certify every possible external environment, all accessibility criteria, unseen
future datasets or separate Canvas submission/presentation obligations.
