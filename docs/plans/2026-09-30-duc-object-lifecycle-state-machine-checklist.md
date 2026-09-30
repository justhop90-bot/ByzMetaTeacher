# DUC Object Lifecycle State Machine Checklist

Date: 2026-09-30
Branch: `duc-object-lifecycle-state-machine`
PR: #207
Scope: compiler-side persistent object identity lifecycle. Native selected-target lifetime and death behavior remain runtime research.

## Cross-reference

Primary existing contract:
- `docs/plans/2026-09-28-duc-target-lifetime-repair-checklist.md`
  - R7 closes compiler liveness modeling with `DucTargetStatus`, `DucTargetProof`, and separate `DucObjectLiveness`.
  - R3/R4 and OPEN_NATIVE_BOUNDARIES remain deliberately unpromoted.
- `LearnerAI/Compiler/ir/duc.py`
  - existing `DucObjectRef.native_object_id`, list generation/index provenance, target validity/proof/liveness.
- `LearnerAI/Compiler/semantic/duc.py`
  - existing search generations, target establishment, `up-set-target-by-id`, target invalidation, pass advancement.
- `LearnerAI/Compiler/tests/test_duc_semantics.py`
  - existing fail-closed target lifetime and reset/mutation coverage.

This slice adds lifecycle state to the existing `DucObjectRef`; it does not introduce a second persistent object API.

## Implementation checklist

- [x] Add typed lifecycle states:
  - `UNBOUND`
  - `DISCOVERED`
  - `STORED`
  - `REACQUIRED`
  - `VALIDATED`
  - `INVALIDATED_NATIVE`
  - `INVALIDATED_WORLD`
  - `INVALIDATED_UNKNOWN`
- [x] Add typed lifecycle events and transition history.
- [x] Enforce illegal transitions with compiler-side `ValueError` subclass.
- [x] Attach lifecycle state to existing `DucObjectRef`.
- [x] Mark `up-set-target-object` results as `DISCOVERED`.
- [x] Capture `object-data-id` goal output as a stored identity binding.
- [x] Represent constant `up-set-target-by-id` as native-ID bind + current acquisition transaction.
- [x] Release `REACQUIRED`/`VALIDATED` to `STORED` at compiler pass advance.
- [x] Keep native/world liveness separate from lifecycle state.
- [x] Keep lifecycle types local to `LearnerAI/Compiler/ir/duc.py`; do not add a package-root re-export that would introduce an `ir`/semantic circular-import edge.
- [x] Add focused legal-transition and illegal-transition tests.
- [x] Add search discovery, object-data identity capture, native-ID reacquisition, symbolic-ID reacquisition, and pass-release tests.

## Guardrails

- [x] Failed native acquisition may produce `INVALIDATED_NATIVE`.
- [x] Identity conflict may produce `INVALIDATED_UNKNOWN`.
- [x] `INVALIDATED_WORLD` requires an independent world witness.
- [x] Lifecycle state does not imply world liveness.
- [x] Selected-target lifetime is not stored as persistent identity.
- [x] Search-list index remains provenance/query state, not durable identity.
- [x] Runtime probes are not embedded in compiler IR.

## Explicitly not promoted

- [ ] Selected-target slot retention after object death.
- [ ] `up-object-data(object-data-id)` behavior after death.
- [ ] Old search-list entry behavior after death.
- [ ] Timing of `up-set-target-by-id` failure after destruction.
- [ ] Ordinary combat death vs forced XS removal equivalence.
- [ ] Any inference from failed target acquisition to `WITNESSED_GONE`.

These remain governed by the existing native capture promotion rule.

## Acceptance

The compiler may rely on the lifecycle state machine now because it describes compiler knowledge and legal transitions only. Native target-lifetime conclusions remain evidence-gated and `RUNTIME_DEPENDENT`.

Required verification:
1. Focused lifecycle tests pass.
2. Full compiler regression passes.
3. Existing native zero-findings fixtures remain green.
4. Cross-platform native-support determinism remains green.
5. No runtime death probe is required for this compiler slice.
