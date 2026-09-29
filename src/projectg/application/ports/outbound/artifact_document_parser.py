"""Port for translating external AEF documents into canonical evaluation rows."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ParsedArtifactEvaluation:
    index: int
    character_key: str | None
    metrics: dict[str, Any] | None
    errors: tuple[dict[str, Any], ...] = ()


class ArtifactDocumentParser(Protocol):
    def parse(self, payload: object) -> tuple[ParsedArtifactEvaluation, ...]: ...
