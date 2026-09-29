# Compiler Project Closure Report — 2026-09-29

## Current source of truth

- Repository: `justhop90-bot/ByzMetaTeacher`
- Branch: `main`
- Code-verified head: `279d360e5907a3ca8a2ccd8e268ed3d073d8fcfb`
- Open pull requests: none
- Compiler workflow: #2531 / run `36547411496`
- Compiler verification gate: PASSED
- Full compiler regression: 1,134 tests, PASSED
- Native zero-findings acceptance: PASSED across all promoted fixtures
- Native-support determinism: 9/9 OS/Python jobs PASSED
- Native-support snapshot comparison: PASSED
- Native parser pin: `3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba`

The code head above is the verified implementation head. Documentation-only follow-up commits may advance `main` without changing the verified compiler code path.

## Completed compiler-safe scope

| Area | Status | Boundary |
|---|---|---|
| Strategic Number allocation/binding/emission | CLOSED for promoted slice | Per-SN defaults, auto-mutation, unknown-SN write behavior remain engine questions. |
| Timer allocation/emission | CLOSED for compiler lowering | Countdown/pass cadence and lifetime/reuse remain runtime questions. |
| Construction lifecycle | IMPLEMENTED / VERIFIED | Same-pass placement/foundation visibility remains runtime-open. |
| Production lifecycle | IMPLEMENTED / VERIFIED for typed seams | Queue-capacity enforcement, provider busy/queued behavior, birth/queue-exit timing, and next-pass visibility remain runtime-open. |
| Research lifecycle | IMPLEMENTED / VERIFIED for promoted semantics | Same-pass escrow release visibility, provider/busy behavior, starvation and handoff remain runtime-open. |
| Escrow release + percentage policy | CLOSED for promoted native lowering | Same-pass action visibility, starvation/emergency release, multi-owner handoff, and broader UP mutation surfaces remain open. |
| DUC promoted slice | CLOSED for emitted/native-promoted commands | Retained-filter/stale-target runtime liveness, group membership/flags, returned reader values, object liveness, and broader expressiveness remain open. |
| Attack issue path | CLOSED for native `attack-now` issue emission | Completion witness, release semantics, group admission/membership, exploration/town-size coupling, attack SNs, and runtime behavior remain open. |
| Attack target policy | CLOSED | DUC target is required only for explicitly DUC-targeted execution; native controller modes do not consume DUC target state as proof. |
| Source graph | CLOSED for deterministic policy-safe materialization | Runtime RNG/weight semantics remain intentionally unmodeled; active .xs input without a .xs↔.per bridge fails closed. |
| Byzantine GameData coverage | CURRENT | 157 modeled / 2 unmodeled / 14 verified-unavailable. |
| Spies/Treason TechId 408 | CLOSED as typed factual data | Uses `VariableCost`; fixed-cost APIs fail closed. Live enemy-civilian evaluation is not synthesized. |
| Demolition Ship 527 | OPEN / fail-closed | Trigger TechId 905 lacks a sufficiently authoritative trigger-safe GameData contract for this IR. |
| Heavy Demolition Ship 528 | OPEN / fail-closed | Trigger TechId 244 lacks a sufficiently authoritative trigger-safe GameData contract for this IR. |
| Patch overlays / universal GameData | OPEN | Current GameData remains a civilization-scoped factual subset. |

## GameData closure

TechId 408 Spies/Treason is now represented as:

- formula: `spies-treason-gold-per-enemy-civilian`
- `minimum_gold=200`
- `maximum_gold=30000`
- `gold_per_civilian=200`
- provider: Castle, BuildingId 82
- research time recorded by the current materializer: 1 second
- explicit provenance retained
- fixed-cost `EffectiveCivData.cost_of()` rejects the dynamic cost instead of fabricating a constant

This closes the previous fixed-`ResourceCost` representation gap without introducing a fake runtime evaluator.

Units 527 and 528 remain deliberately unresolved. The repository has identity and community/engine-data evidence for the unit names, ages and Dock lineage, but the compiler's strict upgrade graph requires an authoritative trigger-safe technology identity before it can emit an upgrade relation. Copying recycled DAT fields or inventing trigger costs would violate the project's evidence gate.

## Verification boundary

The compiler code path is verified at the repository and native-parser level. The project does not claim DE runtime proof for semantics that require live engine observations. Those remain explicit OPEN boundaries rather than hidden assumptions.

The current Basilisk Validator workflow for profile `8596a45` remains RED on an unrelated historical baseline assertion:

`[Ranged] Crossbow action boundary must re-check its live role demand`

at `validation/basilisk-validator.js:5153`, reached from line 7168. The validator profile self-test itself passes. This failure predates and is independent of the compiler GameData/attack changes closed here.

## Completion assessment

The compiler infrastructure is at approximately 88–90% of the practical, evidence-bounded target: the major IR, binding, native-emission, determinism, verification, GameData reconciliation, DUC, escrow, production, research, construction, source-graph, and attack-issue slices are implemented and regression-gated.

The full Basilisk strategic player remains at approximately 74–77% because several strategically important semantics are still engine-runtime dependent: attack completion/release/controller behavior, DUC liveness/group runtime state, queue/provider behavior, same-pass visibility, broader observation policy, and the unresolved 527/528 trigger chain.

This report treats those items as remaining evidence work, not as implementation defects that can be “solved” by inventing state the engine has not yet exposed.
