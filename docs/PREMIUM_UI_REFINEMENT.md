# Premium refinement

Reading: native Genshin planning workspace for players. Smoke glass, silver and
neutral charcoal. DESIGN_VARIANCE 6 / MOTION_INTENSITY 2 / VISUAL_DENSITY 3.

The requested skill is primarily for websites. Apply audit, typography, material
hierarchy, contrast and spacing to Qt; retain the native app and its contracts.

Before: cyan accent, blue/violet ambient background, Segoe UI, PROJECT G wordmark;
large 14-28px radii and uniform translucent filled boxes create a plastic feel.
Keep four destinations, wordmark, field names/order, import, filters, keyboard
navigation, semantic states and controllers. Retire purple ambience, decorative
rings, uniform glass containers, pill buttons and heavy filled table headers.

New hierarchy: neutral canvas; selective smoke glass with a lit rim for the
recommendation and character identity; unboxed supporting data; compact 64px
navigation; 8px controls and a silver primary action. System sans typography.

Verify all four pages and 11 dialogs at 100/125/150% DPI with isolated fixtures,
800x560, 1260x780 and 1600x1000 layouts; inspect screenshots, focus and regressions.

## Implementation

- `premium_style.py`: readable, isolated refinement rules replace the old opaque
  one-line glass overrides; shared colors remain in `theme.py`.
- `SmokedGlassFrame`: gradient rim and inner reflection on the two primary surfaces.
- Recommendation portrait moved to the right at 144px; character portrait 104px.
- Secondary groups are unboxed; tabs/navigation use an underline; 8px controls,
  18px primary material, 12px navigation. Radius choices follow component roles.
- Native focus, disabled, pressed, hover, errors and status colors remain visible.
- Empty states use useful copy and import actions, without a decorative info icon.

## Results

Full regression: 359 passed, 42 existing SQLAlchemy fixture warnings.
Qt captures and structured checks: `docs/ui-preview/premium/scale-*`.
Screenshots use isolated illustrative data, not the user's account database.
The requested premium look is a design refinement; perceived quality is subject
to the user's review. This does not claim native Apple Liquid Glass or a new
packaged executable. No new animation or third-party UI dependency was added.
