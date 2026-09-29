from projectg.presentation.desktop.pyside6.dialog_shell import GlassDialog
"""Native desktop presentation: dialogs."""
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QSplitter, QTabWidget, QTextEdit, QAbstractItemView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QScrollArea, QMenu, QHeaderView
from projectg.interface_adapters.controllers.desktop_reference_controller import target_contract_bundle, parse_snapshot


def _scrollable_form(form):
    """Keep long native forms usable when window height or DPI changes."""
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    container = QWidget()
    container.setLayout(form)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(container)
    scroll.setMinimumHeight(150)
    return scroll


def _form_sections(form, sections):
    """Separate long settings into task-focused tabs, retaining their controls."""
    tabs = QTabWidget()
    for title, count in sections:
        section = QFormLayout()
        section.setSpacing(14)
        for _ in range(count):
            row = form.takeRow(0)
            label = row.labelItem.widget()
            field = row.fieldItem.widget()
            section.addRow(label, field)
        tabs.addTab(_scrollable_form(section), title)
    return tabs


class TargetContractDialog(GlassDialog):
    """One stop prompt, paste, JSON-file, and preview handoff for target imports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhập Target JSON · tương thích dữ liệu cũ")
        self.resize(1000, 700)
        bundle = target_contract_bundle()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Sao chép hướng dẫn, dán JSON trả về hoặc mở tệp, rồi xem trước từng mục tiêu. "
            "Chỉ các dòng được chọn mới được lưu; mục tiêu bỏ chọn sẽ giữ nguyên."))
        self.prompt_view = QTextEdit(); self.prompt_view.setReadOnly(True)
        self.prompt_view.setPlainText(bundle["prompt"])
        self.json_view = QTextEdit()
        self.json_view.setPlaceholderText('Dán JSON trả về, ví dụ {"version":1,"targets":{...}}')
        tabs = QTabWidget()
        tabs.addTab(self.json_view, "Nhập JSON")
        tabs.addTab(self.prompt_view, "Prompt hướng dẫn")
        layout.addWidget(tabs, 1)
        actions = QHBoxLayout()
        reference = QPushButton("Sao chép tài liệu")
        reference_menu = QMenu(reference)
        reference_menu.addAction("Prompt", lambda: QApplication.clipboard().setText(bundle["prompt"]))
        reference_menu.addAction("JSON Schema", lambda: QApplication.clipboard().setText(
            json.dumps(bundle["schema"], ensure_ascii=False, indent=2)))
        reference_menu.addAction("Ví dụ JSON", lambda: QApplication.clipboard().setText(
            json.dumps(bundle["example"], ensure_ascii=False, indent=2)))
        reference.setMenu(reference_menu)
        paste_json = QPushButton("Dán clipboard")
        paste_json.clicked.connect(lambda: self.json_view.setPlainText(QApplication.clipboard().text()))
        open_file = QPushButton("Mở tệp JSON…")
        open_file.clicked.connect(self._open_json_file)
        actions.addWidget(reference)
        actions.addWidget(paste_json); actions.addWidget(open_file)
        actions.addStretch(); layout.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Xem trước mục tiêu")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _open_json_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mở Target JSON", "", "JSON (*.json);;All files (*)")
        if not path:
            return
        try:
            file = Path(path)
            if file.stat().st_size > 10 * 1024 * 1024:
                raise ValueError("Target JSON vượt quá 10 MiB.")
            self.json_view.setPlainText(file.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(self, "Target JSON", str(exc))

    def payload(self) -> object:
        raw = self.json_view.toPlainText()
        if len(raw.encode("utf-8")) > 10 * 1024 * 1024:
            raise ValueError("Target JSON vượt quá 10 MiB.")
        return json.loads(raw)


class SnapshotEditorDialog(GlassDialog):
    """Manual editor and file import for the versioned AccountSnapshot contract."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhập trạng thái tài khoản")
        self.resize(900, 680)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self.tabs = tabs
        json_tab = QWidget(); json_layout = QVBoxLayout(json_tab)
        json_layout.addWidget(QLabel("Dán Account Snapshot JSON hoặc mở tệp. Bộ thánh di vật đang kích hoạt sẽ được tính lại từ từng ô trang bị."))
        self.editor = QTextEdit()
        self.editor.setPlaceholderText('{"version":1,"characters":{"Mavuika":{"level":90,"ascension":6,"constellation":0,"weapon":{"key":"A Thousand Blazing Suns","level":90},"talents":{"normal":6,"skill":9,"burst":9},"artifacts":{},"activeSets":[]}}}')
        json_layout.addWidget(self.editor, 1)
        row = QHBoxLayout()
        open_file = QPushButton("Mở tệp Snapshot JSON…")
        open_file.clicked.connect(self.open_file)
        paste = QPushButton("Dán clipboard")
        paste.clicked.connect(lambda: self.editor.setPlainText(QApplication.clipboard().text()))
        row.addWidget(open_file); row.addWidget(paste); row.addStretch()
        json_layout.addLayout(row)
        tabs.addTab(json_tab, "JSON")
        form_tab = QWidget(); form_layout = QVBoxLayout(form_tab)
        form = QFormLayout()
        self.manual_key = QLineEdit(); self.manual_level = QSpinBox(); self.manual_level.setRange(1, 100); self.manual_level.setValue(90)
        self.manual_ascension = QSpinBox(); self.manual_ascension.setRange(0, 6); self.manual_ascension.setValue(6)
        self.manual_constellation = QSpinBox(); self.manual_constellation.setRange(0, 6)
        self.manual_weapon = QLineEdit(); self.manual_weapon_level = QSpinBox(); self.manual_weapon_level.setRange(1, 90); self.manual_weapon_level.setValue(90)
        self.manual_weapon_ascension = QSpinBox(); self.manual_weapon_ascension.setRange(0, 6); self.manual_weapon_ascension.setValue(6)
        self.manual_key.setPlaceholderText("Ví dụ: YaeMiko")
        form.addRow("Mã nhân vật", self.manual_key); form.addRow("Cấp độ", self.manual_level)
        form.addRow("Đột phá", self.manual_ascension); form.addRow("Cung mệnh", self.manual_constellation)
        weapon_row = QHBoxLayout(); weapon_row.addWidget(self.manual_weapon); weapon_row.addWidget(self.manual_weapon_level)
        form.addRow("Vũ khí / cấp độ", weapon_row)
        form.addRow("Đột phá vũ khí", self.manual_weapon_ascension)
        self.manual_talents = {}
        talent_row = QHBoxLayout()
        for name in ("normal", "skill", "burst"):
            spin = QSpinBox(); spin.setRange(1, 15); spin.setValue(1)
            self.manual_talents[name] = spin
            talent_row.addWidget(QLabel({"normal": "Đánh thường", "skill": "Kỹ năng", "burst": "Nộ"}[name]))
            talent_row.addWidget(spin)
        form.addRow("Thiên phú", talent_row)
        self.manual_artifacts = {}
        for slot in ("flower", "plume", "sands", "goblet", "circlet"):
            set_key = QLineEdit(); set_key.setPlaceholderText("Mã bộ (set key); để trống nếu chưa có món")
            main_stat = QLineEdit(); main_stat.setPlaceholderText("Chỉ số chính")
            known = QCheckBox("Có RV"); rv = QDoubleSpinBox(); rv.setRange(0, 5000); rv.setDecimals(1); rv.setEnabled(False)
            level = QSpinBox(); level.setRange(0, 20); level.setValue(20)
            known.toggled.connect(rv.setEnabled)
            slot_row = QHBoxLayout(); slot_row.addWidget(set_key)
            if slot in {"sands", "goblet", "circlet"}:
                slot_row.addWidget(main_stat)
            slot_row.addWidget(QLabel("Lv")); slot_row.addWidget(level)
            slot_row.addWidget(known); slot_row.addWidget(rv)
            form.addRow({"flower": "Hoa", "plume": "Lông", "sands": "Đồng hồ",
                         "goblet": "Ly", "circlet": "Nón"}[slot], slot_row)
            self.manual_artifacts[slot] = (set_key, main_stat, known, rv, level)
        form_layout.addWidget(_scrollable_form(form), 1)
        add_manual = QPushButton("Thêm / cập nhật nhân vật trong snapshot")
        add_manual.clicked.connect(self._append_manual_character)
        form_layout.addWidget(add_manual); form_layout.addStretch()
        tabs.addTab(form_tab, "Nhập thủ công")
        layout.addWidget(tabs, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Phân tích snapshot")
        buttons.accepted.connect(self._validate_and_accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mở Account Snapshot", "", "JSON (*.json);;All files (*)")
        if path:
            try:
                if Path(path).stat().st_size > 25 * 1024 * 1024:
                    raise ValueError("Snapshot JSON vượt quá 25 MiB.")
                self.editor.setPlainText(Path(path).read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, ValueError) as exc:
                QMessageBox.warning(self, "Account Snapshot", str(exc))

    def payload(self):
        return json.loads(self.editor.toPlainText())

    def _validate_and_accept(self):
        try:
            payload = self.payload()
            parse_snapshot(payload)
        except Exception as exc:
            QMessageBox.warning(self, "Account Snapshot", str(exc))
            return
        self.accept()

    def _append_manual_character(self):
        key = self.manual_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Account Snapshot", "Nhập canonical character key trước.")
            return
        try:
            payload = self.payload() if self.editor.toPlainText().strip() else {"version": 1, "characters": {}}
            if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(payload.get("characters"), dict):
                raise ValueError("JSON hiện tại không phải AccountSnapshot v1.")
            weapon_key = self.manual_weapon.text().strip()
            artifacts = {}
            for slot, (set_box, main_stat, known, rv, level) in self.manual_artifacts.items():
                set_key = set_box.text().strip()
                if set_key:
                    artifacts[slot] = {"setKey": set_key, "rv": rv.value() if known.isChecked() else None,
                                       "level": level.value(),
                                       "mainStat": main_stat.text().strip() or None}
            payload["characters"][key] = {"level": self.manual_level.value(), "ascension": self.manual_ascension.value(),
                "constellation": self.manual_constellation.value(),
                "weapon": ({"key": weapon_key, "level": self.manual_weapon_level.value(),
                            "ascension": self.manual_weapon_ascension.value()} if weapon_key else None),
                "talents": {name: spin.value() for name, spin in self.manual_talents.items()},
                "artifacts": artifacts}
            self.editor.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
            QMessageBox.information(self, "Account Snapshot", f"Đã thêm {key} vào snapshot JSON.")
        except Exception as exc:
            QMessageBox.warning(self, "Account Snapshot", str(exc))


class TargetSelectionDialog(GlassDialog):
    def __init__(self, preview: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Target JSON preview · partial commit")
        self.resize(760, 600)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Hợp lệ: {len(preview['validTargets'])} · "
                                f"Không hợp lệ: {len(preview['invalidTargets'])} · "
                                f"Không sở hữu: {len(preview['unknownCharacters'])} · "
                                f"Sẽ ghi mới/cập nhật: {preview.get('willCreateOrUpdate', 0)} · "
                                f"Ghi đè target hiện tại: {len(preview.get('overwrites', []))}"))
        layout.addWidget(QLabel("Chọn target cần commit. Bỏ chọn, lỗi hoặc nhân vật không sở hữu sẽ giữ nguyên."))
        self.items = QListWidget()
        details = {item["characterKey"]: item for item in preview.get("validTargetDetails", [])}
        for key in preview["validTargets"]:
            detail = details.get(key, {})
            target = detail.get("target") or {}
            previous_version = detail.get("currentVersion")
            version_label = f"ghi đè v{previous_version} → v{previous_version + 1}" if previous_version else "tạo v1"
            enabled_talents = [f"{name} {item['target']}" for name, item in
                               (target.get("talents") or {}).items() if item.get("enabled")]
            weapon = target.get("weapon") or {}
            artifact = target.get("artifact") or {}
            summary = (f"Lv {target.get('level', '?')}/A{target.get('ascension', '?')} · "
                       f"{' / '.join(enabled_talents) or 'không nâng talent'} · "
                       f"weapon Lv {weapon.get('targetLevel', '?')} · "
                       f"artifact {artifact.get('targetQuality', 'off') if artifact.get('enabled') else 'off'}")
            row = QListWidgetItem(f"{key} · {version_label} · {summary}")
            row.setData(Qt.ItemDataRole.UserRole, key)
            row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(Qt.CheckState.Checked)
            notes = (target.get("notes") or "").strip()
            row.setToolTip((summary + (f"\nGhi chú: {notes}" if notes else "")))
            self.items.addItem(row)
        layout.addWidget(self.items, 1)
        selection_actions = QHBoxLayout()
        select_all = QPushButton("Chọn tất cả hợp lệ")
        select_all.clicked.connect(lambda: [self.items.item(i).setCheckState(Qt.CheckState.Checked)
                                            for i in range(self.items.count())])
        select_none = QPushButton("Bỏ chọn tất cả")
        select_none.clicked.connect(lambda: [self.items.item(i).setCheckState(Qt.CheckState.Unchecked)
                                             for i in range(self.items.count())])
        selection_actions.addWidget(select_all); selection_actions.addWidget(select_none)
        selection_actions.addStretch(); layout.addLayout(selection_actions)
        warnings = [f"{item['characterKey']}: {item['message']} ({item['field']})"
                    for item in preview["invalidTargets"]]
        warnings.extend(f"Không sở hữu: {key}" for key in preview["unknownCharacters"])
        if warnings:
            info = QTextEdit()
            info.setReadOnly(True)
            info.setPlainText("\n".join(warnings))
            layout.addWidget(info)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Commit dòng đã chọn")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_keys(self) -> set[str]:
        return {self.items.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.items.count())
                if self.items.item(index).checkState() == Qt.CheckState.Checked}


class ArtifactSelectionDialog(GlassDialog):
    def __init__(self, preview: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xem trước đánh giá thánh di vật")
        self.resize(700, 540)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Hợp lệ: {preview['validCount']} · Tổng: {len(preview['evaluations'])}"))
        layout.addWidget(QLabel("Chọn các đánh giá hợp lệ để xác nhận. Dữ liệu chỉ được ghi sau bước này."))
        self.items = QListWidget()
        self.rows = {}
        messages = []
        for row in preview["evaluations"]:
            key = row.get("characterKey") or f"Dòng {row['index'] + 1}"
            quality = row.get("quality") or {}
            score = quality.get("normalizedScore")
            label = quality.get("qualityLabel") or quality.get("qualityStatus") or "unknown"
            item = QListWidgetItem(f"{key} · {label}" + (f" · {score:.2f}" if isinstance(score, (int, float)) else ""))
            if row["valid"]:
                item.setData(Qt.ItemDataRole.UserRole, row["index"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.rows[row["index"]] = row
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                messages.extend(f"{key}: {issue.get('message', issue.get('code'))}" for issue in row["errors"])
            messages.extend(f"{key}: {warning}" for warning in row["warnings"])
            self.items.addItem(item)
        layout.addWidget(self.items, 1)
        if messages:
            info = QTextEdit(); info.setReadOnly(True); info.setPlainText("\n".join(messages))
            layout.addWidget(info)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_rows(self) -> list[dict]:
        return [self.rows[self.items.item(index).data(Qt.ItemDataRole.UserRole)]
                for index in range(self.items.count())
                if self.items.item(index).data(Qt.ItemDataRole.UserRole) is not None
                and self.items.item(index).checkState() == Qt.CheckState.Checked]


class TeamsDialog(GlassDialog):
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý đội hình")
        self.resize(800, 580)
        layout = QVBoxLayout(self)
        imported = QTextEdit(); imported.setReadOnly(True); imported.setMaximumHeight(130)
        imported.setPlainText("Đội hình từ GOOD (chỉ xem):\n" + ("\n".join(
            f"{row['name']}: {', '.join(row['members'])}" for row in data["importedTeams"]) or "Không có"))
        layout.addWidget(imported)
        layout.addWidget(QLabel("Đội hình lập kế hoạch dùng mã nhân vật chuẩn. Chỉ một đội được chọn làm Đội chính."))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Tên", "Thành viên", "Đội chính"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setTabKeyNavigation(True)
        for row in data["configuredTeams"]:
            self._append(row["teamId"], row["name"], ", ".join(row["members"]), row.get("isPrimary", False))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setCurrentCell(0, 0) if self.table.rowCount() else None
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        add = QPushButton("Thêm đội"); remove = QPushButton("Xóa dòng")
        add.clicked.connect(lambda: self._append("", "", "", False))
        remove.clicked.connect(self._remove_selected)
        actions.addWidget(add); actions.addWidget(remove); actions.addStretch()
        layout.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _append(self, team_id: str, name: str, members: str, is_primary: bool):
        row = self.table.rowCount(); self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(team_id))
        self.table.setItem(row, 1, QTableWidgetItem(name))
        self.table.setItem(row, 2, QTableWidgetItem(members))
        primary = QTableWidgetItem("")
        primary.setFlags(primary.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        primary.setCheckState(Qt.CheckState.Checked if is_primary else Qt.CheckState.Unchecked)
        self.table.setItem(row, 3, primary)

    def _remove_selected(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def rows(self) -> list[dict]:
        result = []
        for index in range(self.table.rowCount()):
            value = lambda column: (self.table.item(index, column).text().strip()
                                    if self.table.item(index, column) else "")
            result.append({"teamId": value(0), "name": value(1),
                           "members": [item.strip() for item in value(2).split(",") if item.strip()],
                           "isPrimary": bool(self.table.item(index, 3) and
                                             self.table.item(index, 3).checkState() == Qt.CheckState.Checked)})
        return result


class PlanRunDialog(GlassDialog):
    def __init__(self, rows: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("PlanRun history")
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Chọn một decision đã ghi để replay bằng input và context lịch sử."))
        self.items = QListWidget()
        for row in rows:
            primary = row.get("primaryTask") or {}
            item = QListWidgetItem(f"{row['createdAt']} · {primary.get('title', 'Không có primary task')}")
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.items.addItem(item)
        if self.items.count(): self.items.setCurrentRow(0)
        layout.addWidget(self.items, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_run(self) -> str | None:
        item = self.items.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class HistoryDialog(GlassDialog):
    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("History")
        self.resize(820, 600)
        layout = QVBoxLayout(self)

        items = payload.get("items", [])
        groups = payload.get("groups") or {
            "accountProgress": [row for row in items if row.get("source") == "SNAPSHOT"],
            "targetConfigChanges": [row for row in items if row.get("source") == "CONFIG"],
            "completionChanges": [row for row in items if row.get("source") == "DERIVED"],
        }
        tabs = QTabWidget()
        for key, title, empty in (
            ("accountProgress", "Account progress", "Chưa có GOOD snapshot."),
            ("targetConfigChanges", "Targets & config", "Chưa có thay đổi target/cấu hình."),
            ("completionChanges", "Completion", "Chưa có chuyển trạng thái completion."),
        ):
            rows = groups.get(key, [])
            view = QTextEdit()
            view.setReadOnly(True)
            text = "\n".join(
                f"{item['when']} · {item['event']}" +
                (f" · {item['character']}" if item.get("character") else "")
                for item in rows
            )
            view.setPlainText(text or empty)
            tabs.addTab(view, f"{title} · {len(rows)}")
        layout.addWidget(QLabel(
            "Account progress = dữ liệu GOOD quan sát được. Completion được tính theo target hiện tại trên snapshot đã chọn; target/config edits nằm riêng."))
        layout.addWidget(tabs, 1)

        snapshots = payload.get("snapshots", [])
        if len(snapshots) >= 2:
            layout.addWidget(QLabel("So sánh hai GOOD snapshot:"))
            row = QHBoxLayout()
            self.before = QComboBox()
            self.after = QComboBox()
            for snapshot in reversed(snapshots):
                label = f"#{snapshot['snapshotIndex']} · {snapshot['when']}"
                self.before.addItem(label, snapshot["id"])
                self.after.addItem(label, snapshot["id"])
            # Default to the latest transition: previous -> current.
            self.before.setCurrentIndex(max(0, self.before.count() - 2))
            self.after.setCurrentIndex(self.after.count() - 1)
            row.addWidget(QLabel("Từ"))
            row.addWidget(self.before, 1)
            row.addWidget(QLabel("Đến"))
            row.addWidget(self.after, 1)
            layout.addLayout(row)
            compare = QPushButton("So sánh snapshot")
            compare.clicked.connect(self.accept)
            layout.addWidget(compare)
        else:
            self.before = self.after = None
            layout.addWidget(QLabel("Cần ít nhất hai snapshot để so sánh."))

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    def selected_pair(self) -> tuple[str, str] | None:
        if self.before is None or self.after is None:
            return None
        before = self.before.currentData()
        after = self.after.currentData()
        if not before or not after:
            return None
        return str(before), str(after)


class CharacterConfigDialog(GlassDialog):
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cấu hình kế hoạch · {data['characterKey']}")
        self.resize(520, 260)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.tier = QComboBox()
        self.tier.addItem("Chưa xếp hạng", None)
        for item in sorted(data["tiers"], key=lambda row: (int(row.get("order", 0)), row["key"])):
            self.tier.addItem(f"{item['label']} ({item['key']})", item["key"])
        current_tier = data.get("tierKey")
        for index in range(self.tier.count()):
            if self.tier.itemData(index) == current_tier:
                self.tier.setCurrentIndex(index)
                break
        self.priority = QComboBox()
        for label, value in (("Ưu tiên", "PRIORITIZED"), ("Bình thường", "NORMAL"),
                             ("Hạ ưu tiên", "DEPRIORITIZED")):
            self.priority.addItem(label, value)
        for index in range(self.priority.count()):
            if self.priority.itemData(index) == data.get("priorityOverride", "NORMAL"):
                self.priority.setCurrentIndex(index)
                break
        form.addRow("Hạng", self.tier)
        form.addRow("Ưu tiên riêng", self.priority)
        layout.addLayout(form)
        active = next((row for row in data.get("presets", []) if row.get("active")), None)
        layout.addWidget(QLabel("Preset đang dùng: " +
                                (f"{active['label']} ({active['key']})" if active else "chưa có target")))
        layout.addWidget(QLabel("Hạng và ưu tiên riêng thay đổi thứ tự lộ trình; ghim trên màn Tiếp theo là thiết lập riêng."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict:
        return {"tierKey": self.tier.currentData(),
                "priorityOverride": self.priority.currentData()}


class TargetEditorDialog(GlassDialog):
    """Form-based target authoring; commits still pass through the JSON preview flow."""
    def __init__(self, characters: list[dict], selected_key: str | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thiết lập mục tiêu nhân vật")
        self.resize(620, 720)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Chọn preset, chỉnh các mốc rồi chọn nhân vật áp dụng. Có thể sửa Tier/Priority và Team riêng ở màn Nhân vật."))
        self.preset = QComboBox()
        self.preset.addItem("DPS · Lv90 / E10 / Q9 / vũ khí 90", "DPS")
        self.preset.addItem("Support · Lv90 / E9 / Q9 / vũ khí 90", "SUPPORT")
        self.preset.addItem("Đầu tư cơ bản · Lv90 / vũ khí 90", "BASIC")
        layout.addWidget(self.preset)
        form = QFormLayout()
        self.level = QSpinBox(); self.level.setRange(1, 90); self.level.setValue(90)
        self.ascension = QSpinBox(); self.ascension.setRange(0, 6); self.ascension.setValue(6)
        form.addRow("Level", self.level); form.addRow("Đột phá", self.ascension)
        self.skill_on = QCheckBox("Đặt mục tiêu kỹ năng"); self.skill_on.setChecked(True)
        self.skill_level = QSpinBox(); self.skill_level.setRange(1, 10); self.skill_level.setValue(10)
        self.burst_on = QCheckBox("Đặt mục tiêu nộ"); self.burst_on.setChecked(True)
        self.burst_level = QSpinBox(); self.burst_level.setRange(1, 10); self.burst_level.setValue(9)
        self.normal_on = QCheckBox("Đặt mục tiêu đánh thường")
        self.normal_level = QSpinBox(); self.normal_level.setRange(1, 10); self.normal_level.setValue(1)
        form.addRow(self.normal_on, self.normal_level); form.addRow(self.skill_on, self.skill_level); form.addRow(self.burst_on, self.burst_level)
        self.weapon_level = QSpinBox(); self.weapon_level.setRange(1, 90); self.weapon_level.setValue(90)
        form.addRow("Vũ khí đến level", self.weapon_level)
        self.artifact_on = QCheckBox("Theo dõi mục tiêu chất lượng artifact")
        self.artifact_quality = QComboBox(); self.artifact_quality.addItems(["ACCEPTABLE", "GOOD", "EXCELLENT"]); self.artifact_quality.setCurrentText("GOOD")
        self.artifact_sets = QLineEdit(); self.artifact_sets.setPlaceholderText("Set key cách nhau bằng dấu phẩy (tùy chọn)")
        form.addRow(self.artifact_on, self.artifact_quality); form.addRow("Artifact set ưu tiên", self.artifact_sets)
        layout.addLayout(form)
        layout.addWidget(QLabel("Áp dụng cho các nhân vật đã chọn:"))
        self.characters = QListWidget()
        self.characters.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for character in characters:
            key = character["key"]
            item = QListWidgetItem(key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if key == selected_key else Qt.CheckState.Unchecked)
            self.characters.addItem(item)
        layout.addWidget(self.characters, 1)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        self._apply_preset()
        existing = next((row.get("target") for row in characters if row.get("key") == selected_key and row.get("target")), None)
        if existing:
            self.level.setValue(int(existing.get("level", 90)))
            self.ascension.setValue(int(existing.get("ascension", 6)))
            talents = existing.get("talents") or {}
            for name, enabled_box, level_box in (("normal", self.normal_on, self.normal_level),
                                                  ("skill", self.skill_on, self.skill_level),
                                                  ("burst", self.burst_on, self.burst_level)):
                item = talents.get(name) or {}
                enabled_box.setChecked(bool(item.get("enabled", False)))
                level_box.setValue(int(item.get("target", 1)))
            weapon = existing.get("weapon") or {}
            self.weapon_level.setValue(int(weapon.get("targetLevel", 90)))
            artifact = existing.get("artifact") or {}
            self.artifact_on.setChecked(bool(artifact.get("enabled", False)))
            quality = artifact.get("targetQuality", "GOOD")
            if quality in ("ACCEPTABLE", "GOOD", "EXCELLENT"):
                self.artifact_quality.setCurrentText(quality)
            self.artifact_sets.setText(", ".join(artifact.get("primarySets") or []))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_preset(self):
        preset = self.preset.currentData()
        self.level.setValue(90); self.ascension.setValue(6); self.weapon_level.setValue(90)
        self.normal_on.setChecked(preset == "DPS"); self.normal_level.setValue(9 if preset == "DPS" else 1)
        self.skill_on.setChecked(preset != "BASIC"); self.skill_level.setValue(10 if preset == "DPS" else 9)
        self.burst_on.setChecked(preset != "BASIC"); self.burst_level.setValue(9)

    def payload(self) -> dict:
        selected = [self.characters.item(i).text() for i in range(self.characters.count())
                    if self.characters.item(i).checkState() == Qt.CheckState.Checked]
        if not selected:
            raise ValueError("Chọn ít nhất một nhân vật.")
        sets = [value.strip() for value in self.artifact_sets.text().split(",") if value.strip()]
        target = {
            "level": self.level.value(), "ascension": self.ascension.value(),
            "importance": {"level": 1.0, "ascension": 1.0},
            "talents": {
                "normal": {"enabled": self.normal_on.isChecked(), "target": self.normal_level.value(), "importance": 1.0 if self.normal_on.isChecked() else 0.0},
                "skill": {"enabled": self.skill_on.isChecked(), "target": self.skill_level.value(), "importance": 1.0 if self.skill_on.isChecked() else 0.0},
                "burst": {"enabled": self.burst_on.isChecked(), "target": self.burst_level.value(), "importance": 1.0 if self.burst_on.isChecked() else 0.0}},
            "weapon": {"weaponKey": None, "targetLevel": self.weapon_level.value(), "importance": 0.8},
            "artifact": {"enabled": self.artifact_on.isChecked(), "targetQuality": self.artifact_quality.currentText(),
                         "importance": 0.8, "primarySets": sets, "alternativeSets": [],
                         "gate": {"minLevel": self.level.value(), "minAscension": self.ascension.value(),
                                  "weaponMinLevel": self.weapon_level.value(), "requiredTalents": [key for key, enabled in (("normal", self.normal_on.isChecked()), ("skill", self.skill_on.isChecked()), ("burst", self.burst_on.isChecked())) if enabled]}},
            "notes": ""}
        return {"version": 1, "targets": {key: target for key in selected}}


class SettingsDialog(GlassDialog):
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWindowTitle("Cài đặt tài khoản")
        self.resize(560, 620)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        account = data["account"]
        self.region = QComboBox(); self.region.addItems(["ASIA", "EUROPE", "AMERICA", "TW_HK_MO"])
        self.region.setCurrentText(account["serverRegion"]); form.addRow("Máy chủ", self.region)
        self.language = QLineEdit(account["gameLanguage"]); form.addRow("Ngôn ngữ trò chơi", self.language)
        self.world_level = QSpinBox(); self.world_level.setRange(0, 9); self.world_level.setValue(account["worldLevel"])
        form.addRow("Cấp thế giới", self.world_level)
        self.resin = QSpinBox(); self.resin.setRange(-1, 200); self.resin.setSpecialValueText("chưa rõ")
        self.resin.setValue(-1 if account["resin"] is None else account["resin"]); form.addRow("Nhựa hiện có", self.resin)
        self.weekly_claimed = QLineEdit(", ".join(account["weeklyClaimed"]))
        self.weekly_claimed.setPlaceholderText("Boss/source keys đã claim, phân cách dấu phẩy")
        form.addRow("Đã nhận trong tuần", self.weekly_claimed)
        self.unavailable_sources = QLineEdit(", ".join(account["unavailableSources"]))
        self.unavailable_sources.setPlaceholderText("Source keys tạm khóa, phân cách dấu phẩy")
        form.addRow("Nguồn tạm khóa", self.unavailable_sources)
        self.switch_threshold = QDoubleSpinBox()
        self.switch_threshold.setRange(0, 1000); self.switch_threshold.setDecimals(2)
        self.switch_threshold.setValue(float(data["planner"]["reorderThreshold"]))
        form.addRow("Ngưỡng đổi việc hôm nay", self.switch_threshold)
        self.manual_order_enabled = QCheckBox("Bật thứ tự thủ công trong cùng hạng")
        self.manual_order_enabled.setChecked(bool(data["planner"].get("manualOrderEnabled", False)))
        form.addRow("Sắp xếp thủ công", self.manual_order_enabled)
        self.manual_order = QLineEdit(", ".join(data["planner"].get("manualOrder", [])))
        self.manual_order.setPlaceholderText("Nahida, Yelan, Furina…")
        form.addRow("Thứ tự nhân vật", self.manual_order)
        self.adapter = QComboBox(); self.adapter.addItems(["rv", "cv", "rank_percent", "custom_score"])
        self.adapter.setCurrentText(data["artifact"]["adapterType"])
        form.addRow("Thước đo thánh di vật", self.adapter)
        self.thresholds = {}
        for label in ("POOR", "ACCEPTABLE", "GOOD", "EXCELLENT"):
            field = QLineEdit()
            value = data["artifact"]["thresholds"].get(label)
            field.setText("" if value is None else str(value))
            field.setPlaceholderText("để trống nếu chưa cấu hình")
            form.addRow(label, field); self.thresholds[label] = field
        self.sections = _form_sections(form, (("Tài khoản", 6), ("Kế hoạch", 3), ("Thánh di vật", 5)))
        layout.addWidget(self.sections, 1)
        explanation = QLabel("RV / CV / custom score: ngưỡng tăng dần. Akasha rankPercent là top %, ngưỡng giảm dần (nhỏ hơn tốt hơn).")
        explanation.setWordWrap(True)
        explanation.setObjectName("secondaryText")
        layout.addWidget(explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu cài đặt")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict:
        planner = dict(self.data["planner"])
        planner["reorderThreshold"] = self.switch_threshold.value()
        manual_order = [value.strip() for value in self.manual_order.text().split(",") if value.strip()]
        if len(manual_order) != len(set(manual_order)):
            raise ValueError("Manual order không được chứa character trùng nhau.")
        planner["manualOrderEnabled"] = self.manual_order_enabled.isChecked()
        planner["manualOrder"] = manual_order
        values = {key: field.text().strip() for key, field in self.thresholds.items()}
        if any(values.values()) and not all(values.values()):
            raise ValueError("Hãy nhập đủ cả bốn ngưỡng artifact hoặc để trống toàn bộ.")
        thresholds = {key: (float(value) if value else None) for key, value in values.items()}
        return {"planner": planner,
                "artifact": {"adapterType": self.adapter.currentText(), "thresholds": thresholds},
                "account": {"serverRegion": self.region.currentText(),
                    "gameLanguage": self.language.text().strip(), "worldLevel": self.world_level.value(),
                    "resin": None if self.resin.value() < 0 else self.resin.value(),
                    "weeklyClaimed": [value.strip() for value in self.weekly_claimed.text().split(",") if value.strip()],
                    "unavailableSources": [value.strip() for value in self.unavailable_sources.text().split(",") if value.strip()]}}


