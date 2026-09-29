"""Native desktop presentation: main_window."""
from .glass import GlassCanvas
from datetime import datetime
from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QAction, QColor, QShortcut, QKeySequence, QPalette
from PySide6.QtWidgets import QBoxLayout, QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget, QToolButton
from projectg.presentation.desktop.pyside6.theme import COLORS, DESKTOP_STYLE, load_project_font, set_state
from projectg.presentation.desktop.pyside6.navigation import NavigationDelegate
from projectg.presentation.desktop.pyside6.workers import OverviewWorker
import logging
log = logging.getLogger(__name__)


from projectg.presentation.desktop.pyside6.pages.today import TodayPage
from projectg.presentation.desktop.pyside6.pages.roadmap import RoadmapPage
from projectg.presentation.desktop.pyside6.pages.characters import CharactersPage
from projectg.presentation.desktop.pyside6.pages.data import DataPage
from projectg.presentation.desktop.pyside6.pages.tier_list import TierListPage
from projectg.presentation.desktop.pyside6.actions.data_io import DataActions
from projectg.presentation.desktop.pyside6.actions.planning import PlanningActions


class MainWindow(TodayPage, RoadmapPage, CharactersPage, DataPage, TierListPage,
                 DataActions, PlanningActions, QMainWindow):
    def __init__(self, account_import_controller, settings_controller, teams_controller,
                 character_configuration_controller, game_data_controller, artifact_exchange_controller,
                 planner_state_controller, target_controller, tier_pack_controller, support_controller,
                 overview_controller, build_intent_controller=None):
        super().__init__()
        self._rail_mode = None
        self._data = None
        self.account_import_controller = account_import_controller
        self.settings_controller = settings_controller
        self.teams_controller = teams_controller
        self.character_configuration_controller = character_configuration_controller
        self.game_data_controller = game_data_controller
        self.artifact_exchange_controller = artifact_exchange_controller
        self.planner_state_controller = planner_state_controller
        self.target_controller = target_controller
        self.tier_pack_controller = tier_pack_controller
        self.support_controller = support_controller
        self.overview_controller = overview_controller
        self.build_intent_controller = build_intent_controller
        self.setWindowTitle("Genshin Account Progression Planner")
        self.resize(1280, 800)
        self.setMinimumSize(800, 560)
        self.project_font_family = load_project_font()
        # Native control arrows and placeholders also need a dark palette.
        palette = self.palette()
        for role, token in ((QPalette.ColorRole.Window, "background"),
                            (QPalette.ColorRole.Base, "elevated"),
                            (QPalette.ColorRole.AlternateBase, "hover"),
                            (QPalette.ColorRole.Button, "elevated"),
                            (QPalette.ColorRole.Text, "text"),
                            (QPalette.ColorRole.WindowText, "text"),
                            (QPalette.ColorRole.ButtonText, "text"),
                            (QPalette.ColorRole.PlaceholderText, "muted"),
                            (QPalette.ColorRole.Highlight, "accent"),
                            (QPalette.ColorRole.HighlightedText, "background")):
            palette.setColor(role, QColor(COLORS[token]))
        self.setPalette(palette)
        self.setStyleSheet(DESKTOP_STYLE)

        root = GlassCanvas()
        self.setCentralWidget(root)
        layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, root)
        self.root_layout = layout
        layout.setContentsMargins(20, 16, 20, 0)
        layout.setSpacing(16)

        # The same top bar is used at every window size.
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        self.sidebar = sidebar
        sidebar_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, sidebar)
        self.sidebar_layout = sidebar_layout
        sidebar_layout.setContentsMargins(20, 12, 16, 12)
        sidebar_layout.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_glyph = QLabel("✦")
        brand_glyph.setObjectName("brandGlyph")
        brand_row.addWidget(brand_glyph)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_title = QLabel("PROJECT G")
        brand_title.setObjectName("brandTitle")
        brand_subtitle = QLabel("HÀNH TRÌNH CỦA BẠN")
        brand_subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_subtitle)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        self.nav.setFlow(QListWidget.Flow.LeftToRight)
        self.nav.setWrapping(False)
        self.nav.setItemDelegate(NavigationDelegate(self.nav))
        self.nav.setMouseTracking(True)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        self.nav.addItems(["Hôm nay", "Kế hoạch", "Nhân vật", "Dữ liệu", "Ưu tiên"])
        self.nav.item(4).setHidden(True)
        self.nav.setAccessibleName("Điều hướng chính")
        for index, description in enumerate((
            "Việc nên làm hôm nay", "Thứ tự nâng cấp toàn tài khoản",
            "Tiến trình và build của từng nhân vật", "Tài khoản và dữ liệu trên máy",
            "Xếp hạng và ưu tiên nhân vật",
        )):
            self.nav.item(index).setToolTip(f"{description} · Ctrl+{index + 1}")
        self.nav.currentRowChanged.connect(self._switch)
        sidebar_layout.addWidget(self.nav, 1)

        sidebar_footer = QLabel("Dữ liệu lưu trên máy")
        sidebar_footer.setWordWrap(True)
        sidebar_footer.setObjectName("sidebarFooter")
        self.account_summary = QLabel("Tài khoản của bạn")
        self.account_summary.setObjectName("sidebarFooter")
        self.account_summary.setWordWrap(True)
        self.account_summary.hide()
        self.sidebar_footer = sidebar_footer
        sidebar_layout.addWidget(self.account_summary)
        sidebar_layout.addWidget(sidebar_footer)
        layout.addWidget(sidebar)

        # Main Panel
        main_panel = QWidget()
        main = QVBoxLayout(main_panel)
        self.main_layout = main
        main.setContentsMargins(12, 12, 12, 20)
        main.setSpacing(20)
        layout.addWidget(main_panel, 1)

        # Page context stays above actions so narrow windows do not clip controls.
        header = QFrame()
        header.setObjectName("pageHeader")
        header_layout = QVBoxLayout(header)
        self.header_layout = header_layout
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(6)
        self.page_kicker = QLabel("HÀNH TRÌNH PHÁT TRIỂN")
        self.page_kicker.setObjectName("pageKicker")
        header_layout.addWidget(self.page_kicker)
        self.page_title = QLabel("Hôm nay")
        self.page_title.setObjectName("pageTitle")
        self.page_description = QLabel()
        self.page_description.setObjectName("pageSubtitle")
        self.page_description.setWordWrap(True)
        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_description)
        main.addWidget(header)

        # Consolidated Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)


        self.target_button = QPushButton("Target JSON…")
        self.target_button.clicked.connect(self.import_targets)
        self.target_button.setVisible(False)

        self.snapshot_button = QToolButton()
        self.snapshot_button.setText("Dữ liệu tài khoản")
        self.snapshot_button.setObjectName("primaryButton")
        self.snapshot_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.snapshot_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.snapshot_button.setToolTip("Nhập hoặc chỉnh sửa Account Snapshot; mở mũi tên để nhập file GOOD")
        self.snapshot_button.setAccessibleName("Nhập tài khoản hoặc file GOOD")
        self.snapshot_button.clicked.connect(self.import_account_file)
        account_menu = QMenu(self.snapshot_button)
        account_menu.addAction("Nhập / chỉnh sửa Account Snapshot…", self.import_snapshot)
        self.good_import_action = account_menu.addAction("Nhập file GOOD…", self.import_good)
        self.snapshot_button.setMenu(account_menu)
        sidebar_layout.addWidget(self.snapshot_button)

        # Additional tools instantiated on self for backward-compatibility
        self.artifact_button = QPushButton("Artifact…")
        self.artifact_button.clicked.connect(self.import_artifacts)
        self.history_button = QPushButton("History…")
        self.history_button.clicked.connect(self.open_history)
        self.runs_button = QPushButton("Plan Runs…")
        self.runs_button.clicked.connect(lambda: self._run_plan_runs())
        self.health_button = QPushButton("Data Health…")
        self.health_button.clicked.connect(self.open_data_health)
        self.settings_button = QPushButton("Settings…")
        self.settings_button.clicked.connect(self.open_settings)
        self.teams_button = QPushButton("Teams…")
        self.teams_button.clicked.connect(lambda: self._run_teams())
        self.backup_button = QPushButton("Backup…")
        self.backup_button.clicked.connect(self.export_backup)
        self.restore_button = QPushButton("Restore…")
        self.restore_button.clicked.connect(self.restore_backup)
        self.logs_button = QPushButton("Logs")
        self.logs_button.clicked.connect(self.open_logs)

        # Group tools without changing their controllers or busy-state guards.
        self.tools_button = QPushButton("⋯")
        self.tools_button.setAccessibleName("Các thao tác và cài đặt khác")
        tools_menu = QMenu(self.tools_button)
        tools_menu.addAction("Cài đặt…", self.settings_button.click)
        tools_menu.addAction("Phím tắt…", lambda: QMessageBox.information(
            self, "Phím tắt Project G",
            "Ctrl+1: Hôm nay\nCtrl+2: Kế hoạch\nCtrl+3: Nhân vật\nCtrl+4: Dữ liệu\n"
            "Ctrl+5: Điều chỉnh ưu tiên\nCtrl+F: Tìm kiếm\nCtrl+R: Cập nhật kế hoạch"))
        planning_menu = tools_menu.addMenu("Lập kế hoạch")
        data_menu = tools_menu.addMenu("Dữ liệu")
        support_menu = tools_menu.addMenu("Hỗ trợ")
        self._tool_actions = []
        self.theater_button = QPushButton("Chuẩn bị Nhà Hát…")
        self.theater_button.clicked.connect(self.open_theater_preparation)
        for menu, text, button in (
            (planning_menu, "Chuẩn bị Nhà Hát…", self.theater_button),
            (planning_menu, "Đánh giá Artifact…", self.artifact_button),
            (planning_menu, "Đội hình…", self.teams_button),
            (planning_menu, "Lịch sử thay đổi…", self.history_button),
            (planning_menu, "Nhật ký kế hoạch…", self.runs_button),
            (data_menu, "Kiểm tra dữ liệu…", self.health_button),
            (data_menu, "Sao lưu dữ liệu…", self.backup_button),
            (data_menu, "Khôi phục dữ liệu…", self.restore_button),
            (support_menu, "Cài đặt tài khoản…", self.settings_button),
            (support_menu, "Mở thư mục Logs", self.logs_button),
        ):
            action = menu.addAction(text, button.click)
            self._tool_actions.append((action, button))
        data_menu.addAction("GameData trên máy…", self.open_game_data)
        for menu in (tools_menu, planning_menu, data_menu, support_menu):
            menu.aboutToShow.connect(self._sync_tool_actions)
        self.tools_button.setMenu(tools_menu)
        toolbar.addStretch(1)
        self.export_results_button = QPushButton("Xuất kết quả…", self)
        self.export_results_button.setToolTip("Xuất báo cáo, JSON và mẫu nhận xét để đánh giá kết quả")
        self.export_results_button.setEnabled(False)
        self.export_results_button.clicked.connect(self.export_planner_results)
        sidebar_layout.addWidget(self.tools_button)
        sidebar_footer.show()

        self.refresh_button = QPushButton("Tính lại", self)
        self.refresh_button.setToolTip("Tính lại kế hoạch từ dữ liệu hiện tại · Ctrl+R")
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh_action = QAction("Tính lại kế hoạch", tools_menu)
        self.refresh_action.triggered.connect(self.refresh_button.click)
        self.export_action = QAction("Xuất kết quả…", tools_menu)
        self.export_action.triggered.connect(self.export_results_button.click)
        tools_menu.insertAction(planning_menu.menuAction(), self.refresh_action)
        tools_menu.insertAction(planning_menu.menuAction(), self.export_action)
        tools_menu.insertSeparator(planning_menu.menuAction())
        self._tool_actions.extend(((self.refresh_action, self.refresh_button),
                                   (self.export_action, self.export_results_button)))
        advanced_menu = tools_menu.addMenu("Công cụ nâng cao")
        advanced_menu.addAction("Điều chỉnh ưu tiên…", lambda: self.nav.setCurrentRow(4))
        advanced_menu.addAction("Chỉnh mục tiêu…", self.open_target_editor)
        advanced_menu.addAction("Nhập Target JSON…", self.import_targets)
        advanced_menu.addAction("Nhập dữ liệu thủ công…", self.import_snapshot)
        advanced_menu.addAction("Nhật ký kế hoạch…", self.runs_button.click)
        self.refresh_button.hide()
        self.export_results_button.hide()

        header_layout.addSpacing(10)
        header_layout.addLayout(toolbar)

        self.feedback_banner = QFrame()
        self.feedback_banner.setObjectName("feedbackBanner")
        feedback_layout = QHBoxLayout(self.feedback_banner)
        feedback_layout.setContentsMargins(12, 8, 12, 8)
        self.feedback_text = QLabel()
        self.feedback_text.setWordWrap(True)
        self.feedback_text.setAccessibleName("Trạng thái cập nhật kế hoạch")
        feedback_layout.addWidget(self.feedback_text, 1)
        self.retry_button = QPushButton("Thử lại")
        self.retry_button.clicked.connect(self.refresh_button.click)
        feedback_layout.addWidget(self.retry_button)
        self.feedback_banner.hide()
        main.addWidget(self.feedback_banner)

        # Stacked Pages
        self.pages = QStackedWidget()
        main.addWidget(self.pages, 1)

        self._make_today()
        self._make_roadmap()
        self._make_characters()
        self._make_data()
        self._make_tier_list()

        self.today_title.setTextFormat(Qt.TextFormat.PlainText)
        self.today_action.setTextFormat(Qt.TextFormat.PlainText)
        self.today_why.setTextFormat(Qt.TextFormat.PlainText)
        self.char_name.setTextFormat(Qt.TextFormat.PlainText)
        self.roadmap_tree.setAccessibleName("Lộ trình nâng cấp toàn tài khoản")
        self.tier_table.setAccessibleName("Xếp hạng và ưu tiên nhân vật")
        self.roadmap_filter.setAccessibleName("Lọc lộ trình theo trạng thái")
        self.export_results_button.setToolTip("Nhập tài khoản và tính kế hoạch để xuất kết quả")
        self._navigation_shortcuts = []
        for index in range(self.nav.count()):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda row=index: self.nav.setCurrentRow(row))
            self._navigation_shortcuts.append(shortcut)
        self._refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self._refresh_shortcut.activated.connect(self.refresh_button.click)
        self._search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._search_shortcut.activated.connect(self._focus_page_search)
        self.nav.setCurrentRow(0)
        self._pool = QThreadPool(self)
        self._generation = 0
        self._loading = False
        self._workers = []
        self._apply_window_layout()
        self.statusBar().showMessage("Đang mở dữ liệu local…")
        QTimer.singleShot(0, self.refresh)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "tier_help"):
            self._apply_window_layout()


    def closeEvent(self, event):
        if self._confirm_tier_discard("Đóng ứng dụng"):
            super().closeEvent(event)
        else:
            event.ignore()


    def _apply_window_layout(self):
        rail = self.width() >= 1180
        short = self.height() < 700
        if rail != self._rail_mode:
            self.root_layout.setDirection(QBoxLayout.Direction.LeftToRight if rail else QBoxLayout.Direction.TopToBottom)
            self.sidebar_layout.setDirection(QBoxLayout.Direction.TopToBottom if rail else QBoxLayout.Direction.LeftToRight)
            self.nav.setFlow(QListWidget.Flow.TopToBottom if rail else QListWidget.Flow.LeftToRight)
            self.nav.setProperty("rail", rail)
            self._rail_mode = rail
        self.root_layout.setContentsMargins(20 if rail else 10,
                                            16 if rail else 8 if short else 16,
                                            20 if rail else 10, 0)
        self.root_layout.setSpacing(16 if rail else 6 if short else 12)
        if rail:
            self.sidebar.setMinimumHeight(0)
            self.sidebar.setMaximumHeight(16777215)
            self.sidebar.setFixedWidth(210)
            self.sidebar_layout.setContentsMargins(16, 22, 16, 16)
            self.nav.setMinimumHeight(0)
            self.nav.setMaximumHeight(16777215)
            self.nav.setFixedWidth(178)
        else:
            self.sidebar.setMinimumWidth(0)
            self.sidebar.setMaximumWidth(16777215)
            self.sidebar.setFixedHeight(58 if short else 68)
            self.sidebar_layout.setContentsMargins(12, 6 if short else 10,
                                                   12, 6 if short else 10)
            self.nav.setMinimumWidth(0)
            self.nav.setMaximumWidth(16777215)
            self.nav.setFixedHeight(46 if short else 52)
        self.main_layout.setContentsMargins(0 if not rail else 8, 8,
                                           0 if not rail else 8, 16)
        self.header_layout.setSpacing(3 if short else 6)
        self.page_description.setVisible(not short)
        self.page_kicker.setVisible(not short and self.pages.currentIndex() == 2)
        self.tier_help.setText(
            "Chọn hạng ưu tiên · Lưu để cập nhật lộ trình."
            if short else
            "Chọn hạng cho nhân vật bạn muốn đầu tư. Hạng cao hơn được ưu tiên trong lộ trình."
        )
        self.roster_label.setVisible(not short)
        compact_character = self.width() < 1060
        self.character_left_panel.setVisible(not compact_character)
        self.character_picker.setVisible(compact_character)
        compact_plan = self.width() < 1060
        self._size_today_cards()
        self._size_data_cards()
        self.today_inspector_back.setVisible(compact_plan)
        if not compact_plan:
            self.today_scroll.show()
        elif not self.today_inspector.isHidden():
            self.today_scroll.hide()
        self.action_back.setVisible(compact_plan)
        self.action_detail_layout.setContentsMargins(
            14 if short else 24, 12 if short else 24,
            14 if short else 24, 12 if short else 24)
        self.action_detail_layout.setSpacing(5 if short else 12)
        if not compact_plan:
            self.action_list_panel.show()
            self.action_detail_panel.show()
            self.roadmap_search.show()
            self.roadmap_filter.show()
        elif not self.action_list_panel.isHidden():
            self.action_detail_panel.hide()
        if short != getattr(self, "_compact_character", None):
            self.char_avatar.setFixedSize(72 if short else 104, 72 if short else 104)
            self.character_header_layout.setContentsMargins(
                16 if short else 24, 12 if short else 22,
                16 if short else 24, 12 if short else 22)
            self.character_visual_layout.setSpacing(8 if short else 14)
            self._compact_character = short
            self._refresh_character_avatar()
        reading_compact_plan = compact_plan and self.action_list_panel.isHidden()
        self.roadmap_summary.setVisible(
            (not short or self.roadmap_metrics.isHidden()) and not reading_compact_plan)
        self.sidebar_footer.setVisible(rail)
        self.account_summary.setVisible(rail and bool(self._data and self._data.get("snapshotId")))
        self.nav.doItemsLayout()


    def _sync_tool_actions(self):
        for action, button in self._tool_actions:
            action.setEnabled(button.isEnabled())


    def _sync_account_action(self, has_snapshot):
        self.snapshot_button.setText("Cập nhật dữ liệu" if has_snapshot else "Dữ liệu tài khoản")
        self.snapshot_button.setObjectName("ghostButton")
        self.snapshot_button.style().unpolish(self.snapshot_button)
        self.snapshot_button.style().polish(self.snapshot_button)


    def _show_feedback(self, text, *, error=False):
        self.feedback_text.setText(text)
        set_state(self.feedback_banner, "error" if error else "")
        self.retry_button.setVisible(error)
        self.feedback_banner.show()


    def _switch(self, index):
        if 0 <= index < self.pages.count():
            if self.pages.currentIndex() == 4 and index != 4 and self._tier_dirty:
                if not self._confirm_tier_discard("Rời màn điều chỉnh ưu tiên"):
                    self.nav.blockSignals(True)
                    self.nav.setCurrentRow(4)
                    self.nav.blockSignals(False)
                    return
                if self._tier_dirty:
                    self._render_tier_list()
            self.pages.setCurrentIndex(index)
            self.snapshot_button.setVisible(index != 3)
            self.page_title.setText(("Hôm nay", "Kế hoạch", "Nhân vật", "Dữ liệu",
                                     "Điều chỉnh ưu tiên")[index])
            self.page_description.setText((
                getattr(self, "_today_description", "Một việc nên làm tiếp theo cho tài khoản của bạn."),
                "Xem nên nâng cấp gì trước.",
                "Chọn một nhân vật để xem bước nâng cấp phù hợp nhất.",
                "Nhập, kiểm tra và sao lưu dữ liệu tài khoản.",
                "Chọn nhân vật bạn muốn nâng cấp trước.",
            )[index])
            self.page_kicker.setVisible(index == 2 and self.height() >= 700)
            self.page_title.setToolTip(self.page_description.text())


    def _focus_page_search(self):
        search = {1: self.roadmap_search,
                  2: self.character_picker.lineEdit() if self.character_picker.isVisible()
                  else self.character_search,
                  4: self.tier_search}.get(self.pages.currentIndex())
        if search is not None:
            search.setFocus(Qt.FocusReason.ShortcutFocusReason)
            search.selectAll()


    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        self.refresh_button.setEnabled(False)
        self.snapshot_button.setEnabled(False)
        self.good_import_action.setEnabled(False)
        self.target_button.setEnabled(False)
        self.artifact_button.setEnabled(False)
        self.history_button.setEnabled(False)
        self.health_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.backup_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.today_import_button.setEnabled(False)
        self._render_data(self._data or {})
        self._show_feedback("Đang tính kế hoạch từ dữ liệu hiện tại…")
        self._sync_tool_actions()
        self.statusBar().showMessage("Đang tính kế hoạch…")
        worker = OverviewWorker(generation, self.overview_controller)
        worker.signals.loaded.connect(self._loaded)
        worker.signals.failed.connect(self._failed)
        self._workers.append(worker)
        self._pool.start(worker)


    def _loaded(self, generation, data):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.target_button.setEnabled(True)
        self.artifact_button.setEnabled(True)
        self.history_button.setEnabled(True)
        self.health_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self.backup_button.setEnabled(True)
        self.restore_button.setEnabled(True)
        self.today_import_button.setEnabled(True)
        self.feedback_banner.hide()
        self._sync_tool_actions()
        self._data = data
        self._apply_window_layout()

        self._sync_account_action(data.get("snapshotId") is not None)
        imported_at = data.get("snapshotImportedAt")
        if imported_at:
            try:
                self.snapshot_button.setText("Dữ liệu " + datetime.fromisoformat(imported_at).strftime("%d/%m"))
                self.snapshot_button.setToolTip("Cập nhật dữ liệu tài khoản · lần nhập gần nhất " +
                                                datetime.fromisoformat(imported_at).strftime("%d/%m/%Y %H:%M"))
            except ValueError:
                pass
        self.export_results_button.setEnabled(data.get("snapshotId") is not None)
        self.export_results_button.setToolTip("Xuất báo cáo, JSON và mẫu nhận xét" if self.export_results_button.isEnabled() else "Nhập tài khoản và tính kế hoạch để xuất kết quả")
        self._render_today(data)
        self._render_roadmap(data)
        self._render_characters(data)
        self._render_data(data)
        # A background recompute must not erase edits in the Tier List table.
        tier_loaded = True if self._tier_dirty else self._render_tier_list()
        self.statusBar().showMessage(
            ("Đã cập nhật" if tier_loaded else "Kế hoạch đã cập nhật · Tier List chưa tải được")
            + " · " + datetime.now().strftime("%H:%M:%S"))


    def _failed(self, generation, message):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.target_button.setEnabled(True)
        self.artifact_button.setEnabled(True)
        self.history_button.setEnabled(True)
        self.health_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self.backup_button.setEnabled(True)
        self.restore_button.setEnabled(True)
        self.statusBar().showMessage("Chưa cập nhật · đang hiển thị kế hoạch cũ" if self._data else "Không thể tải dữ liệu")
        self.today_import_button.setEnabled(True)
        self._render_data(self._data or {})
        self._sync_tool_actions()
        self._show_feedback(
            ("Không thể cập nhật dữ liệu mới. Đang dùng dữ liệu từ " +
             datetime.fromisoformat(self._data["snapshotImportedAt"]).strftime("%d/%m %H:%M") + ". Thử lại.")
            if self._data and self._data.get("snapshotImportedAt") else
            "Chưa cập nhật được kế hoạch. Đang giữ kết quả trước đó. Bạn có thể thử lại."
            if self._data else "Không thể tải kế hoạch. Kiểm tra dữ liệu hoặc thử lại.", error=True)
        self.feedback_text.setToolTip(message)
        log.warning("Overview refresh failed: %s", message)


