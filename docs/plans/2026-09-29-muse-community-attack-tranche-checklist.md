# MUSE + Community Attack/DUC Compiler Tranche Checklist — 2026-09-29

Status: IN PROGRESS

Base research commit: `fdd3c56ef90014a80e16fb65f8627b502445e35e`

## Cross-reference gate

- [x] Read the new MUSE dossier and its 01–09 state/reconciliation artifacts.
- [x] Cross-check attack mechanisms against official update notes.
- [x] Cross-check attack-now / attack-groups / town-size attack against community documentation.
- [x] Inspect direct Duke attack controller source.
- [x] Inspect direct lewisc64 DUC/attack idioms.
- [x] Separate engine/official facts, community practice, and compiler inference.
- [x] Identify the overconstraint in the prior AttackExecution IR: attack-now does not require a DUC target.

## Implementation

- [ ] Correct AttackExecution target requirements to be mode-sensitive.
  - ATTACK_NOW: target optional.
  - ATTACK_GROUPS: target optional.
  - TOWN_SIZE_ATTACK: target optional.
  - DUC_TARGETED: target required for target-dependent ATTACK/PRESS/REINFORCE.
- [ ] Add a canonical `AttackTargetRef.from_duc()` binding helper.
- [ ] Preserve DUC provenance, source generations, proof, and validity without simulating native object liveness.
- [ ] Ensure RETARGET/REASSESS can carry STALE/UNKNOWN target state without authorizing a DUC-dependent attack.
- [ ] Preserve current native issue-only boundary; no attack controller or completion semantics are promoted.

## Focused tests

- [ ] ATTACK_NOW without DUC target is accepted.
- [ ] ATTACK_GROUPS without DUC target is accepted as semantic IR but remains non-executable.
- [ ] TOWN_SIZE_ATTACK without DUC target is accepted as semantic IR but remains non-executable.
- [ ] DUC_TARGETED without a target is rejected.
- [ ] DUC_TARGETED with a valid target is accepted.
- [ ] DUC_TARGETED with STALE/UNKNOWN target is rejected for ATTACK/PRESS/REINFORCE.
- [ ] `AttackTargetRef.from_duc()` preserves target generations/provenance.
- [ ] Existing native attack binder/emitter tests remain unchanged and green.

## Repository documentation

- [ ] Update the attack execution checklist to record the corrected target-policy boundary.
- [ ] Update `compiler_coverage_baseline.md` only where the new semantic bridge changes the documented gap; do not claim native lifecycle closure.
- [ ] Add the MUSE/community reconciliation document to the attack evidence index if one exists.

## Verification gate

- [ ] Focused AttackExecution tests pass.
- [ ] Full compiler regression passes.
- [ ] Native attack zero-findings fixture passes.
- [ ] Nine OS/Python determinism jobs pass.
- [ ] Cross-platform native-support snapshot comparison passes.
- [ ] Aggregate compiler verification gate passes.
- [ ] No open PRs or stale parallel repair branch is treated as current work.

## Closure rule

Close this checklist only when the semantic target-policy bridge is implemented and the fresh full compiler gate is green. Native attack completion, controller ownership, DUC object liveness, attack-group semantics, and runtime attack behavior remain explicitly OPEN.