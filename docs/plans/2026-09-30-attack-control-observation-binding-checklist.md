# Attack-Control Observation Binding Checklist

Date: 2026-09-30
Branch: `strategy-attack-control-observations`
Base: `ed5510cf698e63be75fb58d785b80636582902d2`
Scope: compiler-side strategic observation binding for the two evidence-backed attack-group Strategic Numbers. This slice is descriptive observation only and does not promote native controller execution.

## Cross-reference

Primary open compiler gap:
- `LearnerAI/Compiler/MUSE_NEXT_IMPLEMENTATION_CHECKLIST_2026-09-28.md`
  - Strategy runtime observation closure remains open for attack/controller observations.
  - Attack execution is already typed; this task must not create another attack lifecycle.
- `LearnerAI/Compiler/semantic/native_controller.py`
  - `attack-group-control` is an explicit controller family.
  - `sn-number-attack-groups` and `sn-percent-attack-soldiers` are catalogued control surfaces.
  - Their controller/surface status remains `EVIDENCE_ONLY`.
- `05-SN-TIMER.md`
  - SN 36 `sn-number-attack-groups`: required range `0..Max`, default `0`.
  - SN 227 `sn-percent-attack-soldiers`: required range `0..100`, default `75`.
- `docs/reference/inventories/airef-strategic-number-inventory.json`
  - Pinned Strategic Number namespace and provenance remain authoritative for catalog identity.
- `docs/research/2026-09-29-muse-community-attack-reconciliation.md`
  - Attack-now, attack-groups, and town-size attack remain distinct controller mechanisms.
  - Controller interactions remain evidence-only.
  - Attack completion/release, target acquisition, group membership, and exploration coupling remain OPEN.
- `docs/plans/2026-09-29-attack-execution-ir-checklist.md`
  - AttackExecution is already closed as typed semantic IR.
  - Only `ATTACK_NOW` is currently executable-safe.
  - This observation slice must reuse that IR boundary rather than expand execution semantics.
- `LearnerAI/Compiler/ir/strategy_runtime.py`
  - Existing exact SN observation specializations already bind SN 3, 18, 42, 61, 74, and 264.
  - Generic `up-compare-sn` remains `PERSISTENT_CONTROL_STATE` when no specialized contract applies.
- `LearnerAI/Compiler/tests/test_strategy_runtime.py`
  - Existing specialization tests provide the focused regression pattern.

## Implementation checklist

- [ ] Add `StrategicObservationType.ATTACK_GROUP_CONTROL`.
- [ ] Add `StrategicObservationType.ATTACK_SOLDIER_PERCENT_CONTROL`.
- [ ] Specialize SN 36 comparisons as `ATTACK_GROUP_CONTROL`.
- [ ] Enforce SN 36 configured comparison values as `0..Max`.
- [ ] Specialize SN 227 comparisons as `ATTACK_SOLDIER_PERCENT_CONTROL`.
- [ ] Enforce SN 227 configured comparison values as `0..100`.
- [ ] Preserve all existing comparison operators for SN 36/227.
- [ ] Preserve generic `PERSISTENT_CONTROL_STATE` fallback for unrelated SNs.
- [ ] Add focused valid/invalid binding tests.
- [ ] Add a regression proving the new observations are still observations, not executable controller commands.
- [ ] Keep attack-group controller catalog status `EVIDENCE_ONLY`.
- [ ] Do not change AttackExecution target requirements, completion, release, DUC targeting, exploration coupling, timers, or native attack lowering.
- [ ] Do not add new source syntax or a second strategy/control API.

## Guardrails

- Observation truth describes the evaluated `up-compare-sn` predicate only.
- SN meaning is catalog-backed; controller ownership is not promoted from community evidence.
- No automatic SN mutation is inferred.
- No attack-group membership state is inferred.
- No attack-start/completion witness is inferred.
- No target acquisition is inferred.
- No DUC target is required for attack-control observations.
- No exploration prerequisite is promoted to compiler policy.
- Unknown/open engine behavior remains UNKNOWN/OPEN.

## Acceptance

1. Focused attack-control observation tests pass.
2. Existing strategy-runtime regression remains green.
3. Full compiler regression passes.
4. Native zero-findings fixtures remain green.
5. Cross-platform native-support determinism remains green.
6. The emitted `.per` behavior is unchanged because this slice only specializes semantic observation typing.

## Not in scope

- `attack-groups` executable lowering.
- `sn-special-attack-type2` semantics.
- Attack completion/release.
- Attack-group membership or unit assignment.
- Town-size attack semantics.
- Exploration-to-attack executable coupling.
- Timer-driven attack windows.
- Runtime DE certification.
