from dataclasses import dataclass, field
from enum import StrEnum


class CostStatus(StrEnum):
    ESTIMATED = "ESTIMATED"
    COST_DATA_MISSING = "COST_DATA_MISSING"


@dataclass
class ResolvedCost:
    required_cost: dict[str, int]
    status: CostStatus
    flags: list[str] = field(default_factory=list)
    sources: dict[str, dict] = field(default_factory=dict)
    material_info: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"status": self.status.value, "requiredCost": self.required_cost,
                "flags": self.flags, "sources": self.sources, "materials": self.material_info}
