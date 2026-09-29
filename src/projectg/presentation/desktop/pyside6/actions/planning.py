from projectg.presentation.desktop.pyside6.dialog_shell import GlassDialog
"""Native desktop presentation: actions/planning."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QListWidget, QListWidgetItem, QInputDialog, QMessageBox, QSpinBox, QTextEdit, QVBoxLayout
from projectg.presentation.desktop.pyside6.dialogs import CharacterConfigDialog, HistoryDialog, SettingsDialog, SnapshotEditorDialog, TargetEditorDialog, TeamsDialog
from projectg.presentation.desktop.pyside6.workers import CharacterConfigWorker, PinWorker, SettingsWorker, SupportWorker, TargetPresetWorker, TeamsWorker
import logging
log = logging.getLogger(__name__)


class PlanningActions:
    def open_settings(self):
        self._run_settings()


    def _run_teams(self, rows: list[dict] | None = None):
        if self._loading:
            return
        self._loading = True; self._generation += 1
        generation = self._generation; self.teams_button.setEnabled(False)
        self.statusBar().showMessage("Đang lưu team…" if rows is not None else "Đang tải team…")
        worker = TeamsWorker(generation, self.teams_controller, rows)
        worker.signals.loaded.connect(lambda seq, result: self._teams_loaded(seq, result, rows is not None))
        worker.signals.failed.connect(self._teams_failed)
        self._workers.append(worker); self._pool.start(worker)


    def _teams_loaded(self, generation: int, result: dict, saving: bool):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear(); self.teams_button.setEnabled(True)
        if saving:
            self.statusBar().showMessage("Team configuration đã lưu. Đang tính lại…")
            self.refresh(); return
        dialog = TeamsDialog(result, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._run_teams(dialog.rows())


    def _teams_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear(); self.teams_button.setEnabled(True)
        self.statusBar().showMessage("Team configuration chưa thay đổi")
        QMessageBox.warning(self, "Teams", message)


    def preview_selected_pin(self):
        item = self.character_list.currentItem()
        if item and not self._loading:
            self._run_pin(item.text(), commit=False)


    def _selected_character_key(self) -> str | None:
        item = self.character_list.currentItem()
        return item.text() if item else None


    def open_character_config(self):
        character_key = self._selected_character_key()
        if character_key and not self._loading:
            self._run_character_config(character_key)


    def set_build_intent(self, state: str):
        key = self._selected_character_key()
        if not key or self.build_intent_controller is None:
            return
        try:
            self.build_intent_controller.set_personal_state(key, state)
            self.statusBar().showMessage("Đã cập nhật mục tiêu build. Đang tính lại…")
            self.refresh()
        except Exception as exc:
            log.exception("Could not save personal build intent")
            QMessageBox.warning(self, "Mục tiêu build", str(exc))


    def toggle_wants_build(self):
        key = self._selected_character_key()
        if not key:
            return
        current = ((self._data or {}).get("personalPriorities") or {}).get(key)
        self.set_build_intent("NORMAL" if current == "WANT_BUILD" else "WANT_BUILD")


    def edit_selected_artifact_rv(self):
        key = self._selected_character_key()
        if not key or not self._data:
            return
        rows = self._data.get("characters", [])
        characters = {}
        selected_row = None
        for row in rows:
            weapon = row.get("weapon")
            artifacts = {}
            for artifact in row.get("artifacts", []):
                value = {"setKey": artifact.get("set"), "rv": artifact.get("rv"),
                         "level": artifact.get("level", 20), "mainStat": artifact.get("mainStat")}
                artifacts[artifact["slot"]] = value
            characters[row["key"]] = {
                "level": row["level"], "ascension": row["ascension"], "constellation": row.get("constellation", 0),
                "weapon": ({"key": weapon["key"], "level": weapon["level"], "ascension": weapon.get("ascension", 0),
                            "refinement": weapon.get("refinement", 1)} if weapon else None),
                "talents": row["talents"], "artifacts": artifacts,
            }
            if row["key"] == key:
                selected_row = row
        if selected_row is None:
            return
        dialog = SnapshotEditorDialog(self)
        dialog.editor.setPlainText(json.dumps({"version": 1, "characters": characters}, ensure_ascii=False, indent=2))
        dialog.manual_key.setText(key)
        dialog.manual_level.setValue(min(100, max(1, int(selected_row.get("level", 1)))))
        dialog.manual_ascension.setValue(int(selected_row.get("ascension", 0)))
        dialog.manual_constellation.setValue(int(selected_row.get("constellation", 0)))
        for name, spin in dialog.manual_talents.items():
            spin.setValue(int(selected_row.get("talents", {}).get({"normal": "normal", "skill": "skill", "burst": "burst"}[name], 1)))
        weapon = selected_row.get("weapon")
        if weapon:
            dialog.manual_weapon.setText(weapon["key"])
            dialog.manual_weapon_level.setValue(weapon["level"])
            dialog.manual_weapon_ascension.setValue(int(weapon.get("ascension", 0)))
        for artifact in selected_row.get("artifacts", []):
            fields = dialog.manual_artifacts.get(artifact["slot"])
            if not fields:
                continue
            set_box, main_stat, known, rv, level = fields
            set_box.setText(artifact.get("set") or "")
            if main_stat:
                main_stat.setText(artifact.get("mainStat") or "")
            level.setValue(int(artifact.get("level", 20)))
            if artifact.get("rv") is not None:
                known.setChecked(True)
                rv.setValue(float(artifact["rv"]))
        dialog.tabs.setCurrentIndex(1)
        dialog.setWindowTitle(f"Điền RV · {key}")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._snapshot_payload = dialog.payload()
        self._run_snapshot(self._snapshot_payload, commit=False)


    def open_theater_preparation(self):
        if self.build_intent_controller is None:
            return
        data = self._data or {}
        config = ((data.get("roadmap") or {}).get("theaterPreparation") or {}).get("config") or {}
        dialog = GlassDialog(self)
        dialog.setWindowTitle("Chuẩn bị Nhà Hát Imaginarium")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Chọn đúng ba nguyên tố. Engine ưu tiên nhân vật đã đạt tiêu chuẩn build."))
        elements = sorted({row.get("element") for row in data.get("characters", []) if row.get("element")})
        checks = []
        for element in elements:
            box = QCheckBox(element)
            box.setChecked(element in config.get("elements", []))
            checks.append(box)
            layout.addWidget(box)
        form = QFormLayout()
        count = QSpinBox(); count.setRange(1, 100); count.setValue(int(config.get("requiredCharacters", 4)))
        form.addRow("Số nhân vật cần chuẩn bị", count)
        layout.addLayout(form)
        layout.addWidget(QLabel("Bạn có thể chọn nhân vật cụ thể; để trống danh sách thì engine tự đề xuất."))
        roster = QListWidget()
        roadmap_theater = ((data.get("roadmap") or {}).get("theaterPreparation") or {})
        selected = (set(config.get("selectedCharacters", [])) if config.get("manualSelection", bool(config.get("selectedCharacters")))
                    else set(roadmap_theater.get("selectedKeys", [])))
        roster_selection_changed = [False]
        ready = sum(1 for row in roadmap_theater.get("readiness", {}).values()
                    if row.get("status") == "READY")
        roster_summary = QLabel()
        layout.addWidget(roster_summary)
        def rebuild_roster(*_):
            selected.update(roster.item(i).text() for i in range(roster.count())
                            if roster.item(i).checkState() == Qt.CheckState.Checked)
            roster.clear()
            chosen = {box.text() for box in checks if box.isChecked()}
            matching = [row for row in data.get("characters", []) if row.get("element") in chosen]
            proposal = (set(config.get("selectedCharacters", [])) if config.get("manualSelection", bool(config.get("selectedCharacters")))
                        else set(roadmap_theater.get("selectedKeys", [])))
            ready_count = sum(1 for key in proposal
                              if (roadmap_theater.get("readiness", {}).get(key) or {}).get("status") == "READY")
            roster_summary.setText(
                f"Đề xuất: {len(proposal)}/{count.value()} · Đạt chuẩn: {ready_count}/{count.value()} · "
                f"Nhân vật thuộc nguyên tố đã chọn: {len(matching)}")
            for row in matching:
                item = QListWidgetItem(row["key"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if row["key"] in selected else Qt.CheckState.Unchecked)
                status = roadmap_theater.get("readiness", {}).get(row["key"], {})
                details = "; ".join(status.get("missing", [])) or "Đạt tiêu chuẩn build đã biết"
                item.setToolTip(f"{status.get('status', 'UNKNOWN')}: {details}")
                roster.addItem(item)
        roster.itemChanged.connect(lambda _item: roster_selection_changed.__setitem__(0, True))
        for box in checks:
            box.toggled.connect(rebuild_roster)
        count.valueChanged.connect(rebuild_roster)
        rebuild_roster()
        layout.addWidget(roster)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen_elements = [box.text() for box in checks if box.isChecked()]
        selected_keys = [roster.item(i).text() for i in range(roster.count())
                         if roster.item(i).checkState() == Qt.CheckState.Checked]
        try:
            self.build_intent_controller.save_theater({
                "elements": chosen_elements, "requiredCharacters": count.value(),
                "selectedCharacters": selected_keys,
                "manualSelection": roster_selection_changed[0] or bool(config.get("manualSelection", bool(config.get("selectedCharacters")))),
                "excludedCharacters": config.get("excludedCharacters", []),
            })
            self.refresh()
        except Exception as exc:
            log.exception("Could not save Theater preparation")
            QMessageBox.warning(self, "Chuẩn bị Nhà Hát", str(exc))


    def open_target_editor(self):
        if self._loading or not self._data:
            return
        characters = self._data.get("characters") or []
        if not characters:
            QMessageBox.information(self, "Target", "Import GOOD trước để tải danh sách nhân vật.")
            return
        selected_key = self._selected_character_key()
        if not selected_key:
            selected_key = characters[0].get("key")
        dialog = TargetEditorDialog(characters, selected_key, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            payload = dialog.payload()
        except ValueError as exc:
            QMessageBox.information(self, "Target", str(exc))
            return
        self._run_target(payload=payload, preview_only=True)


    def _run_character_config(self, character_key: str, payload: dict | None = None):
        if self._loading:
            return
        self._loading = True; self._generation += 1
        generation = self._generation
        for button in (self.character_config_button, self.create_preset_action,
                       self.activate_preset_action, self.pin_button, self.unpin_action):
            button.setEnabled(False)
        self.statusBar().showMessage("Đang lưu cấu hình nhân vật…" if payload else "Đang tải cấu hình nhân vật…")
        worker = CharacterConfigWorker(generation, self.character_configuration_controller,
                                       character_key, payload)
        worker.signals.loaded.connect(
            lambda seq, result: self._character_config_loaded(seq, character_key, result, payload is not None))
        worker.signals.failed.connect(self._character_config_failed)
        self._workers.append(worker); self._pool.start(worker)


    def _character_config_loaded(self, generation: int, character_key: str, result: dict, saving: bool):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        for button in (self.character_config_button, self.create_preset_action,
                       self.activate_preset_action, self.pin_button, self.unpin_action):
            button.setEnabled(True)
        if saving:
            self.statusBar().showMessage("Tier / priority đã lưu. Đang tính lại…")
            self.refresh(); return
        dialog = CharacterConfigDialog(result, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._run_character_config(character_key, dialog.payload())


    def _character_config_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        for button in (self.character_config_button, self.create_preset_action,
                       self.activate_preset_action, self.pin_button, self.unpin_action):
            button.setEnabled(True)
        self.statusBar().showMessage("Cấu hình nhân vật chưa thay đổi")
        QMessageBox.warning(self, "Character configuration", message)


    def create_selected_preset(self):
        character_key = self._selected_character_key()
        if not character_key or self._loading:
            return
        label, ok = QInputDialog.getText(self, "Tạo target preset",
                                         f"Tên preset mới cho {character_key}:")
        label = label.strip()
        if ok and label:
            self._run_target_preset(character_key, create_label=label)


    def activate_selected_preset(self):
        character_key = self._selected_character_key()
        if not character_key or self._loading or not self._data:
            return
        row = next((item for item in self._data.get("characters", [])
                    if item["key"] == character_key), None)
        presets = (row or {}).get("presets") or []
        if not presets:
            QMessageBox.information(self, "Target preset", "Nhân vật này chưa có target preset.")
            return
        labels = [f"{item['label']} ({item['key']})" + (" · active" if item.get("active") else "")
                  for item in presets]
        selected, ok = QInputDialog.getItem(self, "Đổi target preset",
                                             f"Preset active cho {character_key}:",
                                             labels, 0, False)
        if not ok:
            return
        index = labels.index(selected)
        preset = presets[index]
        if preset.get("active"):
            self.statusBar().showMessage("Preset này đang active.")
            return
        self._run_target_preset(character_key, activate_key=preset["key"])


    def _run_target_preset(self, character_key: str, *, create_label: str | None = None,
                           activate_key: str | None = None):
        if self._loading:
            return
        self._loading = True; self._generation += 1
        generation = self._generation
        for button in (self.character_config_button, self.create_preset_action,
                       self.activate_preset_action, self.pin_button, self.unpin_action):
            button.setEnabled(False)
        self.statusBar().showMessage("Đang cập nhật target preset…")
        worker = TargetPresetWorker(generation, character_key, self.target_controller,
                                    create_label=create_label, activate_key=activate_key)
        worker.signals.loaded.connect(self._target_preset_loaded)
        worker.signals.failed.connect(self._target_preset_failed)
        self._workers.append(worker); self._pool.start(worker)


    def _target_preset_loaded(self, generation: int, result: dict):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        for button in (self.character_config_button, self.create_preset_action,
                       self.activate_preset_action, self.pin_button, self.unpin_action):
            button.setEnabled(True)
        self.statusBar().showMessage("Target preset đã cập nhật. Đang tính lại…")
        self.refresh()


    def _target_preset_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        for button in (self.character_config_button, self.create_preset_action,
                       self.activate_preset_action, self.pin_button, self.unpin_action):
            button.setEnabled(True)
        self.statusBar().showMessage("Target preset chưa thay đổi")
        QMessageBox.warning(self, "Target preset", message)


    def _run_pin(self, character_key: str | None, *, commit: bool):
        if self._loading:
            return
        self._loading = True; self._generation += 1
        generation = self._generation
        self.pin_button.setEnabled(False); self.unpin_action.setEnabled(False)
        self.statusBar().showMessage("Đang lưu pin…" if commit else "Đang kiểm tra allocation conflict…")
        worker = PinWorker(generation, character_key, commit, self.planner_state_controller)
        worker.signals.loaded.connect(
            lambda seq, result: self._pin_loaded(seq, result, character_key, commit))
        worker.signals.failed.connect(self._pin_failed)
        self._workers.append(worker); self._pool.start(worker)


    def _pin_loaded(self, generation: int, result: dict, character_key: str | None, commit: bool):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        self.pin_button.setEnabled(True); self.unpin_action.setEnabled(True)
        if commit:
            self.statusBar().showMessage("Đã cập nhật pin Today. Đang tính lại…")
            self.refresh(); return
        conflicts = result["conflicts"]
        lines = [f"Pin {character_key} chỉ thay đổi lựa chọn Today.",
                 "Global Plan, tier và priority override vẫn giữ nguyên."]
        if result["candidate"]:
            lines.append("Task được đề xuất: " + result["candidate"]["title"])
        else:
            lines.append("Nhân vật hiện không có task khả dụng; pin vẫn được giữ để chờ target/data.")
        if conflicts:
            lines.append("\nALLOCATION CONFLICT:")
            lines.extend(f"{item['materialKey']}: strategic {item['strategicRequired']} + pin {item['pinnedRequired']} > available {item['available']}"
                         for item in conflicts)
        decision = QMessageBox.warning(self, "Allocation Conflict Preview", "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if decision == QMessageBox.StandardButton.Yes:
            self._run_pin(character_key, commit=True)


    def _pin_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        self.pin_button.setEnabled(True); self.unpin_action.setEnabled(True)
        self.statusBar().showMessage("Pin Today chưa thay đổi")
        QMessageBox.warning(self, "Pin Today", message)


    def _run_settings(self, payload: dict | None = None):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        self.settings_button.setEnabled(False); self.refresh_button.setEnabled(False)
        self.statusBar().showMessage("Đang lưu settings…" if payload else "Đang tải settings…")
        worker = SettingsWorker(generation, self.settings_controller, payload)
        worker.signals.loaded.connect(lambda seq, result: self._settings_loaded(seq, result, payload is not None))
        worker.signals.failed.connect(self._settings_failed)
        self._workers.append(worker); self._pool.start(worker)


    def _settings_loaded(self, generation: int, result: dict, saving: bool):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        self.settings_button.setEnabled(True); self.refresh_button.setEnabled(True)
        if saving:
            self.statusBar().showMessage("Settings đã lưu. Đang tính lại kế hoạch…")
            self.refresh()
            return
        dialog = SettingsDialog(result, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Đã hủy thay đổi settings")
            return
        try:
            payload = dialog.payload()
        except ValueError as exc:
            QMessageBox.warning(self, "Settings", str(exc))
            return
        self._run_settings(payload)


    def _settings_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear()
        self.settings_button.setEnabled(True); self.refresh_button.setEnabled(True)
        self.statusBar().showMessage("Settings chưa được thay đổi")
        QMessageBox.warning(self, "Settings", message)


    def _run_support(self, action: str, value: object = None):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        for button in (self.refresh_button, self.good_import_action, self.target_button,
                       self.artifact_button, self.history_button, self.health_button,
                       self.backup_button, self.restore_button):
            button.setEnabled(False)
        self.statusBar().showMessage("Đang xử lý…")
        worker = SupportWorker(generation, action, value, self.game_data_controller,
                               self.support_controller)
        worker.signals.loaded.connect(lambda seq, result: self._support_loaded(seq, action, result))
        worker.signals.failed.connect(self._support_failed)
        self._workers.append(worker)
        self._pool.start(worker)


    def _support_loaded(self, generation: int, action: str, result):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        for button in (self.refresh_button, self.good_import_action, self.target_button,
                       self.artifact_button, self.history_button, self.health_button,
                       self.backup_button, self.restore_button):
            button.setEnabled(True)
        if action == "history":
            dialog = HistoryDialog(result, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                pair = dialog.selected_pair()
                if pair and pair[0] != pair[1]:
                    self._run_support("history_compare", pair)
        elif action == "history_compare":
            summary = result.get("summary", {})
            lines = [
                f"Tổng thay đổi: {summary.get('totalChanges', 0)}",
                f"Nhân vật lên level: {summary.get('charactersLeveled', 0)}",
                f"Talent tăng: {summary.get('talentsUpgraded', 0)}",
                f"Weapon tăng: {summary.get('weaponsUpgraded', 0)}",
                f"Artifact loadout đổi: {summary.get('artifactLoadoutsChanged', 0)}",
                "",
            ]
            for change in result.get("changes", []):
                character = change.get("characterKey")
                prefix = f"{character} · " if character else ""
                lines.append(prefix + str(change.get("eventType", "CHANGE")))
            dialog = GlassDialog(self)
            dialog.setWindowTitle("So sánh snapshot")
            dialog.resize(760, 560)
            layout = QVBoxLayout(dialog)
            view = QTextEdit(); view.setReadOnly(True); view.setPlainText("\n".join(lines))
            layout.addWidget(view)
            close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            close.rejected.connect(dialog.reject); layout.addWidget(close)
            dialog.exec()
        elif action == "health":
            lines = [f"Trạng thái: {result['status']}",
                     f"Lỗi: {result['counts']['errors']} · Cảnh báo: {result['counts']['warnings']} · Thông tin: {result['counts']['info']}", ""]
            for issue in result["issues"]:
                lines.append(f"[{issue['severity']}] {issue['code']} ×{issue['count']}")
                lines.append(f"  Ảnh hưởng quyết định: {issue.get('decisionImpact', 'Chưa xác định')}")
                lines.append(f"  Hành động: {issue['action']}")
                if issue.get("details"):
                    lines.append("  Chi tiết: " + json.dumps(issue["details"], ensure_ascii=False))
            dialog = GlassDialog(self)
            dialog.setWindowTitle("Data Health")
            dialog.resize(760, 560)
            layout = QVBoxLayout(dialog)
            view = QTextEdit(); view.setReadOnly(True); view.setPlainText("\n".join(lines))
            layout.addWidget(view)
            dialog.exec()
        elif action == "gamedata_preview":
            meta = result.get("metadata") or {}
            cov = result.get("coverage") or {}
            acc = result.get("accountCoverage") or {}
            missing_chars = acc.get("missingCharacters") or []
            missing_weapons = acc.get("missingWeapons") or []
            lines = [
                f"Data version: {meta.get('dataVersion') or 'unknown'}",
                f"Game version: {meta.get('gameVersion') or 'unknown'}",
                f"Characters: {cov.get('characters', 0)} · Weapons: {cov.get('weapons', 0)} · Materials: {cov.get('materials', 0)}",
                f"Account coverage: {acc.get('knownCharacters', 0)}/{acc.get('ownedCharacters', 0)} characters · "
                f"{acc.get('knownWeapons', 0)}/{acc.get('equippedWeapons', 0)} equipped weapons",
            ]
            if missing_chars:
                lines.append("Thiếu character: " + ", ".join(missing_chars))
            if missing_weapons:
                lines.append("Thiếu weapon: " + ", ".join(missing_weapons))
            lines.append("\nPack hợp lệ. Cài đặt pack này? Pack hiện tại sẽ được backup trước khi replace.")
            if QMessageBox.question(
                self, "GameData preview", "\n".join(lines),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            ) == QMessageBox.StandardButton.Yes:
                self._run_support("gamedata_install", result["path"])
        elif action == "gamedata_install":
            meta = result.get("metadata") or {}
            account = result.get("accountCoverage") or {}
            QMessageBox.information(
                self, "GameData",
                f"Đã cài GameData {meta.get('dataVersion') or 'unknown'}.\n"
                f"Coverage account: {account.get('knownCharacters', 0)}/{account.get('ownedCharacters', 0)} characters.\n"
                f"Backup pack cũ: {result.get('backupPath') or 'không có'}",
            )
            self.refresh()
            return
        elif action == "gamedata_export":
            QMessageBox.information(self, "GameData", "Đã xuất pack:\n" + str(result.get("path")))
        elif action == "backup":
            self.statusBar().showMessage("Đã xuất backup: " + result["path"])
        elif action == "restore":
            self.statusBar().showMessage("Đã restore backup. Đang tính lại kế hoạch…")
            self.refresh()


    def _support_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        for button in (self.refresh_button, self.good_import_action, self.target_button,
                       self.artifact_button, self.history_button, self.health_button,
                       self.backup_button, self.restore_button):
            button.setEnabled(True)
        self.statusBar().showMessage("Thao tác không hoàn tất; dữ liệu hiện tại vẫn được giữ")
        QMessageBox.warning(self, "Genshin Planner", message)


