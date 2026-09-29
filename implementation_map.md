# Implementation map — exact files/modules/tests per gap (read-only pointers)
Base: C:\Users\justh\AppData\Local\Temp\opencode\ByzMetaTeacher\LearnerAI\Compiler\

## Construction lifecycle — current mainline
- Status: integrated on current `main`; PR #86 was audited and closed as superseded.
- Current implementation: `semantic/action_issuance.py`, `semantic/completion_witness.py`,
  `semantic/release_state.py`, `semantic/resource_conflicts.py`, `ir/model.py`,
  `ir/construction.py`, `semantic/construction.py`, `emitter/per.py`,
  `primitives/native_engine_effects.py`.
- Tests: current construction lifecycle suite plus native zero-findings acceptance.
- Remaining evidence: same-pass visibility proof; foundation/placement runtime evidence.

## Production provider readiness — typed native admissibility seam
- `up-train-site-ready` is represented by `ProductionProviderReadinessEvidence` in `ir/production.py`.
- Registry binding requires the native Fact schema, ADMISSIBILITY semantic role, literal `c:` typeOp, and the lifecycle target UnitId; symbolic UnitIds are canonicalized to numeric IDs.
- Semantic identity: `admissibility.train.site-ready`. The evidence is explicitly `OPEN`; it does not replace `can-train` and does not authorize `train`.
- Analyzer wiring attaches readiness to `ProductionLifecycle` and preserves the separate `can-train` feasibility path.
- Acceptance: `tests/test_production_provider_readiness.py`, `tests/fixtures/production_provider_readiness.perdsl`, and `tests/assert_production_provider_readiness_native.py`.
- Runtime boundary: current DE busy/queued provider behavior, birth timing, queue-exit timing, and next-pass visibility remain unverified.

## Production birth and queue-exit timing — typed OPEN observational seam
- `ProductionBirthTimingEvidence` records a `game-time` sample paired with canonical `unit-type-count` for the target UnitId.
- `ProductionQueueExitTimingEvidence` records a `game-time` sample paired with canonical `unit-type-count-total` and `up-pending-objects` for the target UnitId.
- Registry resolvers fail closed on wrong fact families, mismatched UnitIds, or non-native timing sources; analyzer canonicalizes symbolic UnitIds before lifecycle threading.
- Both records are explicitly OPEN and observational. They do not become completion witnesses, queue-capacity or provider-idle guards, or same-pass transition claims.
- Acceptance: `tests/test_production_birth_queue_exit_timing.py`, `tests/fixtures/production_birth_queue_exit_timing.perdsl`, and `tests/assert_production_birth_queue_exit_timing_native.py`.
- Runtime boundary: exact DE birth ordering, queue-exit ordering, and next-pass visibility remain unverified.

## Production queue capacity — typed native control seam
- Queue occupancy remains typed through `ir/production.py`: `unit-type-count-total` is observation only; completion remains `unit-type-count`; pending duplicate protection remains `up-pending-objects`.
- Native queue-capacity control is represented by `ProductionQueueCapacityControlEvidence`. The registry cross-references the pinned DE Strategic Number inventory, requires exact SN 264 (`sn-enable-training-queue`) equality, canonicalizes the target to numeric 264, derives the documented total capacity as additional queued slots plus one active training slot, and keeps the evidence `OPEN`.
- Analyzer wiring attaches the control evidence to `ProductionLifecycle` without adding it to action authorization or changing emitted `train` guards.
- Acceptance: `tests/test_production_queue_capacity_native_contract.py`, `tests/fixtures/production_queue_capacity.perdsl`, and `tests/assert_production_queue_capacity_native.py`.
- Runtime boundary: current DE enforcement of SN 264 remains OPEN.

## SN/Timer DSL allocation + catalog
- SN remains executable-safe through its versioned catalog/binding/emission path.
- Timer: `parser.py` accepts `timer <name>` declarations; `ir/recurrent.py` owns `TimerRequest`/`TimerState`; `semantic/analyzer.py` constructs deterministic requests with `DISABLE_BEFORE_FIRST_USE`; `compiler.py:_storage_requests` collects them; existing `runtime_binding.py` allocates `TimerSlot` with 1..50 range/collision checks and manifest provenance.
- Emission: `emitter/per.py` emits deterministic symbolic `defconst` aliases and one-shot `disable-timer` initialization rules; no duration/rearm policy is invented.
- Tests: `tests/test_timer_allocation.py`, `tests/fixtures/timer_allocation.perdsl`, `tests/assert_timer_native.py`, plus Compiler CI native zero-findings and determinism.
- Remaining: engine countdown/pass granularity and explicit TimerId reuse/lifetime model.

## Escrow lowering — release + explicit percentage policy
- Release slice: integrated and previously re-verified on main.
- Percentage policy slice: typed `NativeEscrowPolicyPlan` is now connected through the existing
  `escrow_plan` compiler channel, validated by the resource-control semantic pass and primitive
  registry, promoted through the dedicated native escrow binder, and emitted deterministically as
  `set-escrow-percentage` actions.
- Native contracts: `escrow.execution.release` and `escrow.execution.set-percentage`; policy values
  are constrained to integer 0..100 and resource domain food/wood/stone/gold.
- Acceptance: focused binder/validator tests, six public compiler paths, checked-in
  `tests/fixtures/escrow_policy.perdsl`, dedicated `tests/assert_escrow_policy_native.py`,
  Compiler native zero-findings, cross-platform determinism, and full regression.
- Remaining: same-pass release→ordinary-action runtime proof, starvation/emergency release,
  multi-owner handoff, UP escrow mutation surfaces, and research-claim integration.
- Runtime-evidence specification: `docs/plans/2026-09-28-native-escrow-same-pass-visibility-checklist.md`,
  `docs/reference/oracles/escrow-same-pass-research.schema.json`, candidate
  `docs/reference/oracles/candidates/escrow-same-pass-research.native.json`.
- Oracle-spec regression: `tests/test_escrow_same_pass_oracle_spec.py`; runtime execution remains outside CI/user-owned.

## Research lifecycle status
- `ir/research.py` owns the pinned six-value `ResearchState` family (-1 disabled, 0 unavailable, 1 available, 2 pending, 3 complete, 4 queued) and validates the typed pending-status fact shape.
- `semantic/analyzer.py` resolves the literal technology to its native TechId and emits numeric `up-research-status c: <TechId> >= 2` evidence into the lifecycle.
- `emitter/per.py` retains the existing research pending/retry lifecycle; `research-completed` remains the only completion witness. Explicit targeted `release-escrow` operations are validated against `can-research-with-escrow` for the same technology and emitted immediately before ordinary `research`.
- The targeted release path reuses the existing `escrow_plan` API and `NativeEscrowReleasePlan`; no second public compiler channel is introduced.
- Tests: `test_action_issuance.py`, `test_native_escrow_release.py`, `test_escrow_resource_control.py`, and native `assert_research_escrow_native.py`.
- Protected-research strategy pattern: `ExecutionDemandTemplate.escrow_release_resources` explicitly declares the resources a strategy may release before ordinary `research`; `lower_strategy_profile` builds a targeted `NativeEscrowReleasePlan`, and both strategy compilation entry points forward it through the existing `escrow_plan` channel.
- Remaining: same-pass runtime visibility, provider/busy runtime semantics, starvation/emergency behavior, and handoff semantics.

## Strategy capability recovery
- `ir/strategy.py`: `CapabilityRecoveryContract` requires strategic-demand preservation and reopening after temporary capability recovery; opportunity-cost protection cannot be configured to release merely on capability loss.
- `ir/strategy_runtime.py`: capability-loss/recovery transitions are tied to explicit reassessment reasons; runtime validation rejects accidental invalidation or opportunity-cost release caused solely by capability loss.
- Tests: `tests/test_strategy_runtime.py` covers typed contract, fail-closed policy variants, same-demand blocked-on-loss, and same-demand executable-on-recovery.
- Runtime boundary: native capability/provider behavior remains observation-driven; this contract does not schedule replacement actions or invent engine failure channels.

## Strategy SN61 boat exploration-group observation
- `ir/strategy_runtime.py` binds exact `up-compare-sn 61 ...` observations to `BOAT_EXPLORATION_GROUP_CONTROL`.
- The pinned DE Strategic Number catalog identifies SN 61 as `sn-number-boat-explore-groups`, default 0, required range `0..Max`.
- This remains descriptive strategy evidence only; no water-map detection, boat assignment, controller action, or runtime exploration guarantee is inferred.

## Strategy SN42 exploration-group observation
- `ir/strategy_runtime.py` binds exact `up-compare-sn 42 ...` observations to `EXPLORATION_GROUP_CONTROL`.
- The pinned DE Strategic Number catalog identifies SN 42 as `sn-number-explore-groups`, with default 0 and required range `0..Max`.
- Only the observation surface is promoted; exploration-controller interactions remain descriptive/evidence-only and no exploration actions are synthesized.

## Strategy SN74 town-size observation
- `ir/strategy_runtime.py` binds exact `up-compare-sn 74 ...` comparisons to `TOWN_SIZE_CONTROL`.
- The pinned DE Strategic Number catalog identifies SN 74 as `sn-maximum-town-size` with the documented meaning of setting maximum town size.
- This is descriptive strategy evidence only; the native-controller catalog remains evidence-only and no town-size-to-attack action semantics are promoted.

## Strategy provider-readiness observations
- `ir/strategy_runtime.py` binds `up-train-site-ready` as `TRAIN_PROVIDER_READINESS`, preserving its native ADMISSIBILITY role.
- The observation validates the existing native schema and canonical `c:` UnitId without promoting provider readiness to `can-train` feasibility or completion.
- Runtime busy/queued provider behavior remains OPEN; this observation is descriptive/admissibility evidence only.

## Strategy persistent-control observations
- `ir/strategy_runtime.py` binds generic `up-compare-sn` as `PERSISTENT_CONTROL_STATE` for unresolved SNs, validating the native Strategic Number identifier in 0..511 and comparison operator family.
- Exact SN 264 (`sn-enable-training-queue`) now binds as `PRODUCTION_QUEUE_CAPACITY_CONTROL` only when the documented equality form and additional-slot value 0..15 are present.
- This specialized observation does not promote current DE enforcement or turn queue occupancy into an action authorization; those remain the existing OPEN production runtime boundary.
- Other Strategic Numbers retain the generic persistent-control observation and are not attributed to attack, exploration, or other controllers without separate evidence.

## Generic/client strategy policy boundary
- `tests/test_basilisk_client_boundary.py` now audits both public re-exports and source-level Python imports.
- Generic compiler source excludes downstream `clients/basilisk`, `ir/strategy`, and `ir/strategy_runtime` imports; violations fail the test with source path and line number.
- This is a compiler policy boundary only; no strategy semantics are moved into the generic compiler.

## DUC binder + emission
- Build: primitives/registry.py (DUC adapters; today zero), primitives/native_binder.py
  (ENGINE_SEMANTICS_MAPPED with binding for DUC), emitter DUC lowering, DSL surface decision.
- Tests: convert test_duc_semantics.py patterns to DSL end-to-end; oracle consistency stays.
- Perf: static warnings only (advisory), from oracle + corpus cardinality.

## Controllers/attack lifecycle
- Build: ir/native_attack.py (typed issue-only lifecycle IR), primitives/engine_semantics.py (contracted attack.execution.issue mapping), primitives/native_binder.py (dedicated attack-now promotion), primitives/registry.py (typed-plan validation), emitter/per.py and compiler.py (deterministic lowering/threading).
- Controller ownership remains descriptive in semantic/native_controller.py; attack-group-control is not promoted through its evidence-only status.
- Excluded until separately contracted: attack SNs, exploration gating, town-size targeting, DUC prerequisites, completion/release, group membership, and timer/reset recovery.
- Tests: tests/test_native_attack_lifecycle.py, tests/test_compiler_native_integration.py, tests/assert_attack_native.py plus CI native zero-findings evidence.

## Source graph deterministic load-random materialization
- LoadRandomSelection identifies an active load-random directive by canonical source path + line + column and supplies one declared target.
- SourceGraphResolver remains fail-closed without a policy; with a policy it materializes exactly that target, records a RANDOM edge with target/child provenance, and never emulates engine RNG.
- source_graph_validation.py accepts RANDOM edges as materialized when an active edge has a target; unmaterialized RANDOM edges remain rejected.
- Acceptance: focused source-graph event/edge tests plus full Compiler verification.
- Runtime boundary: actual DE weighted/random selection semantics remain OPEN.
- .xs boundary: active `.xs` entrypoints and active `#load` targets fail closed with `SOURCE-GRAPH-017`; no telemetry/state bridge is inferred.

## Source graph / game data / strategy
- load-random: ir/source_graph.py LoadKind + explicit resolver materialization policy.
- .xs boundary: new module (no current owner) for IDIOM-029.
- Game data: `ir/civ_profile.py`, `ir/game_data_manifest.py`, `ir/game_data_manifest_buildings.py`, `ir/game_data_manifest_technology_conflicts.py`, `ir/game_data_manifest_technologies.py`, and `ir/game_data_manifest_units.py`; authoritative manifest coverage is audited, all 14 manifest `NotAvailable` rows are explicit availability facts, 51 identity-safe technology nodes and 12 identity-safe unit nodes are materialized from pinned 185872 aoe2techtree subsets, Fish Trap 199 is materialized from the pinned building snapshot, and TechIds 54/909 use an explicit identity-conflict override path with independent evidence. The GameData graph carries provenance/provider/line/upgrade semantics. Unit trigger chains remain fail-closed when prerequisite technology IDs are not yet modeled. Current coverage is 155 modeled / 4 unmodeled / 14 unavailable.
- Strategy: ir/strategy_runtime.py now classifies `up-can-search` as `DUC_SEARCH_AVAILABILITY` and escrow-aware affordability/build/research facts as `ESCROW_CAPABILITY`. Attack controller Actions remain fail-closed as non-observations; deeper DUC/escrow runtime semantics remain separate.
