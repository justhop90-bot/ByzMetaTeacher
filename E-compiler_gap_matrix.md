# Compiler gap matrix — native/community capability vs implementation stages
Stages: native-fact | semantic-IR | validator | binding | emitter | native-acceptance |
runtime-evidence | tests | community-corpus | strategy-integration.
Verdict tokens: OK / PARTIAL / MISSING / EVIDENCE-ONLY / FIXTURE-ONLY / OPEN.

## Goals (scalar + spans)
native-fact OK (AIRef 385 schema pins set-goal/goal/up-modify-goal/up-compare-goal) |
IR OK (GoalSlot/GoalSpan/LifecycleEncoding) | validator OK (persistent_state) |
binding OK (RuntimeBinder base 41) | emitter OK (defconst+init+10000/32/255 limits) |
acceptance OK | runtime-evidence PARTIAL (package-collision behavior unobserved) |
tests OK (24 persistent + 40 binding) | corpus OK (23225 hits) | strategy OK (GoalSlotRequest roles).
GAP: package-collision + volatile-vs-strategic discipline is COMPILER POLICY, not engine proof.

## Strategic numbers 0..511
native-fact PARTIAL (slot structure known; per-SN defaults/auto-mutation/version incomplete) |
IR OK | validator OK (SNSEM-001..009) | binding OK | emitter OK | acceptance OK |
runtime-evidence PARTIAL (catalog pins namespace; engine defaults/auto-mutation remain OPEN) |
tests OK (source fixture + native deterministic acceptance) | corpus OK (10202 set + Duke/Niek tables) |
strategy PARTIAL.
GAP: engine knowledge for per-SN defaults/auto-mutation/version behavior and unknown-SN writes.

## Timers (50 slots)
native-fact OK (arm/disarm/trigger/staged-expiry) | IR OK (TimerRuntimeState) |
validator OK (scheduler + recurrent) | binding OK-infra / MISSING-from-DSL |
emitter MISSING | acceptance n/a | runtime-evidence PARTIAL (granularity unmeasured) |
tests PARTIAL (7 semantics + scheduler; triggered never statically true by design) |
corpus OK (1782 enable + 2278 triggered) | strategy PARTIAL (cooldown patterns undescribed).
GAP: DSL allocation; trigger-granularity measurement.

## Construction (build/can-build/pending/placement/retry)
native-fact OK | IR OK | validator OK | binding OK | emitter OK | acceptance OK |
runtime-evidence PARTIAL (foundation/placement same-pass behavior still needs runtime proof) |
tests OK | corpus OK (2977 can-build; buildings.per 88KB Duke) | strategy OK.
GAP: same-pass goal-visibility proof; placement-vs-foundation runtime evidence.

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
native-fact PARTIAL (resource-view formula closed; same-pass release timing OPEN) |
IR OK for typed escrow contracts + release plan | validator OK | binding OPEN for release slice |
emitter OPEN for release slice | acceptance OPEN | runtime-evidence MISSING (native escrow timing) |
tests OK for semantic ownership/order/lifetime + compiler threading | corpus STRONG (10859 hits) |
strategy PARTIAL.
GAP: dedicated release binder/mapping/registry/emitter/fixture; native same-pass timing; starvation/handoff.
Must NOT become a universal scheduler.

## DUC SearchSession (promoted narrow slice)
native-fact OK-structure | IR OK | validator OK | binding OK for promoted commands |
emitter OK for promoted commands | acceptance OK | runtime-evidence PARTIAL |
tests OK (native deterministic acceptance) | corpus STRONG (11.6k up-find) | strategy PARTIAL.
The promoted source slice now includes semantic observation support for Fact-only `up-can-search` and conservative Action-side handling for `up-add-object-by-id`. `up-can-search` proves FALSE only at compiler-proven end/capacity states; `up-add-object-by-id` invalidates affected-list cardinality and content fingerprint, downgrades list-index targets to UNKNOWN, preserves cursor/filter state without claiming a native cursor transition, and refuses to prove liveness, uniqueness, duplicate handling, append position, or full-list behavior. The corrected slice is verified by the next compiler workflow after this change.
GAP: remaining unpromoted DUC source/selection surfaces remain open. Exact native `up-can-search` truth outside proven exhaustion/capacity and `up-add-object-by-id` runtime liveness, duplicate handling, append/reposition semantics, full-list behavior, and Fact truth remain runtime-dependent. Retained list-derived target proof now invalidates across filter-generation changes while runtime object liveness remains open.

## DUC TargetSession/groups/outputs/costs
Same as SearchSession, plus: target liveness remains OPEN; runtime cost measurement remains OPEN; cardinality/performance diagnostics are IMPLEMENTED as advisory evidence consumers.
The compiler models up-get-cost-delta as the existing native four-Goal cost-data-4-goal-span output state, including 41..15996 bounds and writer provenance/generation.
Filter-generation changes now downgrade list-derived target validity/proof to UNKNOWN without claiming object death; native-ID targets remain untouched.
Open boundaries remain cost-data mutation/arithmetic semantics, numeric delta values, runtime object liveness, and any runtime liveness/performance claims.

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
