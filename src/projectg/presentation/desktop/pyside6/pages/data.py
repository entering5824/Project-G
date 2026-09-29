"""Local account data hub for the native desktop presentation."""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from projectg.presentation.desktop.pyside6.theme import set_state
from projectg.presentation.desktop.pyside6.glass import BackdropGlassFrame


class DataPage:
    def _make_data(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(8, 8, 8, 16)
        body.setSpacing(16)

        overview = BackdropGlassFrame()
        overview.setObjectName("surfaceCard")
        overview.setMaximumWidth(960)
        self.data_overview = overview
        overview_layout = QVBoxLayout(overview)
        self.data_overview_layout = overview_layout
        overview_layout.setContentsMargins(28, 26, 28, 26)
        overview_layout.setSpacing(12)
        eyebrow = QLabel("Tài khoản trên máy")
        eyebrow.setObjectName("eyebrow")
        overview_layout.addWidget(eyebrow)
        self.data_status = QLabel("Đang đọc dữ liệu tài khoản…")
        self.data_status.setObjectName("headline")
        self.data_status.setWordWrap(True)
        overview_layout.addWidget(self.data_status)
        self.data_summary = QLabel()
        self.data_summary.setObjectName("secondaryText")
        self.data_summary.setWordWrap(True)
        overview_layout.addWidget(self.data_summary)
        self.data_imported_at = QLabel()
        self.data_imported_at.setObjectName("secondaryText")
        self.data_imported_at.setWordWrap(True)
        overview_layout.addWidget(self.data_imported_at)

        import_actions = QHBoxLayout()
        import_actions.setSpacing(10)
        self.data_import_button = QPushButton("Nhập dữ liệu tài khoản")
        self.data_import_button.setObjectName("primaryButton")
        self.data_import_button.setAccessibleName("Nhập dữ liệu tài khoản từ tệp")
        self.data_import_button.clicked.connect(self.import_account_file)
        import_actions.addWidget(self.data_import_button)
        self.data_good_button = QPushButton("Dùng tệp GOOD")
        self.data_good_button.setObjectName("ghostButton")
        self.data_good_button.clicked.connect(self.import_good)
        import_actions.addWidget(self.data_good_button)
        import_actions.addStretch()
        overview_layout.addLayout(import_actions)
        body.addWidget(overview, 0, Qt.AlignmentFlag.AlignHCenter)

        utilities = BackdropGlassFrame()
        utilities.setObjectName("surfaceCard")
        utilities.setMaximumWidth(960)
        self.data_utilities = utilities
        utilities_layout = QVBoxLayout(utilities)
        self.data_utilities_layout = utilities_layout
        utilities_layout.setContentsMargins(28, 22, 28, 24)
        utilities_layout.setSpacing(10)
        utilities_title = QLabel("Kiểm tra và sao lưu")
        utilities_title.setObjectName("section")
        utilities_layout.addWidget(utilities_title)
        utilities_copy = QLabel(
            "Kiểm tra dữ liệu đã nhập hoặc tạo bản sao để khôi phục trên máy này.")
        utilities_copy.setObjectName("secondaryText")
        utilities_copy.setWordWrap(True)
        utilities_layout.addWidget(utilities_copy)
        utility_actions = QHBoxLayout()
        utility_actions.setSpacing(10)
        self.data_health_button = QPushButton("Kiểm tra dữ liệu")
        self.data_health_button.clicked.connect(self.health_button.click)
        utility_actions.addWidget(self.data_health_button)
        self.data_backup_button = QPushButton("Sao lưu")
        self.data_backup_button.clicked.connect(self.backup_button.click)
        utility_actions.addWidget(self.data_backup_button)
        self.data_restore_button = QPushButton("Khôi phục")
        self.data_restore_button.setObjectName("ghostButton")
        self.data_restore_button.clicked.connect(self.restore_button.click)
        utility_actions.addWidget(self.data_restore_button)
        utility_actions.addStretch()
        utilities_layout.addLayout(utility_actions)
        body.addWidget(utilities, 0, Qt.AlignmentFlag.AlignHCenter)
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.data_scroll = scroll
        self.pages.addWidget(page)
        self._render_data({})

    def _size_data_cards(self):
        width = min(960, max(320, self.width() - 58))
        self.data_overview.setFixedWidth(width)
        self.data_utilities.setFixedWidth(width)
        compact = self.height() < 700
        inset = 18 if compact else 28
        self.data_overview_layout.setContentsMargins(inset, 14 if compact else 26,
                                                     inset, 14 if compact else 26)
        self.data_overview_layout.setSpacing(8 if compact else 12)
        self.data_utilities_layout.setContentsMargins(inset, 14 if compact else 22,
                                                      inset, 14 if compact else 24)
        self.data_utilities_layout.setSpacing(7 if compact else 10)

    def _render_data(self, data):
        loading = getattr(self, "_loading", False)
        has_snapshot = data.get("snapshotId") is not None
        count = len(data.get("characters") or [])
        self.data_status.setText(
            "Dữ liệu đã sẵn sàng" if has_snapshot and count else
            "Chưa có nhân vật trong dữ liệu" if has_snapshot else
            "Chưa có dữ liệu tài khoản")
        self.data_summary.setText(
            f"{count} nhân vật đã được nhập. Project G có thể dùng dữ liệu này để đề xuất bước nâng cấp."
            if has_snapshot and count else
            "Tài khoản đã được nhập nhưng chưa có nhân vật để lập kế hoạch. Kiểm tra dữ liệu hoặc nhập lại."
            if has_snapshot else
            "Nhập Account Snapshot hoặc tệp GOOD để nhận đề xuất nâng cấp đầu tiên.")
        imported_at = data.get("snapshotImportedAt")
        try:
            imported_label = datetime.fromisoformat(str(imported_at)).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            imported_label = "Chưa rõ thời điểm"
        self.data_imported_at.setText(
            f"Lần nhập gần nhất: {imported_label}" if has_snapshot
            else "Dữ liệu chỉ lưu trên máy của bạn")
        set_state(self.data_imported_at, "success" if has_snapshot else "")
        self.data_import_button.setText("Nhập dữ liệu mới" if has_snapshot and count
                                        else "Nhập lại dữ liệu" if has_snapshot
                                        else "Nhập dữ liệu tài khoản")
        self.data_import_button.setEnabled(not loading)
        self.data_good_button.setEnabled(not loading)
        self.data_health_button.setEnabled(has_snapshot and not loading)
        self.data_backup_button.setEnabled(has_snapshot and not loading)
        self.data_restore_button.setEnabled(not loading)
