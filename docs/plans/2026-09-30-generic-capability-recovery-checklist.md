# Generic Capability Loss / Recovery Contract Checklist

Date: 2026-09-30
Base main: 916f7d85d0785f9fcbe0bf45a03d1e0c3e60844e
Branch: generic-capability-recovery-contract

## Audit finding

The forensic repair queue identifies capability-loss/recovery as the next generic compiler seam.
The repository already had a downstream strategy policy, but the generic capability graph had no
typed recovery contract or state transition model.

Cross-references:

- `LearnerAI/Compiler/COMPILER_FORENSIC_AUDIT_2026-09-26.md`
  - ordered repair #6: capability-loss/recovery contract
  - required behavior: preserve persistent demand through temporary capability loss without inventing a scheduler
- `LearnerAI/Compiler/COMMUNITY_ENGINE_SEMANTICS_CHECKLIST_2026-09-26.md`
  - capability history distinguishes EXECUTION_FEASIBILITY from PROVIDER_WORLD_STATE
  - loss requires true -> false evidence
  - recovery requires false -> true evidence
  - provider-state recovery remains partial until generic BUILD/TRAIN/RESEARCH provider semantics exist
- `LearnerAI/Compiler/semantic/community_engine.py`
  - existing descriptive `CapabilityTransition` classifier remains the evidence/history boundary
- `LearnerAI/Compiler/ir/strategy.py`
  - existing strategy-only recovery policy is downstream client semantics and is not imported into generic compiler code
- `LearnerAI/Compiler/ir/capability.py`
  - generic `CapabilityRecoveryContract`, `CapabilityRecoveryState`, and explicit loss/recovery events are now part of the generic capability IR
- `LearnerAI/Compiler/semantic/capability_bridge.py`
  - projected capability demands inherit the generic default recovery contract through `CapabilityDemand`

## Compiler contract

A temporary capability loss does not replace the demand.

- ACTIVE + LOST -> BLOCKED
- BLOCKED + LOST -> BLOCKED
- BLOCKED + RECOVERED -> ACTIVE
- ACTIVE + RECOVERED -> ACTIVE
- COMPLETE + RECOVERED -> COMPLETE
- INVALIDATED + RECOVERED -> rejected

The demand identity is preserved through every temporary loss transition.

The generic recovery contract requires:

- preserve original demand identity;
- preserve opportunity-cost protection during temporary loss;
- reopen the same demand after recovery.

## Boundary

This repair does not:

- infer runtime capability loss from a false `can-*`;
- invent provider failure channels;
- schedule replacement actions;
- claim a provider is destroyed/rebuilt;
- promote runtime truth for BUILD/TRAIN/RESEARCH provider behavior;
- replace explicit world-state invalidation;
- import downstream StrategyProfile or StrategyRuntimeState into generic compiler code.

The existing `CapabilityTransition` classifier remains responsible for deciding whether observed
truth changed from true->false or false->true. The new IR state machine only defines what the
compiler's demand contract means once such a transition is established.

## Tests

- loss blocks the same demand;
- recovery reopens the same demand;
- completed demand does not reopen;
- invalidated demand cannot be reopened by a capability-recovery event;
- repeated loss is idempotent;
- recovery policy cannot disable demand preservation;
- recovery policy cannot disable opportunity-cost preservation;
- recovery policy cannot disable reopening;
- capability projection carries the default generic recovery contract.

## Acceptance

- [ ] TDD red test observed before implementation (not independently observed in this environment).
- [x] Focused capability recovery tests pass.
- [x] Full compiler regression passes.
- [x] Native zero-findings acceptance passes.
- [x] 9/9 native-support determinism passes.
- [x] Snapshot comparison passes.
- [x] Compiler verification gate passes.

## Runtime unknowns retained

- actual DE provider destruction/recovery behavior;
- exact queue/provider semantics;
- capability truth sampling cadence;
- provider loss/recreation timing;
- cross-pass visibility of provider recovery;
- action issuance failure versus capability loss.
