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
validator OK (scheduler + recurrent) | binding OK | emitter OK | acceptance OK | runtime-evidence PARTIAL (granularity unmeasured) |
tests OK (allocation + semantics + native deterministic acceptance) | corpus OK (1782 enable + 2278 triggered) | strategy PARTIAL (cooldown patterns undescribed).
GAP: runtime countdown/pass granularity and full timer reuse/lifetime semantics.

## Construction (build/can-build/pending/placement/retry)
native-fact OK | IR OK | validator OK | binding OK | emitter OK | acceptance OK |
runtime-evidence PARTIAL (foundation/placement same-pass behavior still needs runtime proof) |
tests OK | corpus OK (2977 can-build; buildings.per 88KB Duke) | strategy OK.
GAP: same-pass goal-visibility proof; placement-vs-foundation runtime evidence.

## Train/production (queue/capacity/provider/birth)
native-fact PARTIAL (SN 264 control and UP `up-train-site-ready` readiness fact are documented; birth/queue-exit timing primitives are documented only as component observations and runtime ordering remains unproven) |
IR PARTIAL (typed current+queued/provider-presence/provider-readiness observations plus OPEN queue-capacity/provider-availability/readiness/control/birth/queue-exit timing evidence now exist) | validator PARTIAL |
binding PARTIAL (native-ID queue/provider bindings, exact SN 264 control binding, canonical `up-train-site-ready` binding, and fail-closed timing resolvers are implemented; unresolved engine semantics fail closed as OPEN) | emitter PARTIAL (no capacity guard) | acceptance OK |
runtime-evidence MISSING for current-build capacity enforcement, provider busy/queued behavior, birth timing, queue-exit timing, and next-pass visibility |
tests OK (full existing suite plus focused SN 264, provider-readiness, and birth/queue-exit timing contract coverage) |
corpus OK (current+queued idiom IDIOM-006) | strategy PARTIAL.
GAP: prove current DE SN 264 enforcement, `up-train-site-ready` busy/queued interaction, birth timing, queue-exit timing, next-pass visibility, and explicit recovery semantics.

## Research (availability/prereq/escrow/completion)
native-fact PARTIAL (in-progress signal unknown) | IR OK-generic | validator OK-generic |
binding OK-generic | emitter OK-generic | acceptance OK | runtime-evidence PARTIAL |
tests PARTIAL | corpus OK | strategy OK (feudal-age escrow example).
GAP: escrow-claim lowering; protected-research pattern catalog; in-progress signal.

## Resource/escrow/arbitration
native-fact PARTIAL (resource-view formula closed; same-pass release timing OPEN) |
IR OK for typed escrow contracts + release plan | validator OK | binding OK for promoted release-only slice |
emitter OK for promoted release-only slice | acceptance OK (native zero-findings) | runtime-evidence SPECIFIED but MISSING (native escrow timing) |
tests OK for semantic ownership/order/lifetime + release-only compiler/native acceptance + oracle-spec regression | corpus STRONG (10859 hits) |
strategy PARTIAL.
GAP: native same-pass timing; starvation/emergency release; multi-owner handoff; remaining UP escrow mutation lowering.
Must NOT become a universal scheduler.

## Rule/pass control flow
static control-flow diagnostics now include out-of-range/bypass/unreachable cases plus `RULE-CF-005` for statically provable same-rule re-entry after `disable-self`; broader disabled-target path dependence remains open.

## DUC SearchSession (promoted narrow slice)
native-fact OK-structure | IR OK | validator OK | binding OK for promoted commands |
emitter OK for promoted commands | acceptance OK | runtime-evidence PARTIAL |
tests OK (native deterministic acceptance + composite recurrent/mutation/branch/target fixture) | corpus STRONG (11.6k up-find) | strategy PARTIAL.
The promoted source slice now includes semantic observation support for Fact-only `up-can-search` and conservative Action-side handling for `up-add-object-by-id`. `up-can-search` proves FALSE only at compiler-proven end/capacity states; `up-add-object-by-id` invalidates affected-list cardinality and content fingerprint, downgrades list-index targets to UNKNOWN, preserves cursor/filter state without claiming a native cursor transition, and refuses to prove liveness, uniqueness, duplicate handling, append position, or full-list behavior. The corrected slice is verified on current main by Compiler workflow #2219 at code SHA `c1064aaea324394275bcad43864537fe80a03d58`: 1,009 tests passed, native zero-findings passed, all 9 native-support determinism jobs passed, aggregate snapshot comparison passed, and the Compiler verification gate passed.
GAP: search-state, group-size, cost-delta, point, target-data, DUC group lifecycle, and generic `up-get-fact` Goal output are on the executable lowering path; remaining DUC uncertainty is runtime group membership/flag behavior, reader values, and broader higher-order controller semantics. Native reader values remain engine-produced/runtime-dependent. Target-data values/object liveness, cost-data mutation/arithmetic semantics, runtime delta values, and point runtime values remain engine-produced. Exact native `up-can-search` truth outside proven exhaustion/capacity and `up-add-object-by-id` runtime liveness, duplicate handling, append/reposition semantics, full-list behavior, and Fact truth remain runtime-dependent. Retained list-derived target proof now invalidates across filter-generation changes while runtime object liveness remains open.

## DUC TargetSession/groups/outputs/costs
Same as SearchSession, plus: target liveness remains OPEN; runtime cost measurement remains OPEN; cardinality/performance diagnostics are IMPLEMENTED as advisory evidence consumers.
The compiler models up-get-cost-delta as the existing native four-Goal cost-data-4-goal-span output state, including 41..15996 bounds and writer provenance/generation. Search-state and group-size output lowering are now typed through the native DUC output-storage path.
Filter-generation changes now downgrade list-derived target validity/proof to UNKNOWN without claiming object death; native-ID targets remain untouched.
Open boundaries remain cost-data mutation/arithmetic semantics, numeric delta values, runtime object liveness, and any runtime liveness/performance claims.

## Controllers (9) + interactions (15) incl. attack
native-fact MISSING for causal controller behavior | IR SUBSTRATE IMPLEMENTED / evidence-only catalog |
validator EVIDENCE-ONLY for executable promotion | binding intentionally missing | emitter intentionally missing |
acceptance n/a | runtime-evidence MISSING | tests OK for graph/interactions (hostile contract coverage) |
corpus STRONG (SN clusters, TSA, parity, toggles) | strategy MISSING.
GAP: executable controller plane remains blocked on native causal/runtime proof. Attack lifecycle (admission/completion/release/reassess) remains the critical missing semantic; the compiler now has typed controller and interaction contracts without promoting them into emitted behavior.

## Source graph/loads/fingerprint
native-fact OK | IR OK (EffectiveSourceGraph + fingerprints) | validator OK (1715-line module) |
binding n/a | emitter n/a | acceptance OK | runtime-evidence OK (deterministic fingerprints) |
tests OK (67 across 4 files) | corpus OK (Duke map loads; single-load vendored AI) |
strategy n/a.
GAP: compiler source-graph boundary is closed for active `.xs` inputs; runtime RNG/weight semantics for `load-random` remain OPEN, but deterministic source selection is compiler-policy complete.

## Game data (Byzantine 145-node + broader)
native-fact PARTIAL (Byzantine subset FACTUAL_SUBSET; costs/times missing in places) |
IR OK (GameData + EffectiveCivData + fingerprint) | validator OK (cross-checks) |
binding n/a | emitter n/a | acceptance n/a | runtime-evidence PARTIAL (patch 185872) |
tests OK (7+21+8) | corpus n/a | strategy OK (Byzantine castle strategy).
GAP: pinned 185872 machine-readable technology cost/research-time provenance is now connected for exact-name existing GameData rows; complete 145-node manifest coverage remains OPEN for 73 unmodeled nodes, as do broader civs, replayable patch overlays, native ID provenance, and unsupported prerequisite/provider/effect fields.

## Strategy runtime (demand/posture/targets/cost/invalidation)
native-fact n/a (COMPILER POLICY layer) | IR OK | validator OK (resolve+lower) |
binding OK (observation primitives; DUC search availability + escrow capability promoted) | emitter via demands OK |
acceptance OK | runtime-evidence PARTIAL | tests OK (33 runtime + 9 semantics + 2 integration) |
corpus PARTIAL (idioms cataloged; synthesis unproven) | strategy OK-infra.
GAP: attack/controller observation, retained DUC state, escrow same-pass/runtime semantics, civ-policy vs generic-semantics separation audit, and invalidation/reassessment proof against corpus recovery examples.
