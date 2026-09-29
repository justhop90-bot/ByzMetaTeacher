# Compiler coverage baseline (replaces provisional 56% with measured denominators)
Method: per family, CURRENT = proven stage; TARGET = executable-safe; EVIDENCE = artifact rows;
REMAINING GAP = exact work. Ratios use Artifact A rows + test kinds, NOT test counts.

## Goals — CURRENT: executable-safe. TARGET: met.
EVIDENCE: A rows set-goal/goal/up-compare-goal/up-modify-goal; 23k corpus hits; binding+emission.
IMPLEMENTATION: runtime_binding + emitter + persistent_state. TEST: 24+40.
REMAINING: package-collision runtime proof (minor).

## SN plane — CURRENT: executable-safe for the promoted allocation slice. TARGET: executable-safe incl. emission.
EVIDENCE: A SN rows; ~10k hits; SNSEM-001..009. IMPLEMENTATION: versioned 0..511 catalog, DSL `sn` allocation,
runtime binding, numeric emission, reproducibility/native fixture.
TEST: source fixture + native zero-findings. REMAINING: engine knowledge for per-SN defaults, auto-mutation,
version scope, and unknown-SN write behavior.

## Timers — CURRENT: symbolic allocation + native emission implemented; runtime cadence remains open. TARGET: executable-safe with measured engine timing.
EVIDENCE: A timer rows; ~4k hits; staged-expiry design; community timer idioms use named constants, explicit initialization, trigger reads, and re-arm loops.
IMPLEMENTATION: scheduler + recurrent IR + TimerRequest/TimerState DSL allocation + deterministic TimerSlot binding + native defconst aliases + explicit one-shot initialization.
TEST: runtime scheduler/semantics + focused timer allocation suite + checked-in source fixture + pinned native zero-findings acceptance + binding-manifest determinism.
REMAINING: engine countdown/pass granularity; explicit timer reuse/lifetime model; external co-loaded timer occupancy.

## Construction — CURRENT: executable-safe on main; lifecycle hardening integrated.
TARGET: runtime-proven. EVIDENCE: build rows; ~3k hits; current lifecycle contracts.
IMPLEMENTATION: validators + construction IR + emitter + native placement-pending support.
TEST: current construction lifecycle suite + native zero-findings fixture.
REMAINING: same-pass visibility proof; foundation/placement runtime evidence.

## Train — CURRENT: generic-safe; queue-model typed/OPEN. TARGET: queue-aware safe.
EVIDENCE: A train rows; IDIOM-006. IMPLEMENTATION: production lifecycle registry + community_engine guards + typed queue-capacity/provider-readiness/birth/queue-exit evidence.
TEST: guard tests; witness-rejection policy test; focused queue-capacity/provider-readiness/birth/queue-exit timing fixtures; full native verification.
REMAINING: current-build queue-capacity enforcement, provider busy/queued behavior, birth timing, queue-exit timing, next-pass visibility, and runtime recovery evidence.

## Research — CURRENT: explicit escrow-claim safe for ordinary research. TARGET: runtime/provider-complete.
EVIDENCE: A research rows; 2.9k hits; pinned ResearchState value family. IMPLEMENTATION: generic lifecycle plus typed numeric `up-research-status` observation, retry barrier, and explicit targeted `release-escrow` lowering before matching ordinary `research`.
TEST: research-in-progress + research escrow-claim native fixtures; 1,083-test Compiler gate green. REMAINING: native same-pass release visibility and provider/busy runtime semantics. The protected-research strategy pattern is now catalogued as explicit execution-template policy and lowered through `escrow_plan`.

## Escrow/resources — CURRENT: release + explicit percentage-policy executable-safe; family remains incomplete.
EVIDENCE: escrow rows; 10.9k hits (largest gap by volume).
IMPLEMENTATION: typed escrow IR, ownership/order/lifetime validation, `NativeEscrowReleasePlan` and
`NativeEscrowPolicyPlan`, dedicated native binder, `escrow.execution.release` and
`escrow.execution.set-percentage` mappings, executable registry inventory, deterministic emission,
compiler threading through the shared `escrow_plan` channel.
TEST: escrow semantics + six-path threading + checked-in source-to-.per fixture + pinned native zero-findings +
cross-platform native-support determinism + full compiler regression.
REMAINING: same-pass release→ordinary-action runtime proof, starvation/emergency release, multi-owner handoff,
and remaining UP escrow mutation surfaces. Research claim lowering is now explicitly promoted through the existing `escrow_plan` channel.

## DUC — CURRENT: narrow promoted slice emitted + proven. TARGET: broader executable DUC coverage.
EVIDENCE: DUC rows; 11.6k/11.9k hits; typed plan/binder/emitter; pinned native fixture.
IMPLEMENTATION: semantic/duc.py + ir/duc.py + native binder/engine mapping/registry/emitter.
TEST: native deterministic acceptance fixture + full compiler verification.
REMAINING: retained-filter/stale-target semantics,
measured performance advisories, and broader source-level expressiveness. DUC group create/reset/set/size/flag commands and generic `up-get-fact` Goal output now have contracted native engine mappings and zero-findings acceptance coverage; runtime group membership/flags and returned reader values remain engine state. Search-state, group-size, cost-delta, point, and target-data output bindings are promoted through typed storage requests; returned target-data values and object liveness remain engine-produced/runtime-dependent.

## Controllers/attack — CURRENT: issue-executable, lifecycle incomplete. TARGET: lifecycle-complete.
EVIDENCE: A attack rows; 47 attack-now vs mediated-control finding; native attack-now reference and controller ownership catalog.
IMPLEMENTATION: typed ir/native_attack.py, dedicated binder promotion, contracted issue-only mapping, deterministic emitter/compiler threading.
TEST: test_native_attack_lifecycle.py, compiler native integration, assert_attack_native.py pinned zero-findings artifact gate.
REMAINING: completion witness, release semantics, group membership/admission details, exploration/town-size/targeting coupling, attack Strategic Numbers, runtime behavioral evidence. Target-policy bridge is now mode-sensitive: DUC target is required only for explicitly DUC-targeted execution and remains optional for native controller modes.

## Source graph — CURRENT: deterministic policy-safe with explicit load-random materialization. TARGET: met incl. decision on load-random.
EVIDENCE: depths/fingerprints; source assembly tests; Duke + vendored-AI topology.
IMPLEMENTATION: resolver + validation + explicit per-directive `LoadRandomSelection` materialization. TEST: source-graph focused coverage plus full Compiler verification.
REMAINING: runtime RNG/weight semantics are intentionally not modeled. Active .xs inputs are explicitly rejected at the compiler boundary because no .xs↔.per bridge contract exists.

## Game data — CURRENT: Byzantine subset with manifest coverage audit. TARGET: 145-node factual model + overlays.
EVIDENCE: civ_profile patch 185872; authoritative 28-building + 145-unit/tech manifest; coverage parser and 39+ tests.
IMPLEMENTATION: typed manifest parser/classifier distinguishes modeled, explicitly unavailable, and unmodeled facts without inventing missing values. All 14 `NotAvailable` rows are carried through the civilization availability overlay with manifest provenance.
IMPLEMENTATION: the pinned 185872 aoe2techtree technology snapshot materializes 51 identity-safe Byzantine technology nodes; native Age-advance TechIds 101/102/103 count as modeled through the typed age-advance IR. A pinned unit snapshot subset materializes 12 identity-safe Byzantine unit nodes with manifest + ENGINE_DATA provenance, provider/line wiring, costs, train times, and safe upgrade relations.
IMPLEMENTATION: Fish Trap 199 is materialized through an explicit building seed. Technology IDs 54 and 909 are materialized through a separate identity-conflict seed path with manifest + independent official/community evidence; the normal snapshot seed path remains name-identity-safe.
IMPLEMENTATION: TechIds 527/528 are now modeled as identity-safe units with Dock provider, line membership, bidirectional upgrade links, and typed trigger technologies 905/244. Unit 527/528 fixed cost/train-time remain intentionally `None` because the current authoritative evidence does not support those fields. Tech 408 Spies/Treason is represented by typed `VariableCost` data with explicit fail-closed fixed-cost behavior.
REMAINING: 0 manifest nodes remain unmodeled in the current 173-node Byzantine manifest: 159 modeled and 14 verified-unavailable. Prerequisites/effects, broader civ overlays, replayable overlays, and universal/native-ID provenance remain open.

## Strategy runtime — CURRENT: observation binding + capability recovery contract closed. TARGET: observation-complete.
EVIDENCE: strategy runtime suite plus native observation contracts. Promoted: Fact-only `up-can-search` as `DUC_SEARCH_AVAILABILITY`; escrow-aware affordability/build/research predicates as `ESCROW_CAPABILITY`; `attack-now` remains fail-closed as an Action; capability loss/recovery now has an explicit typed contract.
REMAINING: controller-specific attack/exploration/town-size observation remains OPEN; deeper DUC retained-state and escrow same-pass/runtime semantics remain OPEN; broader corpus recovery evidence remains. Generic persistent Strategic Number state is now bound as `PERSISTENT_CONTROL_STATE` with 0..511 SN validation and no controller attribution.
