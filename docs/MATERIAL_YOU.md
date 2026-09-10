# Material You integration

Applies to the three pages and the shared error shell. The single stylesheet was replaced in place, retaining the existing Flask/Jinja component classes and GET forms. No backend, SQL or database changes belong to this pass.

## Design decisions

- Central semantic tokens: violet primary #6750A4, tinted surface #FFFBFE, lavender containers and rose tertiary accents.
- Roboto 400/500/700 loaded through Google Fonts with display=swap and system-font fallbacks when offline.
- Major containers use 48px rounding (24px on phones); cards use 24px; actions use pills.
- Native fields remain labelled and use 56px filled surfaces with rounded top corners and a 2px bottom border.
- CSS-only decorative blurred shapes, tonal gradients and state overlays; reduced-motion removes interactive transforms.
- Tables preserve all columns in their existing labelled keyboard-focusable scroll regions.
- Pricing/blog/FAB examples from the generic design brief were not added as unrelated features to this academic data application.

## Verification

- Full suite passes after the stylesheet and base-template changes; the current count is recorded in `VERIFICATION.md`.
- Rules that only styled the removed Sub-Task A pages (hero, fact cards, exploration paths, the landing bar chart, coverage status chips and improvement rank badges) were deleted on 10 September 2026. Every remaining class is still referenced by a template.
- No page-level horizontal overflow observed. Phone fields collapse to one column at the 640px breakpoint; data tables scroll within their wrappers.
- A malformed infection year displays the labelled alert and a nonmatching country search displays the page-specific empty state; neither overflows.
- Browser confirms Roboto loaded, background rgb(255,251,254), button radius 9999px, field radius 12px 12px 0 0.
- Contrast calculation: white on #6750A4 = 6.44:1 (AA normal text, not AAA normal text); secondary text on recessed input = 7.24:1; outline on recessed input = 3.53:1. The supplied palette is preserved; the brief's AAA claim for white/primary is mathematically inaccurate.
- Existing semantic/no-JavaScript tests pass. Reduced-motion CSS is retained with additional transform suppression; no runtime JavaScript is used.

Standard startup remains `python app.py`.
