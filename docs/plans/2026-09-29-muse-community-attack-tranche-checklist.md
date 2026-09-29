# MUSE + Community Attack/DUC Compiler Tranche Checklist — 2026-09-29

Status: CLOSED

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

- [x] Correct AttackExecution target requirements to be mode-sensitive.
  - ATTACK_NOW: target optional.
  - ATTACK_GROUPS: target optional.
  - TOWN_SIZE_ATTACK: target optional.
  - DUC_TARGETED: target required for target-dependent ATTACK/PRESS/REINFORCE.
- [x] Add a canonical `AttackTargetRef.from_duc()` binding helper.
- [x] Preserve DUC provenance, source generations, proof, and validity without simulating native object liveness.
- [x] Ensure RETARGET/REASSESS can carry STALE/UNKNOWN target state without authorizing a DUC-dependent attack.
- [x] Preserve current native issue-only boundary; no attack controller or completion semantics are promoted.

## Focused tests

- [x] ATTACK_NOW without DUC target is accepted.
- [x] ATTACK_GROUPS without DUC target is accepted as semantic IR but remains non-executable.
- [x] TOWN_SIZE_ATTACK without DUC target is accepted as semantic IR but remains non-executable.
- [x] DUC_TARGETED without a target is rejected.
- [x] DUC_TARGETED with a valid target is accepted.
- [x] DUC_TARGETED with STALE/UNKNOWN target is rejected for ATTACK/PRESS/REINFORCE.
- [x] `AttackTargetRef.from_duc()` preserves target generations/provenance.
- [x] Existing native attack binder/emitter tests remain unchanged and green.

## Repository documentation

- [x] Update the attack execution checklist to record the corrected target-policy boundary.
- [x] Update `compiler_coverage_baseline.md` only where the new semantic bridge changes the documented gap; do not claim native lifecycle closure.
- [x] Add the MUSE/community reconciliation document to the attack evidence index if one exists.

## Verification gate

- [x] Focused AttackExecution tests pass.
- [x] Full compiler regression passes.
- [x] Native attack zero-findings fixture passes.
- [x] Nine OS/Python determinism jobs pass.
- [x] Cross-platform native-support snapshot comparison passes.
- [x] Aggregate compiler verification gate passes.
- [x] No open PRs or stale parallel repair branch is treated as current work.

## Closure rule

Close this checklist only when the semantic target-policy bridge is implemented and the fresh full compiler gate is green. Native attack completion, controller ownership, DUC object liveness, attack-group semantics, and runtime attack behavior remain explicitly OPEN.

## Closure evidence

- Implementation code commit: `43ee4845b8175efcc1cf7abfea9bea69e98b3576`.
- Focused regression/test commit: `829e5e8b7dd7e1b97b7481c5ca288fcf6b4c5e54`.
- Compiler workflow #2521 / Actions run `36545667502` passed: 1,130 full compiler regression tests; focused persistent-state suites 7/24/29/15; native zero-findings including the attack fixture; 9/9 OS/Python determinism jobs; snapshot comparison; aggregate compiler verification gate.
- Current `main`: `93fa8f36ea9da626af0fe274d528e5e1a448ba68`; later commits in this tranche are documentation-only.
- Open PRs: none.
- Basilisk Validator baseline profile `8596a45` still fails its pre-existing `Crossbow action boundary must re-check its live role demand` assertion. The current validator self-tests pass, and this failure occurs in the historical baseline profile rather than the attack IR/compiler verification path. It remains a separate project-health item, not a blocker for this compiler tranche.

## Result

Closed with the following semantic boundary now explicit and enforced: native controller attack modes do not require DUC targets; only explicitly DUC-targeted attack execution requires a valid DUC target. Native attack completion, controller ownership, group membership, target liveness, and runtime attack behavior remain OPEN.
