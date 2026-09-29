"""Port for translating external GOOD documents into canonical account state."""

from dataclasses import dataclass
from typing import Any, Protocol

from projectg.domain.account.models import NormalizedGood


@dataclass(frozen=True)
class PreparedAccountDocument:
    """Sanitized external document plus its canonical effective account state."""

    raw_content: bytes
    raw_hash: str
    canonical_hash: str
    effective_document: dict[str, Any]
    supplied_sections: frozenset[str]
    state: NormalizedGood
    importer_version: str


class AccountDocumentParser(Protocol):
    def prepare(
        self,
        content: bytes,
        *,
        previous_effective_document: dict[str, Any] | None,
    ) -> PreparedAccountDocument: ...
