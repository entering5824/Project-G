"""Pure application projection for GameData pack metadata and coverage."""

from __future__ import annotations

from projectg.application.game_data.models import GameDataPackResult
from projectg.application.ports.outbound.game_data_account_gateway import AccountCatalogFacts
from projectg.application.ports.outbound.game_data_pack_storage import GameDataPackDocument
from projectg.domain.game_catalog.models import GameData


def metadata_view(data: GameData) -> dict:
    return {
        "schemaVersion": data.metadata.get("schema_version"),
        "gameVersion": data.metadata.get("game_version"),
        "dataVersion": data.metadata.get("data_version"),
        "generatedAt": data.metadata.get("generated_at"),
        "source": data.metadata.get("source"),
    }


def catalog_coverage(data: GameData) -> dict:
    return {
        "characters": len(data.characters),
        "weapons": len(data.weapons),
        "materials": len(data.materials),
        "characterCostPaths": sum(
            1 for steps in data.steps.values()
            if steps and steps[0].component.startswith("CHARACTER")
        ),
        "weaponCostPaths": sum(
            1 for steps in data.steps.values()
            if steps and steps[0].component.startswith("WEAPON")
        ),
        "talentCostPaths": sum(
            1 for steps in data.steps.values()
            if steps and steps[0].component.startswith("TALENT")
        ),
        "domains": len(data.domains),
        "artifactSets": len(data.artifact_sets),
    }


def account_coverage(data: GameData, facts: AccountCatalogFacts) -> dict:
    missing_characters = sorted(key for key in facts.character_keys if key not in data.characters)
    missing_weapons = sorted({key for key in facts.equipped_weapon_keys if key not in data.weapons})
    return {
        "ownedCharacters": len(facts.character_keys),
        "knownCharacters": len(facts.character_keys) - len(missing_characters),
        "missingCharacters": missing_characters,
        "equippedWeapons": len(facts.equipped_weapon_keys),
        "knownWeapons": len(facts.equipped_weapon_keys) - len(missing_weapons),
        "missingWeapons": missing_weapons,
    }


def build_pack_result(
    document: GameDataPackDocument,
    facts: AccountCatalogFacts,
    *,
    current: GameDataPackResult | None = None,
    backup_path: str | None = None,
) -> GameDataPackResult:
    return GameDataPackResult(
        path=document.path,
        metadata=metadata_view(document.data),
        coverage=catalog_coverage(document.data),
        account_coverage=account_coverage(document.data, facts),
        current=current,
        error=document.data.error,
        backup_path=backup_path,
    )
