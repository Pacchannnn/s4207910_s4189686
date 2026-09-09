# Material You integration

Applies to all six pages and the shared error shell. The single stylesheet was replaced in place, retaining the existing Flask/Jinja component classes and GET forms. No backend, SQL or database changes.

## Design decisions

- Central semantic tokens: violet primary #6750A4, tinted surface #FFFBFE, lavender containers and rose tertiary accents.
- Roboto 400/500/700 loaded through Google Fonts with display=swap and system-font fallbacks when offline.
- Major containers use 48px rounding (24px on phones); cards use 24px; actions and status chips use pills.
- Native fields remain labelled and use 56px filled surfaces with rounded top corners and a 2px bottom border.
- CSS-only decorative blurred shapes, tonal gradients, state overlays and interactive-card elevation; reduced-motion removes interactive transforms.
- Tables preserve all columns in their existing labelled keyboard-focusable scroll regions.
- Pricing/blog/FAB examples from the generic design brief were not added as unrelated features to this academic data application.

## Verification

- Full suite: 54 tests passed after the stylesheet/base-template changes.
- Browser layout checks across all six routes at desktop 1440x900, tablet 768x1024 and phone 375x812. A navigation timeout interrupted the initial batch; the phone analytical pages were rechecked after recovery.
- No page-level horizontal overflow observed. Phone fields are one column, 56px high, and 308px wide in the measured 375px browser viewport with a scrollbar. Data tables scroll within their wrappers.
- Visual inspection: Home desktop, Mission desktop, Infection phone and Benchmark desktop/phone. Full-page capture stitching showed duplicate bands in the exported image; normal viewport captures and page structure did not show duplicate content.
- Invalid vaccination year displays the labelled alert; nonmatching infection search displays the page-specific empty state; neither overflows.
- Browser confirms Roboto loaded, background rgb(255,251,254), button radius 9999px, field radius 12px 12px 0 0.
- Contrast calculation: white on #6750A4 = 6.44:1 (AA normal text, not AAA normal text); secondary text on recessed input = 7.24:1; outline on recessed input = 3.53:1. The supplied palette is preserved; the brief's AAA claim for white/primary is mathematically inaccurate.
- Existing semantic/no-JavaScript tests pass. Reduced-motion CSS is retained with additional transform suppression; no new runtime JavaScript is used.

Preview for this session: http://127.0.0.1:5055. Standard startup remains python app.py.
