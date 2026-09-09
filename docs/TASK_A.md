# Task A scope and verification

Contributor: Le Chi Bach (s4207910).

| Requirement | Route | Implementation |
| --- | --- | --- |
| 1A: landing and four database facts | / | home.html, snapshot and latest-case overview queries |
| 2A: vaccination coverage | /vaccinations | vaccinations.html, country/region filters, coverage and regional SQL summaries |
| 3A: vaccination improvement | /vaccination-improvement | vaccination_improvement.html, endpoint population rates, positive improvement, sorting and limit |

Shared files include the Flask application, database connections, validation,
base template, error page, stylesheet, hero image and SQLite dataset.
The supplied infection data remains necessary for the Home dataset overview;
its presence is not an implementation of Task B's analytical pages.
Team/persona bootstrap data is retained as shared project metadata.

Task B routes, templates and analytical queries are excluded from this build.
The previous Task B files already present in this branch are removed in this
change; those removals will appear in the commit diff. Their earlier versions
remain recoverable through Git history.

Run: python -B -m unittest discover -s tests -q

Tests cover Task A database calculations, filters, limits, missing data, input
validation, page rendering, four dynamic facts and shared accessibility helpers.
This separation has automated route verification, not a new visual browser audit.
The full six-page build is retained on local branch codex/refactor-v2.
