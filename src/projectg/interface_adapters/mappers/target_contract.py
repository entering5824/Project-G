"""Versioned Target JSON contract and ChatGPT-Web handoff helpers."""

from __future__ import annotations

import json
from pydantic import BaseModel, ConfigDict

from projectg.interface_adapters.schemas.requests import CharacterTargetRequest


class _TargetDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: int
    targets: dict[str, CharacterTargetRequest]


def target_json_schema() -> dict:
    schema = _TargetDocument.model_json_schema(by_alias=True)
    schema["title"] = "Genshin Planner Target Import v1"
    schema["properties"]["version"] = {"const": 1, "type": "integer", "title": "Version"}
    schema["required"] = ["version", "targets"]
    schema["additionalProperties"] = False
    return schema


def target_json_example() -> dict:
    return {
        "version": 1,
        "targets": {
            "Nahida": {
                "level": 90,
                "ascension": 6,
                "importance": {"level": 1.0, "ascension": 1.0},
                "talents": {
                    "normal": {"enabled": False, "target": 1, "importance": 0.0},
                    "skill": {"enabled": True, "target": 10, "importance": 1.0},
                    "burst": {"enabled": True, "target": 9, "importance": 0.75},
                },
                "weapon": {"weaponKey": "AThousandFloatingDreams", "targetLevel": 90, "importance": 0.8},
                "artifact": {
                    "enabled": True,
                    "targetQuality": "GOOD",
                    "importance": 0.8,
                    "primarySets": ["DeepwoodMemories"],
                    "alternativeSets": [],
                    "gate": {
                        "minLevel": 90,
                        "minAscension": 6,
                        "weaponMinLevel": 90,
                        "requiredTalents": ["skill", "burst"],
                    },
                },
                "notes": "",
            }
        },
    }


def chatgpt_target_prompt() -> str:
    schema = json.dumps(target_json_schema(), ensure_ascii=False, indent=2)
    example = json.dumps(target_json_example(), ensure_ascii=False, indent=2)
    return f"""Bạn đang tạo Target JSON để import vào Genshin Account Progression Planner.

Nhiệm vụ:
- Chuyển mục tiêu build tôi mô tả thành JSON đúng contract bên dưới.
- Chỉ quyết định target theo yêu cầu của tôi; không tự ép mọi nhân vật 90/10/10/10.
- Không tính Mora/material/cost/farm route. App tự tính những phần đó.
- Không thêm nhân vật tôi không yêu cầu.
- Giữ version = 1 và targets là object keyed by canonical character name.
- normal/skill/burst luôn phải có đủ ba entry.
- enabled=false nghĩa là talent đó không tham gia completion; target vẫn phải là số hợp lệ.
- importance dùng số 0..1: 1.0 = chính, khoảng 0.5-0.8 = phụ, 0 = bỏ qua.
- weaponKey có thể null nếu tôi chỉ quan tâm level của weapon đang cầm.
- Nếu không chắc một giá trị do yêu cầu của tôi chưa rõ, đừng tự đoán kín đáo: ghi chú vấn đề trong notes hoặc hỏi tôi trước khi xuất JSON.
- Khi đã đủ thông tin, output CHỈ JSON, không markdown fence, không giải thích ngoài JSON.

JSON Schema v1:
{schema}

Ví dụ hợp lệ:
{example}
"""


def target_contract_bundle() -> dict:
    return {
        "version": 1,
        "schema": target_json_schema(),
        "example": target_json_example(),
        "prompt": chatgpt_target_prompt(),
    }
