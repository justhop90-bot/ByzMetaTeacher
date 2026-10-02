# MUSE Community Gap Roadmap — 2026-10-02

Status: authoritative roadmap for remaining compiler work. Production/train arbitration is closed; DUC semantic substrate is largely closed; the remaining work is downstream strategy synthesis and runtime-bounded control semantics.

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

Status: **CLOSED**.

The compiler now derives the compiler-policy production claim through the existing ResourceClaim/arbitration graph. Ownership is deterministic and no native train conflict class was invented.

The remaining runtime questions stay external: SN 264 enforcement, provider busy/queued behavior, birth timing, queue-exit timing, next-pass visibility, same-pass starvation behavior, and provider-loss effects.

## Phase 2 — DUC execution and strategy exposure

Status: **COMPILER-POLICY CLOSED / RUNTIME EVIDENCE OPEN**.

The compiler already contains the typed DUC state model, recurrent firing coupling, search/filter generations, cursor lifecycle, target provenance, direct-ID identity, group/window inputs, target revalidation, native lowering, and zero-findings acceptance fixtures.

The downstream strategy seam is now connected:
StrategyProfile -> StrategyCompilation -> normal/runtime Byzantine compilation -> existing NativeDucPlan channel.

The default Byzantine strategy now synthesizes two evidence-backed Castle-power target pipelines: observed enemy knight pressure drives remote knight-line discovery, and observed enemy infantry pressure drives remote militia-line discovery. Each pipeline resets the remote search, establishes an object target, and captures native object-data identity through the existing DUC output channel.

The remaining DUC uncertainty is runtime evidence, not missing compiler policy: object liveness after search mutation, retained-filter behavior, group membership, exact output values, cross-pass target lifetime, and native attack-controller consumption remain OPEN unless independently proven.

## Phase 3 — Attack execution lifecycle

Status: **COMPILER-POLICY CLOSED / NATIVE ACKNOWLEDGEMENT OPEN**.

The AttackExecution IR, target revalidation, operational bridge, controller metadata bridge, issue-only native attack plan, and persistent Byzantine attack-phase controller are implemented.

The default Byzantine Castle-power attack now has explicit persistent phases for PREPARE, ISSUE, pressure-cleared completion, force-floor recovery, and reassessment. The attack-now rules are causally gated by a bound persistent Goal state, using the existing control-plane allocator and emitter.

The compiler deliberately does not claim a native attack acknowledgement. The pressure-clear and force-floor witnesses are compiler-policy/world-observation conditions for lifecycle control, not proof that a specific attack-now command killed a specific target.

Remaining native/runtime OPEN work: exact attack-now completion semantics, per-object target liveness, attack-group membership causality, exploration/TSA/town-size controller behavior, reset lifetime, and native acknowledgement.

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

Priority: **CLOSED FOR THE INITIAL STOCK BYZANTINE STRATEGY PACK / OPEN FOR FULL STRATEGIC BREADTH**.

The compiler now has a concrete community-derived stock synthesis layer and a canonical `build_byzantine_strategy()` entry point exercised by the authoritative CI strategy fixture.

Implemented and accepted:
- economy/research package with protected Imperial trajectory;
- Castle economic expansion / second-TC demand;
- production capability synthesis;
- standing Knight/Cataphract floors;
- Castle siege support and Imperial Bombard Cannon conversion;
- Monastery/Monk support;
- defensive Outpost capability;
- decision-grade enemy pressure observations;
- recovery-preserving construction/research/training demands;
- Strategic Number exploration/attack mode synthesis;
- dock-gated fishing continuity;
- community strategy evidence/idiom registry;
- professional strategy/domain contracts;
- native symbol aliases and line-vs-unit binding repairs required to lower the stock pack.

Acceptance:
- PR #275 merged at `bf38e28d8520bbca1c3d6872a6852ce014906500`;
- workflow #3040 passed 1,440 compiler tests;
- native zero-findings acceptance passed;
- 9/9 native-support determinism passed;
- native snapshot comparison passed;
- compiler verification gate passed.

What remains open in the strategy layer:
- full MapProfile/WaterPosture executable synthesis;
- naval production, water shutdown/rebalance, and transport lifecycle execution;
- deeper economy policy for farms, houses, dropsites, market balancing, and resource posture conversion;
- richer late-game, wonder/closer, relic-acquisition, and broad siege/fortification strategy;
- active Strategic Number evidence closure for all consumed community modes;
- broader community corpus closure and empirical game/replay acceptance.

Do not reopen the generic compiler substrate to solve these. Use existing StrategyProfile, StrategicDemandSpec, ResourceClaim, DUC, attack, escrow, SN/Timer, and witness machinery.

## Phase 8 — Community corpus closure

Priority: **IN PROGRESS**.

The 32-idiom seed corpus remains only a starting set. The implemented stock pack now has a provenance/registry layer, but community breadth is not yet closed.

Next corpus work:
- corroborate map/water/transport patterns across independent lineages;
- deepen market/resource balancing;
- catalog TSA/attack cadence and late-game control patterns;
- expand build-order synthesis patterns;
- validate wonder/closer patterns;
- validate relic/Monk control patterns;
- connect each promoted idiom to a focused compiler fixture.

Closure remains:

`DISCOVERED -> CORROBORATED -> SEMANTICIZED -> EXPRESSIBLE -> LOWERABLE -> VERIFIED`

Runtime behavior that cannot be established statically remains OPEN rather than becoming a false compiler fact.

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

1. Remaining DUC runtime-evidence closure where probes are justified, without inventing compiler facts.
2. Remaining native attack acknowledgement/controller evidence where probes are justified.
3. Remaining escrow/resource arbitration and emergency release policy.
4. Active Strategic Number evidence closure in parallel.
5. Byzantine factual closure in parallel.
6. Community strategy synthesis packs.
7. Broad community corpus closure.
8. End-to-end Philosopher's Stone acceptance.

No additional foundation phase is justified by the current evidence.