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

## Research — CURRENT: generic-safe. TARGET: escrow-claim safe.
EVIDENCE: A research rows; 2.9k hits. IMPLEMENTATION: generic lifecycle.
TEST: integration. REMAINING: escrow-claim lowering; in-progress signal.

## Escrow/resources — CURRENT: release-only executable-safe; family remains incomplete.
EVIDENCE: escrow rows; 10.9k hits (largest gap by volume).
IMPLEMENTATION: typed escrow IR, ownership/order/lifetime validation, `NativeEscrowReleasePlan`, dedicated
native binder, `escrow.execution.release` mapping, executable registry inventory, deterministic emission,
compiler threading.
TEST: escrow semantics + six-path threading + checked-in source-to-.per fixture + pinned native zero-findings +
cross-platform native-support determinism + full compiler regression.
REMAINING: same-pass release→ordinary-action proof, starvation/emergency release, multi-owner handoff,
`set-escrow-percentage`/UP escrow mutations, research in-progress integration.

## DUC — CURRENT: narrow promoted slice emitted + proven. TARGET: broader executable DUC coverage.
EVIDENCE: DUC rows; 11.6k/11.9k hits; typed plan/binder/emitter; pinned native fixture.
IMPLEMENTATION: semantic/duc.py + ir/duc.py + native binder/engine mapping/registry/emitter.
TEST: native deterministic acceptance fixture + full compiler verification.
REMAINING: broader group output/storage surfaces, retained-filter/stale-target semantics,
measured performance advisories, and broader source-level expressiveness. Search-state, group-size, cost-delta, point, and target-data output bindings are promoted through typed storage requests; returned target-data values and object liveness remain engine-produced/runtime-dependent.

## Controllers/attack — CURRENT: issue-executable, lifecycle incomplete. TARGET: lifecycle-complete.
EVIDENCE: A attack rows; 47 attack-now vs mediated-control finding; native attack-now reference and controller ownership catalog.
IMPLEMENTATION: typed ir/native_attack.py, dedicated binder promotion, contracted issue-only mapping, deterministic emitter/compiler threading.
TEST: test_native_attack_lifecycle.py, compiler native integration, assert_attack_native.py pinned zero-findings artifact gate.
REMAINING: completion witness, release semantics, group membership/admission details, exploration/town-size/targeting coupling, attack Strategic Numbers, runtime behavioral evidence.

## Source graph — CURRENT: deterministic policy-safe with explicit load-random materialization. TARGET: met incl. decision on load-random.
EVIDENCE: depths/fingerprints; source assembly tests; Duke + vendored-AI topology.
IMPLEMENTATION: resolver + validation + explicit per-directive `LoadRandomSelection` materialization. TEST: source-graph focused coverage plus full Compiler verification.
REMAINING: runtime RNG/weight semantics are intentionally not modeled. Active .xs inputs are explicitly rejected at the compiler boundary because no .xs↔.per bridge contract exists.

## Game data — CURRENT: Byzantine subset. TARGET: 145-node manifest + overlays.
EVIDENCE: civ_profile patch 185872; 36 tests. REMAINING: manifest completion; broader civs.

## Strategy runtime — CURRENT: downstream-only complete. TARGET: observation-complete.
EVIDENCE: 33+9+2 tests; TRAIN-gated observations. REMAINING: DUC/attack/escrow observations;
policy-vs-semantics audit.
