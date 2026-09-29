"""Native desktop presentation: pages/characters."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QScrollArea, QProgressBar
from projectg.presentation.desktop.pyside6.theme import set_state
from projectg.presentation.desktop.pyside6.responsive_grid import ResponsiveCardGrid
from projectg.presentation.desktop.pyside6.assets import get_character_pixmap, get_weapon_pixmap
from projectg.presentation.desktop.pyside6.glass import SmokedGlassFrame
from projectg.presentation.desktop.pyside6.empty_state import EmptyState
from projectg.presentation.desktop.pyside6.goal_copy import goal_display_title


class CharactersPage:
    def _make_characters(self):
        page = QWidget()
        page.setObjectName("characterPage")
        body = QVBoxLayout(page)
        body.setSpacing(12)

        self.character_picker = QComboBox()
        self.character_picker.setEditable(True)
        self.character_picker.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.character_picker.setAccessibleName("Chọn nhân vật")
        self.character_picker.setPlaceholderText("Tìm nhân vật…")
        self.character_picker.currentIndexChanged.connect(self.character_list_row_from_picker)
        self.character_picker.hide()
        body.addWidget(self.character_picker)


        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Search + Character List
        left_panel = QWidget()
        self.character_left_panel = left_panel
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        roster_label = QLabel("NHÂN VẬT TRONG TÀI KHOẢN")
        roster_label.setObjectName("eyebrow")
        self.roster_label = roster_label
        left_layout.addWidget(roster_label)

        self.character_search = QLineEdit()
        self.character_search.setClearButtonEnabled(True)
        self.character_search.setAccessibleName("Tìm nhân vật")
        self.character_search.setToolTip("Tìm trong màn hình hiện tại · Ctrl+F")
        self.character_search.setPlaceholderText("Tìm nhân vật…")
        self.character_search.textChanged.connect(self._filter_characters)
        left_layout.addWidget(self.character_search)

        self.character_list = QListWidget()
        self.character_list.setObjectName("characterList")
        self.character_list.setSpacing(4)
        self.character_list.setUniformItemSizes(True)
        self.character_list.currentRowChanged.connect(self._show_character)
        left_layout.addWidget(self.character_list, 1)
        self.character_search_feedback = QLabel()
        self.character_search_feedback.setObjectName("searchFeedback")
        self.character_search_feedback.setWordWrap(True)
        left_layout.addWidget(self.character_search_feedback)

        splitter.addWidget(left_panel)

        # Right Panel: Tabs (Visual Dashboard + Raw Text)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        char_tabs = QTabWidget()

        # Tab 1: Visual Dashboard
        visual_scroll = QScrollArea()
        visual_scroll.setWidgetResizable(True)
        visual_scroll.setFrameShape(QFrame.Shape.NoFrame)
        visual_container = QWidget()
        visual_layout = QVBoxLayout(visual_container)
        self.character_visual_layout = visual_layout
        visual_layout.setContentsMargins(4, 4, 8, 4)
        visual_layout.setSpacing(14)

        # Character Header Card
        header_card = SmokedGlassFrame()
        header_card.setObjectName("primary")
        header_layout = QHBoxLayout(header_card)
        self.character_header_layout = header_layout
        header_layout.setContentsMargins(24, 22, 24, 22)
        header_layout.setSpacing(16)

        self.char_avatar = QLabel()
        self.char_avatar.setFixedSize(104, 104)
        self.char_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.char_avatar)

        header_info = QVBoxLayout()
        header_info.setSpacing(6)
        self.char_name = QLabel("Chọn nhân vật")
        self.char_name.setObjectName("headline")
        self.char_name.setWordWrap(True)
        header_info.addWidget(self.char_name)

        badges_row = ResponsiveCardGrid(100, 2)
        self.char_tier_badge = QLabel("Ưu tiên: tự động")
        self.char_tier_badge.setObjectName("badge")
        self.char_tier_badge.setWordWrap(True)
        badges_row.add_card(self.char_tier_badge)

        self.char_preset_badge = QLabel("Bản dựng: mặc định")
        self.char_preset_badge.setObjectName("badge")
        self.char_preset_badge.setWordWrap(True)
        badges_row.add_card(self.char_preset_badge)

        self.char_pin_badge = QLabel("Chưa pin")
        self.char_pin_badge.setObjectName("badge")
        self.char_pin_badge.setWordWrap(True)
        badges_row.add_card(self.char_pin_badge)

        self.char_priority_badge = QLabel("Ưu tiên: bình thường")
        self.char_priority_badge.setObjectName("badge")
        self.char_priority_badge.setWordWrap(True)
        badges_row.add_card(self.char_priority_badge)
        self.character_context_toggle = QPushButton("Xem trang bị và chi tiết")
        self.character_context_toggle.setObjectName("ghostButton")
        self.character_context_toggle.setCheckable(True)
        self.character_badges = badges_row
        header_info.addWidget(self.character_context_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        header_info.addWidget(badges_row)
        badges_row.hide()
        header_layout.addLayout(header_info, 1)
        visual_layout.addWidget(header_card)

        next_card = QFrame()
        next_card.setObjectName("surfaceCard")
        next_layout = QHBoxLayout(next_card)
        next_copy = QVBoxLayout()
        next_copy.addWidget(QLabel("VIỆC NÊN LÀM TIẾP"))
        self.char_next_action = QLabel("Project G đang tìm bước tiếp theo…")
        self.char_next_action.setObjectName("section")
        self.char_next_action.setWordWrap(True)
        next_copy.addWidget(self.char_next_action)
        next_layout.addLayout(next_copy, 1)
        self.char_next_button = QPushButton("Xem cách làm")
        self.char_next_button.clicked.connect(self._open_character_next_action)
        next_layout.addWidget(self.char_next_button)
        visual_layout.addWidget(next_card)

        # These are fields of one profile, not three competing dashboard cards.
        stat_card = QFrame()
        stat_card.setObjectName("surfaceCard")
        stat_layout = QVBoxLayout(stat_card)
        stat_layout.setContentsMargins(16, 12, 16, 12)
        prog_row = ResponsiveCardGrid(170, 1)

        # Level Box
        lvl_box = QFrame()
        lvl_box.setObjectName("profileStat")
        lvl_box_layout = QVBoxLayout(lvl_box)
        lvl_box_layout.setContentsMargins(14, 12, 14, 12)
        lvl_box_layout.setSpacing(6)
        lvl_title = QLabel("Cấp độ và đột phá")
        lvl_title.setObjectName("eyebrow")
        lvl_box_layout.addWidget(lvl_title)
        self.char_level_val = QLabel("-")
        self.char_level_val.setObjectName("todayAction")
        lvl_box_layout.addWidget(self.char_level_val)
        self.char_level_progress = QProgressBar()
        self.char_level_progress.setTextVisible(False)
        self.char_level_progress.hide()
        self.char_level_progress.setAccessibleName("Tiến trình cấp độ nhân vật")
        self.char_level_progress.setRange(0, 100)
        self.char_level_progress.setValue(0)
        lvl_box_layout.addWidget(self.char_level_progress)
        prog_row.add_card(lvl_box)

        # Talents Box
        tal_box = QFrame()
        tal_box.setObjectName("profileStat")
        tal_box_layout = QVBoxLayout(tal_box)
        tal_box_layout.setContentsMargins(14, 12, 14, 12)
        tal_box_layout.setSpacing(6)
        tal_title = QLabel("THIÊN PHÚ")
        tal_title.setObjectName("eyebrow")
        tal_box_layout.addWidget(tal_title)
        self.char_talent_val = QLabel("-")
        self.char_talent_val.setWordWrap(True)
        self.char_talent_val.setObjectName("todayAction")
        tal_box_layout.addWidget(self.char_talent_val)
        prog_row.add_card(tal_box)

        # Weapon Box
        wpn_box = QFrame()
        wpn_box.setObjectName("profileStat")
        wpn_box_layout = QVBoxLayout(wpn_box)
        wpn_box_layout.setContentsMargins(14, 12, 14, 12)
        wpn_box_layout.setSpacing(6)
        wpn_title = QLabel("VŨ KHÍ")
        wpn_title.setObjectName("eyebrow")
        wpn_box_layout.addWidget(wpn_title)

        wpn_content = QHBoxLayout()
        self.char_weapon_avatar = QLabel()
        self.char_weapon_avatar.setFixedSize(48, 48)
        self.char_weapon_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wpn_content.addWidget(self.char_weapon_avatar)

        self.char_weapon_val = QLabel("-")
        self.char_weapon_val.setObjectName("todayAction")
        self.char_weapon_val.setWordWrap(True)
        wpn_content.addWidget(self.char_weapon_val, 1)
        wpn_box_layout.addLayout(wpn_content)

        prog_row.add_card(wpn_box)
        stat_layout.addWidget(prog_row)
        visual_layout.addWidget(stat_card)

        # 5 Artifacts Grid
        art_card = QFrame()
        self.character_artifacts_card = art_card
        art_card.setObjectName("surfaceCard")
        art_layout = QVBoxLayout(art_card)
        art_layout.setContentsMargins(14, 12, 14, 12)
        art_layout.setSpacing(10)

        art_header = QHBoxLayout()
        art_heading = QLabel("Thánh di vật đang mặc")
        art_heading.setWordWrap(True)
        art_heading.setObjectName("section")
        art_header.addWidget(art_heading, 1)
        art_header.addStretch()
        self.char_artifact_summary = QLabel("RV tổng: -")
        self.char_artifact_summary.setWordWrap(True)
        self.char_artifact_summary.setObjectName("eyebrow")
        art_header.addWidget(self.char_artifact_summary)
        art_layout.addLayout(art_header)

        self.char_art_slots_layout = ResponsiveCardGrid(130, 5)

        slot_titles = ["Hoa", "Lông", "Đồng hồ", "Ly", "Nón"]
        self.char_art_set = []
        self.char_art_main = []
        self.char_art_subs = []
        self.char_art_rv = []

        for name in slot_titles:
            slot_box = QFrame()
            slot_box.setObjectName("artifactSlot")
            slot_v = QVBoxLayout(slot_box)
            slot_v.setContentsMargins(8, 8, 8, 8)
            slot_v.setSpacing(4)

            lbl_title = QLabel(name)
            lbl_title.setObjectName("eyebrow")
            slot_v.addWidget(lbl_title)

            lbl_set = QLabel("-")
            lbl_set.setObjectName("secondaryText")
            lbl_set.setWordWrap(True)
            slot_v.addWidget(lbl_set)
            self.char_art_set.append(lbl_set)

            lbl_main = QLabel("-")
            lbl_main.setObjectName("eyebrow")
            lbl_main.setWordWrap(True)
            slot_v.addWidget(lbl_main)
            self.char_art_main.append(lbl_main)

            lbl_subs = QLabel("-")
            lbl_subs.setObjectName("secondaryText")
            lbl_subs.setWordWrap(True)
            slot_v.addWidget(lbl_subs, 1)
            lbl_subs.hide()
            self.char_art_subs.append(lbl_subs)

            lbl_rv = QLabel("RV -")
            lbl_rv.setObjectName("badge")
            lbl_rv.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot_v.addWidget(lbl_rv)
            self.char_art_rv.append(lbl_rv)

            self.char_art_slots_layout.add_card(slot_box)

        art_layout.addWidget(self.char_art_slots_layout)
        self.char_substats_toggle = QPushButton("Xem chỉ số phụ")
        self.char_substats_toggle.setObjectName("ghostButton")
        self.char_substats_toggle.setCheckable(True)
        self.char_substats_toggle.toggled.connect(self._set_artifact_substats_visible)
        art_layout.addWidget(self.char_substats_toggle, 0, Qt.AlignmentFlag.AlignLeft)

        self.char_artifact_gate = QLabel("")
        self.char_artifact_gate.setWordWrap(True)
        self.char_artifact_gate.setObjectName("secondaryText")
        art_layout.addWidget(self.char_artifact_gate)

        visual_layout.addWidget(art_card)
        art_card.hide()

        # Teams & Planner Notes Card
        notes_card = QFrame()
        self.character_notes_card = notes_card
        notes_card.setObjectName("surfaceCard")
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(14, 12, 14, 12)
        notes_layout.setSpacing(6)

        notes_title = QLabel("ĐỘI HÌNH & THIẾT LẬP TARGET")
        notes_title.setObjectName("eyebrow")
        notes_layout.addWidget(notes_title)

        self.char_teams_val = QLabel("Đội hình: -")
        self.char_teams_val.setWordWrap(True)
        self.char_teams_val.setObjectName("secondaryText")
        notes_layout.addWidget(self.char_teams_val)

        self.char_target_notes = QLabel("Target: -")
        self.char_target_notes.setWordWrap(True)
        self.char_target_notes.setObjectName("secondaryText")
        notes_layout.addWidget(self.char_target_notes)

        visual_layout.addWidget(notes_card)
        notes_card.hide()
        self.character_context_toggle.toggled.connect(self._set_character_details_visible)

        visual_layout.addStretch()
        visual_scroll.setWidget(visual_container)
        char_tabs.addTab(visual_scroll, "Tổng quan")

        # Tab 2: Raw Text (for full detail / inspection)
        self.character_detail = QTextEdit()
        self.character_detail.setReadOnly(True)
        char_tabs.addTab(self.character_detail, "Chi tiết kỹ thuật")

        self.character_tabs = char_tabs
        char_tabs.tabBar().hide()
        right_layout.addWidget(char_tabs, 1)
        self.character_empty = EmptyState(
            "NHÂN VẬT / BẮT ĐẦU", "Bộ sưu tập của bạn đang trống",
            "Nhập tài khoản để xem cấp độ, vũ khí, thánh di vật và tiến trình build.",
            "Nhập tài khoản", self.snapshot_button.click)
        self.character_empty.hide()
        right_layout.addWidget(self.character_empty, 1)

        # Keep the common actions visible; secondary actions remain in a menu.
        pin_actions = ResponsiveCardGrid(130, 3)
        self.character_config_button = QPushButton("Cấu hình…", self)
        self.character_config_button.hide()
        self.character_config_button.setToolTip("Tier, mức ưu tiên và cấu hình nhân vật")
        self.character_config_button.clicked.connect(self.open_character_config)
        self.pin_button = QPushButton("Ưu tiên hôm nay")
        self.pin_button.clicked.connect(self.preview_selected_pin)
        self.character_more_button = QPushButton("Điều chỉnh ưu tiên")
        character_menu = QMenu(self.character_more_button)
        character_menu.addAction("Điều chỉnh mức ưu tiên…", self._open_character_priorities)
        character_menu.addSeparator()
        self.create_preset_action = character_menu.addAction("Tạo preset…", self.create_selected_preset)
        self.activate_preset_action = character_menu.addAction("Đổi preset…", self.activate_selected_preset)
        character_menu.addSeparator()
        self.unpin_action = character_menu.addAction("Bỏ ghim Today", lambda: self._run_pin(None, commit=True))
        self.character_more_button.setMenu(character_menu)
        self.wants_build_button = QPushButton("Muốn nâng cấp")
        self.wants_build_button.setObjectName("primaryButton")
        self.wants_build_button.clicked.connect(self.toggle_wants_build)
        self.edit_rv_button = QPushButton("Điền RV…", self)
        self.edit_rv_button.hide()
        self.edit_rv_button.setToolTip("Mở biểu mẫu snapshot hiện tại để nhập RV cho thánh di vật đang trang bị")
        self.edit_rv_button.clicked.connect(self.edit_selected_artifact_rv)
        character_menu.addSeparator()
        character_menu.addAction("Đã hoàn thành build", lambda: self.set_build_intent("COMPLETE"))
        character_menu.addAction("Bỏ ưu tiên build", lambda: self.set_build_intent("NORMAL"))
        character_menu.addSeparator()
        self.character_config_action = character_menu.addAction("Cấu hình nhân vật…", self.character_config_button.click)
        self.character_rv_action = character_menu.addAction("Điền RV thánh di vật…", self.edit_rv_button.click)
        character_menu.aboutToShow.connect(self._sync_character_actions)
        pin_actions.add_card(self.wants_build_button)
        pin_actions.add_card(self.pin_button)
        pin_actions.add_card(self.character_more_button)
        self.character_actions = pin_actions
        right_layout.addWidget(pin_actions)

        splitter.addWidget(right_panel)
        splitter.setChildrenCollapsible(False)
        left_panel.setMinimumWidth(150)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([220, 740])
        body.addWidget(splitter, 1)
        self.pages.addWidget(page)


    def _sync_character_actions(self):
        self.character_config_action.setEnabled(self.character_config_button.isEnabled())
        self.character_rv_action.setEnabled(self.edit_rv_button.isEnabled())


    def _set_character_details_visible(self, visible):
        if not visible:
            self.character_tabs.setCurrentIndex(0)
        self.character_tabs.tabBar().setVisible(visible)
        self.character_badges.setVisible(visible)
        self.character_artifacts_card.setVisible(visible)
        self.character_notes_card.setVisible(visible)
        self.character_context_toggle.setText("Ẩn trang bị và chi tiết" if visible else "Xem trang bị và chi tiết")


    def _set_artifact_substats_visible(self, visible):
        for label in self.char_art_subs:
            label.setVisible(visible)
        self.char_substats_toggle.setText("Ẩn chỉ số phụ" if visible else "Xem chỉ số phụ")


    def _filter_characters(self, query: str):
        query = query.strip().casefold()
        for i in range(self.character_list.count()):
            item = self.character_list.item(i)
            item.setHidden(bool(query and query not in item.text().casefold()))
        total = self.character_list.count()
        visible = sum(not self.character_list.item(i).isHidden() for i in range(total))
        self.character_search_feedback.setText(
            "Không tìm thấy nhân vật. Thử từ khóa khác."
            if total and not visible else f"Hiển thị {visible} / {total} nhân vật"
        )


    def _render_characters(self, data):
        self.account_summary.setText(f"{len(data['characters'])} nhân vật trong tài khoản")
        selected = self.character_list.currentItem().text() if self.character_list.currentItem() else None
        self.character_list.clear()

        for row in data["characters"]:
            key = row["key"]
            item = QListWidgetItem(key)
            item.setIcon(QIcon(get_character_pixmap(key, 32)))
            self.character_list.addItem(item)

        keys = [row["key"] for row in data["characters"]]
        self.character_picker.blockSignals(True)
        self.character_picker.clear()
        self.character_picker.addItems(keys)
        self.character_picker.blockSignals(False)
        self.character_tabs.setVisible(bool(keys))
        self.character_empty.setVisible(not keys)
        self.character_actions.setVisible(bool(keys))
        for control in (self.character_config_button, self.pin_button, self.character_more_button):
            control.setEnabled(bool(keys))
        self.wants_build_button.setEnabled(bool(keys) and self.build_intent_controller is not None)
        self.edit_rv_button.setEnabled(bool(keys))
        if keys:
            self.character_list.setCurrentRow(keys.index(selected) if selected in keys else 0)
        else:
            self.char_name.setText("Chưa có nhân vật trong snapshot")
            self.character_detail.setPlainText("Chưa có nhân vật trong snapshot hiện tại.")

        self._filter_characters(self.character_search.text())


    def _show_character(self, index):
        if not self._data or index < 0 or index >= len(self._data["characters"]):
            return
        row = self._data["characters"][index]
        char_key = row["key"]
        goals = ((self._data.get("roadmap") or {}).get("global") or [])
        next_goal = next((goal for goal in goals if (goal.get("character") or {}).get("key") == char_key
                          and goal.get("status") not in {"COMPLETE", "READY"}), None)
        self._character_next_goal = next_goal
        self.char_next_action.setText(goal_display_title(next_goal) if next_goal else "Chưa có bước nâng cấp cần làm")
        self.char_next_button.setVisible(next_goal is not None)
        self.character_picker.blockSignals(True)
        self.character_picker.setCurrentIndex(index)
        self.character_picker.blockSignals(False)
        self._character_key = char_key
        target = row["target"] or {}
        current_talents = row["talents"]

        # 1. Header Card
        self.char_name.setText(char_key)
        self._refresh_character_avatar()
        profile_rows = row.get("buildProfiles") or []
        self.char_tier_badge.setText("Ưu tiên: tự động")
        self.char_preset_badge.setText(f"Số bản dựng: {len(profile_rows)}")

        pinned_key = ((self._data.get("today") or {}).get("todayState") or {}).get("pinnedCharacterKey")
        is_pinned = (pinned_key == char_key)
        self.char_pin_badge.setText("Đang ưu tiên hôm nay" if is_pinned else "Chưa ghim")
        if is_pinned:
            self.char_pin_badge.setObjectName("badge")
            set_state(self.char_pin_badge, "accent")
        else:
            self.char_pin_badge.setObjectName("badge")
            set_state(self.char_pin_badge, "")

        priority_mode = row.get("priorityOverride", "NORMAL")
        priority_label = {"PRIORITIZED": "Ưu tiên", "DEPRIORITIZED": "Hạ ưu tiên"}.get(priority_mode, "Bình thường")
        self.char_priority_badge.setText(f"Ưu tiên chiến lược: {priority_label}")
        set_state(self.char_priority_badge, "accent" if priority_mode == "PRIORITIZED" else "")
        self.char_priority_badge.show()
        personal_state = (self._data.get("personalPriorities") or {}).get(char_key)
        self.wants_build_button.setText({"WANT_BUILD": "Đang ưu tiên nâng cấp", "COMPLETE": "Đã nâng cấp xong"}.get(personal_state, "Muốn nâng cấp"))
        self.wants_build_button.setProperty("buildState", personal_state or "NORMAL")
        self.wants_build_button.setEnabled(self.build_intent_controller is not None)
        unknown_rv_slots = sorted(art.get("slot", "?") for art in row.get("artifacts", []) if art.get("rv") is None)
        self.edit_rv_button.setText(f"Điền RV ({len(unknown_rv_slots)})…" if unknown_rv_slots else "Cập nhật RV…")
        self.edit_rv_button.setToolTip(
            "Thiếu RV ở: " + ", ".join(unknown_rv_slots) if unknown_rv_slots
            else "Mở biểu mẫu snapshot để cập nhật RV")
        self.edit_rv_button.setEnabled(bool(self._data.get("characters")) and not self._loading)

        # 2. Level Box
        cur_lvl = row.get("level", 0)
        cur_asc = row.get("ascension", 0)
        self.char_level_val.setText(f"Hiện tại: Lv {cur_lvl} / 100 (Đột phá {cur_asc})")
        pct = min(100, int((cur_lvl / 100) * 100))
        self.char_level_progress.setValue(pct)
        self.char_level_progress.setFormat(f"Lv {cur_lvl}/100")

        # 3. Talents Box
        talent_labels = {"normal": "Đánh thường", "skill": "Kỹ năng (E)", "burst": "Nộ (Q)"}
        t_lines = []
        for k in ("normal", "skill", "burst"):
            c_val = current_talents.get(k, "-")
            t_lines.append(f"• {talent_labels[k]}: <b>{c_val}</b>")
        self.char_talent_val.setText("<br>".join(t_lines))

        # 4. Weapon Box
        weapon = row.get("weapon")
        w_key = weapon.get("key") if weapon else ""
        self.char_weapon_avatar.setPixmap(get_weapon_pixmap(w_key, 48))

        cur_w_str = f"<b>{weapon['key']}</b> Lv {weapon['level']} (R{weapon['refinement']})" if weapon else "Chưa nhận diện"
        self.char_weapon_val.setText(f"Đang trang bị: {cur_w_str}")

        # 5. 5 Artifacts Box
        slot_aliases = {
            "flower of life": "flower", "flower": "flower",
            "plume of death": "plume", "plume": "plume",
            "sands of eon": "sands", "sands": "sands",
            "goblet of eonothem": "goblet", "goblet": "goblet",
            "circlet of logos": "circlet", "circlet": "circlet",
        }
        artifact_by_slot = {
            slot_aliases.get(str(art.get("slot", "")).casefold(), str(art.get("slot", "")).casefold()): art
            for art in row.get("artifacts", [])
        }
        slot_order = ["flower", "plume", "sands", "goblet", "circlet"]
        known_rv = []

        for i, s_key in enumerate(slot_order):
            art = artifact_by_slot.get(s_key)
            if not art:
                self.char_art_set[i].setText("Chưa có đồ")
                self.char_art_main[i].setText("-")
                self.char_art_subs[i].setText("Thiếu dữ liệu")
                self.char_art_rv[i].setText("RV -")
                continue

            self.char_art_set[i].setText(f"{art.get('set', 'Unknown')} +{art.get('level', 0)}")
            self.char_art_main[i].setText(str(art.get("mainStat", "-")))

            sub_texts = [f"• {s.get('key', '?')}: {s.get('value', '?')}" for s in (art.get("substats") or [])]
            self.char_art_subs[i].setText("\n".join(sub_texts) if sub_texts else "Không có substat")

            rv = art.get("rv")
            if rv is not None:
                known_rv.append(float(rv))
                self.char_art_rv[i].setText(f"RV {float(rv):.1f}")
                self.char_art_rv[i].setObjectName("badge")
                set_state(self.char_art_rv[i], "success")
            else:
                self.char_art_rv[i].setText(f"RV ?")
                self.char_art_rv[i].setObjectName("badge")
                set_state(self.char_art_rv[i], "")

        rv_total = sum(known_rv)
        self.char_artifact_summary.setText(f"RV tổng đã biết: {rv_total:.1f} · Đủ RV {len(known_rv)}/5")

        gate_info = f"RV đã biết: <b>{len(known_rv)}/5 slot</b> · Đánh giá theo build profile"
        self.char_artifact_gate.setText(gate_info)

        # 6. Teams & Planner Notes
        teams = row.get("teams", [])
        if teams:
            team_chips = []
            for tm in teams:
                if tm.get("isPrimary"):
                    team_chips.append(f"<span style='color:#b9c6ff; font-weight:bold;'>✦ {tm['name']} [ĐỘI CHÍNH]</span>")
                else:
                    team_chips.append(f"• {tm['name']}")
            self.char_teams_val.setText("  ·  ".join(team_chips))
        else:
            self.char_teams_val.setText("Chưa gán vào đội hình nào.")

        tgt_lines = [f"{item['archetype']} · {item['depth']} · {item['status']}" for item in profile_rows]
        if not tgt_lines:
            tgt_lines.append("Chưa có build profile được duyệt cho nhân vật này.")
        self.char_target_notes.setText("<br>".join(tgt_lines))

        # 7. Update raw text edit for backward-compatibility & inspection
        lines = [row["key"], "", "ACCOUNT SNAPSHOT"]
        lines.append(f"Level {row['level']} / {row['ascension']} ascension")
        lines.append("Talents: " + " · ".join(f"{k}: {current_talents.get(k, '-')}" for k in ("normal", "skill", "burst")))
        lines.append(f"Weapon: {cur_w_str}")
        lines.append("\n5 ARTIFACT ĐANG MẶC · RV")
        for s_name, s_key in [("Hoa", "flower"), ("Lông", "plume"), ("Đồng hồ", "sands"), ("Ly", "goblet"), ("Nón", "circlet")]:
            art = artifact_by_slot.get(s_key)
            if art:
                rv_txt = f"{float(art['rv']):.1f}" if art.get("rv") is not None else "unknown"
                lines.append(f"{s_name}: {art.get('set')} +{art.get('level')} · {art.get('mainStat')} · RV {rv_txt}")
            else:
                lines.append(f"{s_name}: thiếu dữ liệu")
        lines.append(f"RV tổng đã biết: {rv_total:.1f} · đủ RV {len(known_rv)}/5")
        lines.append("\nPLANNER CONFIGURATION")
        lines.append("Build profiles: " + (", ".join(item["archetype"] for item in profile_rows) or "chưa có profile đã duyệt"))
        lines.append("Pin Today: " + ("đang pin" if is_pinned else "không"))
        self.character_detail.setPlainText("\n".join(lines))


    def _refresh_character_avatar(self):
        key = getattr(self, "_character_key", None)
        if key:
            self.char_avatar.setPixmap(get_character_pixmap(
                key, self.char_avatar.width(), device_pixel_ratio=self.devicePixelRatioF()))


    def character_list_row_from_picker(self, index):
        if index >= 0 and hasattr(self, "character_list"):
            self.character_list.setCurrentRow(index)


    def _open_character_priorities(self):
        key = self._selected_character_key()
        self.nav.setCurrentRow(3)
        if key:
            self.tier_search.setText(key)


    def _open_character_next_action(self):
        goal = getattr(self, "_character_next_goal", None)
        if goal:
            self._show_task_in_roadmap({"character": goal.get("character"),
                                        "primaryGoal": {"goalKey": goal.get("goalKey")}})


