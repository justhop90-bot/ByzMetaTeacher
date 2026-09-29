# 07 — Controller + attack static contracts @ `cd923b5a` (describe, never promote)

Seeded in `semantic/native_controller.py:374-474`; domains ECONOMY/EXPLORATION/ATTACK/DEFENSE/TARGETING/RESOURCE_CONTROL/DUC (`:19-27`).
Representation fields per controller: controller / control surface / input / mutation / feedback / gating /
world-state dependency / lifetime / version / performance-cardinality.

## Controllers (9 — ALL `EVIDENCE_ONLY`, descriptive)

| Controller | Domain | Evidence/Status | Surfaces (inputs) | Mutation | Feedback/Gating/World-dep | Lifetime/Version/Perf |
|---|---|---|---|---|---|---|
| attack-group-control | ATTACK | COMMUNITY_PRACTICE / EVIDENCE_ONLY | `attack-now` (COMMAND) + SN 36,227 | compiler `up-modify-sn` writes; no AUTO_MUTATES proven | GATES→exploration (gated-by); AFFECTS_TARGETING←town-size; REQUIRES_EXPLORATION edge | PERSISTENT, DE, no perf/card |
| civilian-task-allocation | ECONOMY | COMMUNITY_PRACTICE / EVIDENCE_ONLY | SN 117,120,118,119,1,0,2 | compiler writes | COUPLED_WITH↔resource-escrow (explicitly NON-directional, `:537-553`) | PERSISTENT, DE, none |
| exploration-control | EXPLORATION | COMMUNITY_PRACTICE / EVIDENCE_ONLY | SN 42,18,167 | compiler writes | gates attack (target side) | PERSISTENT, DE, none |
| town-size-defense-targeting | DEFENSE | COMMUNITY_PRACTICE / EVIDENCE_ONLY | SN 74,20 | compiler writes | AFFECTS_TARGETING→attack | PERSISTENT, DE, none |
| resource-escrow-control | RESOURCE_CONTROL | COMMUNITY_PRACTICE / EVIDENCE_ONLY | release/set-percentage/up-release/up-modify-escrow (escrow transfer mappings CONTRACTED, controller itself stays EVIDENCE_ONLY) | compiler + engine transfer | GATES→production-admission, →research-admission | PERSISTENT, DE, none |
| duc-search-state | DUC | ENGINE_FACT / EVIDENCE_ONLY | 8 search commands + 2 indices (ENGINE_FACT kind) | ENGINE_AUTOMATIC index resets (8 interactions) | FEEDS→duc-target-control | PERSISTENT; WK/UP→DE; MEDIUM/0..240 local, FAST/0..40 remote (advisory) |
| duc-target-control | DUC | ENGINE_FACT / EVIDENCE_ONLY | 4 target commands | compiler-issued target ops | FEEDS sink | PERSISTENT, DE, none |
| production-admission | ECONOMY | ENGINE_FACT / EVIDENCE_ONLY | can-train/can-train-with-escrow/up-can-train/train | none (admission reads) | GATES sink from escrow | PERSISTENT, DE, none |
| research-admission | ECONOMY | ENGINE_FACT / EVIDENCE_ONLY | can-research/can-research-with-escrow/up-can-research/research | none | GATES sink from escrow | PERSISTENT, DE, none |

Checklist corroboration: `NATIVE_CONTROLLER_SEMANTICS_CHECKLIST_2026-09-28.md:14-22` (family→evidence→disposition);
deliberately-not-claimed list `:67-76` (no 512-SN classification, no simulation, no attack completion/release, no cost
propagation, no auto-promotion). No interaction is `ENGINE_SEMANTICS_MAPPED`; none changes lowering (GapMap:171);
SN bindings are metadata on `StrategicNumberSemanticReport` only (proven non-effect `test_strategic_number_semantics:28-104`).

## Interactions (15 — ALL `EVIDENCE_ONLY`; contract stops at description)

`native_controller_interactions.py:501-740`: attack-groups-gated-by-exploration (GATES, COMMUNITY);
town-size-affects-attack-targeting (AFFECTS_TARGETING, COMMUNITY); civilian-allocation-coupled-with-resource-escrow
(COUPLED_WITH, non-directional); escrow-gates-production/research-admission (GATES, ENGINE_FACT, DE);
duc-local/remote-search-feeds-target-control (FEEDS, ENGINE_FACT, WK→DE, MEDIUM/0..240 + FAST/0..40 advisory);
8× `duc-*-auto-resets-*-index` (AUTO_MUTATES surface→index: filter-include/exclude/range + reset-filters × local/remote,
ENGINE_FACT, PERSISTENT, SAME_RULE, owner ENGINE_AUTOMATIC, UP→DE). Fail-closed guarantees: no reverse duplicates;
FEEDBACK excluded from `dependency_edges()`; MAPPED requires ENGINE_FACT; version-mismatch rejected; AUTO_MUTATES
requires ENGINE_AUTOMATIC + surface target; fingerprint determinism. TEST `test_native_controller_interactions:261-298`
(15-identity corpus + EVIDENCE_ONLY + cardinality/perf), `test_native_controller_semantics` (graph validation, executable
gate `:104-110` — all seeded-surface `require_executable_surface` calls raise, proven).

## Attack — issue vs everything else

A1 `attack-now ()` zero-arg Action — the ONLY executable slice — `EXECUTABLE_SAFE` (issue-only).
Binder `NativeAttackSemanticBinding{command, native_version, kind=Action, params=0, controller=attack-group-control,
mapping=attack.execution.issue, support=EXECUTABLE_SAFE, completion=COMPLETION_UNOBSERVED, evidence_sources}`
(`native_binder:866-948`; mapping `engine_semantics:520-544`; lifecycle 4-tuple
ADMISSION_REQUIRED→ISSUE→COMPLETION_UNOBSERVED→REASSESS_REQUIRED, `ir/native_attack:30-74`).
Plan validation: facts Fact-kind exact arity; actions binder-promoted exact arity + Action-kind (`registry:278-314`).
PROVEN: exact-arity gate (nonzero fails), Fact-position rejected, unknown `up-reset-attack-now` fails closed, generic
`bind("attack-now")` refuses, artifact contains exactly the two `(attack-now)` actions with zero SN/timer/reset/goals,
native lint zero-findings (`test_native_attack_lifecycle`, `assert_attack_native:112-151,195-200`).
Descriptive interactions only (gated-by-exploration, town-size-targeting) — adding facts to attack plans is PROVEN
wrong by test (`:255-262`). Ownership/lifetime: engine owns machinery; compiler owns rule order/identity only.
One-shot request; persistence NONE claimed.
A2–A7 (static contract stops): admission (which units available) EVIDENCE_ONLY (label, not check); group state
(SN 36/227 writes) EVIDENCE_ONLY (`validate_attack_plan` REJECTS SN writes in attack plans; mapping
`attack.group-state-control` EVIDENCE_ONLY `engine_semantics:875-889`); targeting (explored-enemy dependence)
EVIDENCE_ONLY (interaction only, no predicate); completion OPEN (`COMPLETION_UNOBSERVED` IS the contract — never emit
COMPLETE/RELEASE `assert_attack_native:143-146`); release/reset (`up-reset-attack-now`, timers, SN resets)
OPEN/UNKNOWN (binder rejects; assert forbids emitting); reassessment EVIDENCE_ONLY label (no scheduler; recovery =
"reassess through future native evidence").

REPRESENT: controllers/surfaces/interactions descriptively. VALIDATE: graph/lookup/version/fingerprint gates.
EMIT SAFELY: attack-issue only. MUST REMAIN OPEN: causal/runtime ownership, completion, cost propagation, 512-SN
classification, simulation, timer-gated attack loops, SN-driven group control, completion witnesses from attack plane.
