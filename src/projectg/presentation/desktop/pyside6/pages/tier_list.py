"""Native desktop presentation: pages/tier_list."""
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QAbstractItemView, QHeaderView, QScrollArea, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from projectg.interface_adapters.controllers.desktop_reference_controller import label_for, score_for_tier
from projectg.presentation.desktop.pyside6.empty_state import EmptyState
from projectg.presentation.desktop.pyside6.responsive_grid import ResponsiveCardGrid
from projectg.presentation.desktop.pyside6.theme import COLORS, set_state


class RankCellDelegate(QStyledItemDelegate):
    """Keep the model's rank text for tests and accessibility without painting it behind the picker."""

    def paint(self, painter, option, index):
        appearance = QStyleOptionViewItem(option)
        self.initStyleOption(appearance, index)
        appearance.text = ""
        style = appearance.widget.style() if appearance.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, appearance, painter, appearance.widget)


class TierListPage:
    def _make_tier_list(self):
        self._tier_dirty = False
        page = QWidget(); layout = QVBoxLayout(page); layout.setSpacing(8)
        tier_help = QLabel("Chọn hạng cho nhân vật bạn muốn đầu tư. Hạng cao hơn được ưu tiên trong lộ trình.")
        tier_help.setWordWrap(True)
        tier_help.setObjectName("pageSubtitle")
        self.tier_help = tier_help
        layout.addWidget(tier_help)
        tier_help.hide()
        toolbar = QHBoxLayout()
        self.tier_search = QLineEdit(); self.tier_search.setPlaceholderText("Tìm nhân vật…")
        self.tier_search.setMinimumWidth(170)
        self.tier_search.setClearButtonEnabled(True)
        self.tier_search.setAccessibleName("Tìm nhân vật trong Tier List")
        self.tier_search.setToolTip("Tìm nhân vật · Ctrl+F")
        self.tier_search.textChanged.connect(self._filter_tier_list)
        toolbar.addWidget(self.tier_search, 1)

        save = QPushButton("Lưu"); save.setObjectName("primaryButton")
        save.clicked.connect(self._save_tier_list)
        self.tier_save_button = save
        toolbar.addWidget(save)
        self.tier_undo_button = QPushButton("Hoàn tác")
        self.tier_undo_button.clicked.connect(self._render_tier_list)
        self.tier_undo_button.hide()
        toolbar.addWidget(self.tier_undo_button)
        self.tier_options_button = QPushButton("Cài đặt")
        self.tier_options_button.setObjectName("ghostButton")
        self.tier_options_button.setCheckable(True)
        toolbar.addWidget(self.tier_options_button)
        layout.addLayout(toolbar)

        self.tier_options_panel = QWidget()
        options = QHBoxLayout(self.tier_options_panel)
        options.setContentsMargins(12, 8, 12, 8)
        options.addWidget(QLabel("Hạng thấp nhất"))
        self.tier_minimum_help = "Nhân vật dưới hạng này sẽ không được thêm tự động vào lộ trình."
        self.tier_minimum = QComboBox()
        self.tier_minimum.addItems(["S+", "S", "A", "B", "C", "D"])
        self.tier_minimum.setToolTip(self.tier_minimum_help)
        self.tier_minimum.currentIndexChanged.connect(self._mark_tier_dirty)
        options.addWidget(self.tier_minimum)
        self.tier_details_toggle = QCheckBox("Hiện chi tiết")
        self.tier_details_toggle.setToolTip("Hiển thị điểm chính xác, ghi chú và thiết lập build")
        self.tier_details_toggle.toggled.connect(self._configure_tier_columns)
        self.tier_details_toggle.toggled.connect(lambda checked: self.tier_table.setVisible(
            checked and self.tier_table.rowCount() > 0))
        options.addWidget(self.tier_details_toggle)
        self.tier_files_button = QPushButton("Nhập / xuất")
        tier_files_menu = QMenu(self.tier_files_button)
        tier_files_menu.addAction("Nhập Tier List…", self._import_tier_list)
        tier_files_menu.addAction("Xuất Tier List…", self._export_tier_list)
        self.tier_files_button.setMenu(tier_files_menu)
        options.addStretch()
        options.addWidget(self.tier_files_button)
        self.tier_options_panel.setObjectName("tierOptionsPanel")
        self.tier_options_panel.hide()
        self.tier_options_button.toggled.connect(self.tier_options_panel.setVisible)
        self.tier_options_button.toggled.connect(
            lambda open_: self.tier_options_button.setText("Ẩn cài đặt" if open_ else "Cài đặt"))
        layout.addWidget(self.tier_options_panel)
        self.tier_save_status = QLabel()
        self.tier_save_status.setObjectName("tierSaveStatus")
        self.tier_save_status.hide()
        layout.addWidget(self.tier_save_status)
        self.tier_error_banner = QFrame()
        self.tier_error_banner.setObjectName("tierErrorBanner")
        error_layout = QHBoxLayout(self.tier_error_banner)
        error_layout.setContentsMargins(12, 8, 12, 8)
        self.tier_error_text = QLabel()
        self.tier_error_text.setWordWrap(True)
        error_layout.addWidget(self.tier_error_text, 1)
        retry = QPushButton("Thử lại")
        self.tier_error_retry = retry
        retry.clicked.connect(self._render_tier_list)
        error_layout.addWidget(retry)
        self.tier_error_banner.hide()
        layout.addWidget(self.tier_error_banner)
        self.tier_table = QTableWidget(0, 7)
        self.tier_table.setObjectName("tierTable")
        self.tier_table.setItemDelegateForColumn(3, RankCellDelegate(self.tier_table))
        self.tier_table.setHorizontalHeaderLabels(["Nhân vật", "Tài khoản", "Điểm", "Hạng ưu tiên", "Ghi chú", "Cách chọn", "Bộ thánh di vật"])
        self.tier_table.horizontalHeaderItem(2).setToolTip("Nhấp đúp để chấm điểm từ 0 đến 100; để trống nếu chưa xếp hạng")
        self.tier_table.setAlternatingRowColors(False)
        self.tier_table.verticalHeader().setVisible(False)
        self.tier_table.verticalHeader().setDefaultSectionSize(56)
        self.tier_table.setShowGrid(False)
        self.tier_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tier_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tier_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                        QAbstractItemView.EditTrigger.EditKeyPressed)
        self._configure_tier_columns(False)
        self.tier_table.itemChanged.connect(self._tier_item_changed)
        self.tier_progress = QLabel()
        self.tier_progress.setObjectName("tierProgress")
        self.tier_progress.setWordWrap(True)
        self.tier_progress.hide()
        layout.addWidget(self.tier_progress)
        self.tier_bands_scroll = QScrollArea()
        self.tier_bands_scroll.setWidgetResizable(True)
        self.tier_bands_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tier_bands_content = QWidget()
        self.tier_bands_layout = QVBoxLayout(self.tier_bands_content)
        self.tier_bands_layout.setSpacing(8)
        self.tier_bands_scroll.setWidget(self.tier_bands_content)
        layout.addWidget(self.tier_bands_scroll, 1)
        layout.addWidget(self.tier_table, 1)
        self.tier_table.hide()
        self.tier_empty = EmptyState(
            "TIER LIST / BẮT ĐẦU", "Chưa có nhân vật để xếp hạng",
            "Nhập tài khoản để chấm điểm nhân vật và quyết định ai tham gia lộ trình.",
            "Nhập tài khoản", self.snapshot_button.click)
        self.tier_empty.hide()
        layout.addWidget(self.tier_empty, 1)
        self.tier_search_feedback = QLabel()
        self.tier_search_feedback.setObjectName("searchFeedback")
        self.tier_search_feedback.setWordWrap(True)
        layout.addWidget(self.tier_search_feedback)
        self.pages.addWidget(page)


    def _configure_tier_columns(self, detailed):
        table = self.tier_table
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in {1: 84, 2: 70, 3: 150, 4: 180, 5: 150, 6: 210}.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(column, width)
        for column in (1, 2, 4, 5, 6):
            table.setColumnHidden(column, not detailed)


    def _tier_item_changed(self, item):
        if item.column() != 2:
            self._mark_tier_dirty()
            return
        try:
            score = int(item.text().strip()) if item.text().strip() else None
            label = "Chưa xếp" if score is None else label_for(score) if 0 <= score <= 100 else "Sai điểm"
        except ValueError:
            label = "Sai điểm"
        self.tier_table.blockSignals(True)
        self.tier_table.item(item.row(), 3).setText(label)
        invalid = label == "Sai điểm"
        color = QColor(COLORS["danger"] if invalid else COLORS["accent_hover"])
        item.setForeground(color)
        item.setToolTip("Nhập điểm từ 0 đến 100" if invalid else
                        "Nhấp đúp để chấm 0–100; để trống nếu chưa xếp hạng")
        self.tier_table.item(item.row(), 3).setForeground(color)
        self.tier_table.blockSignals(False)
        picker = self.tier_table.cellWidget(item.row(), 3)
        if picker is not None:
            picker.blockSignals(True)
            picker.setCurrentText(label if not invalid else "Chưa xếp")
            picker.blockSignals(False)
        self._update_tier_progress()
        self._mark_tier_dirty()


    def _tier_rank_selected(self, row, rank):
        # A chosen tier maps to its lowest valid score. Exact scores remain
        # available in "Tùy chọn thêm" for existing Tier Pack users.
        score = "" if rank == "Chưa xếp" else str(score_for_tier(rank))
        self.tier_table.item(row, 2).setText(score)


    def _mark_tier_dirty(self, *_args):
        if getattr(self, "_tier_loading", True):
            return
        try:
            current = self._tier_payload_from_table()
            saved = self._tier_saved_payload
            dirty = current != saved
            invalid = False
        except ValueError:
            dirty, invalid = True, True
        self._tier_dirty = dirty
        changed = 0
        if dirty and not invalid:
            for field in ("ratings", "controls", "selectedSets"):
                keys = set(current[field]) | set(saved[field])
                changed += sum(current[field].get(key) != saved[field].get(key) for key in keys)
            changed += current["minimumTierForRoadmap"] != saved["minimumTierForRoadmap"]
        self.tier_save_status.setText("Điểm phải từ 0 đến 100." if invalid else
                                      f"{changed} thay đổi chưa lưu · Lưu để cập nhật kế hoạch." if dirty else "")
        set_state(self.tier_save_status, "danger" if invalid else "warning" if dirty else "")
        self.tier_save_status.setVisible(dirty)
        self.tier_save_button.setText("Lưu thay đổi" if dirty else "Lưu")
        self.tier_save_button.setVisible(dirty)
        self.tier_undo_button.setVisible(dirty)
        self._rebuild_tier_bands()


    def _rebuild_tier_bands(self):
        if not hasattr(self, "tier_bands_layout") or getattr(self, "_tier_loading", True):
            return
        while self.tier_bands_layout.count():
            item = self.tier_bands_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        query = self.tier_search.text().strip().casefold()
        for rank in ("S+", "S", "A", "B", "C", "D", "Chưa xếp"):
            band = QFrame()
            band.setObjectName("surfaceCard")
            band_layout = QVBoxLayout(band)
            band_layout.setContentsMargins(16, 10, 16, 10)
            heading = QLabel(rank if rank != "Chưa xếp" else "Chưa chọn")
            heading.setObjectName("section")
            band_layout.addWidget(heading)
            cards = ResponsiveCardGrid(120, 5)
            found = False
            for row in range(self.tier_table.rowCount()):
                key = self.tier_table.item(row, 0).text()
                if query and query not in key.casefold():
                    continue
                if self.tier_table.item(row, 3).text() != rank:
                    continue
                found = True
                button = QPushButton(key)
                button.setToolTip(f"Chọn mức ưu tiên cho {key}")
                menu = QMenu(button)
                for choice in ("S+", "S", "A", "B", "C", "D", "Chưa xếp"):
                    menu.addAction(choice, lambda checked=False, row_index=row, value=choice:
                                   self._tier_rank_selected(row_index, value))
                button.setMenu(menu)
                cards.add_card(button)
            band_layout.addWidget(cards)
            band.setVisible(found or not query)
            self.tier_bands_layout.addWidget(band)
        self.tier_bands_layout.addStretch()


    def _update_tier_progress(self):
        total = self.tier_table.rowCount()
        ranked = sum(self.tier_table.item(row, 2) is not None and
                     self.tier_table.item(row, 2).text().strip().isdigit() and
                     int(self.tier_table.item(row, 2).text().strip()) <= 100
                     for row in range(total))
        owned = sum(self.tier_table.item(row, 1) is not None and
                    self.tier_table.item(row, 1).text() == "Sở hữu"
                    for row in range(total))
        invalid = sum(self.tier_table.item(row, 3) is not None and
                      self.tier_table.item(row, 3).text() == "Sai điểm"
                      for row in range(total))
        self.tier_progress.setText(
            f"Đã xếp hạng {ranked} / {total} nhân vật  ·  {owned} nhân vật sở hữu"
            + (f"  ·  {invalid} điểm không hợp lệ" if invalid else ""))
        set_state(self.tier_progress, "warning" if invalid else "")
        self.tier_progress.hide()


    def _render_tier_list(self):
        try:
            state = self.tier_pack_controller.load()
        except Exception as exc:
            has_rows = self.tier_table.rowCount() > 0
            self.tier_save_button.setEnabled(False)
            self.tier_table.setEnabled(False)
            self.tier_error_text.setText(
                "Không thể cập nhật Tier List. Bảng đang hiển thị dữ liệu trước đó.")
            self.tier_error_text.setToolTip(str(exc))
            self.tier_error_banner.setVisible(has_rows)
            if not has_rows:
                self.tier_empty.update_copy(
                    "Không thể tải Tier List",
                    "Thử lại hoặc nhập một tệp Tier List từ nút Tệp JSON.",
                    "Thử lại", self._render_tier_list)
                self.tier_empty.show()
                self.tier_table.hide()
            self.statusBar().showMessage("Không thể cập nhật Tier List · xem thông báo trong màn hình")
            return False
        self.tier_error_banner.hide()
        self.tier_save_button.setEnabled(True)
        self.tier_table.setEnabled(True)
        self.tier_empty.update_copy(
            "Chưa có nhân vật để xếp hạng",
            "Nhập tài khoản để chấm điểm nhân vật và quyết định ai tham gia lộ trình.",
            "Nhập tài khoản", self.snapshot_button.click)
        self._tier_pack_current = state["pack"]
        self._tier_loading = True
        self.tier_table.blockSignals(True)
        self.tier_table.setRowCount(len(state["rows"]))
        self.tier_minimum.setCurrentText(state["pack"]["minimumTierForRoadmap"])
        for index, row in enumerate(state["rows"]):
            for col, value in enumerate((row["characterKey"], "Sở hữu" if row["owned"] else "-",
                                         "" if row["score"] is None else str(row["score"]),
                                         "Chưa xếp" if row["score"] is None else row["tier"], row["notes"])):
                item = QTableWidgetItem(value)
                if col in (0, 1, 3):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 2:
                    item.setBackground(QColor(COLORS["elevated"]))
                    item.setForeground(QColor(COLORS["accent_hover"]))
                    item.setToolTip("Nhấp đúp để chấm 0–100; để trống nếu chưa xếp hạng")
                self.tier_table.setItem(index, col, item)
            rank_picker = QComboBox()
            rank_picker.setObjectName("tierRankPicker")
            rank_picker.addItems(["Chưa xếp", "S+", "S", "A", "B", "C", "D"])
            rank_picker.setCurrentText("Chưa xếp" if row["score"] is None else row["tier"])
            rank_picker.setAccessibleName(f"Hạng ưu tiên của {row['characterKey']}")
            rank_picker.setToolTip("Chọn hạng để ưu tiên nhân vật trong lộ trình")
            rank_picker.currentTextChanged.connect(
                lambda rank, row_index=index: self._tier_rank_selected(row_index, rank))
            self.tier_table.setCellWidget(index, 3, rank_picker)
            control = QComboBox()
            for label, value in (("Tự động", "NORMAL"),
                                 ("Luôn chọn", "FORCE_INCLUDE"), ("Không chọn", "IGNORE")):
                control.addItem(label, value)
            control.setCurrentIndex(max(0, control.findData(row["control"])))
            control.setToolTip("Quyết định nhân vật có được xét vào lộ trình hay không")
            control.currentIndexChanged.connect(self._mark_tier_dirty)
            self.tier_table.setCellWidget(index, 5, control)
            chosen = QComboBox(); chosen.addItem("Tự suy luận", "")
            for set_key in row["setOptions"]:
                chosen.addItem(set_key, set_key)
            if row["selectedSet"]:
                position = chosen.findData(row["selectedSet"])
                if position >= 0: chosen.setCurrentIndex(position)
            chosen.currentIndexChanged.connect(self._mark_tier_dirty)
            self.tier_table.setCellWidget(index, 6, chosen)
        self.tier_table.blockSignals(False)
        self._tier_saved_payload = self._tier_payload_from_table()
        self._tier_dirty = False
        self._tier_loading = False
        self._mark_tier_dirty()
        has_rows = bool(state["rows"])
        self.tier_table.setVisible(has_rows and self.tier_details_toggle.isChecked())
        self.tier_bands_scroll.setVisible(has_rows)
        self.tier_empty.setVisible(not has_rows)
        self._update_tier_progress()
        self._filter_tier_list()
        self._rebuild_tier_bands()
        self.statusBar().showMessage("Tier List đã tải lại")
        return True


    def _filter_tier_list(self):
        query = self.tier_search.text().strip().casefold()
        for row in range(self.tier_table.rowCount()):
            key = self.tier_table.item(row, 0).text().casefold()
            self.tier_table.setRowHidden(row, bool(query and query not in key))
        if hasattr(self, "tier_search_feedback"):
            total = self.tier_table.rowCount()
            visible = sum(not self.tier_table.isRowHidden(row) for row in range(total))
            self.tier_search_feedback.setText(
                "Không tìm thấy nhân vật. Thử từ khóa khác."
                if total and not visible else f"Hiển thị {visible} / {total} nhân vật"
            )
            self.tier_search_feedback.setVisible(bool(query))
        self._rebuild_tier_bands()


    def _tier_payload_from_table(self):
        ratings, controls, selected_sets = {}, {}, {}
        for row in range(self.tier_table.rowCount()):
            key = self.tier_table.item(row, 0).text()
            raw = self.tier_table.item(row, 2).text().strip()
            score = int(raw) if raw else None
            if score is not None and not 0 <= score <= 100:
                raise ValueError(f"{key}: điểm phải từ 0 đến 100")
            note = self.tier_table.item(row, 4).text()
            if score is not None or note.strip():
                ratings[key] = {"score": score, "notes": note}
            control = self.tier_table.cellWidget(row, 5).currentData()
            if control != "NORMAL": controls[key] = control
            selected = self.tier_table.cellWidget(row, 6).currentData()
            if selected: selected_sets[key] = selected
        return {"version": 1, "ratings": ratings,
                "minimumTierForRoadmap": self.tier_minimum.currentText(),
                "controls": controls, "selectedSets": selected_sets}


    def _save_tier_list(self):
        try:
            saved = self.tier_pack_controller.save(self._tier_payload_from_table())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Ưu tiên", str(exc)); return False
        self.statusBar().showMessage("Đã lưu ưu tiên · đang cập nhật kế hoạch…")
        self._tier_saved_payload = self._tier_payload_from_table()
        self._mark_tier_dirty()
        self.refresh()
        return True


    def _confirm_tier_discard(self, action):
        if not self._tier_dirty:
            return True
        prompt = QMessageBox(self)
        prompt.setWindowTitle("Ưu tiên chưa lưu")
        prompt.setText("Bạn có thay đổi mức ưu tiên chưa lưu.")
        save = prompt.addButton("Lưu và tiếp tục", QMessageBox.ButtonRole.AcceptRole)
        discard = prompt.addButton("Bỏ thay đổi", QMessageBox.ButtonRole.DestructiveRole)
        prompt.addButton("Quay lại", QMessageBox.ButtonRole.RejectRole)
        prompt.exec()
        if prompt.clickedButton() is save:
            return bool(self._save_tier_list())
        return prompt.clickedButton() is discard


    def _import_tier_list(self):
        path, _ = QFileDialog.getOpenFileName(self, "Nhập Tier List v1", "", "JSON (*.json)")
        if not path: return
        if not self._confirm_tier_discard("Nhập tệp"):
            return
        try:
            self.tier_pack_controller.import_file(path)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Tier List", str(exc)); return
        self._render_tier_list(); self.refresh()


    def _export_tier_list(self):
        path, _ = QFileDialog.getSaveFileName(self, "Xuất Tier List v1", "tier-pack.json", "JSON (*.json)")
        if not path: return
        try:
            self.tier_pack_controller.export_file(path, self._tier_payload_from_table())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Tier List", str(exc))


