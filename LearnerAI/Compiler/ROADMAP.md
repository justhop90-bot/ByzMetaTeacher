# MUSE Community Gap Roadmap — 2026-09-30

Status: authoritative roadmap for remaining compiler work.

## Research conclusion

The repository is past the compiler-plumbing phase. The remaining gap is native control synthesis: connecting community rule idioms to the typed semantic substrate without inventing a scheduler, simulator, or second .per language.

Current community evidence converges on four major execution systems:

1. production admission + pending + queue arbitration;
2. DUC search/target/group execution;
3. attack/controller execution and recovery;
4. escrow/resource protection and emergency release.

Those systems then feed a higher layer of recurring community strategy patterns: goal-backed state machines, SN mode switching, TSA, counter trains, military parity, defense toggles, DUC micro, starvation recovery, water splits, map tables, and persistent research protection.

AIRef confirms that the scripting ecosystem is still fundamentally rule-based Facts plus Actions, with Goals, Strategic Numbers, IO outputs, timers, and DUC as stateful control surfaces. citeturn835749search4turn835749search5turn235050search0

AIRef currently documents 512 Strategic Number IDs, with active/effective/version information for the subset that affects native behavior. UserPatch records SN 264 as sn-enable-training-queue and documents its interaction with can-train, train, up-can-train, and their escrow variants. citeturn436186search0turn436186search1

Public community repositories provide the practical counterexample to a purely primitive-oriented compiler: Niek AI, lewisc64/aoe2ai, and The Duke contain substantial reusable rule patterns for production, persistent control, scouting, DUC, attacks, and strategy selection. citeturn835749search0turn835749search2turn835749search3

## Non-goals

Do not reopen Goal/GoalSpan allocation, generic lifecycle, capability validation, source graph work, construction lifecycle, generic research state, timer allocation, deterministic lowering, native parser replacement, or the already-merged narrow DUC/attack/escrow slices unless new evidence shows a defect.

Do not build a universal scheduler, runtime simulator, optimizer, or separate high-level .per language.

## Phase 1 — Production/train arbitration

Priority: P0. Next implementation target.

Goal: connect ProductionLifecycle to the existing ResourceClaim and arbitration system without inventing a native train conflict class.

Use the existing seams in:
LearnerAI/Compiler/ir/production.py
LearnerAI/Compiler/semantic/resource_conflicts.py
LearnerAI/Compiler/semantic/capability_bridge.py
LearnerAI/Compiler/semantic/capability_validation.py
LearnerAI/Compiler/compiler.py
and the existing production/resource tests.

Contract:
- ordinary train demand may derive one compiler-policy production claim;
- owner = semantic or strategic owner;
- provider UnitId = provider identity only;
- can-train = admission only;
- train = issuance only;
- up-pending-objects = pending/duplicate protection;
- unit-type-count-total = observation only;
- escrowed training keeps the same semantic arbitration owner;
- DUC-targeted training does not inherit ordinary train arbitration accidentally;
- SN 264 remains OPEN evidence, not an emitted capacity proof.

Required tests:
- stable claim identity;
- same-owner conflict;
- distinct-owner separation;
- no claim from can-train alone;
- pending cannot satisfy arbitration;
- escrowed train preserves ownership;
- DUC train remains separate;
- military composition consumes the shared claim;
- deterministic repeated compilation.

Exit: production demands participate in the existing arbitration graph with deterministic ownership/conflict diagnostics and no invented native train conflict class.

Runtime track, kept separate: SN 264 enforcement, provider busy/queued behavior, birth timing, queue-exit timing, and next-pass visibility.

## Phase 2 — DUC execution closure

Priority: P0.

Goal: turn the current DUC semantic slices into one reusable search/target/group execution path.

Use:
LearnerAI/Compiler/ir/duc.py
LearnerAI/Compiler/semantic/duc.py
LearnerAI/Compiler/primitives/registry.py
LearnerAI/Compiler/primitives/native_binder.py
LearnerAI/Compiler/emitter/per.py
LearnerAI/Compiler/runtime_binding.py
and the DUC tests.

Required state machine:
DISCOVER -> STORE_ID -> REACQUIRE -> VALIDATE -> INVALIDATE

Then:
TARGET -> PREPARE -> READY -> ISSUE -> WITNESS -> RESET/RELEASE -> RECOVER -> REASSESS

Required coverage:
- search state;
- group size;
- point outputs;
- cost delta;
- object/target data where evidence permits;
- local and remote search mutation;
- filter generations;
- group creation and flags;
- set-target-by-id;
- target reacquisition.

Hard rules:
- filter-generation change invalidates list-derived target proof;
- native-ID reference is identity, not liveness proof;
- selected-target lifetime is never used as durable object identity;
- runtime reader values are never fabricated.

Exit: community DUC discovery, micro, and target pipelines lower through one typed path with explicit target provenance.

Runtime track: object liveness, retained-filter rules, duplicate handling, runtime output values, group membership, and measured DUC performance remain OPEN.

## Phase 3 — Attack execution lifecycle

Priority: P0 after Phase 2 target closure is sufficient.

Goal: extend the existing issue-only attack plan into a full compiler-facing execution lifecycle.

Required lifecycle:
DEMAND -> ADMISSION -> PREPARE -> READY -> ISSUE -> WITNESS -> RELEASE/RESET -> RECOVERY -> REASSESS

attack-now may implement ISSUE.
attack-now never implements WITNESS by implication.

Reuse:
LearnerAI/Compiler/ir/native_attack.py
LearnerAI/Compiler/semantic/operational_semantics.py
LearnerAI/Compiler/ir/strategy_runtime.py
LearnerAI/Compiler/tests/test_native_attack_lifecycle.py
LearnerAI/Compiler/tests/test_military_composition_proof.py

Required tests:
- issue cannot satisfy witness;
- missing readiness blocks promotion;
- stale target invalidates prepared attack without proving target death;
- DUC target identity and attack target identity remain distinct but linkable;
- reset does not equal completion;
- recovery reopens the same strategic demand where policy allows;
- composition/resource ownership remains shared;
- deterministic lowering.

Runtime track: attack-now completion, attack-group membership, exploration gating, TSA/town-size interactions, offensive-priority interactions, and reset lifetime remain OPEN.

## Phase 4 — Escrow and resource arbitration

Priority: P1.

Goal: finish resource-control semantics without creating a universal scheduler.

Work:
- extend existing escrow_plan for remaining safe UP escrow mutations;
- preserve separate concepts for percentage policy, balance release, balance mutation, escrow-aware admission, and ordinary resource consumption;
- enforce one semantic owner per protected escrow purpose;
- support explicit ownership handoff;
- support explicit starvation/emergency release policy;
- reuse the same ownership model for research and training escrow.

Required tests:
- percentage zero is not balance release;
- release does not stop future accrual unless policy also changes the percentage;
- two escrow owners conflict without handoff;
- explicit handoff passes;
- emergency release preserves strategic-demand identity;
- ordering is deterministic;
- native zero-findings remain clean.

Runtime track: same-pass release visibility, exact handoff behavior, and starvation timing remain external evidence.

## Phase 5 — Active Strategic Number evidence closure

Priority: P1, parallel.

Do not reverse-engineer all 512 SNs before the compiler can use the ones the community actually needs.

Order the catalog by:
1. current community corpus usage;
2. Byzantine strategy usage;
3. production, attack, exploration, town-defense, DUC, and water control;
4. remaining high-frequency active SNs.

Each active SN record must contain:
- ID and canonical name;
- DE version scope;
- default;
- required range;
- effective status;
- automatic-mutation status;
- community prevalence;
- compiler semantic role;
- evidence hash;
- explicit UNKNOWN boundary.

Exit: every SN consumed by an accepted synthesis pack has explicit evidence status and deterministic semantics.

## Phase 6 — Byzantine factual closure

Priority: P1, parallel.

Close the remaining safe GameData blockers required by the Byzantine vertical slice:
- remaining identity-safe nodes;
- ship trigger technology identities;
- the narrow variable-cost research representation needed by Tech 408;
- refreshed GameData and EffectiveCivData fingerprints;
- strategy integration regression.

Exit: no required Byzantine strategy fact depends on invented costs, times, availability, effects, or IDs.

## Phase 7 — Community strategy synthesis

Priority: P1. Largest qualitative milestone.

Rule: no new .per language.

Use the existing StrategyProfile, StrategicDemand, StrategyRuntimeState, capability graph, persistent controls, ResourceClaim, DUC, attack, escrow, and lowering layers.

Pack A — persistent control:
- goal-backed FSM;
- one-shot initialization;
- age-based SN modes;
- jump dispatch;
- cooldown timers;
- persistent reassertion.

Pack B — production strategy:
- current-plus-queued targets;
- queue-capacity policy;
- production arbitration;
- counter trains;
- water/land production split;
- protected research/production demands.

Pack C — military control:
- TSA;
- military parity;
- defense toggles;
- unit-combination tables;
- DUC micro;
- attack cadence/reset;
- target reacquisition.

Pack D — recovery:
- starvation release;
- failed-build recovery;
- provider loss;
- target loss;
- composition replacement;
- obsolete strategy cancellation.

Pack E — map and water:
- map tables;
- camp geometry;
- land/water posture;
- water shutdown/rebalance;
- fishing/warboat split.

Every pack must compile into existing semantic objects, reject illegal states, lower deterministically, and pass native zero-findings acceptance.

## Phase 8 — Community corpus closure

Priority: P1.

The repository's initial 32 idioms are a seed, not the definition of community completeness.

Use the measured corpus already present in the repository: Promisory, Naga, Bright Spark, Odette AI, Illuminati, Belisarius, AiBuilder, root loaders, and campaign AI.

Classify recurring patterns as:
DISCOVERED -> CORROBORATED -> SEMANTICIZED -> EXPRESSIBLE -> LOWERABLE -> VERIFIED

Do not count descendants of the same historical lineage as independent corroboration.

Mandatory pattern families:
- commodity/market balancing;
- goal FSMs;
- SN mode switching;
- TSA;
- military parity;
- defense toggles;
- counter trains;
- starvation release;
- full DUC micro;
- lure DUC;
- water split;
- build-order synthesis;
- wonder/late-game control.

Exit: each high-value community pattern has one semantic owner, one executable lowering path, and an explicit runtime OPEN list.

## Phase 9 — Philosopher's Stone acceptance

Priority: final milestone.

Prove the full path:
community pattern -> strategic demand -> admissibility -> capability -> arbitration -> execution -> witness -> recovery -> reassessment -> native .per

Required verticals:
- construction;
- production;
- research plus escrow;
- DUC target execution;
- attack;
- resource recovery;
- land/water transition.

Required acceptance for every vertical:
- representative community idiom;
- independent corroboration where available;
- typed semantic contract;
- illegal-state regression;
- deterministic native lowering;
- native zero findings;
- full compiler regression;
- 3 OS x 3 Python determinism;
- snapshot equality;
- aggregate compiler verification;
- explicit evidence ledger.

Final exit: remaining uncertainty is bounded native/runtime research, not missing compiler architecture.

## Runtime research program

These probes run independently and do not change compiler facts until executed:

- SN 264 queue enforcement;
- provider busy/queued behavior;
- production birth/queue-exit/next-pass ordering;
- escrow same-pass visibility;
- attack-now lifecycle;
- DUC object liveness and retained filters;
- timer granularity;
- resource-found latch/live behavior;
- load-random RNG/weight semantics;
- .xs/.per bridge;
- package collisions.

## Dependency graph

Phase 1 -> Phase 3 through production ownership and military composition.
Phase 2 -> Phase 3 because target lifecycle precedes attack lifecycle.
Phase 4 is parallel but becomes a dependency of protected resource strategy.
Phase 5 and Phase 6 run in parallel.
Phase 7 composes Phases 1-5 plus required GameData.
Phase 8 is continuous and is a gate before Phase 9.
Phase 9 depends on Phases 1-8.

## Exact implementation order

1. Production/train arbitration.
2. DUC execution closure.
3. Attack lifecycle.
4. Escrow/resource arbitration.
5. Active SN evidence closure in parallel.
6. Byzantine factual closure in parallel.
7. Community strategy synthesis packs.
8. Broad community corpus closure.
9. End-to-end Philosopher's Stone acceptance.

No additional foundation phase is justified by the current evidence.