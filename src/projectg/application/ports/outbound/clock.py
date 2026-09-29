"""Clock contract for use cases that need the current instant."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone aware instant."""
