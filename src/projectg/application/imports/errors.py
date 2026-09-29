"""Application-level account import failures."""


class DuplicateSnapshotError(Exception):
    """The effective account state is identical to the current snapshot."""


class AbnormalAccountChangeError(ValueError):
    def __init__(self, changes: list[dict]):
        super().__init__("GOOD import contains decreases in observed character progression")
        self.changes = changes


class ConcurrentAccountImportError(RuntimeError):
    """The current account snapshot changed between preparation and persistence."""
