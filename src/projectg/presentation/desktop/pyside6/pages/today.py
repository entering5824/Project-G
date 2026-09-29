"""Native desktop presentation: pages/today."""
from datetime import date
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget, QScrollArea
from projectg.presentation.desktop.pyside6.theme import set_state
from projectg.presentation.desktop.pyside6.responsive_grid import ResponsiveCardGrid
from projectg.presentation.desktop.pyside6.assets import get_character_pixmap
from projectg.presentation.desktop.pyside6.glass import SmokedGlassFrame
from projectg.presentation.desktop.pyside6.goal_copy import today_action_copy, today_display_title
from projectg.presentation.desktop.pyside6.action_queue import ActionQueueModel


class TodayPage:
    def eventFilter(self, obj, event):
        if obj is getattr(self, "today_hero_card", None):
            if event.type() == QEvent.Type.DragEnter:
                urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
                if len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith(".json"):
                    event.acceptProposedAction()
                    return True
            if event.type() == QEvent.Type.Drop:
                urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
                if len(urls) == 1 and urls[0].isLocalFile():
                    self.import_account_path(urls[0].toLocalFile())
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

    def _make_today(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(12)


        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        body = QVBoxLayout(container)
        body.setContentsMargins(0, 0, 6, 0)
        body.setSpacing(14)

        # 1. Hero Action Card
        hero_card = SmokedGlassFrame()
        hero_card.setMaximumWidth(920)
        hero_card.setAcceptDrops(True)
        hero_card.installEventFilter(self)
        self.today_hero_card = hero_card
        hero_card.setObjectName("primary")
        hero_layout = QVBoxLayout(hero_card)
        self.today_hero_layout = hero_layout
        hero_layout.setContentsMargins(28, 28, 28, 24)
        hero_layout.setSpacing(18)
        hero_main = QHBoxLayout()
        self.today_hero_main = hero_main
        hero_main.setSpacing(18)

        self.today_avatar = QLabel()
        self.today_avatar.setFixedSize(144, 144)
        self.today_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.today_avatar.setObjectName("characterPortrait")

        hero_center = QVBoxLayout()
        hero_center.setSpacing(6)
        eyebrow_row = QHBoxLayout()
        self.today_eyebrow = QLabel("NÊN LÀM TIẾP")
        self.today_eyebrow.setObjectName("eyebrow")
        self.today_eyebrow.setWordWrap(True)
        eyebrow_row.addWidget(self.today_eyebrow, 1)

        self.today_badge = QLabel("")
        self.today_badge.setWordWrap(True)
        self.today_badge.setObjectName("badge")
        eyebrow_row.addWidget(self.today_badge)
        eyebrow_row.addStretch()
        hero_center.addLayout(eyebrow_row)

        self.today_title = QLabel("Đang tính kế hoạch…")
        self.today_title.setObjectName("headline")
        self.today_title.setWordWrap(True)
        hero_center.addWidget(self.today_title)

        self.today_action = QLabel("")
        self.today_action.setObjectName("todayAction")
        self.today_action.setWordWrap(True)
        hero_center.addWidget(self.today_action)

        self.today_why = QLabel("")
        self.today_why.setObjectName("secondaryText")
        self.today_why.setWordWrap(True)
        hero_center.addWidget(self.today_why)

        self.today_setup_target = QPushButton("Thiết lập mục tiêu đầu tiên")
        self.today_setup_target.setObjectName("primaryButton")
        self.today_setup_target.clicked.connect(self.open_target_editor)
        self.today_setup_target.setVisible(False)
        hero_center.addWidget(self.today_setup_target)
        self.today_import_button = QPushButton("Nhập dữ liệu tài khoản")
        self.today_import_button.setObjectName("primaryButton")
        self.today_import_button.clicked.connect(self.snapshot_button.click)
        self.today_import_button.hide()
        hero_center.addWidget(self.today_import_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.today_good_button = QPushButton("Dùng tệp GOOD")
        self.today_good_button.setObjectName("ghostButton")
        self.today_good_button.clicked.connect(self.import_good)
        self.today_good_button.hide()
        hero_center.addWidget(self.today_good_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.today_rank_button = QPushButton("Điều chỉnh ưu tiên")
        self.today_rank_button.setObjectName("primaryButton")
        self.today_rank_button.clicked.connect(lambda: self.nav.setCurrentRow(3))
        self.today_rank_button.hide()
        hero_center.addWidget(self.today_rank_button, 0, Qt.AlignmentFlag.AlignLeft)

        hero_main.addLayout(hero_center, 1)
        hero_main.addWidget(self.today_avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        hero_layout.addLayout(hero_main)

        hero_facts = ResponsiveCardGrid(180, 2)

        self.today_resin_badge = QLabel("")
        self.today_resin_badge.setObjectName("fact")
        self.today_resin_badge.setWordWrap(True)
        # The availability fact is the one visible on the primary journey.
        # Keep it in the first column even when resin is intentionally hidden.

        self.today_avail_badge = QLabel("")
        self.today_avail_badge.setObjectName("fact")
        self.today_avail_badge.setWordWrap(True)
        hero_facts.add_card(self.today_avail_badge)
        hero_facts.add_card(self.today_resin_badge)

        self.today_facts = hero_facts
        hero_layout.addWidget(self.today_facts)
        self.today_facts.hide()

        self.today_source_label = QLabel("")
        self.today_source_label.setObjectName("sourceDetail")
        self.today_source_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.today_source_label.setWordWrap(True)
        journey = QHBoxLayout()
        self.today_roadmap_button = QPushButton("Xem cách làm")
        self.today_roadmap_button.setObjectName("ghostButton")
        self.today_roadmap_button.clicked.connect(lambda: self._open_today_inspector(
            getattr(self, "_primary_today_task", None)))
        self.today_characters_button = QPushButton("Xem nhân vật")
        self.today_characters_button.setObjectName("ghostButton")
        self.today_characters_button.clicked.connect(self._show_today_character)
        journey.addWidget(self.today_roadmap_button)
        journey.addWidget(self.today_characters_button)
        journey.addStretch()
        hero_layout.addLayout(journey)
        body.addWidget(hero_card)
        body.setAlignment(hero_card, Qt.AlignmentFlag.AlignHCenter)

        self.today_waiting_alt = QFrame()
        self.today_waiting_alt.setMaximumWidth(920)
        self.today_waiting_alt.setObjectName("alternativeCard")
        alt_hint_layout = QHBoxLayout(self.today_waiting_alt)
        alt_hint_layout.setContentsMargins(18, 14, 18, 14)
        alt_hint_layout.setSpacing(12)
        alt_hint_copy = QVBoxLayout()
        alt_hint_copy.setSpacing(4)
        alt_kicker = QLabel("TRONG LÚC CHỜ")
        alt_kicker.setObjectName("eyebrow")
        alt_hint_copy.addWidget(alt_kicker)
        self.today_waiting_alt_title = QLabel()
        self.today_waiting_alt_title.setObjectName("section")
        self.today_waiting_alt_title.setWordWrap(True)
        alt_hint_copy.addWidget(self.today_waiting_alt_title)
        self.today_waiting_alt_action = QLabel()
        self.today_waiting_alt_action.setObjectName("secondaryText")
        self.today_waiting_alt_action.setWordWrap(True)
        alt_hint_copy.addWidget(self.today_waiting_alt_action)
        alt_hint_layout.addLayout(alt_hint_copy, 1)
        self.today_waiting_alt_button = QPushButton("Xem cách làm")
        self.today_waiting_alt_button.setObjectName("primaryButton")
        self.today_waiting_alt_button.clicked.connect(lambda: self._open_today_inspector(
            getattr(self, "_waiting_alternative", None)))
        alt_hint_layout.addWidget(self.today_waiting_alt_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.today_waiting_alt.hide()
        body.addWidget(self.today_waiting_alt)
        body.setAlignment(self.today_waiting_alt, Qt.AlignmentFlag.AlignHCenter)

        self.today_onboarding = QFrame()
        self.today_onboarding.setObjectName("onboarding")
        onboarding_layout = QVBoxLayout(self.today_onboarding)
        onboarding_layout.setContentsMargins(18, 16, 18, 18)
        onboarding_layout.setSpacing(12)
        onboarding_heading = QLabel("BẮT ĐẦU VỚI PROJECT G")
        onboarding_heading.setObjectName("eyebrow")
        onboarding_layout.addWidget(onboarding_heading)
        steps = ResponsiveCardGrid(170, 3)
        for number, title, description in (
            ("01", "Nhập tài khoản", "Chọn tệp dữ liệu nhân vật của bạn."),
            ("02", "Xếp ưu tiên", "Chọn hạng cho nhân vật bạn muốn đầu tư."),
            ("03", "Xem kế hoạch", "Theo dõi việc tiếp theo và lộ trình nâng cấp."),
        ):
            step = QFrame()
            step.setObjectName("onboardingStep")
            step_layout = QVBoxLayout(step)
            step_layout.setContentsMargins(14, 12, 14, 12)
            step_layout.setSpacing(5)
            number_label = QLabel(number)
            number_label.setObjectName("stepNumber")
            title_label = QLabel(title)
            title_label.setObjectName("stepTitle")
            description_label = QLabel(description)
            description_label.setObjectName("secondaryText")
            description_label.setWordWrap(True)
            step_layout.addWidget(number_label)
            step_layout.addWidget(title_label)
            step_layout.addWidget(description_label)
            steps.add_card(step)
        onboarding_layout.addWidget(steps)
        self.today_onboarding.hide()
        body.addWidget(self.today_onboarding)

        # Optional details are shown only when requested.
        self.today_details_button = QPushButton("Tại sao Project G đề xuất bước này? ›")
        self.today_details_button.setToolTip("Thông tin tài khoản và các phương án thay thế")
        self.today_details_button.setObjectName("ghostButton")
        self.today_details_button.setCheckable(True)
        body.addWidget(self.today_details_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.today_details_panel = QWidget()
        bottom_row = ResponsiveCardGrid(200, 2)
        details_layout = QVBoxLayout(self.today_details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        source_heading = QLabel("NGUỒN THỰC HIỆN")
        source_heading.setObjectName("eyebrow")
        details_layout.addWidget(source_heading)
        details_layout.addWidget(self.today_source_label)
        self.today_action_detail = QLabel("")
        self.today_action_detail.setObjectName("secondaryText")
        self.today_action_detail.setWordWrap(True)
        details_layout.addWidget(self.today_action_detail)
        hero_center.removeWidget(self.today_why)
        details_layout.addWidget(self.today_why)
        details_layout.addWidget(bottom_row)
        bottom_row.hide()
        self.today_details_panel.hide()
        self.today_details_button.toggled.connect(self.today_details_panel.setVisible)

        info_card = QFrame()
        info_card.setObjectName("surfaceCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(8)
        info_title = QLabel("Thông tin tài khoản & kế hoạch")
        info_title.setObjectName("secondaryText")
        info_title.setWordWrap(True)
        info_layout.addWidget(info_title)
        self.today_meta_info = QLabel("Đang chờ dữ liệu…")
        self.today_meta_info.setObjectName("secondaryText")
        self.today_meta_info.setWordWrap(True)
        info_layout.addWidget(self.today_meta_info)
        info_layout.addStretch()
        bottom_row.add_card(info_card)

        alt_card = QFrame()
        alt_card.setObjectName("surfaceCard")
        alt_layout = QVBoxLayout(alt_card)
        alt_layout.setContentsMargins(16, 14, 16, 14)
        alt_layout.setSpacing(8)
        alt_title = QLabel("Phương án thay thế")
        alt_title.setObjectName("secondaryText")
        alt_title.setWordWrap(True)
        alt_layout.addWidget(alt_title)
        self.today_alternatives_list = QListWidget()
        self.today_alternatives_list.setFixedHeight(120)
        alt_layout.addWidget(self.today_alternatives_list)
        bottom_row.add_card(alt_card)

        body.addWidget(self.today_details_panel)

        # Retain hidden QTextEdit for backward-compatible access
        self.today_context = QTextEdit()
        self.today_context.setReadOnly(True)
        self.today_context.setVisible(False)
        body.addWidget(self.today_context)

        body.addStretch()
        scroll.setWidget(container)
        self.today_scroll = scroll
        self.today_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.today_splitter.addWidget(scroll)
        self.today_inspector = QFrame()
        self.today_inspector.setObjectName("surfaceCard")
        inspector_layout = QVBoxLayout(self.today_inspector)
        inspector_layout.setContentsMargins(24, 24, 24, 24)
        self.today_inspector_back = QPushButton("← Hôm nay")
        self.today_inspector_back.setObjectName("ghostButton")
        self.today_inspector_back.clicked.connect(self._close_today_inspector)
        inspector_layout.addWidget(self.today_inspector_back, 0, Qt.AlignmentFlag.AlignLeft)
        self.today_inspector_title = QLabel()
        self.today_inspector_title.setObjectName("section")
        self.today_inspector_title.setWordWrap(True)
        inspector_layout.addWidget(self.today_inspector_title)
        self.today_inspector_status = QLabel()
        self.today_inspector_status.setObjectName("actionStatus")
        self.today_inspector_status.setWordWrap(True)
        inspector_layout.addWidget(self.today_inspector_status)
        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setFrameShape(QFrame.Shape.NoFrame)
        inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inspector_content = QWidget()
        inspector_content_layout = QVBoxLayout(inspector_content)
        inspector_content_layout.setContentsMargins(0, 12, 4, 0)
        inspector_content_layout.setSpacing(16)
        self.today_inspector_body = QLabel()
        self.today_inspector_body.setObjectName("secondaryText")
        self.today_inspector_body.setWordWrap(True)
        self.today_inspector_body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        inspector_content_layout.addWidget(self.today_inspector_body)
        self.today_inspector_plan = QPushButton("Mở trong Kế hoạch")
        self.today_inspector_plan.clicked.connect(lambda: self._show_task_in_roadmap(
            getattr(self, "_inspected_today_task", None)))
        inspector_content_layout.addWidget(self.today_inspector_plan, 0, Qt.AlignmentFlag.AlignLeft)
        inspector_content_layout.addStretch()
        inspector_scroll.setWidget(inspector_content)
        inspector_layout.addWidget(inspector_scroll, 1)
        self.today_splitter.addWidget(self.today_inspector)
        self.today_splitter.setStretchFactor(0, 3)
        self.today_splitter.setStretchFactor(1, 2)
        self.today_splitter.setSizes([650, 360])
        self.today_inspector.hide()
        page_layout.addWidget(self.today_splitter, 1)
        self.pages.addWidget(page)


    def _open_today_inspector(self, task):
        if not task:
            return
        self._inspected_today_task = task
        self.today_inspector_title.setText(today_display_title(task))
        source = task.get("source") or {}
        lines = []
        if source.get("name"):
            lines.append("Nguồn: " + source["name"])
        if task.get("availableWeekdays"):
            lines.append("Mở: " + " · ".join(task["availableWeekdays"]))
        resin_cost = source.get("resinCost", source.get("resin_cost"))
        if resin_cost is not None:
            lines.append(f"Tốn khoảng {resin_cost} Nhựa/lượt")
        availability = task.get("availability")
        if availability == "UNAVAILABLE_TODAY" and task.get("nextAvailableDate"):
            try:
                status_text = "Mở lại " + date.fromisoformat(str(task["nextAvailableDate"])).strftime("%d/%m")
            except ValueError:
                status_text = "Chưa mở hôm nay"
        elif availability == "UNAVAILABLE_TODAY":
            status_text = "Chưa mở hôm nay"
        elif availability in {"AVAILABLE", "ALWAYS_AVAILABLE"}:
            status_text = "Làm được ngay"
        elif availability == "PREREQUISITE_BLOCKED":
            status_text = "Cần hoàn thành bước trước"
        else:
            status_text = "Xem điều kiện"
        self.today_inspector_status.setText(status_text)
        set_state(self.today_inspector_status,
                  "success" if availability in {"AVAILABLE", "ALWAYS_AVAILABLE"} else
                  "warning" if availability in {"UNAVAILABLE_TODAY", "PREREQUISITE_BLOCKED"} else "accent")
        if task.get("whySummary"):
            lines.append("Vì sao bước này? " + task["whySummary"])
        self.today_inspector_body.setText("\n\n".join(lines) or "Xem bước này trong Kế hoạch để biết thêm chi tiết.")
        self.today_inspector_back.setVisible(self.width() < 1060)
        self.today_inspector.show()
        self._size_today_cards()
        if self.width() < 1060:
            self.today_scroll.hide()


    def _close_today_inspector(self):
        self.today_inspector.hide()
        self.today_scroll.show()
        self._size_today_cards()


    def _size_today_cards(self):
        available = self.width() - 60
        if not self.today_inspector.isHidden() and self.width() >= 1060:
            available = int(available * 0.6) - 30
        width = min(920, max(320, available))
        self.today_hero_card.setFixedWidth(width)
        self.today_waiting_alt.setFixedWidth(width)
        compact = self.height() < 700
        portrait_size = 104 if compact else 144
        if self.today_avatar.width() != portrait_size:
            self.today_avatar.setFixedSize(portrait_size, portrait_size)
            key = getattr(self, "_today_avatar_key", "")
            if key:
                self.today_avatar.setPixmap(get_character_pixmap(
                    key, portrait_size, device_pixel_ratio=self.devicePixelRatioF()))
        self.today_hero_main.setSpacing(10 if compact else 18)
        self.today_hero_layout.setSpacing(10 if compact else 18)
        waiting = self.today_hero_card.objectName() == "surfaceCard"
        inset = 16 if compact else 20 if waiting else 28
        self.today_hero_layout.setContentsMargins(inset, 14 if compact else 18 if waiting else 28,
                                                 inset, 14 if compact else 18 if waiting else 24)


    def _render_today(self, data):
        self._close_today_inspector()
        self._today_avatar_key = ""
        self._set_today_description("Một việc nên làm tiếp theo cho tài khoản của bạn.")
        self._waiting_alternative = None
        self.today_waiting_alt.hide()
        self.today_roadmap_button.hide()
        self.today_characters_button.hide()
        self.today_eyebrow.setText("NÊN LÀM TIẾP")
        self.today_hero_layout.setContentsMargins(28, 28, 28, 24)
        self.today_hero_card.setObjectName("primary")
        self.today_hero_card.style().unpolish(self.today_hero_card)
        self.today_hero_card.style().polish(self.today_hero_card)
        self.today_action.show()
        self.today_avatar.show()
        self.today_import_button.hide()
        self.today_good_button.hide()
        self.today_import_button.setText("Nhập dữ liệu tài khoản")
        self.today_rank_button.hide()
        self.today_onboarding.hide()
        self.today_details_button.hide()
        self.today_details_panel.hide()
        self.today_details_button.setChecked(False)
        self.today_facts.hide()
        self.today_resin_badge.hide()
        self.today_action_detail.clear()
        for label in (self.today_badge, self.today_avail_badge, self.today_resin_badge):
            set_state(label, "")
        plan = data["today"]
        if plan is None:
            self._set_today_description("Nhập dữ liệu tài khoản để nhận việc nâng cấp nên làm tiếp.")
            self.today_setup_target.setVisible(False)
            self._primary_today_task = None
            self.today_title.setText("Bắt đầu với dữ liệu tài khoản")
            self.today_eyebrow.setText("BẮT ĐẦU")
            self.today_import_button.show()
            self.today_good_button.show()
            self.today_onboarding.hide()
            self.today_import_button.setEnabled(not self._loading)
            self.today_action.setText("Chọn hoặc thả tệp JSON chứa dữ liệu tài khoản. Project G sẽ tìm việc nâng cấp đáng làm tiếp theo. Dữ liệu chỉ lưu trên máy.")
            self.today_why.setText("")
            self.today_badge.clear()
            self.today_avatar.hide()
            self.today_resin_badge.clear()
            self.today_avail_badge.setText("Khả dụng: chưa có dữ liệu")
            self.today_source_label.setText("")
            self.today_action_detail.clear()
            self.today_meta_info.setText("Chưa có dữ liệu.")
            self.today_alternatives_list.clear()
            self.today_context.clear()
            return

        task = plan.get("primaryTask")

        if task is None:
            self._primary_today_task = None
            reason = plan.get("noActionReason") or "NO_STRATEGIC_GOAL"
            missing_targets = int((plan.get("coverage") or {}).get("missingTargets") or 0)
            missing_profiles = int((plan.get("coverage") or {}).get("missingProfiles") or 0)
            knowledge_ready = bool((plan.get("coverage") or {}).get("buildKnowledgeReady", True))
            needs_target = reason == "NO_STRATEGIC_GOAL" and missing_targets > 0
            needs_knowledge = reason == "NO_STRATEGIC_GOAL" and (missing_profiles > 0 or not knowledge_ready)
            messages = {
                "PINNED_CHARACTER_NO_TASK": "Nhân vật đang ghim chưa có việc trực tiếp có thể đề xuất.",
                "STRATEGIC_CHARACTER_NO_TASK": "Ưu tiên chiến lược hiện tại chưa có việc trực tiếp có thể đề xuất.",
                "NO_STRATEGIC_GOAL": (f"Cần cập nhật dữ liệu của {missing_targets} nhân vật để lập kế hoạch."
                                       if needs_target else f"Chưa có hướng nâng cấp cho {missing_profiles} nhân vật. Hãy cập nhật dữ liệu build."
                                       if needs_knowledge else "Các mục tiêu hiện tại đã hoàn thành."),
            }
            self.today_title.setText("Thiếu hướng nâng cấp" if needs_knowledge else "Chưa có việc cần làm")
            self._set_today_description("Cập nhật dữ liệu tài khoản để Project G tìm bước tiếp theo.")
            self.today_action.setText(messages.get(reason, "Chưa có hành động trực tiếp."))
            self.today_why.setText("Mục tiêu không có việc còn thiếu sẽ tự được loại khỏi kế hoạch." if not needs_target else "")
            self.today_setup_target.setVisible(False)
            self.today_rank_button.hide()
            if needs_target:
                self.today_import_button.setText("Cập nhật tài khoản")
                self.today_import_button.show()
            self.today_badge.setText("CHƯA CÓ HÀNH ĐỘNG")
            self.today_avatar.hide()
            self.today_resin_badge.clear()
            self.today_avail_badge.setText("Khả dụng: chưa có dữ liệu")
            self.today_source_label.setText("")

            # Alternatives
            self.today_alternatives_list.clear()
            alternatives = plan.get("alternativeTasks") or []
            for alt in alternatives:
                item = QListWidgetItem(f"• {alt.get('title', alt.get('id', 'task'))}")
                self.today_alternatives_list.addItem(item)

            meta_lines = [f"Nhân vật đã có hướng nâng cấp: {int((plan.get('coverage') or {}).get('configuredTargets') or 0)}"]
            self.today_meta_info.setText("\n".join(meta_lines))
            self.today_context.setPlainText("\n".join(meta_lines))
            theater = ((data.get("roadmap") or {}).get("theaterPreparation") or {})
            config = theater.get("config") or {}
            if config.get("elements"):
                ready = sum(1 for key in theater.get("selectedKeys", [])
                            if (theater.get("readiness", {}).get(key) or {}).get("status") == "READY")
                self.today_context.append(
                    f"Chuẩn bị Nhà Hát: {ready}/{int(config.get('requiredCharacters', 0))} nhân vật đạt chuẩn build đã biết.")
            return

        self._primary_today_task = task
        self.today_details_button.show()
        self.today_facts.show()
        self.today_setup_target.setVisible(False)

        character = task.get("character") or {}
        char_name = character.get("name") or character.get("key")
        char_key = character.get("key") or char_name or ""
        self._today_avatar_key = char_key
        portrait_size = self.today_avatar.width()
        self.today_avatar.setPixmap(get_character_pixmap(
            char_key, portrait_size, device_pixel_ratio=self.devicePixelRatioF()))
        self.today_avatar.setVisible(bool(char_key))
        self.today_roadmap_button.setVisible(bool(char_key))
        self.today_characters_button.setVisible(bool(char_key))

        title_text = today_display_title(task)
        self.today_title.setText(title_text)

        raw_action = task.get("actionText") or task.get("summary") or title_text
        action_text = title_text if raw_action == task.get("title") else today_action_copy(raw_action)
        why_summary = task.get("whySummary") or "Theo thứ tự ưu tiên chiến lược hiện tại."

        friendly_action = {
            "WEAPON_LEVEL": "Thu thập vật phẩm để nâng vũ khí.",
            "CHARACTER_LEVEL": "Thu thập vật phẩm để nâng cấp nhân vật.",
            "CHARACTER_ASCENSION": "Thu thập vật phẩm để đột phá nhân vật.",
            "TALENT_AUTO": "Thu thập vật phẩm để nâng thiên phú.",
            "TALENT_SKILL": "Thu thập vật phẩm để nâng thiên phú.",
            "TALENT_BURST": "Thu thập vật phẩm để nâng thiên phú.",
        }.get(task.get("goalType"), "")
        if not friendly_action and char_name and ";" in action_text:
            friendly_action = "Thu thập vật phẩm cần cho bước nâng này."
        self.today_action.setText(friendly_action or (action_text if action_text != title_text else ""))
        self.today_action.setVisible(bool(self.today_action.text()))
        self.today_why.setText(f"Vì sao: {why_summary}")
        self.today_action_detail.setText(action_text if action_text != title_text else "")

        # Action Badge
        waiting = task.get("availability") in {"UNAVAILABLE_TODAY", "PREREQUISITE_BLOCKED"}
        self.today_hero_card.setObjectName("surfaceCard" if waiting else "primary")
        self.today_hero_card.style().unpolish(self.today_hero_card)
        self.today_hero_card.style().polish(self.today_hero_card)
        self.today_avatar.setVisible(bool(char_key))
        self.today_action.setVisible(bool(self.today_action.text()) and not waiting)
        compact = self.height() < 700
        inset = 16 if compact else 20 if waiting else 28
        self.today_hero_layout.setContentsMargins(inset, 14 if compact else 18 if waiting else 28,
                                                 inset, 14 if compact else 18 if waiting else 24)
        self.today_eyebrow.setText("NÊN LÀM TIẾP")
        self.today_badge.setText("CHƯA MỞ HÔM NAY" if waiting else "LÀM ĐƯỢC NGAY")
        self.today_badge.setObjectName("badge")
        set_state(self.today_badge, "warning" if waiting else "accent")

        # Resin & Availability Badges
        source = task.get("source") or {}
        resin_cost = source.get("resinCost", source.get("resin_cost"))
        self.today_resin_badge.clear()
        self.today_resin_badge.hide()

        avail_labels = {
            "AVAILABLE": "Làm được ngay",
            "PREREQUISITE_BLOCKED": "Cần hoàn thành bước tiên quyết",
            "ALWAYS_AVAILABLE": "Làm được ngay",
            "UNAVAILABLE_TODAY": "Chưa mở hôm nay",
            "WEEKLY_LIMITED": "Giới hạn tuần",
        }
        avail_str = avail_labels.get(task.get("availability"), task.get("availability") or "-")
        next_date = task.get("nextAvailableDate")
        if task.get("availability") == "UNAVAILABLE_TODAY" and next_date:
            try:
                avail_str += " · Mở lại " + date.fromisoformat(str(next_date)).strftime("%d/%m")
            except ValueError:
                pass
        self.today_avail_badge.setText(avail_str)
        if task.get("availability") in {"UNAVAILABLE_TODAY", "PREREQUISITE_BLOCKED"}:
            self.today_avail_badge.setObjectName("fact")
            set_state(self.today_avail_badge, "warning")
        elif task.get("availability") in {"AVAILABLE", "ALWAYS_AVAILABLE"}:
            self.today_avail_badge.setObjectName("fact")
            set_state(self.today_avail_badge, "success")

        if waiting:
            self._set_today_description("Ưu tiên chính đang chờ; xem điều kiện và ngày khả dụng.")
            actionable = [*plan.get("quickActions", []), *plan.get("farming", [])]
            alternative = next((candidate for candidate in (plan.get("alternativeTasks") or [])
                                if candidate in actionable and candidate is not task), None)
            if alternative is not None:
                self._waiting_alternative = alternative
                self.today_waiting_alt_title.setText(today_display_title(alternative))
                self.today_waiting_alt_action.setText(today_action_copy(alternative.get("actionText") or ""))
                self.today_waiting_alt_button.setVisible(True)
                self.today_waiting_alt.show()
                self._set_today_description("Có việc khác làm được trong lúc ưu tiên chính đang chờ.")

        source_name = source.get("name") or source.get("key") or ""
        if task.get("availableWeekdays"):
            source_name += f" ({', '.join(task['availableWeekdays'])})"
        methods = task.get("farmMethods") or []
        method_names = list(dict.fromkeys((method.get("source") or {}).get("name")
                                         for method in methods if (method.get("source") or {}).get("name")))
        self.today_source_label.setText(" · ".join(method_names) or source_name)

        # Metadata Card
        account_settings = plan.get("accountSettings") or {}
        wl = account_settings.get("worldLevel", "?")
        srv = plan.get("serverRegion", "ASIA")
        state = plan.get("todayState") or {}
        pinned_text = state.get("pinnedCharacterKey") or "Không có"
        if state.get("pinnedCharacterKey"):
            pinned_text += f" ({state.get('pinStatus')})"

        dec_labels = {"STRATEGIC": "Ưu tiên chiến lược", "PINNED": "Theo nhân vật ghim", "FALLBACK": "Phương án tốt nhất"}
        dec_mode = dec_labels.get(plan.get("decisionMode"), plan.get("decisionMode") or "-")

        meta_rows = [
            f"• Cấp thế giới: <b>{wl}</b>",
            f"• Máy chủ: <b>{srv}</b>",
            f"• Nhân vật ghim: <b>{pinned_text}</b>",
        ]
        if task.get("dependsOn"):
            meta_rows.append(f"• Cần làm trước: {' · '.join(task['dependsOn'])}")
        self.today_meta_info.setText("<br>".join(meta_rows))

        # Alternatives
        self.today_alternatives_list.clear()
        alternatives = plan.get("alternativeTasks") or []
        if alternatives:
            for alt in alternatives:
                item = QListWidgetItem(alt.get('title', alt.get('id', 'task')))
                self.today_alternatives_list.addItem(item)
        else:
            self.today_alternatives_list.addItem(QListWidgetItem("Không có phương án thay thế khả dụng."))

        # Retain plain text in hidden today_context
        lines = [
            f"Hành động đề xuất: {action_text}", f"Chi phí ước tính: {task.get('requiredCost') or {}}", f"Vì sao: {why_summary}",
            f"Khả dụng: {avail_str}", f"Điểm ưu tiên: {task.get('score', 0):.1f}"
        ]
        self.today_context.setPlainText("\n".join(lines))


    def _show_today_in_roadmap(self):
        self._show_task_in_roadmap(getattr(self, "_primary_today_task", None))


    def _set_today_description(self, description):
        self._today_description = description
        if self.pages.currentIndex() == 0:
            self.page_description.setText(description)
            self.page_title.setToolTip(description)


    def _show_today_character(self):
        self.nav.setCurrentRow(2)
        task = getattr(self, "_primary_today_task", None) or {}
        key = (task.get("character") or {}).get("key")
        if not key:
            return
        for index in range(self.character_list.count()):
            item = self.character_list.item(index)
            if item.text() == key:
                if item.isHidden():
                    self.character_search.clear()
                self.character_list.setCurrentRow(index)
                self.character_list.scrollToItem(item)
                break


    def _show_alternative_in_roadmap(self):
        self._show_task_in_roadmap(getattr(self, "_waiting_alternative", None))


    def _show_task_in_roadmap(self, task):
        self.nav.setCurrentRow(1)
        task = task or {}
        character_key = (task.get("character") or {}).get("key")
        goal_key = (task.get("primaryGoal") or {}).get("goalKey")
        title = task.get("title") or ""
        if not character_key and not goal_key:
            return
        fallback = None
        for index in range(self.roadmap_tree.topLevelItemCount()):
            item = self.roadmap_tree.topLevelItem(index)
            if goal_key and item.data(1, Qt.ItemDataRole.UserRole) == goal_key:
                fallback = item
                break
            if character_key and item.data(0, Qt.ItemDataRole.UserRole) == character_key:
                if fallback is None or title and title in item.text(1):
                    fallback = item
                if title and title in item.text(1):
                    break
        if fallback is not None:
            if fallback.isHidden():
                self.roadmap_search.clear()
                self.roadmap_filter.setCurrentIndex(0)
            self.roadmap_tree.setCurrentItem(fallback)
            self.roadmap_tree.scrollToItem(fallback)
        for row in range(self.action_queue_filter.rowCount()):
            index = self.action_queue_filter.index(row, 0)
            goal = index.data(ActionQueueModel.GoalRole) or {}
            if (goal_key and goal.get("goalKey") == goal_key or
                    not goal_key and (goal.get("character") or {}).get("key") == character_key):
                self.action_queue.setCurrentIndex(index)
                self.action_queue.scrollTo(index)
                self._show_action_detail(index)
                break


