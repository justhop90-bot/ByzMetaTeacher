# AttackExecution IR Checklist

Status: **CLOSED**

Date: 2026-09-29  
Repository: `justhop90-bot/ByzMetaTeacher`  
Final main commit: `3a38cc9e1e9a6172cbfa468255ada2adaff51eea`  
Compiler verification run: **#2519 / 36545008794**  
Compiler result: **SUCCESS**

## 1. Cross-reference matrix

| Checklist item | Existing owner / evidence | Implementation result | Status |
|---|---|---|---|
| Typed semantic attack state | `LearnerAI/Compiler/ir/attack.py` + existing `ir/native_attack.py` | Added `AttackExecutionState` with READY/PREPARE/ASSEMBLE/ATTACK/PRESS/RETREAT/REINFORCE/RETARGET/COMPLETE/REASSESS | [x] |
| Typed native attack mode | `ir/native_attack.py`, native attack binder/tests | Added `AttackExecutionMode`; current executable mode remains ATTACK_NOW | [x] |
| Strategic objective identity | Existing `SemanticId` / strategy demand model in `ir/model.py` and `ir/strategy.py` | `AttackExecution.objective` preserves persistent strategic identity independently of execution state | [x] |
| Attack attempt identity | Existing semantic identity convention | Added execution `identity` and non-negative `attack_attempt_generation` | [x] |
| Capability references | `ir/capability.py` / `CapabilityGraph` | Added immutable `AttackCapabilityRef` with explicit roles; no duplicate capability/role references | [x] |
| DUC target reference | `ir/duc.py` / `DucTargetState` | Added `AttackTargetRef` retaining target validity, generation, filter/list lineage, and provenance | [x] |
| Capability recovery | `ir/strategy.py` / `CapabilityRecoveryContract` | Reused existing recovery contract instead of introducing attack-specific recovery state | [x] |
| Reassessment | `ir/strategy_runtime.py` / `ReassessmentReason` | Added `AttackReassessment` using existing reassessment reasons | [x] |
| Completion witness | `ir/model.py` / `CompletionWitnessContract` | Added `AttackCompletionContract`; COMPLETE requires an explicit objective witness | [x] |
| Attack result classification | Existing Basilisk four-quadrant runtime contract in `validation/attack-four-quadrant-test.md` | Added UNKNOWN/DAMAGED/STALLED/REASSESS/SEVERE_COLLAPSE without treating result classification as completion | [x] |
| Legal transition contract | Existing lifecycle validation doctrine in `ir/model.py` and Basilisk lifecycle audit | Added deterministic legal transition table plus transition provenance | [x] |
| Native plan composition | `ir/native_attack.py` / `NativeAttackLifecyclePlan` | `AttackExecution.native_plan` composes the existing native issue-only plan; native ownership remains unchanged | [x] |
| Native package export | `ir/__init__.py` | Exported all typed AttackExecution symbols | [x] |
| Generic compiler boundary | `tests/test_basilisk_client_boundary.py` | Strategy symbols remain referenced through private module aliases and are not re-exported by generic attack IR | [x] |
| Invalid target protection | `ir/duc.py` + new attack tests | DUC-dependent ATTACK/PRESS/REINFORCE reject stale/invalid target bindings; native attack-now does not require a DUC target | [x] |
| Missing native plan protection | `ir/native_attack.py` + new attack tests | ATTACK/PRESS reject absent native attack plan | [x] |
| Completion protection | `ir/model.py` + new attack tests | COMPLETE rejects missing completion witness | [x] |
| Transition protection | New attack tests | Illegal transitions are rejected | [x] |
| Reassessment protection | New attack tests | REASSESS rejects missing reason contract | [x] |
| Regression coverage | `LearnerAI/Compiler/tests/test_attack_execution_ir.py` | New focused behavioral coverage added | [x] |
| Full compiler verification | GitHub Actions run **36545008794** | 1,123 compiler tests passed; native zero-findings passed | [x] |
| Cross-platform determinism | Same run | 9/9 OS/Python native-support jobs passed | [x] |
| Determinism comparison | Same run | Cross-platform native-support snapshot comparison passed | [x] |
| Aggregate compiler gate | Same run | Compiler verification gate passed | [x] |
| Runtime certification | User-owned DE runtime | No gameplay/runtime claim added by this IR tranche | [x] |

## 2. Implementation commits

- `ac6e6158b6bb685cd2cf58e5685476c1165e5c45` — add typed AttackExecution IR.
- `de0bd4dec92ed70bb9d8b7f1a67b120e1e3a2cde` — export typed IR and preserve generic strategy boundary.
- `6c0bbc82a1b3fafb99ebe09062db309e34e2073c` — bind DUC state through AttackTargetRef in tests.
- `3a38cc9e1e9a6172cbfa468255ada2adaff51eea` — cover transition and reassessment contracts.

## 3. Ownership boundary

The completed contract preserves the intended ownership split, with target admission corrected by the 2026-09-29 MUSE/community reconciliation:

```
AttackExecution
    owns semantic attack-attempt lifecycle

NativeAttackLifecyclePlan
    owns currently supported native attack emission

CapabilityGraph
    owns capability/provider state

DUC IR
    owns target/search state and target provenance

StrategyRuntime
    owns strategic demand, posture, capability recovery, and reassessment reasons

World-state witnesses
    own evidence of actual completion
```

No combat simulator, generic scheduler, second DUC manager, or second capability graph was introduced.

## 4. Closure condition

This checklist is closed because every defined AttackExecution field and invariant has a concrete repository owner, an implementation path, focused regression coverage, and fresh full-compiler verification evidence.

The remaining attack semantics are intentionally outside this tranche where the engine evidence is still open: broader attack-controller modes, native group-state semantics, full DUC runtime targeting behavior, and gameplay completion/replay evidence. Those remain separate research/runtime obligations rather than hidden inside the typed IR.


## Target-policy correction

The follow-up MUSE/community reconciliation established that `attack-now`, `attack-groups`, and town-size attack are native controller mechanisms whose target selection is not the same thing as DUC target acquisition. Therefore `AttackExecution.target` is optional for those modes and mandatory only for `DUC_TARGETED` execution states that actually consume a DUC target. See `docs/research/2026-09-29-muse-community-attack-reconciliation.md`.
