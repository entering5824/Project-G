# Desktop UI/UX update

Scope: the native PySide6 desktop shell and shared styling across all four destinations.

Changed:
- Shared page title and contextual description, separate from import/tools/refresh actions.
- One primary import action; recalculation is a secondary action with Ctrl+R.
- Compact sidebar with descriptive tooltips and Ctrl+1 through Ctrl+4 navigation.
- Ctrl+F, select-all search, clear buttons, accessible search/navigation names.
- Visible focus styles and more readable secondary labels; transparent label backgrounds.
- Separate character configuration and Today pin action rows.
- Separate tier search/settings and file action rows, with wrapping help text.
- Today hero badges below its main content, wrapping explanations, and readable table headers.
- A shared theme module extracted from MainWindow.

Files created:
- src/projectg/presentation/desktop/pyside6/theme.py
- tests/presentation/test_desktop_navigation.py
- docs/desktop-ui-update.md

Files modified:
- src/projectg/presentation/desktop/pyside6/main_window.py
- README.md
- .gitignore (local verification dependencies, captures and test temp directories)

Validation:
- Full pytest with locally installed PySide6 and Qt offscreen: 298 passed, 40 warnings,
  exit 0 (9.32 seconds). Includes 68 architecture tests and 4 native UI tests.
- python -m compileall -q src tests scripts: exit 0.
- Rendered and inspected all four pages at 1260x780 and 800x560.
- UI tests cover actual keyboard navigation, focused search selection, disabled refresh,
  toolbar bounds, and Today without horizontal scrolling at the minimum window size.

PySide6 is installed only in ignored .ui-test-deps for verification. Preview captures
in ignored docs/ui-preview are generated with stub controllers and the no-snapshot
state; they are not screenshots of a live account. Populated planner behavior is
covered by the existing full suite. Existing SQLAlchemy warnings concern the
accounts/snapshots foreign-key cycle during fixture teardown.

No planner, persistence, application policy, or data pack code changed in this UI update.


## Follow-up: compact desktop UI

User preference: reduce scrolling and prioritize information and actions.

- Character badges, progression cards and artifact slots reflow into columns that fit
  the available detail-pane width. Long artifact names no longer force horizontal scrolling.
- Character actions now occupy one row: configuration, Today pin, and a secondary menu
  containing create/activate preset and unpin actions. Busy-state disabling is preserved
  on the menu actions; obsolete button objects were removed rather than proxied.
- Artifact substats are initially collapsed and can be shown with an explicit toggle.
  Main stats, set names and RV remain visible.
- Today supplementary account/alternative information is collapsed by default. The
  action and material requirements stay first; an empty material table is replaced by
  a short placeholder that automatically follows model row insertion/removal.
- Reduced header/content margins and added bottom stretch so cards do not expand
  merely to occupy unused space.
- Roadmap, character and tier search show matching-row counts and useful no-result text.

Additional file: src/projectg/presentation/desktop/pyside6/responsive_grid.py.
Updated main_window.py, theme.py and tests/presentation/test_desktop_navigation.py.
Final verification: 303 full-suite tests passed (including 68 architecture and 9 native
UI tests); compileall passed. Existing SQLAlchemy fixture warnings remain.
Final previews are in ignored docs/ui-preview/compact-page-*.png and contain explicitly
labelled illustrative character data, not a live account.


## Follow-up: compact tables and account import

- Roadmap defaults to rank, source/character, current/target count, next milestone/resin
  and status. The Details checkbox reveals progression/final target and score columns.
- Tier List defaults to character, score, tier and planner control. Details reveals
  ownership, notes and build set. Hidden values remain in save/export payloads.
- Fixed widths on compact numeric/status columns and a stretching name column avoid
  horizontal scrolling at the 800px minimum window. Long header labels have tooltips.
- Account import now uses a split button: the main area opens Account Snapshot entry;
  the arrow menu offers Account Snapshot and GOOD. The previous separate GOOD button
  was replaced with an actual action, without a proxy/shim.
- Tier JSON import/export are grouped in a file menu. Tier rows are tall enough for
  embedded combobox controls.
- Import controls show the disabled state during overview refresh and GOOD processing.
- Fixed stale roadmap result counts when a refreshed plan becomes empty.
- Fixed native alternating rows falling back to white in the dark theme.

Files modified in this follow-up: main_window.py, theme.py,
tests/presentation/test_desktop_navigation.py, README.md and this report.

Verification: 308 full-suite tests passed, including 68 architecture tests and
14 native UI tests; compileall passed. 40 existing SQLAlchemy fixture warnings remain.
Tests cover hidden-column payload preservation, compact table widths, both import
paths, empty refresh counts and dark alternating-row palette.
Rendered populated illustrative tables at 1260x780 and 800x560. Updated captures:
docs/ui-preview/tables-page-{1,3}-{1260,800}.png (ignored verification artifacts).
No application/domain/planner/persistence behavior changed.


## Follow-up: accessible roadmap details and populated Today

- Added a read-only roadmap details dialog, available from the selected-row footer
  action or Enter while the roadmap table has focus. It includes hidden column values
  and the existing beneficiary explanation, with selectable plain text and a copy action.
- The detail action is disabled for no selection or a selected row hidden by filters.
  Double-click navigation to characters is preserved. Closed dialogs are released.
- Today material requirements use two columns; the repeated theoretical-estimate note
  now appears once above the table. Amounts, ordering and unknown/zero handling are unchanged.
- Today source/resin/availability badges reflow with available width. Duplicate action
  text and unused character placeholders are removed from source-level tasks.

Created: src/projectg/presentation/desktop/pyside6/row_details_dialog.py.
Modified: main_window.py, tests/presentation/test_desktop_navigation.py, README.md,
and this report. No files deleted or compatibility shims introduced.

Validation: 311 full-suite tests passed (68 architecture and 17 native UI tests);
compileall passed. Existing SQLAlchemy fixture warnings remain. New tests verify
keyboard detail access, hidden-column content, filter safety, populated Today at 800px,
unknown/zero material amounts and unchanged incoming data.

Updated illustrative previews: docs/ui-preview/details-page-{0,1}-{1260,800}.png
and docs/ui-preview/roadmap-details-dialog.png. These use test data, not a live account.

## Superdesign v3 native UI upgrade

The approved design is implemented across Today, Roadmap, Characters and Tier List.
Shared tokens replace per-widget styling. Native controls have explicit readable
states and offline Qt arrow/check glyphs. Tools are grouped by planning/data/support
and track underlying busy-state guards. Persistent overview failure feedback has
retry and keeps the previous result. Empty accounts provide a direct import action;
empty character snapshots cannot show old equipment. Snapshot and Settings forms
scroll while their confirm/cancel actions stay visible.

Validation: full suite 340 passed (40 existing fixture cleanup warnings); final
presentation/architecture checks 102 passed; compileall passed. Four screens were
rendered and checked at three sizes and DPI 100%, 125%, 150%; long forms also checked.
See UI_UX_AUDIT.md for evidence, reproducible commands and limits. No packaged
executable rebuild or complete accessibility certification is claimed.
