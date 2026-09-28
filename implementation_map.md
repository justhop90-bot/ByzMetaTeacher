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

## Source graph / game data / strategy
- load-random: ir/source_graph.py LoadKind + resolver materialization.
- .xs boundary: new module (no current owner) for IDIOM-029.
- Game data: ir/civ_profile.py (145-node manifest), patch overlays, broader civs.
- Strategy: ir/strategy_runtime.py observation primitives (DUC/attack/escrow) +
  policy-vs-semantics audit of _validate_native_operand token sets.
