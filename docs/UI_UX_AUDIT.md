> Historical audit of the earlier graphite/amber UI. The current liquid-glass redesign and verification are documented in [LIQUID_GLASS_UI.md](LIQUID_GLASS_UI.md).

# ProjectG UI/UX upgrade: implementation and verification

Status: implemented in native PySide6 after user approval of Superdesign v3 on 2026-09-27. No application/planner policy, persistence or account contracts changed by this UI work.

## Design decisions
Design read: Vietnamese desktop planning workspace; dark slate with existing amber identity, restrained styling, information first. DESIGN_VARIANCE 3 / MOTION_INTENSITY 2 / VISUAL_DENSITY 5. Custom Qt design system, not an official Fluent implementation. The design-taste skill's marketing guidance was adapted only where relevant to this data product.

The source audit found duplicate inline styling, inconsistent emoji control glyphs, small uppercase labels, a flat tools menu, incomplete button states, and technical content competing with the main recommendation.

## Implemented
- A shared token palette and QSS for all four destinations and inherited dialogs; Segoe UI body 14px, title 26px, consistent surface/control radii.
- Preserved existing star/wordmark and navigation labels. Removed decorative operational glyphs. Standard Qt arrow/check glyphs bundled offline with existing assets; build_desktop.ps1 already includes that directory.
- Primary account import, secondary recalculation, visible hover/pressed/keyboard-focus/disabled states and descriptive accessible names.
- Tools grouped into planning, data and support; menu availability follows underlying controls.
- Today prioritizes the recommendation and materials. Unknown amounts stay unknown; zero amounts remain zero. Materials are read-only and do not imply account inventory.
- Empty account has an actionable import CTA. Availability colors reset between tasks and empty states.
- Supplementary Today details and artifact substats are progressively disclosed; grids reflow with width.
- Persistent loading/failure feedback with retry. Failure retains the previous result; stale generations cannot replace current feedback.
- Characters with an empty snapshot hide stale equipment and disable character actions.
- Snapshot and Settings forms scroll at low window heights. Submit/cancel remain outside the scroll region. Field names and order preserved.
- Roadmap compact headers and details retain hidden values, filtering and keyboard access.

## Evidence
| Requirement | Evidence |
| --- | --- |
| Design on Superdesign and approval | Baseline v1, refinement v2, corrections v3; user replied ok to implementation |
| Full regression suite | 340 passed, 40 existing SQLAlchemy fixture teardown warnings, 11.34s, exit 0 |
| Final UI and architecture checks | 102 passed, 6.68s, exit 0 after the final header adjustment |
| Compilation | python -m compileall -q src tests scripts, exit 0 |
| Four screens and supported sizes | verify_desktop_ui.py checks 800x560, 1260x780, 1600x1000; global actions within bounds, no horizontal scrolling for Today/character cards |
| DPI | Same layout checks at QT_SCALE_FACTOR=1 / 1.25 / 1.5, 36 screen captures plus dialog/state captures |
| Long forms | Snapshot and Settings rendered at 800x560 for each DPI; submit/cancel within dialog bounds |
| Interaction regressions | Keyboard navigation/search, disabled refresh, import paths, filters, hidden details, export/cancel, empty account CTA, failure/retry, stale feedback, semantic reset, read-only materials and empty character actions |
| Visual inspection | Actual Qt fixture screenshots reviewed for all four default screens, selected minimum-size screens, empty/error states and forms including high DPI |
| Text contrast | text/surface 16.07:1; secondary/elevated 7.51:1; button text/accent 10.25:1; semantic colors 8.44:1 or higher |

Baseline earlier in this session had 330 passes and one NORMAL_BOSS test-fixture failure. The current authoritative suite passes; this UI work did not edit that domain test. Keep the historical result distinct from the final one.

## Reproduce locally
```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-temp-ui-check
.venv\Scripts\python.exe scripts\verify_desktop_ui.py --output docs\ui-preview\v3\scale-100
$env:QT_SCALE_FACTOR = '1.25'
.venv\Scripts\python.exe scripts\verify_desktop_ui.py --output docs\ui-preview\v3\scale-125
$env:QT_SCALE_FACTOR = '1.5'
.venv\Scripts\python.exe scripts\verify_desktop_ui.py --output docs\ui-preview\v3\scale-150
Remove-Item Env:QT_SCALE_FACTOR
```

Captures under docs/ui-preview are ignored and explicitly use illustrative data; verification never opens the user's account database. The structured verification.json files record scale and size checks. UI control PNGs are durable offline assets.

## Scope and limits
This is verified source-level UI/UX work, not a claim of company-wide release certification. Packaged executable rebuild, manual screen-reader testing, a representative live-account usability study and platform-wide release review were not performed. Existing SQLAlchemy warnings concern fixture cleanup. Full accessibility compliance cannot be inferred from token contrast or keyboard tests alone. Hosted Superdesign preview interaction limitations are not native implementation limitations.

Canvas: https://superdesign.dev/teams/581c549a-ee03-488e-b298-ad67aff46364/projects/3bee9619-827a-42b5-a49a-81cae4d18b79
Approved visual draft: https://p.superdesign.dev/draft/7fd33fc9-ba87-4a2b-80f4-fd480ddc44fb
