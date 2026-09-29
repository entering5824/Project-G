"""Anime-fantasy overlay: design.ms §4–§5 glass, §10–§12 cards, §19 buttons.

Layered over the base stylesheet in theme.py.  Overrides take effect in
declaration order so the most specific (Teyvat-flavored) rules win.

Key design decisions:
  • Background: dark blue-gray canvas with subtle radial glows (§26)
  • Glass panels: rgba(20,27,39,0.68) + 18-28px *conceptual* blur (§5)
  • Borders: 1px rgba(255,255,255,0.08) — low-contrast, not black (§3.2)
  • Gold accent used sparingly: CTA, selected state, mini badge only (§4.1)
  • Elemental accents: icon / glow / progress / selected outline only (§4.3)
  • Corner radii: radius-md=14px for cards, radius-lg=20px for large panels (§3.1)
"""

PREMIUM_STYLE = '''

/* ── Canvas and main shell — §26 dark blue-gray, subtle gradient ──────── */
QMainWindow, QDialog { background: #0C1018; }

/* ── Sidebar glass panel — §5 standard glass, §3 radius-lg=20px ─────── */
QFrame#sidebar {
  background: rgba(18, 26, 40, 0.92);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 20px;
}

/* ── Page header — §6 typography, gold separator ─────────────────────── */
QFrame#pageHeader {
  border-bottom: 1px solid rgba(217,194,139,0.18);
}

/* ── Typography overrides — §6 hierarchy ─────────────────────────────── */
/* Display / page title */
QLabel#pageTitle, QLabel#headline {
  color: #F3F5F7;
  font-size: 30px;
  font-weight: 600;
}
/* Kicker / eyebrow — 12px/700, gold */
QLabel#pageKicker, QLabel#eyebrow, QLabel#stepNumber {
  color: #D9C28B;
  font-size: 12px;
  font-weight: 700;
}
/* Secondary text */
QLabel#pageSubtitle, QLabel#secondaryText, QLabel#metricLabel { color: #B9C0CB; }
/* Section / card titles */
QLabel#section, QLabel#stepTitle, QLabel#metricValue { color: #F3F5F7; }
QLabel#metricValue { font-size: 22px; font-weight: 600; }
/* Brand */
QLabel#brandGlyph { color: #D9C28B; font-size: 24px; font-weight: 700; }
QLabel#brandTitle { color: #F3F5F7; font-size: 15px; font-weight: 600; }
QLabel#brandSubtitle, QLabel#sidebarFooter { color: #7F8998; font-size: 12px; }

/* ── Character portrait badge — §11 radial glow background ───────────── */
QLabel#characterPortrait {
  background: qradialgradient(
    cx:0.5, cy:0.55, radius:0.62,
    stop:0   rgba(217,194,139,60),
    stop:0.6 rgba(20,32,48,50),
    stop:1   rgba(12,16,24,0)
  );
  border: 1px solid rgba(217,194,139,0.25);
  border-radius: 72px;
}

/* ── Cards — §12, §5 glass panels ────────────────────────────────────── */
/* Hero / primary recommendation card — §10, SmokedGlassFrame uses paintEvent */
QFrame#primary {
  background: transparent;
  border: none;
  border-radius: 14px;
}

/* Surface card — secondary supporting information */
QFrame#surfaceCard, QFrame#metricCard, QFrame#onboarding {
  background: rgba(20,27,39,0.68);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
}

/* Onboarding step chip */
QFrame#onboardingStep {
  background: rgba(28,38,56,0.72);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
}

/* Alternative task card — teal-glass per spec §4.3 Anemo tint */
QFrame#alternativeCard {
  background: rgba(16,52,52,0.68);
  border: 1px solid rgba(101,213,197,0.28);
  border-radius: 14px;
}

/* Artifact slot — smallest enclosed surface */
QFrame#artifactSlot,
QWidget#characterPage QFrame#artifactSlot {
  background: rgba(12,16,24,0.80);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
}

/* Character page card override */
QWidget#characterPage QFrame#surfaceCard {
  background: rgba(20,27,39,0.72);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
}

/* ── Tier error banner ────────────────────────────────────────────────── */
QFrame#tierErrorBanner { background: rgba(64,28,44,0.88); border: 1px solid #9B3B5A; border-radius: 9px; }
QFrame#tierErrorBanner QLabel { color: #FFCDD8; }

/* ── Empty state — §20 instructional, not "No data found" ────────────── */
QFrame#emptyState {
  background: rgba(20,27,39,0.68);
  border: 1px solid rgba(217,194,139,0.22);
  border-radius: 14px;
}
QFrame#emptyState QLabel#eyebrow { color: #D9C28B; }
QLabel#emptyTitle { color: #F3F5F7; font-size: 22px; font-weight: 600; }
QLabel#emptyDescription { color: #B9C0CB; font-size: 14px; }

/* ── Fact labels (info strips in hero card) ───────────────────────────── */
QLabel#fact {
  background: rgba(20,27,39,0.60);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 12px 16px;
  color: #F3F5F7;
}
QLabel#fact[state="success"] { border-color: rgba(101,213,197,0.35); color: #65D5C5; }
QLabel#fact[state="warning"] { border-color: rgba(228,180,93,0.35);  color: #E4B45D; }

/* ── Badge labels ─────────────────────────────────────────────────────── */
QLabel#badge { background: transparent; border: none; color: #B9C0CB; padding: 4px 0; font-weight: 400; }

/* ── Source detail ───────────────────────────────────────────────────── */
QLabel#sourceDetail { color: #F3F5F7; font-size: 14px; padding: 6px 0; }

/* ── Action status chip ───────────────────────────────────────────────── */
QLabel#actionStatus {
  background: rgba(32,42,60,0.80);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 9px;
  color: #D9C28B;
  padding: 9px 12px;
  font-weight: 600;
}
QLabel#actionStatus[state="success"] {
  background: rgba(16,52,52,0.80);
  border-color: rgba(101,213,197,0.30);
  color: #65D5C5;
}
QLabel#actionStatus[state="warning"] {
  background: rgba(56,44,20,0.80);
  border-color: rgba(228,180,93,0.35);
  color: #E4B45D;
}

/* ── Tier progress ────────────────────────────────────────────────────── */
QLabel#tierProgress {
  color: #F3F5F7;
  background: rgba(18,24,36,0.80);
  border-left: 2px solid #D9C28B;
  padding: 9px 14px;
}
QLabel#tierProgress[state="warning"] { color: #E4B45D; border-left-color: #E4B45D; }
QLabel#tierSaveStatus { color: #E4B45D; font-size: 12px; padding: 0 8px; }
QLabel#tierSaveStatus[state="danger"] { color: #F06A58; }

/* ── Buttons — §19  gold primary, neutral ghost ───────────────────────── */
QPushButton, QToolButton {
  background: rgba(28,38,56,0.90);
  color: #F3F5F7;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 500;
}
QPushButton:hover, QToolButton:hover {
  background: rgba(38,52,76,0.95);
  border-color: rgba(255,255,255,0.22);
}
QPushButton:pressed, QToolButton:pressed {
  background: rgba(12,16,24,0.95);
  border-color: #D9C28B;
}
QPushButton:checked, QToolButton:checked {
  background: rgba(42,58,84,0.95);
  color: #F0D89C;
  border-color: #D9C28B;
}
QPushButton:disabled, QToolButton:disabled {
  background: rgba(20,28,42,0.70);
  color: #7F8998;
  border-color: rgba(255,255,255,0.06);
}

/* Primary — gold gradient, one per screen */
QPushButton#primaryButton, QToolButton#primaryButton {
  background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F0D89C, stop:1 #D9C28B);
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
  background: #C8A865;
  border-color: #C8A865;
}
QPushButton#primaryButton:disabled, QToolButton#primaryButton:disabled {
  background: rgba(28,38,56,0.70);
  color: #7F8998;
  border-color: rgba(255,255,255,0.06);
}
QToolButton#primaryButton { padding-right: 30px; }
QToolButton#primaryButton::menu-button {
  border-left: 1px solid rgba(217,194,139,0.40);
  width: 22px;
}

/* Ghost — tertiary, transparent */
QPushButton#ghostButton, QToolButton#ghostButton {
  background: rgba(20,27,39,0.40);
  color: #B9C0CB;
  border: 1px solid rgba(255,255,255,0.12);
}
QPushButton#ghostButton:hover,
QPushButton#ghostButton:checked,
QToolButton#ghostButton:hover {
  color: #F0D89C;
  background: rgba(32,44,64,0.80);
  border-color: #D9C28B;
}
QToolButton#ghostButton { padding-right: 30px; }
QToolButton#ghostButton::menu-button {
  border-left: 1px solid rgba(255,255,255,0.12);
  width: 22px;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
  background: rgba(12,16,24,0.90);
  color: #F3F5F7;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 10px;
  padding: 7px 11px;
}

/* ── Tables / lists ───────────────────────────────────────────────────── */
QTableWidget, QTreeWidget, QListWidget, QTextEdit {
  background: rgba(18,24,36,0.80);
  alternate-background-color: rgba(20,28,44,0.90);
  color: #F3F5F7;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
}
QListWidget#navList, QListWidget#characterList {
  background: transparent;
  border: none;
}
QListWidget::item { border-radius: 6px; }
QListWidget::item:selected { background: rgba(38,52,76,0.90); color: #F3F5F7; }
QListWidget::item:hover { background: rgba(28,38,56,0.80); }

/* Character list */
QListWidget#characterList { background: transparent; border: none; padding: 2px; }
QListWidget#characterList:focus { border: none; }
QListWidget#characterList::item {
  border: none;
  border-left: 3px solid transparent;
  border-radius: 8px;
  padding: 11px 12px;
  margin: 1px 0;
}
QListWidget#characterList::item:hover { background: rgba(28,38,56,0.80); }
QListWidget#characterList::item:selected {
  background: rgba(38,52,76,0.90);
  border-left: 3px solid #D9C28B;
  color: #F3F5F7;
}

/* Tier table */
QTableWidget#tierTable { background: transparent; border: none; }
QTableWidget#tierTable:focus { border: none; }
QTableWidget#tierTable::item {
  background: rgba(18,24,36,0.80);
  border: none;
  border-bottom: 2px solid #0C1018;
  padding: 10px 14px;
}
QTableWidget#tierTable::item:hover { background: rgba(28,38,56,0.80); }
QTableWidget#tierTable::item:selected {
  background: rgba(38,52,76,0.90);
  color: #F3F5F7;
}
QTableWidget#tierTable QComboBox#tierRankPicker {
  background: rgba(38,52,76,0.90);
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 9px;
  margin: 6px 8px;
  padding: 3px 10px;
  color: #F3F5F7;
  font-weight: 600;
}
QTableWidget#tierTable QComboBox#tierRankPicker:hover,
QTableWidget#tierTable QComboBox#tierRankPicker:focus {
  border-color: #D9C28B;
}

/* Header */
QHeaderView::section {
  background: rgba(18,24,36,0.90);
  color: #B9C0CB;
  border: none;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  padding: 10px;
  font-weight: 500;
}
QTableWidget::item, QTreeWidget::item {
  padding: 8px;
  border: none;
}
QTableWidget::item:selected, QTreeWidget::item:selected {
  background: rgba(38,52,76,0.90);
  color: #F3F5F7;
}

/* ── Menus ────────────────────────────────────────────────────────────── */
QMenu {
  background: rgba(18,24,36,0.96);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 10px;
  padding: 6px;
  color: #F3F5F7;
}
QMenu::item { border-radius: 6px; padding: 9px 22px; }
QMenu::item:selected { background: rgba(38,52,76,0.90); color: #F3F5F7; }

/* ── Tabs ─────────────────────────────────────────────────────────────── */
QTabWidget::pane {
  background: transparent;
  border: none;
  border-top: 1px solid rgba(255,255,255,0.08);
  border-radius: 0;
}
QTabBar::tab {
  background: transparent;
  color: #B9C0CB;
  padding: 10px 16px;
  border-radius: 0;
  border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: #F3F5F7; border-bottom-color: #D9C28B; }

/* ── Progress bar — §14 thin track, accent gold ──────────────────────── */
QProgressBar { background: rgba(18,24,36,0.80); border: none; border-radius: 3px; }
QProgressBar::chunk { background: #D9C28B; border-radius: 3px; }

/* ── Scroll / splitter ───────────────────────────────────────────────── */
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }
QSplitter::handle { background: rgba(255,255,255,0.08); width: 1px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
  background: rgba(255,255,255,0.14);
}

/* ── Status bar ───────────────────────────────────────────────────────── */
QStatusBar { background: transparent; border: none; color: #7F8998; padding-left: 24px; }

/* ── Feedback banner ──────────────────────────────────────────────────── */
QFrame#feedbackBanner {
  background: rgba(20,27,39,0.80);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 10px;
}
QFrame#feedbackBanner[state="error"] { border-color: #F06A58; }

/* ── Focus ring — §32  2px accent gold ───────────────────────────────── */
QPushButton:focus, QToolButton:focus,
QLineEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus,
QListWidget:focus, QTreeWidget:focus,
QTableWidget:focus, QTextEdit:focus {
  border: 2px solid #D9C28B;
}
'''
