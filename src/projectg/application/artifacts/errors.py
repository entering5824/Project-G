"""Application errors for artifact exchange workflows."""


class ArtifactExchangeError(ValueError):
    """Raised when an artifact exchange cannot be previewed or committed safely."""


class ArtifactDocumentError(ArtifactExchangeError):
    """Raised when an external AEF document violates the exchange contract."""

    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.field = field
