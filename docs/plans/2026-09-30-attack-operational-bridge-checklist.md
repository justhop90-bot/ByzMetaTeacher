# Typed AttackExecution Operational Bridge Checklist

Date: 2026-09-30
Base: b8d851a47cfd14c87317d06e905e7458ab11f0be (PR #209 head)

## Gap

AttackExecution already owns the typed semantic lifecycle, target provenance, capability references, completion contract, reassessment, and native-plan composition. The operational-semantics layer only projected NativeAttackLifecyclePlan, leaving the typed lifecycle as an unconsumed compiler IR.

## Cross-reference

| Contract | Existing owner | Repair |
|---|---|---|
| Attack lifecycle | ir/attack.py | Preserve existing state/transition validation |
| Operational loop | semantic/operational_domains.py | Add typed AttackExecution projection |
| Native issue emission | emitter/per.py | Emit only execution.native_plan |
| Native schema validation | primitives/registry.py | Validate nested native plan, not semantic wrapper |
| Compiler threading | compiler.py | Keep existing attack_plan channel |
| Evidence boundary | operational policy | References for lifecycle/target/capability are compiler policy; no runtime truth inferred |

## Invariants

- Attack objective identity remains separate from attack attempt identity.
- AttackExecution state never becomes native completion truth.
- DUC target validity remains compiler-state validation only.
- Capability references remain prerequisite observations, not simulator outputs.
- AttackExecution.native_plan is the only executable/native emission surface.
- DUC_TARGETED recovery includes DUC identity reacquisition.
- Terminal COMPLETE state does not generate a recurrent operational loop.

## Tests

- Typed ATTACK execution projects to OperationalDomain.ATTACK.
- Existing attack action is preserved as the operational request.
- DUC_TARGETED projection carries REACQUIRE_DUC_IDENTITY.
- Public attack_plan channel accepts typed AttackExecution.
- Existing native NativeAttackLifecyclePlan emission remains unchanged.

## Explicitly open

- Native attack completion/release semantics.
- Runtime DUC target liveness.
- Attack-group controller causality.
- Town-size/exploration coupling.
- Gameplay/runtime execution.

No runtime probe is part of this repair.


## Follow-on repair: mode-specific controller control bridge
- [x] ATTACK_GROUPS references the existing SN 36 attack-group count control.
- [x] ATTACK_GROUPS references the existing SN 227 soldier-percentage control.
- [x] TOWN_SIZE_ATTACK references the existing SN 74 town-size control.
- [x] Controls are READ-only operational state; no automatic mutation or controller ownership is inferred.
- [x] ATTACK_NOW native emission remains unchanged.
- [x] DUC_TARGETED retains its separate DUC identity recovery/control reference.
- [x] Add focused projection tests.
- [x] Add no-runtime-claim boundary documentation.
