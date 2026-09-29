from dataclasses import dataclass
from typing import Any

from projectg.domain.planning.models import CharacterState

VALID = {"complete", "incomplete", "unknown", "invalid_target"}


@dataclass(frozen=True)
class CompletionResult:
    status: str
    components: dict[str, dict[str, Any]]

    @property
    def complete(self) -> bool:
        return self.status == "complete"


def evaluate_completion(state: CharacterState | None, target: dict | None, *,
                        artifact_status: str | None = None,
                        artifact_stale: bool = False) -> CompletionResult:
    if state is None:
        return CompletionResult("unknown", {"character": {"status": "unknown"}})
    if not isinstance(target, dict):
        return CompletionResult("invalid_target", {"target": {"status": "invalid_target"}})
    components = {}

    def numeric(name: str, current, required, minimum: int, maximum: int):
        if isinstance(required, bool) or not isinstance(required, int) or not minimum <= required <= maximum:
            components[name] = {"status": "invalid_target", "current": current, "target": required}
        else:
            components[name] = {"status": "complete" if current >= required else "incomplete",
                                "current": current, "target": required}

    numeric("level", state.level, target.get("level"), 1, 90)
    numeric("ascension", state.ascension, target.get("ascension"), 0, 6)
    talents = target.get("talents")
    if not isinstance(talents, dict):
        components["talents"] = {"status": "invalid_target"}
    else:
        for target_key, state_key in (("normal", "auto"), ("skill", "skill"), ("burst", "burst")):
            part = talents.get(target_key)
            if not isinstance(part, dict) or not isinstance(part.get("enabled"), bool):
                components[f"talent.{target_key}"] = {"status": "invalid_target"}
            elif part["enabled"]:
                numeric(f"talent.{target_key}", state.talents.get(state_key, 0),
                        part.get("target"), 1, 13)
    weapon_target = target.get("weapon")
    if not isinstance(weapon_target, dict):
        components["weapon"] = {"status": "invalid_target"}
    else:
        level = weapon_target.get("targetLevel")
        key = weapon_target.get("weaponKey")
        if key is not None and (not isinstance(key, str) or not key):
            components["weapon"] = {"status": "invalid_target", "targetWeaponKey": key}
        elif state.weapon is None:
            components["weapon"] = {"status": "unknown", "target": level,
                                    "targetWeaponKey": key}
        elif key and state.weapon.key != key:
            components["weapon"] = {"status": "incomplete", "reason": "weapon_mismatch",
                "currentWeaponKey": state.weapon.key, "targetWeaponKey": key,
                "current": state.weapon.level, "target": level}
        else:
            numeric("weapon", state.weapon.level, level, 1, 90)
            components["weapon"]["currentWeaponKey"] = state.weapon.key
            components["weapon"]["targetWeaponKey"] = key
    artifact = target.get("artifact")
    if not isinstance(artifact, dict):
        components["artifact"] = {"status": "invalid_target"}
    elif artifact.get("enabled"):
        gate = artifact.get("gate") or {}
        gate_failures = []
        if gate.get("minLevel") is not None and state.level < gate["minLevel"]:
            gate_failures.append("minLevel")
        if gate.get("minAscension") is not None and state.ascension < gate["minAscension"]:
            gate_failures.append("minAscension")
        if gate.get("weaponMinLevel") is not None:
            if state.weapon is None:
                gate_failures.append("weaponUnknown")
            elif state.weapon.level < gate["weaponMinLevel"]:
                gate_failures.append("weaponMinLevel")
        for name in gate.get("requiredTalents", []):
            target_key = str(name).lower().replace("talent_", "")
            state_key = {"normal": "auto"}.get(target_key, target_key)
            talent_target = (target.get("talents") or {}).get(target_key)
            if not talent_target or not talent_target.get("enabled"):
                gate_failures.append(f"talent.{target_key}.target")
            elif state.talents.get(state_key, 0) < talent_target.get("target", 1):
                gate_failures.append(f"talent.{target_key}")
        if gate_failures:
            status = "unknown" if "weaponUnknown" in gate_failures else "incomplete"
            components["artifact"] = {"status": status,
                "qualityStatus": artifact_status, "stale": artifact_stale,
                "gateFailures": gate_failures}
        elif artifact_stale or artifact_status in {None, "UNKNOWN", "NEEDS_QUALITY_CONFIG"}:
            components["artifact"] = {"status": "unknown", "stale": artifact_stale}
        elif artifact_status == "COMPLETE":
            components["artifact"] = {"status": "complete"}
        elif artifact_status in {"BELOW_TARGET"}:
            components["artifact"] = {"status": "incomplete"}
        else:
            components["artifact"] = {"status": "invalid_target", "qualityStatus": artifact_status}
    statuses = {value["status"] for value in components.values()}
    assert statuses <= VALID
    overall = ("invalid_target" if "invalid_target" in statuses else
               "incomplete" if "incomplete" in statuses else
               "unknown" if "unknown" in statuses else "complete")
    return CompletionResult(overall, components)
