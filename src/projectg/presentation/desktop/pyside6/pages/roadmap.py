"""Native desktop presentation: pages/roadmap."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QPushButton, QAbstractItemView, QHeaderView, QScrollArea, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QSplitter
from projectg.presentation.desktop.pyside6.theme import COLORS, set_state
from projectg.presentation.desktop.pyside6.row_details_dialog import RowDetailsDialog
from projectg.presentation.desktop.pyside6.empty_state import EmptyState
from projectg.presentation.desktop.pyside6.responsive_grid import ResponsiveCardGrid
from projectg.presentation.desktop.pyside6.goal_copy import goal_display_title
from projectg.presentation.desktop.pyside6.action_queue import ActionQueueModel, ActionQueueFilter, ActionQueueDelegate, availability_text


class RoadmapPage:
    def _make_roadmap(self):
        page = QWidget()
        body = QVBoxLayout(page)
        body.setSpacing(12)


        self.roadmap_summary = QLabel("")
        self.roadmap_summary.setObjectName("pageSubtitle")
        self.roadmap_summary.setWordWrap(True)
        body.addWidget(self.roadmap_summary)
        self.roadmap_metrics = ResponsiveCardGrid(150, 4)
        self.roadmap_metric_values = {}
        for key, label in (("goals", "Mục tiêu"), ("characters", "Nhân vật"),
                           ("actionable", "Có thể làm"), ("blocked", "Đang chờ")):
            card = QFrame()
            card.setObjectName("metricCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(2)
            value = QLabel("0")
            value.setObjectName("metricValue")
            caption = QLabel(label)
            caption.setObjectName("metricLabel")
            card_layout.addWidget(value)
            card_layout.addWidget(caption)
            self.roadmap_metric_values[key] = value
            self.roadmap_metrics.add_card(card)
        self.roadmap_metrics.hide()
        body.addWidget(self.roadmap_metrics)
        self.roadmap_setup_target = QPushButton("Thiết lập mục tiêu đầu tiên")
        self.roadmap_setup_target.setObjectName("primaryButton")
        self.roadmap_setup_target.clicked.connect(self.open_target_editor)
        self.roadmap_setup_target.setVisible(False)
        body.addWidget(self.roadmap_setup_target, 0, Qt.AlignmentFlag.AlignLeft)

        # Search and Filter Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.roadmap_search = QLineEdit()
        self.roadmap_search.setClearButtonEnabled(True)
        self.roadmap_search.setAccessibleName("Tìm nhân vật")
        self.roadmap_search.setToolTip("Tìm trong màn hình hiện tại · Ctrl+F")
        self.roadmap_search.setPlaceholderText("Tìm nhân vật hoặc thành phần…")
        self.roadmap_search.textChanged.connect(self._filter_roadmap)
        filter_bar.addWidget(self.roadmap_search, 1)

        self.roadmap_filter = QComboBox()
        self.roadmap_filter.addItems([
            "Tất cả trạng thái",
            "Có thể làm",
            "Đang chờ",
            "Đã đạt",
            "Hoàn tất",
        ])
        self.roadmap_filter.currentIndexChanged.connect(self._filter_roadmap)
        filter_bar.addWidget(self.roadmap_filter)

        self.roadmap_details_toggle = QCheckBox("Thêm cột")
        self.roadmap_details_toggle.setToolTip("Hiển thị target cuối / tiến triển và điểm ưu tiên")
        self.roadmap_details_toggle.toggled.connect(self._configure_roadmap_columns)
        filter_bar.addWidget(self.roadmap_details_toggle)
        self.roadmap_details_toggle.hide()
        body.addLayout(filter_bar)

        self.roadmap_tree = QTreeWidget()
        self.roadmap_tree.setHeaderLabels(["#", "Việc nâng cấp", "Hiện tại", "Bước tiếp theo",
                                           "Mục tiêu cuối", "Trạng thái", "Điểm ưu tiên"])
        self.roadmap_tree.setRootIsDecorated(False)
        self.roadmap_tree.setAlternatingRowColors(True)
        self.roadmap_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.roadmap_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.roadmap_tree.itemDoubleClicked.connect(self._open_goal_character)
        self.roadmap_tree.setWordWrap(True)
        self._configure_roadmap_columns(False)
        body.addWidget(self.roadmap_tree)
        self.roadmap_tree.hide()
        self.action_queue_model = ActionQueueModel(self)
        self.action_queue_filter = ActionQueueFilter(self)
        self.action_queue_filter.setSourceModel(self.action_queue_model)
        self.action_queue = QListView()
        self.action_queue.setObjectName("actionQueue")
        self.action_queue.setModel(self.action_queue_filter)
        self.action_queue.setItemDelegate(ActionQueueDelegate(self.action_queue))
        self.action_queue.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.action_queue.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.action_queue.setMouseTracking(True)
        self.action_queue.setAccessibleName("Hàng đợi nâng cấp theo thứ tự ưu tiên")
        self.action_queue.clicked.connect(self._show_action_detail)
        self.action_queue.activated.connect(self._show_action_detail)
        self.action_queue.selectionModel().currentChanged.connect(
            lambda index, _previous: self._show_action_detail(index, navigate=False))
        self.action_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.action_list_panel = QWidget()
        action_list_layout = QVBoxLayout(self.action_list_panel)
        action_list_layout.setContentsMargins(0, 0, 0, 0)
        action_list_layout.addWidget(self.action_queue)
        self.action_splitter.addWidget(self.action_list_panel)
        self.action_detail_panel = QFrame()
        self.action_detail_panel.setObjectName("surfaceCard")
        detail_layout = QVBoxLayout(self.action_detail_panel)
        detail_layout.setContentsMargins(24, 24, 24, 24)
        self.action_back = QPushButton("← Kế hoạch")
        self.action_back.setObjectName("ghostButton")
        self.action_back.clicked.connect(self._back_to_action_queue)
        detail_layout.addWidget(self.action_back, 0, Qt.AlignmentFlag.AlignLeft)
        self.action_detail_title = QLabel()
        self.action_detail_title.setObjectName("section")
        self.action_detail_title.setWordWrap(True)
        detail_layout.addWidget(self.action_detail_title)
        self.action_detail_status = QLabel()
        self.action_detail_status.setObjectName("actionStatus")
        self.action_detail_status.setWordWrap(True)
        detail_layout.addWidget(self.action_detail_status)
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_content = QWidget()
        detail_content_layout = QVBoxLayout(detail_content)
        detail_content_layout.setContentsMargins(0, 12, 4, 0)
        detail_content_layout.setSpacing(16)
        self.action_detail_body = QLabel()
        self.action_detail_body.setObjectName("secondaryText")
        self.action_detail_body.setWordWrap(True)
        self.action_detail_body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_content_layout.addWidget(self.action_detail_body)
        self.action_character_button = QPushButton("Xem hồ sơ nhân vật")
        self.action_character_button.clicked.connect(self._open_selected_action_character)
        detail_content_layout.addWidget(self.action_character_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail_content_layout.addStretch()
        detail_scroll.setWidget(detail_content)
        detail_layout.addWidget(detail_scroll, 1)
        self.action_splitter.addWidget(self.action_detail_panel)
        self.action_splitter.setStretchFactor(0, 3)
        self.action_splitter.setStretchFactor(1, 2)
        self.action_splitter.setSizes([650, 360])
        body.addWidget(self.action_splitter, 1)
        self.roadmap_empty = EmptyState(
            "LỘ TRÌNH / BẮT ĐẦU", "Lộ trình sẽ bắt đầu từ tài khoản của bạn",
            "Nhập snapshot để xem các mục tiêu và thứ tự nâng cấp.",
            "Nhập tài khoản", self.snapshot_button.click)
        self.roadmap_empty.hide()
        body.addWidget(self.roadmap_empty, 1)
        self.roadmap_search_feedback = QLabel()
        self.roadmap_search_feedback.setObjectName("searchFeedback")
        self.roadmap_search_feedback.setWordWrap(True)
        footer = QHBoxLayout()
        footer.addWidget(self.roadmap_search_feedback, 1)
        self.roadmap_open_details_button = QPushButton("Xem mục đang chọn")
        self.roadmap_open_details_button.setEnabled(False)
        self.roadmap_open_details_button.clicked.connect(self._open_roadmap_details)
        footer.addWidget(self.roadmap_open_details_button)
        body.addLayout(footer)
        self.roadmap_tree.itemSelectionChanged.connect(self._update_roadmap_detail_action)
        self._roadmap_details_shortcut = QShortcut(QKeySequence("Return"), self.roadmap_tree)
        self._roadmap_details_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._roadmap_details_shortcut.activated.connect(self.roadmap_open_details_button.click)
        self.roadmap_open_details_button.setToolTip("Đọc đầy đủ nội dung, kể cả cột ẩn · Enter")
        self.roadmap_open_details_button.hide()
        self.pages.addWidget(page)


    def _show_action_detail(self, index, navigate=True):
        goal = index.data(ActionQueueModel.GoalRole) if index.isValid() else None
        if not goal:
            return
        self._selected_action_goal = goal
        character = (goal.get("character") or {}).get("name") or (goal.get("character") or {}).get("key") or "Nhân vật"
        self.action_detail_title.setText(f"{character}\n{goal_display_title(goal)}")
        self.action_detail_status.setText(availability_text(goal, self.action_queue_model.today_tasks))
        set_state(self.action_detail_status,
                  "success" if goal.get("status") == "ACTIONABLE" else
                  "warning" if goal.get("status") == "BLOCKED" else "accent")
        current = (goal.get("current") or {}).get("value")
        milestone = (goal.get("nextMilestone") or {}).get("value")
        progress = f"{current} → {milestone}" if current is not None and milestone is not None else "Xem bước nâng cấp"
        lines = [f"Bước nâng cấp: {progress}"]
        task = next((item for item in self.action_queue_model.today_tasks
                     if (item.get("primaryGoal") or {}).get("goalKey") == goal.get("goalKey")), None)
        if task:
            source = task.get("source") or {}
            if source.get("name"):
                lines.append("Nguồn: " + source["name"])
            if task.get("availableWeekdays"):
                lines.append("Mở: " + " · ".join(task["availableWeekdays"]))
            resin_cost = source.get("resinCost", source.get("resin_cost"))
            if resin_cost is not None:
                lines.append(f"Tốn khoảng {resin_cost} Nhựa/lượt")
            if task.get("whySummary"):
                lines.append("Vì sao bước này? " + task["whySummary"])
        if goal.get("planningGroup") == "PERSONAL":
            lines.append("Đứng trước vì đây là mục tiêu cá nhân bạn đã chọn.")
        elif goal.get("planningGroup") == "THEATER":
            lines.append("Đây là bước chuẩn bị cho Nhà Hát.")
        else:
            lines.append(f"Project G xếp bước này ở vị trí #{goal.get('rank', '—')} theo kế hoạch hiện tại.")
        self.action_detail_body.setText("\n\n".join(lines))
        self.action_character_button.setEnabled(bool((goal.get("character") or {}).get("key")))
        if navigate and self.width() < 1060:
            self.action_list_panel.hide()
            self.action_detail_panel.show()
            self.roadmap_search.hide()
            self.roadmap_filter.hide()


    def _back_to_action_queue(self):
        self.action_list_panel.show()
        self.roadmap_search.show()
        self.roadmap_filter.show()
        if self.width() < 1060:
            self.action_detail_panel.hide()
        self.action_queue.setFocus()


    def _open_selected_action_character(self):
        goal = getattr(self, "_selected_action_goal", None) or {}
        key = (goal.get("character") or {}).get("key")
        for row in range(self.character_list.count()):
            if self.character_list.item(row).text() == key:
                self.nav.setCurrentRow(2)
                self.character_list.setCurrentRow(row)
                break


    def _update_roadmap_detail_action(self):
        item = self.roadmap_tree.currentItem()
        self.roadmap_open_details_button.setEnabled(
            item is not None and item.isSelected() and not item.isHidden()
        )


    def _roadmap_details_dialog(self):
        item = self.roadmap_tree.currentItem()
        if item is None or not item.isSelected() or item.isHidden():
            return None
        fields = tuple((self.roadmap_tree.headerItem().text(column), item.text(column))
                       for column in range(self.roadmap_tree.columnCount()))
        details = "\n".join(dict.fromkeys(item.toolTip(column) for column in range(item.columnCount())
                                         if item.toolTip(column)))
        return RowDetailsDialog(item.text(1), fields, details, self)


    def _open_roadmap_details(self):
        dialog = self._roadmap_details_dialog()
        if dialog is not None:
            dialog.exec()
            dialog.deleteLater()


    def _configure_roadmap_columns(self, detailed):
        tree = self.roadmap_tree
        header = tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column, width in {0: 42, 2: 70, 3: 130, 4: 240, 5: 120, 6: 74}.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            tree.setColumnWidth(column, width)
        for column in range(tree.columnCount()):
            tree.headerItem().setToolTip(column, tree.headerItem().text(column))
        tree.headerItem().setToolTip(3, "Milestone kế tiếp trong chuỗi nâng cấp")
        for column in (0, 2, 4, 6):
            tree.setColumnHidden(column, not detailed)


    def _filter_roadmap(self):
        query = self.roadmap_search.text().strip().casefold()
        filter_idx = self.roadmap_filter.currentIndex()
        status_map = {1: "ACTIONABLE", 2: "BLOCKED", 3: "READY", 4: "COMPLETE"}
        target_status = status_map.get(filter_idx)
        self.action_queue_filter.set_query(query)
        self.action_queue_filter.set_status(target_status)

        for i in range(self.roadmap_tree.topLevelItemCount()):
            item = self.roadmap_tree.topLevelItem(i)
            char_key = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
            col_text = " ".join(item.text(col) for col in range(item.columnCount())).casefold()
            raw_status = str(item.data(5, Qt.ItemDataRole.UserRole) or "")

            matches_query = not query or query in char_key.casefold() or query in col_text
            matches_status = not target_status or raw_status == target_status
            item.setHidden(not (matches_query and matches_status))
        if hasattr(self, "roadmap_search_feedback"):
            total = self.roadmap_tree.topLevelItemCount()
            visible = sum(not self.roadmap_tree.topLevelItem(i).isHidden() for i in range(total))
            self.roadmap_search_feedback.setText(
                "Không có kết quả. Thử từ khóa khác hoặc chọn tất cả trạng thái."
                if total and not visible else f"Hiển thị {visible} / {total} mục"
            )
        self._update_roadmap_detail_action()


    def _render_roadmap(self, data):
        tree = self.roadmap_tree
        selected = tree.currentItem()
        selected_key = selected.data(1, Qt.ItemDataRole.UserRole) if selected else None
        selected_label = selected.text(1) if selected else None
        tree.clear()
        plan = data["roadmap"]
        goals = sorted((plan or {}).get("global", []), key=lambda goal: int(goal.get("rank", 0)))
        if not goals:
            self.action_queue_model.set_goals([])
            self.action_splitter.hide()
            self.roadmap_metrics.hide()
            has_snapshot = data.get("snapshotId") is not None
            missing_profiles = int((((data.get("today") or {}).get("coverage") or {}).get("missingProfiles")) or 0)
            knowledge_ready = bool((((data.get("today") or {}).get("coverage") or {}).get("buildKnowledgeReady", True)))
            self.roadmap_summary.setText(
                "Nhập tài khoản để tạo lộ trình nâng cấp."
                if not has_snapshot else
                f"Còn {missing_profiles} nhân vật chưa có hướng nâng cấp. Hãy cập nhật dữ liệu build."
                if missing_profiles or not knowledge_ready else "Các bước nâng cấp hiện tại đã hoàn thành.")
            self.roadmap_setup_target.setVisible(False)
            if has_snapshot:
                self.roadmap_empty.update_copy(
                    "Chưa có mục tiêu để xếp lộ trình",
                    "Kiểm tra dữ liệu build hoặc cập nhật tài khoản, rồi tính lại kế hoạch.",
                    "Tính lại kế hoạch", self.refresh_button.click)
            else:
                self.roadmap_empty.update_copy(
                    "Lộ trình sẽ bắt đầu từ tài khoản của bạn",
                    "Nhập dữ liệu tài khoản để xem thứ tự nâng cấp.",
                    "Nhập tài khoản", self.snapshot_button.click)
            self.roadmap_empty.show()
            self.roadmap_tree.hide()
            self.roadmap_summary.show()
            self._filter_roadmap()
            return
        self.roadmap_empty.hide()
        self.roadmap_tree.hide()
        self.action_splitter.show()
        self.roadmap_metrics.hide()
        self.roadmap_summary.show()
        self.roadmap_setup_target.setVisible(False)

        status_labels = {
            "ACTIONABLE": "Có thể làm",
            "BLOCKED": "Đang chờ",
            "READY": "Đã đạt",
            "COMPLETE": "Hoàn tất",
        }
        characters = {goal.get("character", {}).get("key") for goal in goals}
        for key, value in (
            ("goals", len(goals)), ("characters", len(characters)),
            ("actionable", sum(goal.get("status") == "ACTIONABLE" for goal in goals)),
            ("blocked", sum(goal.get("status") == "BLOCKED" for goal in goals)),
        ):
            self.roadmap_metric_values[key].setText(str(value))
        self.roadmap_summary.setText(
            f"{len(goals)} bước nâng cấp cho {len(characters)} nhân vật · Việc nên làm ở trên cùng")

        today = data.get("today") or {}
        tasks = [today.get("primaryTask"), *(today.get("alternativeTasks") or [])]
        self.action_queue_model.set_goals(goals, [task for task in tasks if task])
        self._back_to_action_queue()
        self.action_detail_panel.setVisible(self.width() >= 1060)

        for goal in goals:
            character = goal.get("character") or {}
            character_key = character.get("key") or "-"
            group = goal.get("planningGroup", "NORMAL")
            group_label = {"PERSONAL": "Muốn build", "THEATER": "Nhà Hát"}.get(group)
            character_label = f"{group_label} · {character_key}" if group_label else character_key

            milestone = goal.get("nextMilestone") or {}
            final_target = goal.get("strategicTarget") or {}
            if final_target.get("value") is None:
                final_target = goal.get("target") or {}
            score = goal.get("score")
            rank_str = str(goal.get("rank", "-"))

            raw_status = goal.get("status")
            status_text = status_labels.get(raw_status, raw_status or "-")

            row = QTreeWidgetItem([
                f"#{rank_str}",
                character_label + " · " + goal_display_title(goal),
                str((goal.get("current") or {}).get("value", "-")),
                (f"{(goal.get('current') or {}).get('value')} → {milestone.get('value')}"
                 if (goal.get("current") or {}).get("value") is not None and milestone.get("value") is not None
                 else str(milestone.get("value", "-"))),
                str(final_target.get("value", "-")),
                status_text,
                f"{float(score):.1f}" if score is not None else "-",
            ])
            row.setData(0, Qt.ItemDataRole.UserRole, character_key)
            row.setData(1, Qt.ItemDataRole.UserRole, goal.get("goalKey"))
            row.setData(5, Qt.ItemDataRole.UserRole, raw_status)

            # Center text for specific columns
            for col in (0, 2, 3, 4, 5, 6):
                row.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter)

            # Highlight top 3 ranks
            if rank_str in ("1", "2", "3"):
                row.setForeground(0, QColor(COLORS["accent_hover"]))
                font = row.font(0)
                font.setBold(True)
                row.setFont(0, font)

            # Color status
            if raw_status == "ACTIONABLE":
                row.setForeground(5, QColor(COLORS["success"]))
            elif raw_status == "BLOCKED":
                row.setForeground(5, QColor(COLORS["warning"]))
            elif raw_status == "READY":
                row.setForeground(5, QColor(COLORS["secondary"]))
            elif raw_status == "COMPLETE":
                row.setForeground(5, QColor(COLORS["secondary"]))

            chain = goal.get("milestoneChain") or []
            chain_text = " → ".join(str(value) for value in ([chain[0]["from"]] + [step["to"] for step in chain])) if chain else "-"
            row.setToolTip(3, "Chuỗi milestone: " + chain_text)
            row.setToolTip(4, "Mốc progression cuối theo build profile đã duyệt.")
            tree.addTopLevelItem(row)

        self._configure_roadmap_columns(self.roadmap_details_toggle.isChecked())

        self._filter_roadmap()
        visible = [tree.topLevelItem(index) for index in range(tree.topLevelItemCount())
                   if not tree.topLevelItem(index).isHidden()]
        if visible:
            restored = next((item for item in visible
                             if selected_key and item.data(1, Qt.ItemDataRole.UserRole) == selected_key), None)
            if restored is None and selected_label:
                restored = next((item for item in visible if item.text(1) == selected_label), None)
            tree.setCurrentItem(restored or visible[0])
        if self.action_queue_filter.rowCount():
            index = self.action_queue_filter.index(0, 0)
            self.action_queue.setCurrentIndex(index)
            self._show_action_detail(index, navigate=False)


    def _open_goal_character(self, item, _column=0):
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if not key:
            return
        for index in range(self.character_list.count()):
            if self.character_list.item(index).text() == key:
                self.nav.setCurrentRow(2)
                self.character_list.setCurrentRow(index)
                return


