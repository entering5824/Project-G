"""Application event dispatch contract."""

from typing import Protocol


class EventPublisher(Protocol):
    def publish(self, event: object) -> None:
        """Publish a completed domain or application event."""
