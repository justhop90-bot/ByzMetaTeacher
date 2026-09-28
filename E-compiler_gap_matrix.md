# Compiler gap matrix — native/community capability vs implementation stages
Stages: native-fact | semantic-IR | validator | binding | emitter | native-acceptance |
runtime-evidence | tests | community-corpus | strategy-integration.
Verdict tokens: OK / PARTIAL / MISSING / EVIDENCE-ONLY / FIXTURE-ONLY / UNMERGED-PR86.

## Goals (scalar + spans)
native-fact OK (AIRef 385 schema pins set-goal/goal/up-modify-goal/up-compare-goal) |
IR OK (GoalSlot/GoalSpan/LifecycleEncoding) | validator OK (persistent_state) |
binding OK (RuntimeBinder base 41) | emitter OK (defconst+init+10000/32/255 limits) |
acceptance OK | runtime-evidence PARTIAL (package-collision behavior unobserved) |
tests OK (24 persistent + 40 binding) | corpus OK (23225 hits) | strategy OK (GoalSlotRequest roles).
GAP: package-collision + volatile-vs-strategic discipline is COMPILER POLICY, not engine proof.

## Strategic numbers 0..511
native-fact PARTIAL (slot structure known; per-SN defaults/auto-mutation/version incomplete) |
IR OK (StrategicNumberMutation/Comparison/Access/Dependency) |
validator OK (SNSEM-001..009, c:/g:/s:) | binding OK-infra / MISSING-from-DSL |
emitter MISSING | acceptance n/a | runtime-evidence MISSING (no auto-mutation catalog) |
tests FIXTURE-ONLY (synthetic EffectiveRule; default inventory raises) |
corpus OK (10202 set + Duke/Niek tables) | strategy PARTIAL (descriptive access binding).
GAP: (1) full 0..511 catalog with defaults/version/auto-mutation; (2) DSL allocation path.

## Timers (50 slots)
native-fact OK (arm/disarm/trigger/staged-expiry) | IR OK (TimerRuntimeState) |
validator OK (scheduler + recurrent) | binding OK-infra / MISSING-from-DSL |
emitter MISSING | acceptance n/a | runtime-evidence PARTIAL (granularity unmeasured) |
tests PARTIAL (7 semantics + scheduler; triggered never statically true by design) |
corpus OK (1782 enable + 2278 triggered) | strategy PARTIAL (cooldown patterns undescribed).
GAP: DSL allocation; trigger-granularity measurement.

## Construction (build/can-build/pending/placement/retry)
native-fact OK | IR OK (LifecycleState + PR86 transitions) | validator OK (+PR86 UNMERGED) |
binding OK | emitter OK (+PR86 UNMERGED emission) | acceptance OK |
runtime-evidence PARTIAL (foundation/placement split per PR86 needs runtime proof) |
tests OK (+PR86 fixtures UNMERGED) | corpus OK (2977 can-build; buildings.per 88KB Duke) |
strategy OK (build_land_castle_strategy).
GAP: merge PR86; same-pass goal-visibility proof; placement-vs-foundation runtime evidence.

## Train/production (queue/capacity/provider/birth)
native-fact PARTIAL (queue exists; capacity/provider-idle/birth-timing unproven) |
IR PARTIAL (generic lifecycle; no queue-state/provider-state) | validator PARTIAL |
binding PARTIAL | emitter PARTIAL (no capacity guard) | acceptance OK |
runtime-evidence MISSING | tests PARTIAL (pending-as-witness rejected by policy) |
corpus OK (current+queued idiom IDIOM-006) | strategy PARTIAL.
GAP: queue-state + provider-state + capacity + birth + explicit recovery model.

## Research (availability/prereq/escrow/completion)
native-fact PARTIAL (in-progress signal unknown) | IR OK-generic | validator OK-generic |
binding OK-generic | emitter OK-generic | acceptance OK | runtime-evidence PARTIAL |
tests PARTIAL | corpus OK | strategy OK (feudal-age escrow example).
GAP: escrow-claim lowering; protected-research pattern catalog; in-progress signal.

## Resource/escrow/arbitration
native-fact PARTIAL (gating formula unproven) | IR PARTIAL (transient claims only) |
validator PARTIAL (resource_conflicts 1-owner claims; build singleton only) |
binding PARTIAL | emitter PARTIAL (claim reset/guard for build) |
acceptance PARTIAL | runtime-evidence MISSING (no escrow timing proof) |
tests PARTIAL (8 resource_conflicts; feasibility-fact tests) | corpus STRONG (10859 hits) |
strategy PARTIAL (OpportunityCost/ProtectedFloor are strategy-level, not native).
GAP: biggest corpus-to-compiler gap by hit count. Needs escrow op lowering + starvation/
emergency-override + ownership/release semantics. Must NOT become universal scheduler
(brief constraint) — bound to claim/escrow/release primitives.

## DUC SearchSession (lists/cursor/generation/filter/reset/capacity)
native-fact OK-structure (240/40/groups 20x40/widths) | IR OK (DucSemanticState) |
validator OK (DUC-008/012/016, widening limit 3) | binding MISSING (zero adapters → UNSUPPORTED) |
emitter MISSING | acceptance n/a | runtime-evidence PARTIAL (oracle schema + candidates) |
tests FIXTURE-ONLY (124 semantics on synthetic rules) | corpus STRONG (11.6k up-find) |
strategy MISSING.
GAP: binder adapters + DSL emission; retained-filter rules; reset taxonomy proof.

## DUC TargetSession/groups/outputs/costs
Same as SearchSession, plus: liveness/cardinality/performance OPEN (no measurements;
advisory-only rule required — never correctness rules per brief).

## Controllers (9) + interactions (15) incl. attack
native-fact MISSING (no per-controller causal proof) | IR EVIDENCE-ONLY catalog |
validator EVIDENCE-ONLY (gates always raise) | binding MISSING | emitter MISSING |
acceptance n/a | runtime-evidence MISSING | tests EVIDENCE-ONLY (21+11) |
corpus STRONG (SN clusters, TSA, parity, toggles) | strategy MISSING.
GAP: entire executable controller plane. Attack lifecycle (admission/completion/release/
reassess) is the critical missing semantic; corpus proves demand (47 attack-now but
1455 town-size + posture SNs = mediated control).

## Source graph/loads/fingerprint
native-fact OK | IR OK (EffectiveSourceGraph + fingerprints) | validator OK (1715-line module) |
binding n/a | emitter n/a | acceptance OK | runtime-evidence OK (deterministic fingerprints) |
tests OK (67 across 4 files) | corpus OK (Duke map loads; single-load vendored AI) |
strategy n/a.
GAP: load-random materialization only.

## Game data (Byzantine 145-node + broader)
native-fact PARTIAL (Byzantine subset FACTUAL_SUBSET; costs/times missing in places) |
IR OK (GameData + EffectiveCivData + fingerprint) | validator OK (cross-checks) |
binding n/a | emitter n/a | acceptance n/a | runtime-evidence PARTIAL (patch 185872) |
tests OK (7+21+8) | corpus n/a | strategy OK (Byzantine castle strategy).
GAP: complete 145-node manifest; broader civs; patch overlays; native ID provenance.

## Strategy runtime (demand/posture/targets/cost/invalidation)
native-fact n/a (COMPILER POLICY layer) | IR OK | validator OK (resolve+lower) |
binding OK (observation primitives; TRAIN+unit+VERIFIED only) | emitter via demands OK |
acceptance OK | runtime-evidence PARTIAL | tests OK (33 runtime + 9 semantics + 2 integration) |
corpus PARTIAL (idioms cataloged; synthesis unproven) | strategy OK-infra.
GAP: observation primitive coverage (no DUC/attack/escrow); civ-policy vs generic-semantics
separation audit; invalidation/reassessment proof against corpus recovery examples.
