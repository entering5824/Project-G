"""Native desktop presentation: workers."""
from PySide6.QtCore import QObject, QRunnable, Signal
import logging
log = logging.getLogger(__name__)


class WorkerSignals(QObject):
    loaded = Signal(int, object)
    failed = Signal(int, str)


class OverviewWorker(QRunnable):
    def __init__(self, generation: int, controller):
        super().__init__()
        self.generation = generation
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.loaded.emit(self.generation, self.controller.load())
        except Exception as exc:
            log.exception("Desktop overview calculation failed")
            self.signals.failed.emit(self.generation, str(exc))


class GoodWorker(QRunnable):
    def __init__(self, generation: int, path: str, controller, commit: bool, allow_regression: bool = False):
        super().__init__()
        self.generation = generation
        self.path = path
        self.controller = controller
        self.commit = commit
        self.allow_regression = allow_regression
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.commit_good_file(self.path, allow_regression=self.allow_regression)
                      if self.commit else self.controller.preview_good_file(self.path))
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("GOOD %s failed", "commit" if self.commit else "preview")
            self.signals.failed.emit(self.generation, str(exc))


class SnapshotWorker(QRunnable):
    def __init__(self, generation: int, payload: object, controller, *, commit: bool = False,
                 allow_regression: bool = False):
        super().__init__()
        self.generation, self.payload, self.commit = generation, payload, commit
        self.controller = controller
        self.allow_regression = allow_regression
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.commit_snapshot(self.payload, allow_regression=self.allow_regression)
                      if self.commit else self.controller.preview_snapshot(self.payload))
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("AccountSnapshot %s failed", "commit" if self.commit else "preview")
            self.signals.failed.emit(self.generation, str(exc))


class TargetWorker(QRunnable):
    def __init__(self, generation: int, *, path: str | None = None, payload: object = None,
                 selected: set[str] | None = None, operation_id: str | None = None,
                 preview_only: bool = False, controller=None):
        super().__init__()
        self.generation = generation
        self.path = path
        self.payload = payload
        self.selected = selected
        self.operation_id = operation_id
        self.preview_only = preview_only
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.preview_file(self.path) if self.path else
                      self.controller.preview_payload(self.payload) if self.preview_only else
                      self.controller.commit(self.payload, self.selected, self.operation_id))
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Target JSON %s failed", "preview" if self.path or self.preview_only else "commit")
            self.signals.failed.emit(self.generation, str(exc))


class ArtifactWorker(QRunnable):
    def __init__(self, generation: int, payload: object, *, snapshot_id: str | None = None,
                 rows: list[dict] | None = None, controller=None):
        super().__init__()
        self.generation, self.payload = generation, payload
        self.snapshot_id, self.rows = snapshot_id, rows
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.confirm(self.rows or [], self.snapshot_id or "")
                      if self.rows is not None else self.controller.preview(self.payload))
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Artifact evaluation operation failed")
            self.signals.failed.emit(self.generation, str(exc))


class SettingsWorker(QRunnable):
    def __init__(self, generation: int, controller, payload: dict | None = None):
        super().__init__()
        self.generation, self.payload = generation, payload
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.save(self.payload["planner"], self.payload["artifact"], self.payload["account"])
                      if self.payload is not None else self.controller.load())
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Settings operation failed")
            self.signals.failed.emit(self.generation, str(exc))


class PinWorker(QRunnable):
    def __init__(self, generation: int, character_key: str | None, commit: bool, controller=None):
        super().__init__()
        self.generation, self.character_key, self.commit = generation, character_key, commit
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.set_pin(self.character_key) if self.commit
                      else self.controller.preview_pin(self.character_key or ""))
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Today pin operation failed")
            self.signals.failed.emit(self.generation, str(exc))


class PlanRunWorker(QRunnable):
    def __init__(self, generation: int, run_id: str | None = None, controller=None):
        super().__init__()
        self.generation, self.run_id = generation, run_id
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.controller.replay_run(self.run_id) if self.run_id else self.controller.list_runs()
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("PlanRun operation failed")
            self.signals.failed.emit(self.generation, str(exc))


class TeamsWorker(QRunnable):
    def __init__(self, generation: int, controller, rows: list[dict] | None = None):
        super().__init__()
        self.generation, self.rows = generation, rows
        self.controller = controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.controller.save(self.rows) if self.rows is not None else self.controller.load()
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Team configuration failed")
            self.signals.failed.emit(self.generation, str(exc))


class CharacterConfigWorker(QRunnable):
    def __init__(self, generation: int, controller, character_key: str, payload: dict | None = None):
        super().__init__()
        self.generation = generation
        self.character_key = character_key
        self.controller = controller
        self.payload = payload
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = (self.controller.save(
                self.character_key,
                tier_key=self.payload.get("tierKey"),
                priority_override=self.payload["priorityOverride"],
            ) if self.payload is not None else
                self.controller.load(self.character_key))
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Character planner configuration failed")
            self.signals.failed.emit(self.generation, str(exc))


class TargetPresetWorker(QRunnable):
    def __init__(self, generation: int, character_key: str, controller, *,
                 create_label: str | None = None, activate_key: str | None = None):
        super().__init__()
        self.generation = generation
        self.character_key = character_key
        self.controller = controller
        self.create_label = create_label
        self.activate_key = activate_key
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.create_label is not None:
                result = self.controller.create_preset(self.character_key, self.create_label)
            elif self.activate_key is not None:
                result = self.controller.activate_preset(self.character_key, self.activate_key)
            else:
                raise ValueError("Preset operation is missing.")
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Target preset operation failed")
            self.signals.failed.emit(self.generation, str(exc))


class SupportWorker(QRunnable):
    def __init__(self, generation: int, action: str, value: object = None,
                 game_data_controller=None, support_controller=None):
        super().__init__()
        self.generation, self.action, self.value = generation, action, value
        self.game_data_controller = game_data_controller
        self.support_controller = support_controller
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.action == "history":
                result = self.support_controller.history()
            elif self.action == "history_compare":
                before, after = self.value
                result = self.support_controller.compare_history(before, after)
            elif self.action == "health":
                result = self.support_controller.data_health()
            elif self.action == "backup":
                result = self.support_controller.create_backup(str(self.value))
            elif self.action == "restore":
                result = self.support_controller.restore_backup(str(self.value))
            elif self.action == "gamedata_status":
                result = self.game_data_controller.status()
            elif self.action == "gamedata_preview":
                result = self.game_data_controller.preview(str(self.value))
            elif self.action == "gamedata_install":
                result = self.game_data_controller.install(str(self.value))
            elif self.action == "gamedata_export":
                result = self.game_data_controller.export(str(self.value))
            else:
                raise ValueError(f"Unsupported support action: {self.action}")
            self.signals.loaded.emit(self.generation, result)
        except Exception as exc:
            log.exception("Desktop support action failed: %s", self.action)
            self.signals.failed.emit(self.generation, str(exc))


