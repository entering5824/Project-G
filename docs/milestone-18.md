# Milestone 18 — Planner persistence decomposition

SqlitePlannerGateway is a 37-line facade, reduced from 197 lines (160 lines removed,
81.2% reduction). It composes typed persistence facts through five independent readers.
Application prepare_planner_input, called by RunPlanner, continues to construct PlannerInput.
Team membership projection now belongs to application; SQLite returns stored team facts.
Snapshot and artifact facts contain dataclasses rather than nested untyped artifact dictionaries.
Fingerprint serialization, query filters/order, tier-pack defaults and planner semantics are preserved.
No ORM object crosses the planner port. No compatibility shim was introduced.

## Created

- src/projectg/infrastructure/persistence/sqlite/planner/__init__.py
- src/projectg/infrastructure/persistence/sqlite/planner/snapshot_reader.py
- src/projectg/infrastructure/persistence/sqlite/planner/configuration_reader.py
- src/projectg/infrastructure/persistence/sqlite/planner/team_reader.py
- src/projectg/infrastructure/persistence/sqlite/planner/tier_reader.py
- src/projectg/infrastructure/persistence/sqlite/planner/artifact_evaluation_reader.py
- tests/infrastructure/sqlite/test_planner_persistence_readers.py
- docs/milestone-18.md

## Modified

- src/projectg/infrastructure/persistence/sqlite/planner_gateway.py
- src/projectg/application/ports/outbound/planner_gateway.py
- src/projectg/application/planning/input.py
- tests/application/planning/test_planner_input.py
- tests/architecture/test_dependency_rules.py

## Deleted

None. Every pre-existing helper still has callers.
No target_reader.py was created: this planner gateway never queried stored targets.
Build targets remain derived from Build Knowledge by application policy. An empty reader
or adding persisted target consumption would add unnecessary structure or change semantics.

## Validation

Bundled Python executable:
C:/Users/Entering/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe

- Full pytest: 294 passed, 40 warnings, 9.05 seconds; exit 0.
  Command: python -m pytest -q --basetemp .pytest-temp-verified-m18 --tb=short
- Architecture tests: 68 passed; exit 0.
  Command: python -m pytest -q tests/architecture --basetemp .pytest-temp-arch-m18
- Compile: python -m compileall -q src tests scripts; exit 0.
- GameData: python scripts/validate_game_data.py; exit 0.
- Build Knowledge: python scripts/validate_build_profiles.py; exit 1.
  errors=[], missing=[], stale=[], verifiedBasic=127, verifiedStandard=0,
  verifiedDeep=0, recommendationsReady=true, releaseReady=false.
  The remaining release gate is Standard/Deep coverage, as allowed by this milestone.

The initial full run encountered temp-directory permissions; using a workspace basetemp
resolved setup errors. SQLAlchemy warnings concern the existing accounts/snapshots FK cycle
at fixture teardown. New tests also exercise that fixture; there are no failed tests.

Architecture guards restrict facade imports, prohibit query calls/comprehensions/loops,
require narrow model ownership and independent read-only readers, and keep production
PlannerInput construction outside infrastructure. Runtime tests recursively reject ORM
objects and consume facts after expunging ORM rows.

## Candidates for Milestone 19

- Type remaining raw/normalized artifact metric JSON and Build Knowledge payload boundaries
  once their supported schemas are explicitly defined.
- Decompose shared artifact service read/serialization helpers if reducing wider SQLite
  coupling becomes the next architectural focus; existing callers still require them.
- Expand verified Standard/Deep Build Knowledge coverage (content work, not a refactor regression).
- Resolve the existing account/snapshot foreign-key teardown warning separately.

The provided workspace has no .git directory, so no Git diff/status or commit was available.
