"""Project G light glass language shared by every native screen and dialog."""

LIQUID_STYLE = '''
QMainWindow, QDialog { background: #E9F1F3; color: #243B50; }
QWidget { color: #243B50; font-family: "HYWenHei", "Segoe UI", sans-serif; }
QLabel { background: transparent; }

/* The persistent rail anchors the image-backed workspace. */
QFrame#sidebar {
  background: rgba(30, 58, 81, 0.94);
  border: 1px solid rgba(255,255,255,0.36);
  border-radius: 18px;
}
QFrame#sidebar QLabel#brandTitle { color: #F5FAFA; font-size: 17px; }
QFrame#sidebar QLabel#brandSubtitle,
QFrame#sidebar QLabel#sidebarFooter { color: #BDD1DC; }
QFrame#sidebar QLabel#brandGlyph { color: #F0D69C; }
QFrame#sidebar QToolButton,
QFrame#sidebar QPushButton {
  background: rgba(255,255,255,0.10);
  color: #F4FAFB;
  border: 1px solid rgba(255,255,255,0.24);
}
QFrame#sidebar QToolButton:hover,
QFrame#sidebar QPushButton:hover { background: rgba(255,255,255,0.18); }
QListWidget#navList { background: transparent; border: none; }

/* Page hierarchy is calm and dark over the bright Mondstadt sky. */
QFrame#pageHeader { background: transparent; border: none; }
QLabel#pageKicker { color: #6B8491; font-size: 11px; font-weight: 600; }
QLabel#pageTitle, QLabel#headline { color: #20364D; font-size: 30px; font-weight: 600; }
QLabel#pageSubtitle, QLabel#secondaryText, QLabel#metricLabel,
QLabel#searchFeedback { color: #617786; }
QLabel#pageSubtitle { color: #29495D; font-weight: 500; }
QLabel#section, QLabel#stepTitle, QLabel#metricValue { color: #294358; }
QLabel#eyebrow, QLabel#stepNumber { color: #967542; }
QLabel#todayAction, QLabel#sourceDetail, QLabel#materialAmount { color: #344D5D; }

/* Shared glass surfaces; the Mondstadt canvas stays visible around them. */
QFrame#surfaceCard, QFrame#metricCard, QFrame#onboarding,
QFrame#alternativeCard, QFrame#emptyState {
  background: rgba(250,253,252,0.84);
  border: 1px solid rgba(255,255,255,0.92);
  border-radius: 17px;
}
QFrame#alternativeCard { background: rgba(231,246,238,0.88); }
QFrame#onboardingStep, QFrame#profileStat {
  background: rgba(242,249,249,0.90);
  border: 1px solid rgba(117,152,167,0.16);
  border-radius: 12px;
}
QFrame#artifactSlot, QWidget#characterPage QFrame#artifactSlot {
  background: rgba(244,249,249,0.96);
  border: 1px solid rgba(117,152,167,0.16);
  border-radius: 10px;
}
QWidget#characterPage QFrame#surfaceCard {
  background: rgba(250,253,253,0.88);
  border: 1px solid rgba(255,255,255,0.88);
  border-radius: 15px;
}
QFrame#primary, QFrame#characterNext,
QFrame#characterRoster, QFrame#characterDetailPanel {
  background: transparent;
  border: none;
}
QFrame#characterHero {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
    stop:0 rgba(234,243,242,0.97), stop:0.6 rgba(213,231,232,0.90),
    stop:1 rgba(230,213,173,0.70));
  border: 1px solid rgba(255,255,255,0.82);
  border-radius: 15px;
}
QLabel#characterSectionTitle { color: #294358; font-size: 18px; font-weight: 600; }
QLabel#characterHeroContext { color: #697F8C; font-size: 12px; }
QLabel#characterTaskLabel { color: #967542; font-size: 11px; font-weight: 600; }
QLabel#characterPortrait { background: transparent; border: none; }
QLabel#badge {
  background: rgba(228,239,239,0.80);
  color: #607787;
  border: none;
  border-radius: 7px;
  padding: 5px 9px;
}
QLabel#badge[state="success"] { background: #E0F0E6; color: #427C60; }
QLabel#badge[state="warning"] { background: #F5EDDA; color: #967542; }
QLabel#badge[state="accent"] { background: #F7F0DE; color: #8D6B38; }
QLabel#fact, QLabel#actionStatus, QLabel#tierProgress {
  background: rgba(241,248,248,0.88);
  border: 1px solid rgba(117,152,167,0.18);
  border-radius: 10px;
  color: #344E60;
  padding: 9px 12px;
}
QLabel#fact[state="success"], QLabel#actionStatus[state="success"] {
  background: #E3F1E9; border-color: #B7D7C4; color: #427C60;
}
QLabel#fact[state="warning"], QLabel#actionStatus[state="warning"] {
  background: #F7F0DE; border-color: #E7D5AF; color: #967542;
}
QLabel#emptyTitle { color: #243B50; }
QLabel#emptyDescription { color: #617786; }

/* One clear navy action per view, with quiet secondary controls. */
QPushButton, QToolButton {
  background: rgba(249,252,252,0.88);
  color: #345266;
  border: 1px solid rgba(114,146,160,0.27);
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 500;
}
QPushButton:hover, QToolButton:hover {
  background: #FFFFFF; border-color: #B9A274;
}
QPushButton:pressed, QToolButton:pressed { background: #E0ECEE; }
QPushButton:checked, QToolButton:checked {
  background: #E4EFF0; color: #24465D; border-color: #BFA36E;
}
QPushButton:disabled, QToolButton:disabled {
  background: rgba(238,244,244,0.58);
  color: #94A7AE;
  border-color: rgba(114,146,160,0.14);
}
QPushButton#primaryButton, QToolButton#primaryButton {
  background: #31546B; color: #FFFFFF;
  border: 1px solid #31546B; font-weight: 600;
}
QPushButton#primaryButton:hover, QToolButton#primaryButton:hover {
  background: #203F55; color: #FFFFFF; border-color: #203F55;
}
QPushButton#primaryButton:disabled, QToolButton#primaryButton:disabled {
  background: #CAD8DD; color: #78909B; border-color: #CAD8DD;
}
QPushButton#ghostButton, QToolButton#ghostButton {
  background: rgba(246,251,251,0.58); color: #547183;
  border: 1px solid rgba(114,146,160,0.22);
}
QPushButton#ghostButton:hover, QToolButton#ghostButton:hover {
  background: #FFFFFF; color: #294B61; border-color: #BFA36E;
}
QPushButton#characterFilter {
  background: rgba(237,246,246,0.89); color: #5F7988;
  border: 1px solid #D3E3E7; font-size: 11px;
  padding: 6px 8px; min-height: 23px;
}
QPushButton#characterFilter:checked {
  background: #294B62; color: #FFFFFF; border-color: #294B62;
}

/* Inputs, data views, and secondary workflows use the same light surfaces. */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
  background: rgba(250,253,253,0.94);
  color: #294358;
  border: 1px solid #D5E4E7;
  border-radius: 10px;
  padding: 7px 11px;
}
QComboBox QAbstractItemView {
  background: #F9FCFC; color: #294358;
  selection-background-color: #DCEAEC;
  selection-color: #294358;
}
QListWidget, QTreeWidget, QTableWidget {
  background: rgba(250,253,253,0.88);
  alternate-background-color: #EDF5F6;
  color: #294358;
  border: 1px solid rgba(112,146,161,0.20);
  border-radius: 12px;
}
QListWidget#characterList, QListWidget#navList,
QListView#actionQueue, QTableWidget#tierTable {
  background: transparent; border: none;
}
QListWidget#characterList::item { padding: 0; border: none; margin: 0; }
QListWidget#characterList::item:selected,
QListWidget#characterList::item:hover { background: transparent; border: none; }
QListWidget::item:selected, QTreeWidget::item:selected,
QTableWidget::item:selected { background: #DDECEE; color: #243B50; }
QTreeWidget::item:hover, QTableWidget::item:hover { background: #EDF6F6; }
QTableWidget#tierTable::item {
  background: rgba(250,253,253,0.91);
  border: none; border-bottom: 2px solid #E5EFF1;
  padding: 10px 14px;
}
QTableWidget#tierTable::item:selected { background: #DDECEE; color: #243B50; }
QTableWidget#tierTable QComboBox#tierRankPicker {
  background: #EDF5F5; color: #294358; border-color: #C7DADD;
}
QHeaderView::section {
  background: #E5F0F1; color: #5B7381;
  border: none; border-bottom: 1px solid #CDDFE3;
  padding: 9px; font-weight: 600;
}
QTabWidget::pane { background: transparent; border: none; }
QTabBar::tab { background: transparent; color: #617786; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #294358; border-bottom-color: #BEA16B; }
QProgressBar { background: #DCEAEC; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #BDA16C; border-radius: 3px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
  background: rgba(92,129,146,0.30);
}
QSplitter::handle { background: transparent; width: 8px; }
QSplitter#characterSplitter::handle { background: transparent; width: 10px; }

QMenu { background: #F7FBFB; color: #294358; border: 1px solid #D2E1E4; }
QMenu::item:selected { background: #E4F0F1; color: #294358; }
QToolTip { background: #F9FCFC; color: #294358; border: 1px solid #C9DCE0; }
QStatusBar { background: rgba(247,251,251,0.75); color: #5F7786; border: none; }
QFrame#feedbackBanner { background: rgba(250,253,253,0.94); border: 1px solid #CEDFE2; }
QFrame#feedbackBanner[state="error"] { border-color: #B4544B; }
QFrame#tierErrorBanner { background: #F8E9E8; border: 1px solid #D19A95; }
QFrame#tierErrorBanner QLabel { color: #953F3B; }
QLabel#tierSaveStatus { color: #967542; }
QLabel#tierSaveStatus[state="danger"] { color: #B4544B; }
QPushButton:focus, QToolButton:focus, QLineEdit:focus,
QComboBox:focus, QListWidget:focus, QTreeWidget:focus,
QTableWidget:focus, QTextEdit:focus { border: 2px solid #B9975D; }
'''
