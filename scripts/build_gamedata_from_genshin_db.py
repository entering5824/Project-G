#!/usr/bin/env python3
"""Build an offline Planner GameData pack from a local genshin-db checkout.

No runtime networking is used by the planner.  This is a developer/update tool:

    python scripts/build_gamedata_from_genshin_db.py genshin-db-5.2.14.tgz out.json --game-version 7.1

The converter intentionally prefers verified upstream cost rows.  If a progression
family/path cannot be derived without guessing, it is omitted; Data Health will
report the missing coverage instead of silently inventing values.
"""
from __future__ import annotations

import argparse
import json
import re
import tarfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


WEAPON_LEVEL_COSTS = {
    2: [(1, 20, 36_400, 3_640), (20, 40, 186_825, 18_700),
        (40, 50, 188_425, 18_860), (50, 60, 278_300, 27_840),
        (60, 70, 389_725, 38_980)],
    5: [(1, 20, 121_550, 12_160), (20, 40, 622_800, 62_280),
        (40, 50, 628_150, 62_820), (50, 60, 927_675, 92_780),
        (60, 70, 1_299_125, 129_920), (70, 80, 1_750_375, 175_040),
        (80, 90, 3_714_775, 371_480)],
}


def canonical(name: str) -> str:
    # GOOD stable keys capitalize each token (e.g. ThrillingTalesOfDragonSlayers).
    # genshin-db titles often keep particles such as "of" lowercase.
    value = re.sub(r"['’]s\b", "s", str(name or ""), flags=re.IGNORECASE)
    return "".join(part[0].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", value))


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_folder(path: Path) -> list[dict]:
    return [read_json(item) for item in sorted(path.glob("*.json"))]


def load_source(source: Path) -> tuple[dict[str, list[dict]], str]:
    """Load either the source checkout or the published npm package/data bundle."""
    if source.is_dir():
        english = source / "src" / "data" / "English"
        required = ("characters", "talents", "weapons", "materials", "domains", "artifacts")
        missing = [str(english / name) for name in required if not (english / name).is_dir()]
        if missing:
            raise SystemExit("Missing genshin-db folders:\n" + "\n".join(missing))
        return {name: load_folder(english / name) for name in required}, "theBowja/genshin-db checkout"

    if source.suffix.lower() in {".tgz", ".gz"}:
        with tarfile.open(source, "r:gz") as archive:
            member = next((item for item in archive.getmembers()
                           if item.name.endswith("src/min/data.min.json")), None)
            if member is None:
                raise SystemExit("Package archive does not contain src/min/data.min.json")
            stream = archive.extractfile(member)
            if stream is None:
                raise SystemExit("Could not read packaged genshin-db data")
            bundle = json.load(stream)
            package_member = next((item for item in archive.getmembers()
                                   if item.name.endswith("package/package.json")), None)
            package_stream = archive.extractfile(package_member) if package_member else None
            package_meta = json.load(package_stream) if package_stream else {}
        source_name = f"genshin-db npm package {package_meta.get('version', 'unknown')}"
    else:
        bundle = read_json(source)
        source_name = "genshin-db data bundle"

    if "data" in bundle:
        bundle = bundle["data"]
    english = bundle.get("English") if isinstance(bundle, dict) else None
    if not isinstance(english, dict):
        raise SystemExit("Expected a genshin-db data.min.json bundle with data.English")
    required = ("characters", "talents", "weapons", "materials", "domains", "artifacts")
    missing = [name for name in required if not isinstance(english.get(name), dict)]
    if missing:
        raise SystemExit("Packaged GameData is missing categories: " + ", ".join(missing))
    return {name: list(english[name].values()) for name in required}, source_name


def day_group(days: list[str] | None) -> str | None:
    days = {str(day).upper() for day in (days or []) if str(day).upper() != "SUNDAY"}
    if days == {"MONDAY", "THURSDAY"}: return "MON_THU_SUN"
    if days == {"TUESDAY", "FRIDAY"}: return "TUE_FRI"
    if days == {"WEDNESDAY", "SATURDAY"}: return "WED_SAT"
    if not days: return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("genshin_db", type=Path,
                        help="local genshin-db checkout, npm .tgz package, or src/min/data.min.json")
    parser.add_argument("output", type=Path)
    parser.add_argument("--game-version", default="unknown")
    parser.add_argument("--data-version", default=None)
    args = parser.parse_args()

    source = args.genshin_db.resolve()
    source_data, source_name = load_source(source)
    characters_raw = source_data["characters"]
    talents_raw = {canonical(row.get("name")): row for row in source_data["talents"]}
    weapons_raw = source_data["weapons"]
    materials_raw = source_data["materials"]
    domains_raw = source_data["domains"]
    artifacts_raw = source_data["artifacts"]
    traveler = next((row for row in characters_raw if canonical(row.get("name")) == "Aether"), None)
    if traveler:
        for element in ("Anemo", "Geo", "Electro", "Dendro", "Hydro", "Pyro", "Cryo"):
            variant_key = canonical(f"Traveler {element}")
            if variant_key in talents_raw:
                variant = dict(traveler)
                variant["name"] = f"Traveler {element}"
                variant["elementText"] = element
                characters_raw.append(variant)
    material_by_id = {int(row["id"]): row for row in materials_raw if row.get("id") is not None}

    # Keep the planner's verified generic character/EXP paths as templates.
    bundled = read_json(Path(__file__).resolve().parents[1] / "data" / "static" / "genshin-impact" / "game_data.json")
    steps = {key: value for key, value in bundled.get("steps", {}).items()
             if key in {"character_level", "character_ascension", "talent"} or key.startswith("weapon_level_")}
    for rarity, ranges in WEAPON_LEVEL_COSTS.items():
        steps[f"weapon_level_{rarity}"] = [
            {"component": "WEAPON_LEVEL", "from_value": low, "to_value": high,
             "requirements": [{"material_key": "WeaponEXP", "amount": exp},
                              {"material_key": "Mora", "amount": mora}]}
            for low, high, exp, mora in ranges]

    materials: dict[str, dict] = {}
    families: dict[str, dict[int, str]] = defaultdict(dict)
    bosses: dict[str, dict] = {}
    domains: dict[str, dict] = {}

    def upstream_material(mid: int) -> dict | None:
        return material_by_id.get(int(mid))

    def ensure_material(mid: int, *, category: str, family: str | None = None,
                        tier: int | None = None, farmable: bool = True) -> str:
        raw = upstream_material(mid)
        if not raw:
            raise ValueError(f"Unknown upstream material id {mid}")
        key = canonical(raw.get("name"))
        source = {}
        if raw.get("dropDomainName"):
            source = {"type": "DOMAIN_TEXT", "name": raw["dropDomainName"]}
        elif raw.get("sources"):
            source = {"type": "SOURCE_TEXT", "sources": list(raw.get("sources") or [])}
        row = materials.setdefault(key, {
            "key": key, "name": raw.get("name") or key, "category": category,
            "rarity": raw.get("rarity"), "farmable": farmable, "source": source,
        })
        # A more specific progression classification wins over a generic one.
        row["category"] = category
        row["farmable"] = farmable
        if family is not None and tier is not None:
            row["family_key"] = family; row["tier"] = tier
            families[family][tier] = key
        return key

    # Synthetic aggregate resources remain explicit; inventory item optimizer maps
    # actual EXP books/ores separately.
    for key, name, category, source in (
        ("Mora", "Mora", "MORA", {"type":"LEY_LINE"}),
        ("CharacterEXP", "Character EXP equivalent", "CHARACTER_EXP", {"type":"LEY_LINE"}),
        ("WeaponEXP", "Weapon EXP equivalent", "WEAPON_EXP", {"type":"FORGE_OR_LEY_LINE"}),
    ):
        materials[key] = {"key":key,"name":name,"category":category,"source":source}
    # Keep the real GOOD inventory units alongside the planner's aggregate EXP
    # currencies so the user can reserve books and ores as actual items.
    for name, category, exp_value in (
        ("Wanderer's Advice", "CHARACTER_EXP_ITEM", 1_000),
        ("Adventurer's Experience", "CHARACTER_EXP_ITEM", 5_000),
        ("Hero's Wit", "CHARACTER_EXP_ITEM", 20_000),
        ("Enhancement Ore", "WEAPON_EXP_ITEM", 400),
        ("Fine Enhancement Ore", "WEAPON_EXP_ITEM", 2_000),
        ("Mystic Enhancement Ore", "WEAPON_EXP_ITEM", 10_000),
    ):
        raw = next((row for row in materials_raw if row.get("name") == name), None)
        materials[name] = {"key":name,"name":name,"category":category,"rarity":raw.get("rarity") if raw else None,
                           "farmable":True,"source":{"type":"EXP_ITEM"},"exp_value":exp_value}
    crown_raw = next((row for row in materials_raw if row.get("name") == "Crown of Insight"), None)
    if crown_raw:
        crown_key = ensure_material(crown_raw["id"], category="CROWN", farmable=False)
    else:
        crown_key = "CrownOfInsight"
        materials[crown_key] = {"key":crown_key,"name":"Crown of Insight","category":"CROWN","rarity":5,
                                "farmable":False,"source":{"type":"LIMITED_EVENT"}}

    def costs(row: dict, key: str) -> list[dict]:
        return list((row.get("costs") or {}).get(key) or [])

    characters = []
    for char in characters_raw:
        key = canonical(char.get("name"))
        c1, c2, c3, c4, c5, c6 = [costs(char, f"ascend{i}") for i in range(1, 7)]
        talent = talents_raw.get(key) or {}
        t2, t3, t7 = costs(talent, "lvl2"), costs(talent, "lvl3"), costs(talent, "lvl7")
        try:
            def non_mora(rows): return [item for item in rows if int(item.get("id", -1)) != 202]
            a1, a2, a3, a4, a5, a6 = map(non_mora, (c1,c2,c3,c4,c5,c6))
            is_traveler = key in {"Aether", "Lumine"} or key.startswith("Traveler")
            # Traveler ascensions do not consume a normal-boss drop. All other
            # characters follow the standard 4-item phase layout.
            valid_ascension = (len(a1) >= 3 and len(a2) >= 3 and len(a6) >= 3) if is_traveler else (
                len(a1) >= 3 and len(a2) >= 4 and len(a6) >= 4)
            if not (valid_ascension and len(non_mora(t2)) >= 2 and len(non_mora(t3)) >= 2 and len(non_mora(t7)) >= 3):
                continue
            gem_ids=[a1[0]["id"],a2[0]["id"],a4[0]["id"],a6[0]["id"]]
            enemy_ids=[a1[-1]["id"],a3[-1]["id"],a5[-1]["id"]]
            book_ids=[non_mora(t2)[0]["id"],non_mora(t3)[0]["id"],non_mora(t7)[0]["id"]]
            gem_family=f"Gem:{canonical((upstream_material(gem_ids[0]) or {}).get('name'))}"
            enemy_family=f"Enemy:{canonical((upstream_material(enemy_ids[0]) or {}).get('name'))}"
            book_names=[(upstream_material(mid) or {}).get("name", "") for mid in book_ids]
            suffixes=[re.sub(r"^(?:Teachings|Guide|Philosophies)\s+(?:of|to)\s+", "", name, flags=re.I)
                      for name in book_names]
            books_form_family=len(set(suffixes)) == 1 and all(suffixes)
            book_family=f"Talent:{canonical(book_names[0])}"
            gem_keys=[ensure_material(mid,category="CHARACTER_ASCENSION",family=gem_family,tier=i+1) for i,mid in enumerate(gem_ids)]
            enemy_keys=[ensure_material(mid,category="ENEMY_DROP",family=enemy_family,tier=i+1) for i,mid in enumerate(enemy_ids)]
            if books_form_family:
                book_keys=[ensure_material(mid,category="TALENT_BOOK",family=book_family,tier=i+1) for i,mid in enumerate(book_ids)]
            else:
                book_keys=[]
                for mid in book_ids:
                    material_key=canonical((upstream_material(mid) or {}).get("name"))
                    if material_key not in materials:
                        ensure_material(mid,category="TALENT_BOOK")
                    book_keys.append(material_key)
                book_family=materials[book_keys[0]].get("family_key") or book_family
            specialty=ensure_material(a1[1]["id"],category="LOCAL_SPECIALTY")
            boss_mat=None if is_traveler else ensure_material(a2[1]["id"],category="NORMAL_BOSS")
            weekly=ensure_material(non_mora(t7)[2]["id"],category="WEEKLY_BOSS")
            boss_key=f"Boss:{boss_mat}" if boss_mat else None; weekly_boss_key=f"Weekly:{weekly}"
            if boss_mat:
                boss_sources=list((upstream_material(a2[1]["id"]) or {}).get("sources") or [])
                materials[boss_mat]["source"]={"type":"NORMAL_BOSS","bossKey":boss_key,"sources":boss_sources}
            weekly_sources=list((upstream_material(non_mora(t7)[2]["id"]) or {}).get("sources") or [])
            materials[weekly]["source"]={"type":"WEEKLY_BOSS","bossKey":weekly_boss_key,"sources":weekly_sources}
            weekly_name=(upstream_material(non_mora(t7)[2]["id"]) or {}).get("sources", [weekly])[0] if upstream_material(non_mora(t7)[2]["id"]) else weekly
            if boss_mat:
                boss_name=(upstream_material(a2[1]["id"]) or {}).get("sources", [boss_mat])[0] if upstream_material(a2[1]["id"]) else boss_mat
                bosses[boss_key]={"key":boss_key,"name":boss_name,"reward_materials":[boss_mat],"resin_cost":40,"weekly_limited":False}
            bosses[weekly_boss_key]={"key":weekly_boss_key,"name":weekly_name,"reward_materials":[weekly],
                "resin_cost":30,"resin_cost_after_discount":60,"weekly_limited":True}
            characters.append({
                "key":key,"rarity":int(char.get("rarity") or 4),"element":str(char.get("elementText") or "UNKNOWN").upper(),
                "weapon_type":str(char.get("weaponText") or char.get("weaponType") or "UNKNOWN").upper(),
                "region":str(char.get("region") or "UNKNOWN").upper(),"local_specialty":specialty,
                "normal_boss_material":boss_mat,"enemy_material_family":enemy_family,
                "talent_book_family":book_family,"weekly_boss_materials":[weekly],"gem_family":gem_family,
                "material_keys":{"LOCAL_SPECIALTY":specialty,**({"BOSS":boss_mat} if boss_mat else {}),"ENEMY":enemy_family,
                                 "TALENT_BOOK":book_family,"WEEKLY":weekly,"GEM":gem_family},
            })
            if is_traveler:
                exact=[]
                for phase, raw_cost in enumerate((c1,c2,c3,c4,c5,c6)):
                    requirements=[]
                    for item in raw_cost:
                        mid=int(item["id"]); material_key="Mora" if mid==202 else canonical(item.get("name"))
                        if material_key != "Mora" and material_key not in materials:
                            ensure_material(mid,category="CHARACTER_ASCENSION")
                        requirements.append({"material_key":material_key,"amount":int(item["count"])})
                    exact.append({"component":"CHARACTER_ASCENSION","from_value":phase,"to_value":phase+1,"requirements":requirements})
                steps[f"character_ascension:{key}"]=exact
            exact_talent=[]
            for level in range(2,11):
                requirements=[]
                for item in costs(talent,f"lvl{level}"):
                    mid=int(item["id"]); material_key="Mora" if mid==202 else canonical(item.get("name"))
                    if material_key != "Mora" and material_key not in materials:
                        category="CROWN" if item.get("name") == "Crown of Insight" else "TALENT_BOOK"
                        ensure_material(mid,category=category,farmable=category!="CROWN")
                    requirements.append({"material_key":material_key,"amount":int(item["count"])})
                exact_talent.append({"component":"TALENT","from_value":level-1,"to_value":level,"requirements":requirements})
            steps[f"talent:{key}"]=exact_talent
            # Domain rows are generated from the lowest family member's metadata.
            for mid in book_ids:
                family=materials.get(canonical((upstream_material(mid) or {}).get("name")),{}).get("family_key")
                raw=upstream_material(mid) or {}; name=raw.get("dropDomainName")
                if name and family:
                    dkey=canonical(name); domains.setdefault(dkey,{"key":dkey,"name":name,"type":"TALENT",
                        "reward_material_families":[],"schedule_group":day_group(raw.get("daysOfWeek")),"resin_cost":20})
                    if family not in domains[dkey]["reward_material_families"]: domains[dkey]["reward_material_families"].append(family)
        except (KeyError, IndexError, TypeError, ValueError):
            continue

    weapons = []
    emitted_weapon_keys: set[str] = set()
    for weapon in weapons_raw:
        key=canonical(weapon.get("name")); asc=[costs(weapon,f"ascend{i}") for i in range(1,7)]
        if key in emitted_weapon_keys:
            continue
        if not asc[0]:
            continue
        try:
            non=lambda rows:[item for item in rows if int(item.get("id",-1))!=202]
            rows=[non(x) for x in asc]
            rarity=int(weapon.get("rarity") or 1)
            max_level=70 if rarity <=2 else 90
            domain_family = enemy_a = enemy_b = None
            domain_ids = []
            # Six-phase weapons with the standard material layout can be grouped
            # into craftable families. Retain exact rows for shorter or unusual
            # event-weapon paths without fabricating those family relationships.
            if len(asc) == 6 and all(len(row) >= 3 for row in rows):
                domain_ids=[rows[0][0]["id"],rows[1][0]["id"],rows[3][0]["id"],rows[5][0]["id"]]
                enemy_a_ids=[rows[0][1]["id"],rows[2][1]["id"],rows[4][1]["id"]]
                enemy_b_ids=[rows[0][2]["id"],rows[2][2]["id"],rows[4][2]["id"]]
                domain_family=f"WeaponDomain:{canonical((upstream_material(domain_ids[0]) or {}).get('name'))}"
                enemy_a=f"Enemy:{canonical((upstream_material(enemy_a_ids[0]) or {}).get('name'))}"
                enemy_b=f"Enemy:{canonical((upstream_material(enemy_b_ids[0]) or {}).get('name'))}"
                for i,mid in enumerate(domain_ids): ensure_material(mid,category="WEAPON_ASCENSION",family=domain_family,tier=i+1)
                for i,mid in enumerate(enemy_a_ids): ensure_material(mid,category="ENEMY_DROP",family=enemy_a,tier=i+1)
                for i,mid in enumerate(enemy_b_ids): ensure_material(mid,category="ENEMY_DROP",family=enemy_b,tier=i+1)
            weapons.append({"key":key,"name":weapon.get("name") or key,"rarity":rarity,
                "weapon_type":str(weapon.get("weaponText") or weapon.get("weaponType") or "UNKNOWN").upper(),
                "weapon_ascension_material_family":domain_family,"enemy_material_family":enemy_a,"max_level":max_level})
            exact=[]
            for phase, raw_cost in enumerate(asc):
                req=[]
                for item in raw_cost:
                    mid=int(item["id"]); amount=int(item["count"])
                    mkey="Mora" if mid==202 else canonical((upstream_material(mid) or {}).get("name"))
                    if mkey and mkey not in materials and mid!=202:
                        ensure_material(mid,category="ENEMY_DROP")
                    elif mkey and mid!=202 and not domain_family:
                        ensure_material(mid,category="WEAPON_ASCENSION")
                    req.append({"material_key":mkey,"amount":amount})
                exact.append({"component":"WEAPON_ASCENSION","from_value":phase,"to_value":phase+1,"requirements":req})
            steps[f"weapon_ascension:{key}"]=exact
            emitted_weapon_keys.add(key)
            raw=upstream_material(domain_ids[0]) or {} if domain_ids else {}; name=raw.get("dropDomainName")
            if name and domain_family:
                dkey=canonical(name); domains.setdefault(dkey,{"key":dkey,"name":name,"type":"WEAPON",
                    "reward_material_families":[],"schedule_group":day_group(raw.get("daysOfWeek")),"resin_cost":20})
                if domain_family not in domains[dkey]["reward_material_families"]: domains[dkey]["reward_material_families"].append(domain_family)
        except (KeyError, IndexError, TypeError, ValueError):
            continue

    # Add deterministic 3->1 recipes after every family has been discovered.
    for family, tiers in families.items():
        for tier, key in sorted(tiers.items()):
            if tier <= 1: continue
            lower=tiers.get(tier-1)
            if lower:
                materials[key]["craft_recipe"]={"from_material":lower,"consume_amount":3,"produce_amount":1}

    # Resolve domains from the reward IDs in the packaged payload. Older checkout
    # JSON may instead carry dropDomainName directly on materials.
    material_key_by_id = {int(row["id"]): canonical(row.get("name"))
                          for row in materials_raw if row.get("id") is not None}
    for raw in domains_raw:
        preview = raw.get("rewardPreview") or []
        text = str(raw.get("domainText") or "").lower()
        kind = ("TALENT" if "talent" in text else "WEAPON" if "weapon" in text
                else "ARTIFACT" if "artifact" in text else None)
        entrance = raw.get("entranceName") or raw.get("name")
        if not kind or not entrance:
            continue
        dkey = canonical(entrance)
        entry = domains.setdefault(dkey, {"key": dkey, "name": entrance, "type": kind,
            "reward_material_families": [], "schedule_group": day_group(raw.get("daysOfWeek")),"resin_cost":20})
        for reward in preview:
            rid = reward.get("id")
            reward_key = material_key_by_id.get(int(rid)) if rid is not None else None
            family = materials.get(reward_key, {}).get("family_key") if reward_key else None
            if family and family not in entry["reward_material_families"]:
                entry["reward_material_families"].append(family)

    # Best-effort artifact-domain mapping: only map a set when the package lists
    # that exact set in a domain's reward preview.
    artifact_sets=[]
    domain_text=[(row, json.dumps(row, ensure_ascii=False)) for row in domains_raw]
    for artifact in artifacts_raw:
        name=artifact.get("name"); key=canonical(name)
        matched=next((row for row,text in domain_text if name and name in text),None)
        if not matched: continue
        dname=matched.get("entranceName") or matched.get("name") or matched.get("nameText") or canonical(str(matched.get("id") or "ArtifactDomain"))
        dkey=canonical(dname)
        domains.setdefault(dkey,{"key":dkey,"name":dname,"type":"ARTIFACT","reward_material_families":[],"schedule_group":"DAILY","resin_cost":20})
        artifact_sets.append({"key":key,"name":name,"domain_key":dkey})

    output={
        "metadata":{"schema_version":1,"game_version":args.game_version,
                    "data_version":args.data_version or f"genshin-db-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                    "generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
                    "source":f"Generated offline from {source_name}; licensed dataset components and source notes in data/static/genshin-impact/README.md"},
        "materials":sorted(materials.values(),key=lambda x:x["key"]),
        "characters":sorted(characters,key=lambda x:x["key"]),
        "weapons":sorted(weapons,key=lambda x:x["key"]),
        "domains":sorted(domains.values(),key=lambda x:x["key"]),
        "bosses":sorted(bosses.values(),key=lambda x:x["key"]),
        "steps":steps,"artifact_sets":sorted(artifact_sets,key=lambda x:x["key"]),
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {args.output}: {len(characters)} characters, {len(weapons)} weapons, {len(materials)} materials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
