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

## Escrow lowering — release-only executable slice
- Status: **integrated and verified on main; release-only slice re-verified by Compiler #2149 / Actions `36497398646`.**
- IR/semantic seam: `ir/resource_control.py` `NativeEscrowReleasePlan`; `semantic/resource_control.py`
  release-plan validator; compiler threading through all six public surfaces.
- Native promotion: `primitives/native_binder.py` dedicated `NativeEscrowSemanticBinding`;
  `primitives/engine_semantics.py` `escrow.execution.release`; `primitives/registry.py`
  executable command inventory and resource-domain validation.
- Emission: `emitter/per.py` deterministic rule grouping by `rule_order` and preserving
  `within_rule_order`.
- Acceptance: `tests/fixtures/escrow_release.perdsl`, `tests/assert_escrow_native.py`,
  `tests/test_native_escrow_release.py`, `tests/test_native_semantic_binder.py`,
  `tests/test_semantic_support_state.py`, plus CI native zero-findings and 9-way determinism.
- Non-goals preserved: `set-escrow-percentage`, UP escrow mutation, starvation scheduling,
  multi-owner handoff, and same-pass release→ordinary-action coupling remain OPEN.
- Runtime-evidence specification: `docs/plans/2026-09-28-native-escrow-same-pass-visibility-checklist.md`,
  `docs/reference/oracles/escrow-same-pass-research.schema.json`, candidate
  `docs/reference/oracles/candidates/escrow-same-pass-research.native.json`.
- Oracle-spec regression: `tests/test_escrow_same_pass_oracle_spec.py`; runtime execution remains outside CI/user-owned.

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
- Game data: `ir/civ_profile.py` plus `ir/game_data_manifest.py` and `ir/game_data_dat_snapshot.py`; authoritative manifest coverage is audited, DAT-derived technology metadata has a deterministic provenance-checked import/merge boundary, and `parse_aoe2techtree_technologies_json()` adapts the upstream `data.data.Tech` machine-readable subset into that contract. A pinned 185872 technology snapshot is now committed at `docs/reference/game-data/aoe2techtree-185872-technologies.json`, sourced from aoe2techtree revision `3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f` / blob `c4f7da961e82a8231b1ba49459949c4d6e479bc8`. It is used only to fill unresolved technology cost/research-time fields; prerequisites, providers, effects, civ availability, and the remaining 73 unmodeled manifest nodes remain untouched.
- Strategy: ir/strategy_runtime.py now classifies `up-can-search` as `DUC_SEARCH_AVAILABILITY` and escrow-aware affordability/build/research facts as `ESCROW_CAPABILITY`. Attack controller Actions remain fail-closed as non-observations; deeper DUC/escrow runtime semantics remain separate.
