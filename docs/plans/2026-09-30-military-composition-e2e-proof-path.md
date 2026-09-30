# Military composition end-to-end proof path

Date: 2026-09-30.
Status: first integration proof slice.

## Objective

Prove one compiler-level causal path across existing semantic subsystems:

military composition -> production queue -> resource arbitration -> DUC target -> attack lifecycle -> world witness -> capability recovery.

This is a structural compiler proof. It is not a runtime claim and it does not promote DUC-targeted attack lowering.

## Existing subsystem inputs

| Stage | Existing contract | Proof requirement |
| --- | --- | --- |
| Military composition | Semantic demand identity | composition owns production demands |
| Production queue | ProductionLifecycle | each unit target matches a production lifecycle and UnitId |
| Resource arbitration | ResourceClaim | each production demand has a transient claim owned by composition |
| DUC target | AttackTargetRef / DucTargetState | target is VALID and is the exact target consumed by attack |
| Attack lifecycle | AttackExecution | ATTACK/PRESS, DUC_TARGETED, PRIMARY_FORCE, native attack plan |
| Witness | CompletionWitnessContract | witness establishes attack objective |
| Recovery | CapabilityRecoveryContract + State | LOSS -> BLOCKED -> RECOVERED -> ACTIVE preserves demand |

## New internal proof IR

`LearnerAI/Compiler/ir/military_composition.py` contains:

- `MilitaryCompositionUnitTarget`
- `MilitaryCompositionPlan`
- `MilitaryCompositionProofPath`

It is internal IR, not source syntax, not a scheduler, not a utility optimizer, and not combat simulation.

`CompilerSemanticProgram.military_proof_path` is the internal assembly slot.

## Native boundary

The proof intentionally uses `AttackExecutionMode.DUC_TARGETED` so DUC targeting is causal. Current compiler policy does not mark DUC-targeted attack as natively executable. Therefore the path is recorded as structural-semantic complete with native lowering OPEN.

No runtime engine fact is promoted.

## Acceptance

The slice is accepted when the proof IR is immutable, illegal cross-domain links are rejected, a complete proof validates, the proof attaches to `CompilerSemanticProgram`, compiler determinism remains green, and the DUC-targeted native boundary remains documented as OPEN.

The next slice is native lowering/research for this path, not another parallel composition architecture.
