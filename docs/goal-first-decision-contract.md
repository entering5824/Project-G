# Goal-first decision contract

The public unit of ranking is one character/component goal. For example:

```text
#1 YaeMiko — Weapon 80 → 90
Action: Farm/obtain Mora; Farm/obtain Weapon EXP
```

Farm sources are execution methods attached to this goal, never independent strategic recommendations. They have no shared-source score or bonus. The same source serving ten characters leaves ten component goals with their own scores.

## Decision rules

Global retains the original account state, goal score and strategic target once per `goalKey`. Simulation builds the full `milestoneChain` inside that row; it does not emit independent milestone rows. The configured horizon now bounds semantic rows rather than individual steps.

Today compiles these semantic goals in Global order. It selects the first actionable goal within its planning window. A closed Talent Book domain moves that goal to `unavailable`, allowing the next actionable goal to be selected. A pin restricts this rule to that character; if no pinned goal is actionable, its waiting goal remains visible with an explicit no-action reason. Character progression prerequisites may still block a goal. Resource requirements cannot block it.

`ResourcePolicy.TALENT_BOOK_AFFECTS_TODAY` applies only when the goal is a Talent component and the required material is categorized as a Talent Book. Zero quantities do not gate availability. Weapon domains, Mora, EXP, normal/weekly bosses and crowns are informational methods. Their schedule, quantity, weekly claims or resin availability do not reorder goals or make those goals unavailable.

Goal scoring retains deficiency, importance, tier, team, completion, configured confidence, priority override and component efficiency. Resource shortages, cost magnitude and shared-source bonuses do not enter scoring. The previous C/D reductions now belong to the component score: C uses a 0.5 multiplier and D uses 0.2. B and above keep a 1.0 multiplier. The multiplier is visible in `scoreBreakdown.tierPriorityMultiplier`.

## Output and inventory cleanup

- Today tasks have `type: GOAL_ACTION`, their own `primaryGoal`, the exact goal score, `requiredCost`, and nested `farmMethods`.
- `ResolvedCost` describes an `ESTIMATED` theoretical cost or missing catalog data. It makes no ownership, shortage, crafting or material-readiness claim.
- Runtime output no longer exposes `missingResources`, `missingSummary`, `requiredResources`, `sharedBonus`, `batchContribution`, `sourceRoadmap` or `farmRoadmap`.
- Global rows expose `milestoneChain`; desktop details and exports include that chain.
- The result export uses schema version 2 and exports semantic goals and execution methods.
- Inventory reserve validation was removed from backup restore. Historical migration identifiers remain so existing backups can still be recognized and migrated; no active reserve fields or decisions remain.
- No replacement legacy module or compatibility shim was introduced.

## Completion evidence

| Requirement | Evidence |
| --- | --- |
| Rank character/component goals, never resources | Goal-only `globalGoals`, `GOAL_ACTION` tasks, selection using semantic `goalKey` order; architecture guards prevent costs/catalog/availability imports into scoring and selection |
| Separate goals and sources | `UpgradeGoal` and frozen `FarmSource`; compiler projects sources into nested `farmMethods` |
| Remove resource/shared cost scoring | Deleted source-ranking modules and batch-bonus constants; integration tests vary Mora, Weapon EXP and boss costs between zero and very large amounts without changing Global/Today priority |
| Choose strategic goal before today's action | Selection follows Global goal keys; closed Talent test selects the next actionable goal without changing its score |
| One row per semantic goal | Core and integration tests assert unique goal keys and complete nested milestone chains; Qt test checks one row and visible chain details |
| Remove obsolete inventory contracts | Simplified cost model and task output; AST architecture test rejects obsolete fields across all runtime Python modules; reserve restore check and empty EXP recommendation widget removed |
| Explicit Talent Book exception | Policy enum and compiler architecture test require the only availability call to be guarded by that policy |
| Required regressions | Resource invariance covers Mora, character EXP, Weapon EXP, normal boss, weekly boss and crown; end-to-end selection and ten-character shared-source tests; Sunday/closed Talent tests |
| Goal-first titles and exports | Desktop title/action assertions, semantic Global title assertion, export round-trip tests and rendered native UI preview |

Validation: full pytest **333 passed**, including native UI tests; architecture **72 passed**. Compileall and strict GameData validation pass. There are 40 existing SQLAlchemy foreign-key teardown warnings. Build Knowledge validation reports no errors and retains exit 1 solely because `verifiedStandard = 0` and `verifiedDeep = 0`.

## Files

Created:

- `src/projectg/domain/planning/resource_policy.py`
- `tests/domain/planning/test_goal_action_contract.py`
- `tests/application/today/test_goal_priority_integration.py`
- `tests/architecture/test_goal_first_contract.py`
- `tests/application/planner/test_manual_tier_pack.py` (retains the manual tier-pack tests from the removed source-ranking suite)
- `docs/goal-first-decision-contract.md`

Modified runtime modules:

- `domain/planning/models.py`, `tiers.py`, `scorer.py`, `simulator.py`, `engine.py`
- `domain/planning/today/compiler.py`, `models.py`, `config.py`, `availability.py`
- `domain/costs/models.py`, `resolver.py`, `__init__.py`
- `application/planning/today.py`, `application/overview/policy.py`, `application/ports/outbound/overview_gateway.py`
- `infrastructure/persistence/sqlite/today_planner.py`, `overview_gateway.py`, `backup_database.py`
- `presentation/desktop/result_export.py`, `presentation/desktop/pyside6/main_window.py`

Updated existing tests: planner core, artifact planner, Today compiler, costs, overview, Today state, desktop application, Today selection, result export and desktop navigation. Updated documentation: `README.md` and the superseded `docs/farm-priority-update.md`.

Deleted:

- `src/projectg/domain/planning/farm_sources.py`
- `src/projectg/domain/planning/farm_priority.py`
- `tests/application/planner/test_tier_farm_sources.py`

Further work outside this contract: add verified Standard/Deep Build Knowledge coverage. There are no remaining requirements for this goal.
