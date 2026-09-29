# Desktop architecture

This document is the architecture contract for the native desktop application.
The dependency rule is absolute: source dependencies point inward. Inner layers do not import or name outer layers.

```text
presentation -> interface_adapters -> application -> domain
infrastructure ---------------------> application ports -> domain
bootstrap -> all concrete layers
```

The canonical Python package is **only** `src/projectg/`. The historical `backend/app` package has been removed from the repository and from packaging/test import paths.

## Layer responsibilities

### `domain/` — enterprise/domain rules

Contains planning, target validation/preset policy, artifact evaluation, completion, cost, account-state, and game-catalog rules and types.

Constraints:

- standard library only;
- no PySide6, SQLAlchemy, Pydantic, Alembic, filesystem, JSON transport parsing, networking, or SQLite;
- no global `datetime.now()`, `date.today()`, or UUID generation;
- no imports from application or any outer layer.

External facts such as time or generated identifiers enter through application ports or explicit values.

### `application/` — use cases and ports

Owns user actions, request/response models, and abstractions required by those actions.

Important areas include:

- `ports/` — `Clock`, ID generation, persistence, file storage, transaction/event and feature-specific gateways;
- `use_cases/imports/` — typed account import workflows;
- `use_cases/settings/` — settings query/save workflows;
- `use_cases/teams/` and `use_cases/characters/` — team and character configuration;
- `use_cases/game_data/` — local GameData status/preview/install/export;
- `use_cases/artifacts/` — artifact exchange preview and confirmation;
- `use_cases/planner_state/` — PlanRun history/replay and Today pin state;
- `use_cases/targets/` plus `application/targets/` — target import preview/selection/idempotency validation and preset workflows;
- `tier_packs/`, `support/`, and `overview/` — remaining application actions.

Constraints:

- may import `domain` and application-owned code only;
- no driver/framework imports;
- no direct filesystem/database/environment I/O;
- no concrete infrastructure selection;
- time/IDs/external state arrive through ports.

### `interface_adapters/` — boundary translation

Owns translation between external/UI representations and application/domain values.

Examples:

- GOOD and AccountSnapshot mappers;
- strict external request schemas;
- TierPack JSON translation;
- presenters/view-model shaping where required.

Adapters may depend inward on `application` and `domain`, but do not choose SQLite, filesystem, or Qt implementations.

### `infrastructure/` — frameworks and drivers

Implements application-owned outbound ports.

Current drivers include:

- `persistence/sqlite/` — SQLAlchemy rows, sessions, repositories, persistence mapping, typed read-side fact gateways, validated account/target adapters, a centralized transaction-effects Unit of Work, and SQLite-specific backup database mechanics; planner execution, account-import duplicate/regression/coverage policy, GOOD parsing/merge rules, target validation/import policy, preset-key policy, cost policy, health policy, artifact status policy, snapshot-diff policy, backup-format policy, and ZIP archive mechanics are deliberately outside this package;
- `game_data/json/` — GameData loading/normalization/validation, local pack management, and build-profile loading;
- `filesystem/` — external file storage operations;
- `serialization/` — transport/exchange serialization;
- `clock/` and `ids/` — operating-system time and UUID adapters;
- `configuration/` — environment-backed runtime settings.

Infrastructure may depend on application ports and domain types. The application layer never imports these concrete implementations.

### `presentation/desktop/pyside6/` — UI driver

Contains the native Qt presentation. UI code invokes application-facing controllers/use cases and consumes boundary/view models. It does not issue SQL, read GameData files, or instantiate repositories.

### `bootstrap/` — composition root

This is the intentional outermost exception. It may import all concrete layers in order to assemble the application.

Runtime configuration, desktop environment preparation, migrations, controller construction, and concrete dependency wiring belong here. Concrete adapters should not be instantiated inside domain/application code.

## Static data and runtime data

Repository-owned immutable/offline data:

```text
data/static/genshin-impact/game_data.json
data/static/builds/build_profiles.json
data/static/tier-packs/*.json
assets/genshin-impact/
```

Development defaults use `data/runtime/`, which is git-ignored. Native Windows execution overrides runtime paths to `%LOCALAPPDATA%\GenshinPlanner` during bootstrap.

`desktop_environment.py` still knows the string `backend/data` only as a **one-way upgrade source** for installations created by older versions. That directory is not part of the current Python architecture.

## Persistence boundary

ORM rows are infrastructure records, not domain entities. Repositories map persistence data into domain/application-facing values rather than leaking SQLAlchemy models inward.

SQLite transactions, migrations, raw queries, filesystem snapshot paths, backup archives, and persistence timestamps stay outside `domain` and `application` unless represented through ports or explicit immutable values.

## Target boundary

Target JSON is treated as an external document, not a persistence model. `infrastructure/serialization/target_document_source.py` owns JSON/filesystem decoding and byte sizing. `application/targets/import_policy.py` owns import preview, row selection, and operation-key validation. `domain/targets/` owns strict target invariants and preset-key policy.

`SqliteTargetGateway` receives already-normalized target decisions and is now a thin facade over `persistence/sqlite/targets/`: `TargetContextReader` owns account/target context queries, `TargetWriter` owns versioned target-row writes, `TargetPresetRepository` owns preset persistence, and `TargetIdempotencyRepository` owns import-receipt hashing/storage. Pre-mutation recovery checkpoints, CONFIG/DERIVED history events, completion reconciliation, commit, and rollback are delegated to the transaction-scoped `SqliteMutationUnitOfWork`. The previous `target_operations.py` god-module is intentionally removed and guarded by architecture tests.

## Account import boundary

GOOD is an external interchange format. `infrastructure/serialization/good_document.py` owns UTF-8/JSON decoding, removal of unsupported `materials`, partial-document merge against the previous effective export, normalization through `GoodImporter`, and deterministic raw/canonical hashing. It implements the application-owned `AccountDocumentParser` port.

`application/imports/policy.py` owns import semantics that affect user decisions: section coverage provenance, duplicate detection, and progression-regression detection. `PreviewAccountImport` and `CommitAccountImport` orchestrate these policies; commit allocates time/IDs through ports only after duplicate/regression validation succeeds.

`SqliteAccountImportGateway` receives an `AccountImportCommitCommand` that is already validated and now acts only as a persistence coordinator. `account_import/context_reader.py` owns current-snapshot facts, `account_import/snapshot_writer.py` owns immutable snapshot/child-row persistence and the account pointer, `account_import/history_effects.py` delegates snapshot-diff/completion transitions to the shared Unit of Work, and `infrastructure/filesystem/account_import_raw_storage.py` owns atomic raw-document writes/cleanup. Snapshot-diff history, completion reconciliation, recovery checkpointing, commit, and rollback remain delegated to the transaction-scoped SQLite Unit of Work. The previous `good_import_service.py` god-service is intentionally removed and guarded by architecture tests.

## GameData boundary

GameData JSON is an infrastructure format. The JSON loader validates and normalizes it into `domain.game_catalog` records. Use cases and domain services consume those records or application-owned catalog ports; they do not open JSON files.

Build profiles follow the same rule: the pack resides under `data/static/builds/`, loading is an infrastructure responsibility, and planning rules receive the resulting domain-facing data explicitly.

## Desktop startup boundary

The native startup sequence is:

```text
projectg.main
  -> bootstrap desktop environment
  -> select/create local runtime paths
  -> optionally import historical backend/data once
  -> migrate SQLite schema
  -> construct concrete adapters/use cases/controllers
  -> start PySide6 presentation
```

Alembic is configured from root `alembic.ini`; migrations live in root `migrations/`.

## Enforced invariants

`tests/architecture/test_dependency_rules.py` is part of the architecture, not incidental testing. It rejects, among other things:

1. outward `projectg.*` imports from inner layers;
2. third-party/framework imports in domain;
3. direct driver/I/O imports in application;
4. global time/UUID creation in core;
5. runtime singleton leakage into selected planner/artifact adapters;
6. reintroduction of the removed `app.*` package or legacy packaging path.

A structural change is incomplete until these tests and the full test suite pass.

## Migration status

The Python source migration is complete at the package-boundary level:

- `src/projectg` is the sole application package;
- tests import `projectg.*`, not `app.*`;
- project scripts import `projectg.*`, not `app.*`;
- setuptools discovers packages only below `src/`;
- pytest adds only `src/` to `PYTHONPATH`;
- the repository-level `backend/` source directory has been removed;
- the root virtual environment is `.venv/`.

The second migration milestone also moved business policy out of SQLite:

- progression cost projection now lives in `domain/costs/engine.py`;
- planner execution/orchestration now lives in `application/planning/generate.py`;
- planner response projection lives in `application/planning/projection.py`;
- Data Health severity/decision-impact policy lives in `application/health/report.py`;
- artifact status evaluation lives in `domain/artifacts/status.py`;
- GOOD progression-regression detection lives in `domain/account/regression.py`;
- snapshot change detection lives in `domain/history/diff.py`.

SQLite adapters now collect and map persisted facts before delegating to these inner policies. Further refactoring should continue shrinking persistence services rather than creating compatibility modules or restoring the legacy namespace.

## Clean Architecture Milestone 3 — Today planning boundary

The Today pipeline is split across explicit inward layers:

- `application/planning/today.py` compiles a `PlannerResult` plus normalized planner input into the Today read model. It owns cost resolution orchestration, task compilation, source-roadmap projection, and coverage projection, with no SQLAlchemy/SQLite dependency.
- `domain/planning/today/selection.py` owns pure strategic-character selection, pin precedence, hysteresis, pin status, no-action reasons, and alternatives.
- `infrastructure/persistence/sqlite/today_planner.py` now orchestrates only the caller-owned session, planner execution, runtime context, inward Today compilation/selection, and narrow SQLite Today persistence primitives.

Architecture tests explicitly forbid moving `TaskCompiler`, cost resolution, farm-roadmap compilation, or task-selection helpers back into the SQLite Today adapter.

## Clean Architecture Milestone 4 — Target boundary

The target subsystem no longer uses `target_operations.py`. Strict invariants and preset-key policy live in `domain/targets/`, import selection/idempotency workflow lives in application code, JSON/file decoding lives in serialization infrastructure, and `SqliteTargetGateway` exposes only the application port while delegating persistence primitives to the `persistence/sqlite/targets/` package.

## Clean Architecture Milestone 5 — GOOD account import boundary

The account import subsystem no longer uses `good_import_service.py`. `GoodDocumentParser` is the anti-corruption/serialization adapter for GOOD, application policy owns duplicate/regression/coverage decisions, and `SqliteAccountImportGateway` persists only a validated commit command. Architecture tests enforce that regression detection, canonical hashing, and GOOD parsing cannot drift back into SQLite persistence.

## Artifact exchange boundary

Artifact Evaluation Format (AEF) exchange is split across explicit Clean Architecture boundaries:

- `infrastructure/serialization/aef_exchange.py` owns the external AEF v1 syntax and normalization adapter.
- `application/artifacts/policy.py` owns preview enrichment, account ownership checks, metric revalidation, duplicate protection, snapshot-consistency validation, and preparation of normalized evaluation decisions.
- `application/use_cases/artifacts/` orchestrates parser and persistence ports.
- `infrastructure/persistence/sqlite/artifact_exchange_gateway.py` loads persisted facts and atomically persists only validated decisions, including version supersession and history/completion side effects.

The previous `infrastructure/persistence/sqlite/artifact_operations.py` workflow god-module is intentionally removed and guarded by architecture tests.

## Clean Architecture Milestone 7 — Configuration boundaries

Four remaining configuration-style SQLite workflow modules were removed:

- `character_operations.py`;
- `settings_operations.py`;
- `team_operations.py`;
- `tier_pack_operations.py`.

Their responsibilities are now split by ownership rather than hidden behind a gateway-to-operations facade:

- `domain/planning/character_configuration.py` owns character tier/priority invariants;
- `domain/teams/configuration.py` owns configured-team normalization, ownership checks, primary-team constraints, and deterministic IDs;
- `domain/account/settings.py` owns account-settings validation and normalization;
- `domain/planning/config.py` owns planner-config validation/projection rather than SQLite;
- `domain/planning/tier_pack.py` owns tier-pack validation and canonical user-authored content;
- `application/use_cases/characters`, `settings`, `teams`, and `tier_packs` validate/normalize user intent before calling persistence;
- `application/tier_packs/policy.py` owns the editable tier-pack read model;
- SQLite gateways expose persisted facts and `commit_validated(...)` operations, while tier-pack row/version persistence is isolated in `repositories/tier_pack.py`.

Tier-pack JSON hashing is a serialization/infrastructure concern and lives in `infrastructure/serialization/tier_pack_digest.py`; it is not a domain rule.

Architecture tests prevent the four deleted `*_operations.py` modules from returning and verify that input validation remains in domain/application code rather than SQLite adapters.

## Clean Architecture Milestone 8 — Read-side workflow boundaries

The last three SQLite `*_operations.py` workflow modules were removed:

- `overview_operations.py`;
- `planner_state_operations.py`;
- `support_operations.py`.

The read side is now split by responsibility instead of hiding application policy behind procedural persistence helpers:

- `application/overview/policy.py` owns the desktop overview projection, including tier labels and presentation-neutral defaults; `SqliteOverviewGateway` returns typed persisted/planning facts through `OverviewContext`.
- `application/planner_state/policy.py` owns Today pin preview selection. `PreviewPin` consumes `PinContext`, while `SetPin` validates ownership before calling `persist_pin(...)`; SQLite owns only PlanRun queries, Today-plan fact loading, pin persistence, and history side effects.
- `application/support/policy.py` owns history timeline ordering, grouping, and display limiting. `SqliteSupportGateway` returns typed snapshot/event facts and retains only history/database comparison and log-directory driver operations. Backup/restore use a dedicated `BackupGateway` boundary.

Architecture tests prohibit these three operations modules from returning and ensure overview projection, pin preview/ownership validation, and history grouping remain in the application layer.

## Clean Architecture Milestone 9 — Planner input boundary

The legacy SQLite `planner_service.py` facade and its embedded `PlannerDataRepository` are removed. Planner execution now starts in the application layer:

- `application/use_cases/planning/run_planner.py` owns the planner use case and depends only on outbound ports plus `Clock`;
- `application/planning/input.py` owns composition of persisted facts, GameData, Build Knowledge, tier semantics, team membership, artifact-evaluation freshness, artifact-domain mapping, and planner unresolved issues into `PlannerInput`;
- `application/planning/build_knowledge.py` owns the conservative `BuildKnowledgePack -> progression targets` policy;
- `application/ports/outbound/planner_gateway.py` exposes typed persistence facts rather than SQLAlchemy rows or an already-composed `PlannerInput`;
- `application/ports/outbound/game_data_gateway.py` and `build_knowledge_gateway.py` isolate the two non-database planner inputs;
- `infrastructure/persistence/sqlite/planner_gateway.py` is a session-bound fact adapter: it queries snapshot/team/tier/evaluation rows and maps them to application-owned fact records only;
- `infrastructure/game_data/json/catalog_gateway.py` and `build_knowledge_gateway.py` implement configured local catalog adapters.

`TodayPlanner` and Overview receive a composed `RunPlanner` for the caller-owned database session. Data Health invokes the same application planner execution through an injected composition-root callback. None of these paths call `planner.repository.load(...)`, and persistence no longer decides build targets, tier labels, artifact freshness, or planner input shape.

Architecture tests explicitly require `planner_service.py` to remain absent and prevent `PlannerInput` construction or build/tier/freshness policy from drifting back into SQLite or JSON-loading adapters.

## Clean Architecture Milestone 10 — GameData pack boundary

The local GameData pack workflow no longer uses `game_data_pack_operations.py` or the proxy-style `pack_gateway.py`. The previous adapter mixed JSON/filesystem mechanics, SQLite account queries, metadata projection, account coverage, preview composition, and install orchestration in one infrastructure path.

The boundary is now split explicitly:

- `application/game_data/policy.py` owns metadata projection, catalog coverage, account coverage, and pack-result composition;
- `application/use_cases/game_data/` owns status, preview, install, and export workflow sequencing;
- `application/ports/outbound/game_data_pack_storage.py` exposes only local-pack document/storage capabilities;
- `application/ports/outbound/game_data_account_gateway.py` exposes only the account character/equipped-weapon keys required for coverage evaluation;
- `infrastructure/game_data/json/pack_storage.py` owns candidate/installed JSON loading, filesystem copy, backup naming, copied-byte validation, and atomic `os.replace(...)` installation;
- `infrastructure/persistence/sqlite/game_data_account_gateway.py` owns only the SQLite queries that produce `AccountCatalogFacts`.

Consequently, JSON GameData infrastructure does not import SQLAlchemy or SQLite persistence, while the SQLite account adapter does not import the GameData loader/model. Candidate validation occurs in the application workflow before mutation is requested; the storage adapter validates copied bytes again as an integrity check before atomic replacement.

`GameDataPackResult` is application-owned rather than an outbound-port return type, so use-case output is not defined by a concrete driver contract. Architecture tests prohibit the removed operations/proxy modules from returning and verify that metadata/coverage/workflow policy remains in the application layer.

## Clean Architecture Milestone 11 — Data Health facts boundary

The legacy SQLite `health_service.py` has been removed. Data Health is now an independent application workflow rather than a hidden capability of `SupportGateway`:

- `application/ports/outbound/data_health_gateway.py` defines the typed `DataHealthFacts` contract: account availability, artifact-quality configuration state, owned character keys, and equipped weapon keys;
- `infrastructure/persistence/sqlite/data_health_gateway.py` performs only those SQLite queries and returns typed facts; it does not import the Data Health report policy, `CostEngine`, or GameData loaders;
- `application/use_cases/support/get_data_health.py` owns orchestration of planner execution, cost calculation, GameData coverage comparison, backend-error capture, and `application/health/report.py`;
- `SqliteSupportGateway` no longer exposes `data_health()` and no longer receives a health-service factory; the composition root wires Data Health independently.

Architecture tests require `health_service.py` to remain absent and prevent report/severity/cost/catalog policy from drifting back into SQLite.

The same milestone narrows the old planner-review helper into technical provenance only. `planner_review.py` has been removed; `infrastructure/persistence/sqlite/planner_provenance.py` owns deterministic dataset/context hashing for persisted PlanRun provenance. Unused `PlannerFeedback` summary/serialization helpers were deleted rather than preserved behind another facade. `TodayPlanner` receives the already-loaded `GameData` object directly when building provenance, so the provenance adapter does not call a GameData provider callback or global loader.

## Clean Architecture Milestone 12 — Backup/archive boundary

The previous `infrastructure/persistence/sqlite/backup_storage.py` god-module has been removed. Backup is now split across application policy and two distinct outer-driver concerns:

- `application/backups/models.py` owns typed manifest/export/restore records;
- `application/backups/policy.py` owns backup-format compatibility and automatic-backup retention selection without filesystem, ZIP, or SQLite calls;
- `application/ports/outbound/backup_gateway.py` is the dedicated manual backup/restore port, so `SupportGateway` no longer exposes `create_backup()` or `restore_backup()`;
- `application/use_cases/backups/` owns the manual export/restore application entry points;
- `infrastructure/archive/backup_archive.py` owns ZIP path safety, archive limits, integrity hashing, manifest/settings decoding, writing, and extraction, and does not import SQLAlchemy or SQLite;
- `infrastructure/persistence/sqlite/backup_database.py` owns SQLite integrity/schema/domain-relation validation, SQLite backup-copy mechanics, snapshot-path rewrite during restore, live database installation, and rollback, and does not know the ZIP format;
- `infrastructure/backups/local_backup_gateway.py` coordinates those two outer adapters, filesystem directory swaps, pre-mutation recovery checkpoints, and maintenance-gate/engine lifecycle.

`SqliteSupportGateway` no longer receives an engine or backup service. The composition root wires one dedicated `LocalBackupGateway` into the backup use cases and reuses the same recovery adapter for persistence pre-mutation checkpoints. Architecture tests require `backup_storage.py` to remain absent, prohibit ZIP concerns from leaking into the SQLite backup adapter, prohibit SQLAlchemy/SQLite from leaking into the ZIP adapter, and keep manifest/retention policy in application code.


## Clean Architecture Milestone 13 — SQLite mutation Unit of Work

Cross-cutting SQLite write effects are now centralized instead of being reimplemented in every persistence gateway. `infrastructure/persistence/sqlite/mutation_uow.py` owns the transaction-scoped mechanics shared by mutations:

- `BEGIN IMMEDIATE` acquisition when a new transaction is required;
- one pre-mutation recovery checkpoint per SQLAlchemy transaction;
- CONFIG/SNAPSHOT/DERIVED history-event persistence;
- completion/reopen reconciliation;
- account snapshot-diff persistence;
- commit and rollback, including rollback when the commit itself raises.

`SqliteMutationUnitOfWork` is composed in `bootstrap/dependencies.py` and injected into mutating SQLite gateways. Gateways do not construct their own UoW, call `before_mutation(...)`, or call `db.commit()` / `db.rollback()` directly. This applies to account import, target/preset mutation, settings, teams, character configuration, tier-pack mutation, artifact evaluation import, and Today pin persistence.

`TodayPlanner` still receives a caller-owned SQLAlchemy session because planner execution and Today read/write composition happen in one existing session. Its persistence finalization uses `finalize_existing_transaction(...)` from the same transaction boundary module, so direct commit/rollback calls remain centralized.

The old `history/service.py` and `history/completion.py` catch-all modules are removed. History persistence is split into narrow drivers:

- `history/events.py` persists one typed history event;
- `history/snapshots.py` maps persisted snapshots and delegates semantic diffing to `domain/history/diff.py`;
- `history/completion_reader.py` loads/evaluates target-completion facts but does not record events or reconcile transitions.

Completion transition reconciliation is now a transaction effect owned by `SqliteMutationEffects`, ensuring completion events are emitted in the same transaction as the bounded-context mutation that caused them. Architecture tests prohibit direct transaction finalization and direct backup/history/completion orchestration from returning to individual mutation gateways.

## Clean Architecture Milestone 14 — Target adapter decomposition

The target boundary is now decomposed internally without changing its application port. `SqliteTargetGateway` remains the single adapter exposed to application use cases, but it no longer owns SQL/query/hash/version mechanics directly:

- `targets/context_reader.py` maps account/snapshot/preset rows into `TargetImportContext` and `TargetPresetContext`;
- `targets/target_writer.py` owns target-version allocation and versioned target-row persistence;
- `targets/preset_repository.py` owns preset create/activate persistence and keeps activation preparation read-only until the UoW recovery checkpoint has run;
- `targets/idempotency_repository.py` owns deterministic request fingerprinting plus `IdempotencyReceipt` storage.

`SqliteTargetGateway` now coordinates these primitives with `SqliteMutationUnitOfWork` and emits target-specific history/completion effects, but contains no direct `select(...)`, target ORM model, payload hashing, or version-allocation implementation. Architecture tests prohibit those mechanics from drifting back into the facade and explicitly guard the read-only preset-activation prepare phase.



## Clean Architecture Milestone 15 — Today adapter decomposition

The Today SQLite boundary is now decomposed internally while keeping the existing `TodayPlanner` integration surface:

- `today/context_reader.py` maps only persisted account runtime facts into `TodayAccountFacts`;
- `today/state_repository.py` maps only `TodayState` rows to/from the pure `TodaySelectionState`;
- `today/plan_run_repository.py` owns target-version reads, normalized planner-input serialization, source-availability capture, immutable `PlanRun` construction, and run-ID allocation;
- `today_planner.py` remains the orchestration facade that executes the planner, builds `TodayAccountContext`, delegates compilation/selection inward, delegates state/run persistence to the three primitives, and finalizes the caller-owned transaction through the centralized mutation boundary.

The facade no longer imports `select`, `CharacterTargetVersion`, `PlanRun`, `TodayState`, `asdict`, or planner-config serialization helpers. Architecture tests guard this decomposition and keep account facts, hysteresis state mapping, and PlanRun persistence in separate modules.

## Clean Architecture Milestone 16 — Artifact exchange adapter decomposition

The artifact-evaluation exchange boundary is now decomposed internally while preserving the existing `ArtifactExchangeGateway` application port:

- `artifact_exchange/context_reader.py` owns read-only account/snapshot/target/evaluation facts and maps them into `ArtifactExchangeContext`;
- `artifact_exchange/evaluation_writer.py` owns version supersession, `ArtifactEvaluation` row creation, and persistence-facing evaluation/status response projection;
- `artifact_exchange/history_effects.py` captures the pre-mutation completion baseline and owns artifact-specific derived-history transitions (`ARTIFACT_EVALUATION_CHANGED`, `ARTIFACT_TARGET_REACHED`, `CHARACTER_COMPLETED`, and `CHARACTER_REOPENED`);
- `artifact_exchange_gateway.py` is now a thin facade that validates snapshot/ownership concurrency, opens the shared SQLite mutation UoW, creates the recovery checkpoint, and coordinates those three persistence primitives.

The facade no longer imports `SnapshotCharacter` or `ArtifactEvaluation`, performs ORM character queries, loads target/evaluation rows directly, calculates completion transitions, or constructs artifact-evaluation persistence rows. Architecture tests guard the read/write/event split and prohibit those mechanics from drifting back into the facade.


## Clean Architecture Milestone 17 — Account import adapter decomposition

The validated GOOD account-import persistence boundary is now decomposed internally while preserving the existing `AccountImportGateway` application port:

- `account_import/context_reader.py` owns read-only account/current-snapshot context and maps persisted character/weapon rows to `AccountImportContext`;
- `account_import/snapshot_writer.py` owns immutable `Snapshot`, character, weapon, artifact, and team row persistence plus movement of `Account.current_snapshot_id`;
- `account_import/history_effects.py` owns account-import-specific delegation of snapshot-diff and completion reconciliation to `SqliteMutationEffects`;
- `infrastructure/filesystem/account_import_raw_storage.py` owns atomic sanitized GOOD byte persistence and failed-transaction cleanup, so SQLite code no longer imports `os`/`Path` to manage snapshot documents;
- `account_import_gateway.py` is the thin facade that performs the optimistic snapshot-concurrency guard, creates the `PRE_GOOD_IMPORT` recovery checkpoint, coordinates the three persistence primitives plus the filesystem adapter, and returns the commit result.

The raw-document storage adapter is composed explicitly in `bootstrap/dependencies.py` rather than constructed by the SQLite gateway. Architecture tests prohibit snapshot ORM/query mechanics, raw-file mechanics, and history/completion implementation from drifting back into the facade, and keep filesystem storage free of SQLAlchemy/SQLite dependencies.
