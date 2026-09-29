> Historical design direction. See [LIQUID_GLASS_UI.md](LIQUID_GLASS_UI.md) for the current interface.

# Native desktop UI redesign

## Audit and direction

The existing application has four destinations: Tiếp theo, Lộ trình, Nhân vật,
and Tier List. Account Snapshot and GOOD are the input paths. Keyboard navigation,
search, editable tiers, character build intentions, and controller busy guards
remain part of the native interface.

The previous dark blue interface used gold accents, Segoe UI, and bordered cards
inside bordered cards. A repeated global toolbar took space from the main task.
The character action row could clip its buttons at small window widths.

The redesign uses graphite surfaces and the existing gold accent. It applies the
audit and visual hierarchy principles of design-taste-frontend to Qt, without
introducing a web frontend. Design variance: 6; motion intensity: 2; visual density: 5.
Transitions stay immediate for predictable keyboard operation.

## Changes

- Sidebar navigation includes descriptions on wide windows and shortcut hints.
  Descriptions collapse when the window is narrower than 1100 logical pixels.
- Account import and the tools menu live in the sidebar alongside the roster count.
- Export and recalculation sit beside the page title, leaving more vertical space.
- The recommended action has the strongest visual weight. Farm facts use spacing
  and separators rather than another set of bordered cards.
- Quick navigation connects the recommendation to the roadmap and characters.
- Material table height follows its rows, capped at 320 logical pixels for long lists.
- Character actions reflow into multiple rows when their panel becomes narrow.
- Shared color tokens cover fallback portraits, focus states, and semantic badges.

## Verification

`scripts/verify_desktop_ui.py` renders isolated illustrative data and never opens
the account database. It checks all four pages at 800x560, 1260x780, and 1600x1000,
plus the settings and snapshot dialogs, empty account, and retry state.

Preview directories:

- `docs/ui-preview/before-redesign`: baseline.
- `docs/ui-preview/redesign`: 100% scaling.
- `docs/ui-preview/redesign-dpi125`: 125% scaling.
- `docs/ui-preview/redesign-dpi150`: 150% scaling.

The focused suite covers presentation, architecture, and desktop application behavior.
The native render checks use Qt's offscreen platform; interactive testing on a
physical display remains separate from these checks.
