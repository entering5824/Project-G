"""Pure application policy for preparing account-import decisions."""

from dataclasses import dataclass

from projectg.application.ports.outbound.account_document_parser import PreparedAccountDocument
from projectg.application.ports.outbound.account_import_gateway import AccountImportContext
from projectg.domain.account.regression import detect_progression_regressions


SECTIONS = ("characters", "weapons", "artifacts", "teams")


@dataclass(frozen=True)
class AccountImportDecision:
    coverage: dict[str, str]
    duplicate: bool
    regressions: tuple[dict, ...]


def evaluate_account_import(
    context: AccountImportContext,
    document: PreparedAccountDocument,
    *,
    next_snapshot_id: str | None = None,
) -> AccountImportDecision:
    """Evaluate duplicate/regression/coverage semantics without persistence concerns."""
    coverage: dict[str, str] = {}
    for section in SECTIONS:
        if section in document.supplied_sections:
            coverage[section] = next_snapshot_id or "CURRENT"
        elif context.current_snapshot_id is not None:
            coverage[section] = context.coverage.get(section, context.current_snapshot_id)

    regressions = detect_progression_regressions(
        context.previous_characters,
        context.previous_weapons,
        document.state,
    ) if context.current_snapshot_id else []

    return AccountImportDecision(
        coverage=coverage,
        duplicate=(
            context.current_snapshot_id is not None
            and context.current_canonical_hash is not None
            and context.current_canonical_hash == document.canonical_hash
        ),
        regressions=tuple(regressions),
    )
