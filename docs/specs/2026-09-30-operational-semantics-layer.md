# Operational Semantics Layer

## Purpose

The compiler represents recurrent .per control using the operational cycle:

**OBSERVE -> ADMIT -> REQUEST -> DEBOUNCE -> REOBSERVE -> REASSERT / RETRY**

This is an internal compiler semantic layer. It does not add source syntax, simulate the game, or invent native acknowledgements.

## Semantic boundary

A native request establishes only request issuance.

A debounce condition establishes only that repeated issuance should be suppressed.

A world-state or controller observation establishes truth.

UNKNOWN remains distinct from FALSE.

Temporary execution blockage preserves strategic demand unless an explicit invalidation contract says otherwise.

DUC identity remains reacquirable identity, not permanent native target liveness.

Timers provide cadence/control and cannot independently establish world-state completion.

## Core IR

OperationalLoopContract owns one recurrent execution pattern. It references existing semantic demand identity, observation expressions/references, native/compiler requests, persistent control references, and recovery policy.

The required stages are:

1. observe
2. admission
3. request
4. debounce
5. reobserve
6. recovery

The operational IR is static. It describes legal semantic structure; it does not store mutable runtime state.

## Domain cross-reference

| Domain | Observation | Admission | Request | Debounce | Re-observation | Recovery |
| --- | --- | --- | --- | --- | --- | --- |
| Attack | army, enemy, exploration, controller state | attack-mode conditions | attack controller / native attack plan | timer, Goal, controller state | pressure/reassessment/world state | reissue, reassess, retarget |
| Production | can-train, provider, counts, pending | target capability + unmet demand | train | pending/current+queued | unit/world count | retry after fresh admission |
| Construction | can-build, pending, building count | build capability | build | pending-object suppression | building count | retry |
| Research | can-research, research state | research capability | research | research-pending/retry barrier | research completion | retry/reassess |
| DUC | search availability, identity, search state | search/target admissibility | DUC operation | retained identity/generation | target/data/reassessment state | reacquire/reset/retry |
| Escrow | resource-control state | protected execution admission | release/policy/action | escrow ownership/state | resource/action state | release/reassess/handoff |
| Timer | timer state/trigger | cadence condition | timer mutation | timer state | non-timing world/control state | rearm |
| Goal | Goal state | mode/phase condition | Goal mutation | desired persistent value | Goal/control/world observation | restore/reassert |
| Strategic Number | SN state | controller reconfiguration condition | SN mutation | desired SN value | downstream controller/world observation | restore/reconfigure |

## Existing compiler integration

LearnerAI/Compiler/ir/operational.py defines the typed operational IR.

LearnerAI/Compiler/semantic/operational_semantics.py defines structural validation and projection from SemanticDemand.

LearnerAI/Compiler/semantic/operational_domains.py projects compiler-owned attack, DUC, and escrow plans into the same model.

LearnerAI/Compiler/compiler.py runs the operational semantic gate during compilation.

The layer consumes existing SemanticDemand, NativeAttackLifecyclePlan, NativeDucPlan, NativeEscrowReleasePlan, and NativeEscrowPolicyPlan rather than creating parallel execution representations.

## Evidence classification

The operational projection itself is COMPILER POLICY.

Underlying native facts, community practices, and unresolved engine behavior remain authoritative in the existing evidence registry. The operational layer does not manufacture new EvidenceRef provenance.

A future promotion of an operational relationship to ENGINE FACT or COMMUNITY PRACTICE must attach explicit supporting evidence rather than changing the enum alone.

## Validation invariants

The validator rejects:

- missing observation stages;
- unresolved stage or guard observation references;
- empty admission;
- requests without commands or execution references;
- timing-only re-observation;
- retry without explicit admission;
- recovery that discards the owning demand;
- empty control references.

The validator intentionally does not require a universal completion witness for controller-owned attack or DUC operational loops.

## Non-goals

This layer is not:

- a runtime scheduler;
- a game simulator;
- a hidden action-success API;
- a replacement for lifecycle state;
- a second .per language;
- a tournament bot architecture.

## Verification

The compiler workflow is the authoritative integration gate. Focused tests cover the IR invariants and domain adapters. Native validation remains responsible for the emitted .per artifact.
