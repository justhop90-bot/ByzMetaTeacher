# AttackExecution Mode-Control Bridge Checklist

Date: 2026-09-30
Base main: b74004d07c740ddcfab32584378f6dc5ba8e035e

## Audited gap

AttackExecution now reaches the operational-semantics layer, but non-ATTACK_NOW modes were not connected to the persistent Strategic Number control surfaces that community practice already models and the compiler already types as observations.

## Cross-reference

| Mode | Existing evidence/owner | New compiler connection |
|---|---|---|
| ATTACK_GROUPS | strategy_runtime SN 36 + SN 227 observation bindings; native controller catalog remains evidence-only | READ controls for sn-number-attack-groups and sn-percent-attack-soldiers |
| TOWN_SIZE_ATTACK | strategy_runtime SN 74 observation binding; town-size controller remains evidence-only | READ control for sn-maximum-town-size |
| ATTACK_NOW | native attack issue slice | no new controller control dependency |
| DUC_TARGETED | DUC SearchSession/TargetSession state | retain DUC identity recovery/reference separately |

## Invariants

- Control references describe persistent native control state; they are not completion or action-acknowledgement facts.
- No Strategic Number mutation is inferred.
- No attack-group membership is inferred.
- No attack target-selection ownership is promoted.
- No exploration coupling is promoted.
- No attack completion or release semantics are added.
- Native .per emission is unchanged.
- Existing attack_plan public API remains the only channel.

## Acceptance

- [ ] Focused operational-domain tests pass.
- [ ] Every attack SN control resolves through NativeControllerCatalog surface + controller metadata.
- [ ] Every resolved attack control is READ-only and remains EVIDENCE_ONLY in the existing catalog.
- [ ] Every resolved attack control links to a CONTROL_STATE observation included in observe and reobserve.
- [ ] Evidence-only control observations are not promoted to boolean admission facts or mutation permissions.
- [ ] Full compiler regression passes.
- [ ] Native zero-findings and 9/9 determinism remain green.
- [ ] Compiler verification gate passes.

Runtime DE certification remains user-owned and outside this repair.
