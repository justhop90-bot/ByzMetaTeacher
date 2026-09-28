# Compiler coverage baseline (replaces provisional 56% with measured denominators)
Method: per family, CURRENT = proven stage; TARGET = executable-safe; EVIDENCE = artifact rows;
REMAINING GAP = exact work. Ratios use Artifact A rows + test kinds, NOT test counts.

## Goals — CURRENT: executable-safe. TARGET: met.
EVIDENCE: A rows set-goal/goal/up-compare-goal/up-modify-goal; 23k corpus hits; binding+emission.
IMPLEMENTATION: runtime_binding + emitter + persistent_state. TEST: 24+40.
REMAINING: package-collision runtime proof (minor).

## SN plane — CURRENT: analysis-safe, emission-open. TARGET: executable-safe incl. emission.
EVIDENCE: A SN rows; 10k hits; SNSEM-001..009. IMPLEMENTATION: semantics + binding infra.
TEST: fixture-only. REMAINING: 0..511 catalog; DSL allocation; emission tests.

## Timers — CURRENT: model-safe, emission-open. TARGET: executable-safe.
EVIDENCE: A timer rows; ~4k hits; staged-expiry design. IMPLEMENTATION: scheduler + recurrent IR.
TEST: scheduler + semantics (static-true impossible by design). REMAINING: DSL alloc; granularity measure.

## Construction — CURRENT: executable-safe on main; hardened in UNMERGED PR86.
TARGET: PR86 merged + runtime-proven. EVIDENCE: A build rows; 3k hits; PR86 contracts.
IMPLEMENTATION: validators + emitter (+PR86). TEST: issuance/witness/release suites (+PR86).
REMAINING: merge; same-pass visibility proof; foundation/placement evidence.

## Train — CURRENT: generic-safe; queue-model open. TARGET: queue-aware safe.
EVIDENCE: A train rows; IDIOM-006. IMPLEMENTATION: registry + community_engine guards.
TEST: guard tests; witness-rejection policy test. REMAINING: queue/capacity/provider/birth.

## Research — CURRENT: generic-safe. TARGET: escrow-claim safe.
EVIDENCE: A research rows; 2.9k hits. IMPLEMENTATION: generic lifecycle.
TEST: integration. REMAINING: escrow-claim lowering; in-progress signal.

## Escrow/resources — CURRENT: evidence-only + build-singleton. TARGET: claim/release safe.
EVIDENCE: A escrow rows; 10.9k hits (largest gap by volume).
IMPLEMENTATION: feasibility facts + resource_conflicts (1-owner). TEST: 8 + feasibility tests.
REMAINING: full op lowering; gating formula; starvation/override.

## DUC — CURRENT: analyzer-complete, binder-unsupported. TARGET: emitted + proven.
EVIDENCE: A DUC rows; 11.6k/11.9k hits; 124 tests fixture-only; oracle schema.
IMPLEMENTATION: semantic/duc.py + ir/duc.py + hygiene contracts.
TEST: fixture-only (no DSL end-to-end). REMAINING: adapters; emission; reset taxonomy; perf advisories.

## Controllers/attack — CURRENT: issue-executable, lifecycle incomplete. TARGET: lifecycle-complete.
EVIDENCE: A attack rows; 47 attack-now vs mediated-control finding; native attack-now reference and controller ownership catalog.
IMPLEMENTATION: typed ir/native_attack.py, dedicated binder promotion, contracted issue-only mapping, deterministic emitter/compiler threading.
TEST: test_native_attack_lifecycle.py, compiler native integration, assert_attack_native.py pinned zero-findings artifact gate.
REMAINING: completion witness, release semantics, group membership/admission details, exploration/town-size/targeting coupling, attack Strategic Numbers, runtime behavioral evidence.

## Source graph — CURRENT: executable-safe minus load-random. TARGET: met incl. decision on load-random.
EVIDENCE: depths/fingerprints; 67 tests; Duke + vendored-AI topology.
IMPLEMENTATION: resolver + validation. TEST: strong. REMAINING: load-random; .xs boundary.

## Game data — CURRENT: Byzantine subset. TARGET: 145-node manifest + overlays.
EVIDENCE: civ_profile patch 185872; 36 tests. REMAINING: manifest completion; broader civs.

## Strategy runtime — CURRENT: downstream-only complete. TARGET: observation-complete.
EVIDENCE: 33+9+2 tests; TRAIN-gated observations. REMAINING: DUC/attack/escrow observations;
policy-vs-semantics audit.
