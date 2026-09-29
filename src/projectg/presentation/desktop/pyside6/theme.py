"""Native Qt design tokens, independent of application and planner behavior.

Design spec: design.ms (Genshin / Project G visual design principles)
  §4  Color System — global dark palette
  §3  Shape Language — radius tokens
  §7  Spacing System — 4 px base grid
  §6  Typography — hierarchy
  §19 Buttons — heights, weights
  §32 Focus State — 2 px accent ring
"""
from string import Template
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# §4.1  Global dark palette
# ---------------------------------------------------------------------------
COLORS = dict(
    # canvas / surfaces
    background='#0C1018',        # bg-canvas
    elevated='#121824',          # bg-elevated
    surface='rgba(24,32,46,0.72)',      # bg-panel (approximated as opaque for Qt)
    surface_strong='rgba(28,38,54,0.88)',  # bg-panel-strong

    # sidebar (slightly elevated, warm teal-navy)
    sidebar='#16202e',

    # text
    text='#F3F5F7',              # text-primary
    secondary='#B9C0CB',         # text-secondary
    muted='#7F8998',             # text-muted

    # strokes
    border='rgba(255,255,255,0.08)',    # stroke-soft
    border_medium='rgba(255,255,255,0.14)',  # stroke-medium

    # gold accents
    accent='#D9C28B',            # gold-soft
    accent_hover='#F0D89C',      # gold-highlight
    accent_pressed='#C8A865',

    # semantic
    success='#65D5C5',           # Anemo (positive / available)
    warning='#E4B45D',           # Geo (warning / limited)
    danger='#F06A58',            # Pyro (error / critical)

    # hover surface
    hover='#1E2C3E',
)

# Standard Qt glyphs are bundled with the existing offline assets directory.
_asset_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[5]))
_glyphs = _asset_root / 'assets' / 'genshin-impact' / 'ui-controls'
_style_tokens = {**COLORS, **{name: (_glyphs / f'{name}.png').as_posix()
                            for name in ('up', 'down', 'check')}}

# ---------------------------------------------------------------------------
# Base stylesheet — design.ms §3–§7, §19, §32
# ---------------------------------------------------------------------------
DESKTOP_STYLE = Template('''
/* ── Global reset ─────────────────────────────────────────────────────── */
QWidget {
  background: $background;
  color: $text;
  font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
  font-size: 14px;
  selection-background-color: $accent;
  selection-color: $background;
}
QMainWindow, QDialog { background: $background; }
QLabel { background: transparent; }

/* ── Typography — §6 ──────────────────────────────────────────────────── */
/* Display  30–36 px / 600 */
QLabel#pageTitle, QLabel#headline {
  font-size: 30px;
  font-weight: 600;
  color: $text;
}
/* Page kicker  12 px / 700  gold */
QLabel#pageKicker {
  color: $accent;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 0;
}
/* Section title  18–20 px / 600 */
QLabel#section {
  font-size: 18px;
  font-weight: 600;
  color: $text;
}
/* Card title  15–17 px / 600 */
QLabel#stepTitle {
  font-size: 15px;
  font-weight: 600;
  color: $text;
}
/* Body  14 px / 400 */
QLabel#todayAction { color: $secondary; font-size: 14px; }
/* Label  12–13 px / 500 */
QLabel#pageSubtitle,
QLabel#searchFeedback,
QLabel#secondaryText { color: $secondary; font-size: 13px; }
/* Eyebrow  12 px / 600  muted gold */
QLabel#eyebrow { color: $accent; font-size: 12px; font-weight: 600; }
/* Metadata  11–12 px / 400 */
QLabel#metricLabel,
QLabel#sidebarFooter,
QLabel#brandSubtitle { color: $muted; font-size: 12px; }

/* ── Brand / sidebar labels ──────────────────────────────────────────── */
QLabel#brandGlyph { color: $accent; font-size: 24px; font-weight: 700; }
QLabel#brandTitle { font-size: 15px; font-weight: 600; color: $text; }
QLabel#pageHeader { background: transparent; }

/* ── Sidebar surface — §5 glass, §3 radius-lg=20px ───────────────────── */
QFrame#sidebar {
  background: $sidebar;
  border: 1px solid $border;
  border-radius: 20px;
}
QFrame#sidebarDivider { background: $border; border: none; }

/* ── Navigation list ─────────────────────────────────────────────────── */
QListWidget#navList { background: transparent; border: 1px solid transparent; }
QListWidget#navList::item { padding: 0; margin: 0; border: none; }
QListWidget#navList::item:selected { background: transparent; }
QFrame#sidebar QToolButton { padding-left: 8px; padding-right: 24px; }

/* ── Cards — §12, §3 radius-md=14 ────────────────────────────────────── */
/* primary = hero card with gold left accent */
QFrame#primary {
  background: #16202e;
  border: 1px solid $border_medium;
  border-radius: 14px;
  border-left: 3px solid $accent;
}
/* surfaceCard = secondary cards */
QFrame#surfaceCard {
  background: #14202e;
  border: 1px solid $border;
  border-radius: 14px;
}
/* artifactSlot */
QFrame#artifactSlot {
  background: $background;
  border: 1px solid $border;
  border-radius: 10px;
}
QFrame#artifactSlot QLabel { background: transparent; border: none; }

/* ── Badges ───────────────────────────────────────────────────────────── */
QLabel#badge {
  background: #1E2C3E;
  color: $secondary;
  border: none;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
}
QLabel#badge[state="accent"]   { color: $accent_hover; }
QLabel#badge[state="success"]  { color: $success; }
QLabel#badge[state="warning"]  { color: $warning; }
QLabel#badge[state="danger"]   { color: $danger; }

/* fact label (availability/resin info strip) */
QLabel#fact {
  background: transparent;
  color: $secondary;
  border: none;
  border-left: 1px solid $border_medium;
  border-radius: 0;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
}
QLabel#fact[state="success"] { color: $success; border-left-color: $success; }
QLabel#fact[state="warning"] { color: $warning; border-left-color: $warning; }

/* ── Buttons — §19  height 40–44 px, radius 10–12 px, weight 600 ─────── */
QPushButton, QToolButton {
  background: #1E2C3E;
  color: $text;
  border: 1px solid $border_medium;
  border-radius: 10px;
  padding: 8px 14px;
  min-height: 26px;
  font-weight: 500;
}
QPushButton:hover, QToolButton:hover {
  background: $hover;
  border-color: rgba(255,255,255,0.22);
}
QPushButton:pressed, QToolButton:pressed {
  background: $background;
  border-color: $accent;
}
QPushButton:checked, QToolButton:checked {
  background: $hover;
  color: $accent_hover;
  border-color: $accent;
}
QPushButton:disabled, QToolButton:disabled {
  background: #111925;
  color: $muted;
  border-color: $border;
}

/* Primary button — one per screen, gold luminous edge */
QPushButton#primaryButton, QToolButton#primaryButton {
  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #F0D89C, stop:1 #D9C28B);
  color: #0C1018;
  border: 1px solid #F0D89C;
  font-weight: 700;
}
QPushButton#primaryButton:hover, QToolButton#primaryButton:hover {
  background: #FFF0BD;
  border-color: #FFF0BD;
  color: #0C1018;
}
QPushButton#primaryButton:pressed, QToolButton#primaryButton:pressed {
  background: $accent_pressed;
  border-color: $accent_pressed;
}
QPushButton#primaryButton:disabled, QToolButton#primaryButton:disabled {
  background: #1E2C3E;
  color: $muted;
  border-color: $border;
}
QToolButton#primaryButton { padding-right: 30px; }
QToolButton#primaryButton::menu-button {
  border-left: 1px solid rgba(217,194,139,0.5);
  width: 22px;
}

/* Ghost button — secondary, neutral glass */
QPushButton#ghostButton, QToolButton#ghostButton {
  background: transparent;
  color: $secondary;
  border: 1px solid $border_medium;
}
QPushButton#ghostButton:hover,
QPushButton#ghostButton:checked,
QToolButton#ghostButton:hover {
  color: $accent_hover;
  background: #1E2C3E;
  border-color: $accent;
}
QToolButton#ghostButton { padding-right: 30px; }
QToolButton#ghostButton::menu-button {
  border-left: 1px solid $border;
  width: 22px;
}

/* ── Inputs — §3 radius-sm=10 ────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
  background: $elevated;
  border: 1px solid $border_medium;
  border-radius: 10px;
  padding: 6px 10px;
  min-height: 22px;
  color: $text;
}
QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled { color: $muted; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url("$down"); width: 12px; height: 12px; }
QSpinBox, QDoubleSpinBox { padding-right: 24px; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
  subcontrol-origin: border; subcontrol-position: top right; width: 22px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
  subcontrol-origin: border; subcontrol-position: bottom right; width: 22px;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
  image: url("$up"); width: 10px; height: 10px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
  image: url("$down"); width: 10px; height: 10px;
}
QComboBox QAbstractItemView {
  background: $elevated;
  color: $text;
  border: 1px solid $border_medium;
  selection-background-color: $hover;
  selection-color: $text;
  padding: 4px;
  border-radius: 10px;
}

/* ── Checkbox ─────────────────────────────────────────────────────────── */
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
  width: 16px; height: 16px;
  border: 1px solid $border_medium;
  border-radius: 4px;
  background: $elevated;
}
QCheckBox::indicator:checked {
  image: url("$check");
  background: $hover;
  border-color: $accent;
}
QCheckBox:disabled { color: $muted; }

/* ── Lists / tables ───────────────────────────────────────────────────── */
QListView#actionQueue { background: transparent; border: none; }
QListWidget, QTreeWidget, QTableWidget, QTextEdit {
  background: $elevated;
  alternate-background-color: #151E2A;
  border: 1px solid $border;
  border-radius: 10px;
  gridline-color: $border;
}
QListWidget::item, QTreeWidget::item { padding: 10px 12px; }
QListWidget::item:hover, QTreeWidget::item:hover,
QTableWidget::item:hover { background: $hover; }
QListWidget::item:selected, QTreeWidget::item:selected,
QTableWidget::item:selected {
  background: $hover;
  color: $text;
}

/* ── Table header ─────────────────────────────────────────────────────── */
QHeaderView::section {
  background: $elevated;
  color: $secondary;
  padding: 10px;
  border: none;
  border-bottom: 1px solid $border;
  font-weight: 600;
  font-size: 12px;
}

/* ── Scrollbars — thin, low-contrast ─────────────────────────────────── */
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 2px; }
QScrollBar::handle:vertical {
  background: rgba(255,255,255,0.12);
  border-radius: 4px;
  min-height: 28px;
}
QScrollBar::handle:horizontal {
  background: rgba(255,255,255,0.12);
  border-radius: 4px;
  min-width: 28px;
}
QScrollBar::handle:hover { background: rgba(255,255,255,0.22); }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ── Splitter ─────────────────────────────────────────────────────────── */
QSplitter::handle { background: $border; }
QSplitter::handle:hover { background: $accent; }

/* ── Menus ────────────────────────────────────────────────────────────── */
QMenu {
  background: $elevated;
  color: $text;
  border: 1px solid $border_medium;
  border-radius: 10px;
  padding: 6px;
}
QMenu::item { padding: 8px 22px; border-radius: 6px; }
QMenu::item:selected { background: $hover; color: $accent_hover; }
QMenu::item:disabled { color: $muted; }
QMenu::separator { height: 1px; background: $border; margin: 6px 4px; }

/* ── Tabs ─────────────────────────────────────────────────────────────── */
QTabWidget::pane { border: 1px solid $border; border-radius: 10px; top: -1px; }
QTabBar::tab {
  background: transparent;
  color: $secondary;
  padding: 8px 16px;
  border-bottom: 2px solid transparent;
  margin-right: 2px;
}
QTabBar::tab:selected { color: $text; border-bottom-color: $accent; }
QTabBar::tab:hover { color: $text; }

/* ── Progress bar — §14 thin track, accent chunk ─────────────────────── */
QProgressBar {
  background: $elevated;
  border: none;
  border-radius: 4px;
  text-align: center;
  color: $text;
  font-size: 12px;
  max-height: 6px;
  min-height: 6px;
}
QProgressBar::chunk { background: $accent; border-radius: 3px; }

/* ── Status bar ───────────────────────────────────────────────────────── */
QStatusBar {
  background: transparent;
  color: $muted;
  border-top: 1px solid $border;
  font-size: 12px;
  padding-left: 16px;
}

/* ── Tooltip ──────────────────────────────────────────────────────────── */
QToolTip {
  background: $elevated;
  color: $text;
  border: 1px solid $border_medium;
  border-radius: 6px;
  padding: 7px 10px;
}

/* ── Focus ring — §32  2px accent, offset 2px ────────────────────────── */
QPushButton:focus, QToolButton:focus,
QLineEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus,
QListWidget:focus, QTreeWidget:focus,
QTableWidget:focus, QTextEdit:focus {
  border: 2px solid $accent;
}
QCheckBox:focus { color: $accent_hover; }
QTabBar::tab:focus { border-bottom-color: $accent; }

/* ── Feedback banner ──────────────────────────────────────────────────── */
QFrame#feedbackBanner {
  background: $elevated;
  border: 1px solid $border_medium;
  border-radius: 10px;
}
QFrame#feedbackBanner[state="error"] { border-color: $danger; }
''').substitute(_style_tokens)


from .premium_style import PREMIUM_STYLE
DESKTOP_STYLE += PREMIUM_STYLE


def set_state(widget, state: str) -> None:
    """Re-polish semantic state without duplicating per-widget styling."""
    widget.setProperty('state', state)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
