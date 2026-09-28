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
- Build: semantic/analyzer.py (construct StrategicNumberRequest/TimerRequest),
  compiler.py:_storage_requests (collect them), runtime_binding.py (inventory wiring).
- Catalog: new SN table (defaults/version/auto-mutation) + timer granularity note.
- Tests: tests/test_strategic_number_*.py + test_timer_* (add DSL end-to-end, not fixtures).

## Escrow lowering — release-only executable slice
- Status: **integrated and verified on main `adec462b420f87bc66c2868908058c0e272baf7c`**.
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
