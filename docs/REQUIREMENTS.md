# Requirement-to-implementation matrix

Primary source: Studio Project Sub-Task Req ver1.pdf, all six pages read.
PDF examples are illustrative. Numerical expectations below use the supplied database.

| Requirement | Implementation / evidence | Status |
| --- | --- | --- |
| Overall: informative, respectful, unbiased | Neutral copy; no causal medical claims; units and limitations in each view | Implemented |
| Diverse users; overview and detailed exploration | Plain-language overview, four personas, six linked pages | Implemented |
| Six separate subtasks; A/B distinction | Separate routes/templates for 1A, 1B, 2A, 2B, 3A, 3B | Implemented |
| 1A capture interest and identify topic | Vaccination and Disease Data title; disease totals and exploration links | Implemented |
| 1A four facts | Dynamic countries, antigens, vaccination record count, timeframe | Implemented |
| Additional requested supporting facts | Raw doses, cases, infection record count and infection types; correct labels | Implemented |
| 1B mission and how to use | Mission text, four usage steps and data glossary | Implemented |
| 1B personas from database | Persona table; Queries.mission; update regression | Implemented |
| 1B member names/IDs from database | TeamMember table; Queries.mission; update regression | Implemented |
| Level 2 select/filter/sort/join/aggregate in SQL | queries.py and derived views in extensions.sql | Implemented |
| Identify/handle missing and inconsistent data | Explicit numeric validation, fallback provenance, above-100 flags, missing denominators and orphan notes | Implemented |
| 2A country and/or region; year | Bound GET choices; filters combined on detail results | Implemented |
| 2A vaccination rates and regional summaries | Country table plus all selected-region countries, available/missing counts, mean and threshold counts | Implemented |
| 2A herd immunity context | Coverage proxy and threshold summary; explicit 'Not measured' immunity column | Data limitation disclosed |
| 2B choose one economic status, disease and year | Required selectors populated from actual reference tables | Implemented |
| 2B filter/organise any result column | Categorical selectors, literal country search, numeric bounds, all-column SQL sort | Implemented |
| 2B summarize across tables | Disease/year totals and matched population-weighted rates across all economies | Implemented |
| Level 3 query result feeds subdataset | Eligible CTE + top-N subquery for 3A; valid/global CTEs and above-global subquery for 3B | Implemented |
| Level 3 SQL-selected sorting, no Python data processing | Whitelisted SQL ORDER BY; main arithmetic and ranking in SQL | Implemented |
| 3A years, antigen and number countries | Start/end/antigen/top-N controls, strict start < end | Implemented |
| 3A population-dependent vaccination rate | SUM(valid doses) / same-year positive population * 100 | Implemented |
| 3A rank before display sort | Top positive increases selected in subquery, then display order applied | Implemented |
| 3B global reported infection rate | Matched cases / matched population * 100000; includes real zeros | Implemented |
| 3B global row first, countries exceeding it | Global first tbody row; comparison uses unrounded rates | Implemented |
| Input validation, SQL safety, custom errors | Parameter binding; column/direction whitelist; 400/404/405/413/500/503 handlers | Tested |
| Local use, no JavaScript | Flask + HTML/CSS; CSP script-src none; real browser with JavaScript disabled | Tested |
| Responsive tables, forms, charts | 1440px, 390px and 320px checks plus real filter/reset/sort workflows | Tested |
| Original tables preserved | All nine content hashes match original; integrity_check ok | Tested |
| Student A/B ownership | Pages remain distinct; this technical build does not establish student authorship | Outside technical verification |

The PDF requests regional herd-immunity levels but the database does not measure them
or provide disease-specific immunity thresholds. The site shows coverage and comparison-target
counts with explicit limitations. It does not invent a measured immunity percentage.
The supplied PDF has older semester labels; this build follows the provided file's functional
requirements without assuming dates or submission instructions not present in it.
