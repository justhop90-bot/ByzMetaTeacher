# Implementation map — exact files/modules/tests per gap (read-only pointers)
Base: C:\Users\justh\AppData\Local\Temp\opencode\ByzMetaTeacher\LearnerAI\Compiler\

## Merge PR86 (construction hardening into main)
- Branch: compiler-construction-lifecycle-final-verify (731f193; parent 88006ce).
- Files: semantic/action_issuance.py, completion_witness.py, release_state.py,
  resource_conflicts.py, ir/model.py (+PR86 transition types), emitter/per.py,
  primitives/native_engine_effects.py (placement-pending fact).
- Tests: existing issuance/witness/release suites + PR86 fixtures.
- Evidence needed: same-pass visibility proof; foundation/placement runtime runs.

## SN/Timer DSL allocation + catalog
- Build: semantic/analyzer.py (construct StrategicNumberRequest/TimerRequest),
  compiler.py:_storage_requests (collect them), runtime_binding.py (inventory wiring).
- Catalog: new SN table (defaults/version/auto-mutation) + timer granularity note.
- Tests: tests/test_strategic_number_*.py + test_timer_* (add DSL end-to-end, not fixtures).

## Escrow lowering
- Build: analyzer + emitter paths for set-escrow-percentage/release-escrow/up-modify-escrow;
  extend resource_conflicts.py beyond 1-owner build singleton.
- Tests: extend test_resource_conflicts.py (8) + escrow fixtures (ID 007/024/026).

## DUC binder + emission
- Build: primitives/registry.py (DUC adapters; today zero), primitives/native_binder.py
  (ENGINE_SEMANTICS_MAPPED with binding for DUC), emitter DUC lowering, DSL surface decision.
- Tests: convert test_duc_semantics.py patterns to DSL end-to-end; oracle consistency stays.
- Perf: static warnings only (advisory), from oracle + corpus cardinality.

## Controllers/attack lifecycle
- Build: semantic/native_controller.py (promote attack-group-control first),
  native_controller_interactions.py (exploration→attack, town-size→targeting),
  new attack-lifecycle validator (admission/completion/release/reassess).
- Tests: new attack-lifecycle suite (ID 012/014 + 47-attack-now corpus sample).

## Source graph / game data / strategy
- load-random: ir/source_graph.py LoadKind + resolver materialization.
- .xs boundary: new module (no current owner) for IDIOM-029.
- Game data: ir/civ_profile.py (145-node manifest), patch overlays, broader civs.
- Strategy: ir/strategy_runtime.py observation primitives (DUC/attack/escrow) +
  policy-vs-semantics audit of _validate_native_operand token sets.
