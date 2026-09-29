"""Translate support use cases into values for the desktop view."""

from projectg.application.use_cases.support.compare_history import CompareHistory, CompareHistoryRequest
from projectg.application.use_cases.backups.create_backup import CreateBackup, CreateBackupRequest
from projectg.application.use_cases.support.get_data_health import GetDataHealth
from projectg.application.use_cases.support.get_history import GetHistory
from projectg.application.use_cases.support.get_logs_directory import GetLogsDirectory
from projectg.application.use_cases.backups.restore_backup import RestoreBackup, RestoreBackupRequest


class SupportController:
    def __init__(self, history: GetHistory, compare: CompareHistory, health: GetDataHealth,
                 backup: CreateBackup, restore: RestoreBackup, logs: GetLogsDirectory):
        self._history, self._compare, self._health = history, compare, health
        self._backup, self._restore, self._logs = backup, restore, logs

    def history(self) -> dict:
        return self._history.execute().values

    def compare_history(self, before: str, after: str) -> dict:
        return self._compare.execute(CompareHistoryRequest(before, after)).values

    def data_health(self) -> dict:
        return self._health.execute().values

    def create_backup(self, destination: str) -> dict:
        return self._backup.execute(CreateBackupRequest(destination)).values

    def restore_backup(self, source: str) -> dict:
        return self._restore.execute(RestoreBackupRequest(source)).values

    def logs_directory(self) -> str:
        return self._logs.execute().path
