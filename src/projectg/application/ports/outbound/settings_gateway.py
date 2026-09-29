"""Contract for application-owned planner and account settings."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SettingsData:
    planner: dict[str, Any]
    planner_version: int
    artifact: dict[str, Any]
    artifact_configured: bool
    account: dict[str, Any]


class SettingsGateway(Protocol):
    def load(self) -> SettingsData: ...

    def commit_validated(
        self,
        planner: dict[str, Any],
        artifact: dict[str, Any],
        account: dict[str, Any] | None,
    ) -> SettingsData: ...
