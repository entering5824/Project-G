# Local GameData dataset

The committed offline pack is generated from **`genshin-db@5.2.14` (Genshin 7.1)**. It covers 127 character entries (including Traveler variants), 253 weapons, 511 progression materials, six EXP item denominations, 86 domains, and 57 artifact-set domain mappings. The account export currently stored in `docs/Database_1_2026-09-23_07-22-11.json` is covered for all 84 characters and all 109 distinct weapon types it contains.

## Progression costs

- Character ascension and talent costs are built from the package's exact cost rows. Traveler ascension uses per-character rows because it has no normal-boss material; talent levels also retain their exact rows to handle regional exceptions.
- Weapon ascension costs are retained per weapon and phase, including low-rarity and event weapons with shorter or nonstandard material rows.
- Character EXP and weapon EXP use exact costs at the bundled level-band milestones. Weapon level paths cover rarities 1–5; 2-star and 5-star totals are included in the builder. If a current level falls inside a band, the resolver apportions that band's total evenly; those partial-band estimates are not level-by-level exact.
- Materials sharing a 3:1 crafting chain are grouped into craftable families. Family grouping is omitted if the upstream rows do not prove a consistent tier chain.

## Farm sources

- Talent, weapon-ascension, and artifact domains retain their entrance name, reward family, weekday group, and 20-Resin cost. Sundays remain open for every domain reward family.
- Normal bosses show their reward source and 40-Resin cost. Trounce domains show the weekly source; their reward costs 30 Resin for the first three weekly discounted claims and 60 thereafter.
- Ley lines cost 20 Resin. Mora and character EXP point to Blossoms of Wealth and Revelation; weapon EXP can be forged with enhancement ores or farmed from a Ley Line.
- Open-world specialties and enemy drops retain the package's source notes in the task output, with no Resin cost. These notes are upstream text and may be English even when the desktop UI is Vietnamese.
- The pack includes character EXP books and weapon enhancement ores as material definitions for calculating target progression costs. The app does not track owned material counts or reserves.

Character and weapon EXP reference tables are documented at [Character EXP](https://genshin-impact.fandom.com/wiki/Character_EXP) and [Weapon EXP](https://genshin-impact.fandom.com/wiki/Weapon_EXP). The package itself identifies the fandom wiki and GenshinData repository as its sources.

## Update and validation

Runtime reads `game_data.json` from disk and makes no network requests. To update the pack, download a pinned npm tarball and build from it:

```text
npm pack genshin-db@5.2.14
python scripts/build_gamedata_from_genshin_db.py genshin-db-5.2.14.tgz game_data.json --game-version 7.1 --data-version genshin-db-5.2.14
```

The converter also accepts `src/min/data.min.json` or a local source checkout. Validate the candidate before installing or replacing the pack:

```text
python scripts/validate_game_data.py
```

The package describes its sources as the fandom wiki and GenshinData repository. Keep this provenance with redistributed packs and review the applicable source terms before redistribution. No upstream package or external service is required at runtime.
