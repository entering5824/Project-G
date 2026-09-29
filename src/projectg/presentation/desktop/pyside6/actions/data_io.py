from projectg.presentation.desktop.pyside6.dialog_shell import GlassDialog
"""Native desktop presentation: actions/data_io."""
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox, QTextEdit, QVBoxLayout
from projectg.presentation.desktop.result_export import export_results
from projectg.presentation.desktop.pyside6.dialogs import ArtifactSelectionDialog, PlanRunDialog, SnapshotEditorDialog, TargetContractDialog, TargetSelectionDialog
from projectg.presentation.desktop.pyside6.workers import ArtifactWorker, GoodWorker, PlanRunWorker, SnapshotWorker, TargetWorker


class DataActions:
    def import_account_file(self):
        """One entry point for account files; existing workers own preview and commit."""
        if self._loading:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn dữ liệu tài khoản", "", "Dữ liệu JSON (*.json);;Tất cả tệp (*)")
        self.import_account_path(path)

    def import_account_path(self, path):
        if self._loading or not path:
            return
        try:
            file_path = Path(path)
            if file_path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Tệp lớn hơn 32 MB. Hãy kiểm tra tệp xuất tài khoản.")
            payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            QMessageBox.warning(self, "Dữ liệu tài khoản", f"Không đọc được tệp: {exc}")
            return
        if isinstance(payload, dict) and payload.get("format") == "GOOD":
            self._run_good(path, commit=False)
        elif isinstance(payload, dict) and isinstance(payload.get("characters"), list):
            self._snapshot_payload = payload
            self._run_snapshot(payload, commit=False)
        else:
            QMessageBox.warning(self, "Dữ liệu tài khoản", "Không nhận diện được định dạng tệp.")

    def export_planner_results(self):
        if not self._data or self._data.get("snapshotId") is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất kết quả để đánh giá", datetime.now().strftime("ProjectG-results-%Y%m%d-%H%M%S.zip"),
            "Gói đánh giá (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            export_results(path, self._data)
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể xuất kết quả", str(exc))
            return
        self.statusBar().showMessage(f"Đã xuất kết quả: {path}")
        QMessageBox.information(self, "Đã xuất kết quả", "Gói đánh giá gồm report.md, results.json và review.md.\n" + path)


    def import_good(self):
        if self._loading:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Chọn GOOD snapshot", "", "JSON (*.json);;All files (*)")
        if path:
            self._run_good(path, commit=False)


    def import_snapshot(self):
        if self._loading:
            return
        dialog = SnapshotEditorDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._snapshot_payload = dialog.payload()
        self._run_snapshot(self._snapshot_payload, commit=False)


    def _run_snapshot(self, payload, *, commit: bool, allow_regression: bool = False):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        self.refresh_button.setEnabled(False)
        self.good_import_action.setEnabled(False)
        self.snapshot_button.setEnabled(False)
        self.statusBar().showMessage("Đang nhập dữ liệu tài khoản…" if commit else "Đang đọc dữ liệu tài khoản…")
        worker = SnapshotWorker(generation, payload, self.account_import_controller,
                                commit=commit, allow_regression=allow_regression)
        worker.signals.loaded.connect(lambda seq, result: self._snapshot_loaded(seq, payload, commit, result))
        worker.signals.failed.connect(self._snapshot_failed)
        self._workers.append(worker)
        self._pool.start(worker)


    def _snapshot_loaded(self, generation: int, payload, commit: bool, result: dict):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        if commit:
            self.statusBar().showMessage("Đã nhập dữ liệu tài khoản")
            self.refresh()
            return
        report = result.get("report") or {}
        lines = [f"Nhân vật: {result['characters']}",
                 f"Thánh di vật đang trang bị: {result['equippedArtifacts']}"]
        warnings = list(report.get("warnings") or [])
        if warnings:
            lines.extend(["", "Cảnh báo:", *(str(item) for item in warnings[:30])])
        regressions = result.get("abnormalChanges") or []
        if regressions:
            lines.extend(["", "Thay đổi progression giảm:", *(f"{row['characterKey']} {row['field']}: {row['before']} → {row['after']}" for row in regressions[:20])])
        if result.get("duplicate"):
            QMessageBox.information(self, "Dữ liệu tài khoản", "Tệp này giống dữ liệu hiện tại.")
            self.statusBar().showMessage("Snapshot không đổi")
            return
        if QMessageBox.question(self, "Xem trước dữ liệu tài khoản", "\n".join(lines) + "\n\nNhập và tính kế hoạch?") != QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage("Đã hủy import")
            return
        allow_regression = False
        if regressions:
            answer = QMessageBox.warning(self, "Xác nhận thay đổi progression",
            "Tệp mới có một số cấp hoặc thiên phú thấp hơn dữ liệu trước. Vẫn nhập dữ liệu này?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                self.statusBar().showMessage("Đã hủy import")
                return
            allow_regression = True
        self._run_snapshot(payload, commit=True, allow_regression=allow_regression)


    def _snapshot_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        self.statusBar().showMessage("Account Snapshot chưa được nhập")
        QMessageBox.warning(self, "Account Snapshot", message)


    def import_targets(self):
        if self._loading:
            return
        dialog = TargetContractDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            payload = dialog.payload()
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "Target JSON", f"JSON không hợp lệ: {exc.msg} (dòng {exc.lineno}).")
            return
        except ValueError as exc:
            QMessageBox.warning(self, "Target JSON", str(exc))
            return
        self._run_target(payload=payload, preview_only=True)


    def import_artifacts(self):
        if self._loading:
            return
        dialog = GlassDialog(self)
        dialog.setWindowTitle("Xác nhận artifact evaluation")
        dialog.resize(720, 560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Dán AEF JSON từ công cụ đánh giá artifact. Bản preview cho phép chọn từng dòng trước khi ghi."))
        editor = QTextEdit()
        editor.setPlaceholderText('{"format":"AEF","version":1,"evaluations":[...]}')
        layout.addWidget(editor, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            payload = json.loads(editor.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "Artifact evaluation", f"AEF JSON không hợp lệ: {exc.msg}")
            return
        self._run_artifact(payload)


    def open_logs(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.support_controller.logs_directory()))


    def open_history(self):
        self._run_support("history")


    def _run_plan_runs(self, run_id: str | None = None):
        if self._loading:
            return
        self._loading = True; self._generation += 1
        generation = self._generation; self.runs_button.setEnabled(False)
        self.statusBar().showMessage("Đang replay PlanRun…" if run_id else "Đang tải PlanRun…")
        worker = PlanRunWorker(generation, run_id, self.planner_state_controller)
        worker.signals.loaded.connect(lambda seq, result: self._plan_runs_loaded(seq, result, run_id))
        worker.signals.failed.connect(self._plan_runs_failed)
        self._workers.append(worker); self._pool.start(worker)


    def _plan_runs_loaded(self, generation: int, result, run_id: str | None):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear(); self.runs_button.setEnabled(True)
        if run_id:
            dialog = GlassDialog(self); dialog.setWindowTitle("PlanRun replay"); dialog.resize(820, 620)
            layout = QVBoxLayout(dialog)
            view = QTextEdit(); view.setReadOnly(True)
            view.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
            layout.addWidget(view); dialog.exec(); return
        dialog = PlanRunDialog(result, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_run():
            self._run_plan_runs(dialog.selected_run())


    def _plan_runs_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False; self._workers.clear(); self.runs_button.setEnabled(True)
        self.statusBar().showMessage("Không thể đọc PlanRun")
        QMessageBox.warning(self, "PlanRun", message)


    def open_data_health(self):
        self._run_support("health")


    def open_game_data(self):
        if self._loading:
            return
        current = self.game_data_controller.status()
        metadata = current.get("metadata") or {}
        coverage = current.get("coverage") or {}
        account = current.get("accountCoverage") or {}
        message = (
            f"GameData hiện tại: {metadata.get('dataVersion') or 'unknown'} · game {metadata.get('gameVersion') or 'unknown'}\n"
            f"Pack: {coverage.get('characters', 0)} nhân vật · {coverage.get('weapons', 0)} vũ khí · "
            f"{coverage.get('materials', 0)} material\n"
            f"Account: {account.get('knownCharacters', 0)}/{account.get('ownedCharacters', 0)} nhân vật · "
            f"{account.get('knownWeapons', 0)}/{account.get('equippedWeapons', 0)} weapon đang dùng được nhận diện.\n\n"
            "Chọn GameData pack JSON mới để preview/replace."
        )
        if QMessageBox.information(
            self, "GameData local", message,
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        ) != QMessageBox.StandardButton.Open:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Chọn GameData pack", "", "JSON (*.json);;All files (*)")
        if path:
            self._run_support("gamedata_preview", path)


    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Xuất backup", "GenshinPlanner-backup.zip",
                                               "ZIP backup (*.zip)")
        if path:
            self._run_support("backup", path)


    def restore_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Khôi phục backup", "", "ZIP backup (*.zip)")
        if not path:
            return
        result = QMessageBox.warning(self, "Khôi phục backup",
                                     "Dữ liệu local hiện tại sẽ được thay bằng backup đã chọn. Một backup trước restore sẽ được tạo tự động.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Cancel)
        if result == QMessageBox.StandardButton.Yes:
            self._run_support("restore", path)


    def _run_target(self, *, path: str | None = None, payload: object = None,
                    selected: set[str] | None = None, operation_id: str | None = None,
                    preview_only: bool = False):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        self.refresh_button.setEnabled(False)
        self.good_import_action.setEnabled(False)
        self.target_button.setEnabled(False)
        self.artifact_button.setEnabled(False)
        self.statusBar().showMessage("Đang kiểm tra Target JSON…" if path or preview_only else "Đang lưu target…")
        worker = TargetWorker(generation, path=path, payload=payload,
                              selected=selected, operation_id=operation_id,
                              preview_only=preview_only, controller=self.target_controller)
        worker.signals.loaded.connect(lambda seq, result: self._target_loaded(
            seq, result, path=path, preview_only=preview_only))
        worker.signals.failed.connect(self._target_failed)
        self._workers.append(worker)
        self._pool.start(worker)


    def _target_loaded(self, generation: int, result: dict, *, path: str | None,
                       preview_only: bool = False):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.target_button.setEnabled(True)
        self.artifact_button.setEnabled(True)
        if path is None and not preview_only:
            saved = result.get("saved", [])
            details = [f"Đã commit {len(saved)} target."]
            if saved:
                details.append("Đã lưu: " + ", ".join(item["characterKey"] for item in saved))
            if result.get("invalidTargets"):
                details.append(f"Giữ nguyên {len(result['invalidTargets'])} target lỗi.")
            if result.get("unknownCharacters"):
                details.append(f"Giữ nguyên {len(result['unknownCharacters'])} nhân vật không thuộc account.")
            self.statusBar().showMessage(f"Đã lưu {len(saved)} target")
            QMessageBox.information(self, "Target JSON", "\n".join(details))
            self.refresh()
            return
        preview = result["preview"]
        dialog = TargetSelectionDialog(preview, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Đã hủy Target import")
            return
        selected = dialog.selected_keys()
        if not selected:
            self.statusBar().showMessage("Chưa chọn target hợp lệ")
            return
        self._run_target(payload=result["payload"], selected=selected,
                         operation_id=str(uuid4()))


    def _target_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.target_button.setEnabled(True)
        self.artifact_button.setEnabled(True)
        self.statusBar().showMessage("Target import chưa thực hiện")
        QMessageBox.warning(self, "Target JSON", message)


    def _run_artifact(self, payload: object, *, snapshot_id: str | None = None,
                      rows: list[dict] | None = None):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        for button in (self.refresh_button, self.good_import_action, self.target_button,
                       self.artifact_button):
            button.setEnabled(False)
        self.statusBar().showMessage("Đang xác nhận artifact…" if rows is not None else "Đang kiểm tra artifact…")
        worker = ArtifactWorker(generation, payload, snapshot_id=snapshot_id, rows=rows,
                                controller=self.artifact_exchange_controller)
        worker.signals.loaded.connect(
            lambda seq, result: self._artifact_loaded(seq, result, confirming=rows is not None))
        worker.signals.failed.connect(self._artifact_failed)
        self._workers.append(worker)
        self._pool.start(worker)


    def _artifact_loaded(self, generation: int, result: dict, *, confirming: bool):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        for button in (self.refresh_button, self.good_import_action, self.target_button,
                       self.artifact_button):
            button.setEnabled(True)
        if confirming:
            self.statusBar().showMessage(f"Đã xác nhận {len(result['evaluations'])} artifact evaluation. Đang tính lại…")
            self.refresh()
            return
        dialog = ArtifactSelectionDialog(result, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Đã hủy artifact evaluation")
            return
        rows = dialog.selected_rows()
        if not rows:
            self.statusBar().showMessage("Chưa chọn artifact evaluation hợp lệ")
            return
        self._run_artifact(None, snapshot_id=result["snapshotId"], rows=rows)


    def _artifact_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        for button in (self.refresh_button, self.good_import_action, self.target_button,
                       self.artifact_button):
            button.setEnabled(True)
        self.statusBar().showMessage("Artifact evaluation chưa được ghi")
        QMessageBox.warning(self, "Artifact evaluation", message)


    def _run_good(self, path: str, *, commit: bool, allow_regression: bool = False):
        if self._loading:
            return
        self._loading = True
        self._generation += 1
        generation = self._generation
        self.refresh_button.setEnabled(False)
        self.snapshot_button.setEnabled(False)
        self.good_import_action.setEnabled(False)
        self.target_button.setEnabled(False)
        self.statusBar().showMessage("Đang nhập dữ liệu tài khoản…" if commit else "Đang đọc dữ liệu tài khoản…")
        worker = GoodWorker(generation, path, self.account_import_controller, commit, allow_regression)
        worker.signals.loaded.connect(lambda seq, result: self._good_loaded(seq, path, commit, result))
        worker.signals.failed.connect(self._good_failed)
        self._workers.append(worker)
        self._pool.start(worker)


    def _good_loaded(self, generation: int, path: str, commit: bool, result: dict):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.target_button.setEnabled(True)
        if commit:
            self.statusBar().showMessage("Đã nhập dữ liệu tài khoản")
            self.refresh()
            return
        if result["duplicate"]:
            QMessageBox.information(self, "Dữ liệu tài khoản", "Tệp này giống dữ liệu hiện tại.")
            self.statusBar().showMessage("Snapshot không đổi")
            return
        lines = [f"Nhân vật: {result['characters']}", f"Vũ khí: {result['weapons']}",
                 f"Thánh di vật đang trang bị: {result['equippedArtifacts']}",
                 f"Đội hình: {result['teams']}"]
        if result["warnings"]:
            lines.extend(["", "Cảnh báo:", *(str(item) for item in result["warnings"])])
        regressions = result["abnormalChanges"]
        if regressions:
            lines.extend(["", "GIẢM BẤT THƯỜNG:", *(f"{item['characterKey']} {item['field']}: {item['before']} → {item['after']}"
                                                    for item in regressions)])
        decision = QMessageBox.question(self, "Xem trước dữ liệu tài khoản", "\n".join(lines) + "\n\nNhập và tính kế hoạch?")
        if decision == QMessageBox.StandardButton.Yes:
            allow_regression = False
            if regressions:
                override = QMessageBox.warning(
                    self, "Xác nhận giảm progression",
                    "GOOD mới có level/talent thấp hơn snapshot hiện tại. Vẫn import và ghi nhận thay đổi này?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel)
                if override != QMessageBox.StandardButton.Yes:
                    self.statusBar().showMessage("Đã hủy import")
                    return
                allow_regression = True
            self._run_good(path, commit=True, allow_regression=allow_regression)
        else:
            self.statusBar().showMessage("Đã hủy import")


    def _good_failed(self, generation: int, message: str):
        if generation != self._generation:
            return
        self._loading = False
        self._workers.clear()
        self.refresh_button.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        self.good_import_action.setEnabled(True)
        self.target_button.setEnabled(True)
        self.statusBar().showMessage("GOOD import chưa thực hiện")
        QMessageBox.warning(self, "GOOD import", message)


