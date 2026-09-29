# Compiler next implementation checklist — Muse cross-reference
Date: 2026-09-28
Research pin: 51489706c54ce5c0680d295169ac72a24467e36a
Verified main SHA: 82f4dd93ee2d6c468bc911c3f35b53156bfa5656.
Latest main verification: Compiler workflow #2263 / Actions run 36509926898 at that exact main SHA is green: 1,023 tests, focused suites 7 / 24 / 27 / 15, production queue-capacity and provider-readiness native zero-findings gates, all 9 native-support determinism jobs, snapshot comparison, and the Compiler verification gate.

This is the execution checklist derived from the Muse forensic package. Evidence is mapped to the actual compiler gap, not treated as a feature wishlist.

## Tier 0 — establish executable foundations

- [x] Construction lifecycle hardening is on main.
  - PR #86 was audited and closed as superseded because its emitter/compiler revisions were stale against current main.
  - Current implementation includes foundation/placement observation, retry barriers, canonical build witnesses, and current diagnostics/tests.
  - Remaining gate: same-pass visibility proof plus runtime evidence for foundation/placement semantics.

- [x] Close the Strategic Number binding persistence and execution slice.
  - Muse: `compiler_coverage_baseline.md` identifies the SN plane as analysis-safe/emission-open and explicitly calls out inventory, DSL allocation, and emission; `implementation_map.md` assigns request construction to `semantic/analyzer.py`, request collection to `compiler.py:_storage_requests`, and inventory wiring to `runtime_binding.py`; `compiler_undercoverage.md` says the 10k-hit SN corpus justifies catalog + DSL allocation now.
  - Manifest/persistence: v4 schema in `schemas/binding-manifest-v4.schema.json`, request fingerprints, inventory provenance, integrity verification, explicit v1-v3 migration, and regression coverage.
  - Compiler-owned request construction: `parser.py` accepts explicit `sn <name> = <initial>` state declarations; `ir/strategic_number.py` carries typed `StrategicNumberState` + `StrategicNumberStorageRequest`; `semantic/analyzer.py` assigns owner/request identity, WHY_NOT_GOAL, stability key, and native contract.
  - Versioned catalog/inventory: `primitives/strategic_number_catalog.py` consumes the pinned DE-filtered AIRef snapshot, materializes the full 0..511 namespace, derives documented/candidate IDs, records the source SHA, pins catalog version `airef-de-2026-04-29-v1`, and excludes compiler allocation of SN 511.
  - Compiler-to-binder integration: `compiler.py:_storage_requests()` now collects compiler-owned SN requests; absent explicit inventory the compiler installs the versioned catalog inventory; binding is required to produce `StrategicNumberSlot`.
  - Numeric emission: `emitter/per.py` resolves symbolic state identity through `BindingResult`, emits numeric `defconst` aliases, and emits one-shot `set-strategic-number` initialization rules.
  - Native acceptance: `tests/fixtures/strategic_number.perdsl` is now a checked-in compiler fixture; `assert_strategic_number_native.py` compiles it twice, verifies deterministic numeric allocation against the catalog, and runs the pinned `aoe2_ai_lab` zero-findings gate. This directly addresses the Muse false assumption that fixture-only semantic tests prove emission coverage.
  - Remaining SN unknowns are now engine-knowledge questions, not allocation plumbing: per-SN defaults/auto-mutation/version scope and unknown-SN write behavior remain explicitly OPEN in `native_unknowns.md`.

- [x] Timer allocation using the same symbolic-storage boundary is implemented and CI/native-verified.
  - Parser/IR: `timer <name>` declarations become typed `TimerState` + `TimerRequest` records with explicit `DISABLE_BEFORE_FIRST_USE` policy and deterministic stability keys.
  - Binding: `compiler.py:_storage_requests()` now collects Timer requests; existing `TimerSlot` allocation/inventory/manifests are reused unchanged.
  - Emission: deterministic TimerId `defconst` aliases plus one-shot `disable-timer` initialization are emitted only for declared compiler-owned timers.
  - Acceptance: checked-in `tests/fixtures/timer_allocation.perdsl`, `tests/assert_timer_native.py`, focused `test_timer_allocation.py`, and Compiler CI native zero-findings gate are green.
  - Remaining engine unknowns: actual countdown/pass granularity and timer reuse/lifetime remain explicitly unpromoted.

## Tier 1 — largest evidence-backed lowering gaps

- [~] Escrow/resource-control executable lowering.
  - **Release-only promoted slice is complete and independently re-verified by Compiler workflow #2149.** Added dedicated native binder, `escrow.execution.release` mapping, executable registry inventory, deterministic `release-escrow` emission, source-to-.per fixture, pinned native zero-findings acceptance, and cross-platform determinism coverage.
  - The family remains partial: `set-escrow-percentage`, UP escrow mutations, starvation/emergency release, multi-owner handoff, and direct native proof of same-pass `release-escrow -> ordinary action` remain outside executable-safe promotion.
  - Repository-side same-pass evidence package is now specified and machine-checked: `docs/plans/2026-09-28-native-escrow-same-pass-visibility-checklist.md`, `docs/reference/oracles/escrow-same-pass-research.schema.json`, candidate `docs/reference/oracles/candidates/escrow-same-pass-research.native.json`, and `tests/test_escrow_same_pass_oracle_spec.py`. The DE runtime gate remains user-owned and OPEN.
- [x] Escrow ownership/order/lifetime semantic gate.
  - Added typed ordered `EscrowOperation` IR plus contract-set ownership validation and execution-order validation.
  - Acceptance coverage: same-rule release-before-consume, reversed ordering, escrow-aware consume, post-release stale consumption, policy-reset cleanup, and hostile owner mismatch/resource contention.
  - Deliberately does not claim native DE same-pass visibility or starvation/handoff runtime proof.
  - Checklist: `LearnerAI/Compiler/MUSE_ESCROW_EXECUTION_CHECKLIST_2026-09-28.md`.
  - Same-pass runtime checklist/oracle: `docs/plans/2026-09-28-native-escrow-same-pass-visibility-checklist.md`; native candidate remains UNVERIFIED until DE execution.
  
  - Muse: `compiler_undercoverage.md` identifies 10.9k escrow hits as the largest volume gap. The affordability/resource-view formula and mutation/ownership/lifetime model are now closed in the research repair; same-pass visibility, starvation recovery, and multi-owner handoff remain open runtime questions.
  - Owner: `semantic/resource_conflicts.py`, analyzer/emitter escrow paths, native contracts.
  - Gate: admission, claim, release, starvation/recovery, and hostile competing-owner tests.

- [x] DUC binder and emission.
  - Muse evidence remains the same: `implementation_map.md`, `compiler_undercoverage.md`, `compiler_coverage_baseline.md`; corpus gives 11.6k `up-find` and 11.9k `up-set-target` hits.
  - Typed internal path implemented with no new source syntax: `ir/native_duc.py`, `primitives/native_binder.py`, `primitives/engine_semantics.py`, `primitives/registry.py`, `emitter/per.py`, compiler threading in `compiler.py`.
  - Promoted executable slice: search, filter, reset, list mutation, direct/object/point target establishment, and `up-target-objects`.
  - Promoted output slice now includes `up-get-search-state` four-Goal output binding plus `up-get-group-size` width-1 Goal output binding through the existing GoalSpan/GoalSlot storage allocator and emitter.
  - Remaining boundary: returned reader values, runtime group membership/flags, and broader higher-order controller semantics remain runtime-dependent; the point/cost/target-data output writers themselves are promoted.
  - Native proof: `assert_duc_native.py` compiles the internal plan twice, checks deterministic search-state and group-size output binding, and runs the pinned native parser zero-findings gate.
  - Mainline verification for the prior search-state tranche is green on 1,034 tests; the group-size tranche in this branch remains pending final CI verification.
  - PR #101 added the composite recurrent + branch + mutation + target fixture, covering unreachable-branch state seeding, clean-search target-proof degradation, remove-objects preservation/invalidation, and stale-target consumer diagnostics.

- [~] Native controller attack lifecycle (issue-only slice connected; lifecycle remains open).
  - Muse: `implementation_map.md`, `compiler_undercoverage.md`, `native_unknowns.md`; `attack-now` is only 47 corpus hits and the corpus says attack is largely mediated by persistent SN/town-size/group state.
  - Connected issue path: typed `ir/native_attack.py`, dedicated attack binder promotion, deterministic `emitter/per.py` lowering, compiler threading, and pinned native artifact gate `tests/assert_attack_native.py`.
  - Deliberate open boundary: attack completion, release, target acquisition, group membership, exploration/town-size coupling, and attack Strategic Number control remain non-executable.
  - Owner: `semantic/native_controller.py`, `semantic/native_controller_interactions.py`, typed attack IR/binder/emitter.
  - Gate: admission/completion/release/reassess model before lifecycle-complete promotion; current tranche proves only issue connectivity with completion `UNOBSERVED`.

- [~] Production queue semantics.
  - Production lifecycle now carries typed current+queued `unit-type-count-total` observation and exact provider `building-type-count` observation, plus explicit `ProductionQueueCapacityEvidence`, `ProductionProviderAvailabilityEvidence`, `ProductionProviderReadinessEvidence`, and `ProductionQueueCapacityControlEvidence` records. All evidence remains fail-closed and OPEN where engine behavior is unresolved.
  - SN 264 (`sn-enable-training-queue`) is typed as a native control input with documented queue-slot meaning; `up-train-site-ready` is now typed as a distinct train-provider readiness/admissibility fact.
  - PR #103 connected the SN 264 control seam. PR #104 connects the AIRef/UserPatch training-site readiness seam, canonicalizes `c:` UnitIds, carries OPEN readiness through `ProductionLifecycle`, and preserves `can-train` as the sole training-feasibility authority.
  - Production birth/queue-exit timing is now typed as two separate OPEN observational records: `ProductionBirthTimingEvidence` (game-time + unit-world-state boundary) and `ProductionQueueExitTimingEvidence` (game-time + current/queued total + pending-work observation). Symbolic production pending UnitIds are canonicalized to native numeric IDs before emission. These records do not infer events, same-pass ordering, or completion.
  - Remaining native questions are current-build SN 264 enforcement, exact provider busy/queued interaction of `up-train-site-ready`, birth timing, queue-exit timing, and next-pass visibility. `unit-type-count-total` is observation, not completion; provider presence is not provider idleness; readiness does not establish completion.
  - Owner: production async semantics and witness layer. Runtime behavior remains OPEN and user-owned.

- [~] Research escrow/in-progress semantics.
  - The repository now has a machine-checked same-pass escrow/research evidence specification and capture candidate: `docs/plans/2026-09-28-native-escrow-same-pass-visibility-checklist.md`, `docs/reference/oracles/escrow-same-pass-research.schema.json`, `docs/reference/oracles/candidates/escrow-same-pass-research.native.json`, and `tests/test_escrow_same_pass_oracle_spec.py`.
  - The compiler-side release-only escrow slice and research in-progress lifecycle remain statically verified; direct DE same-pass visibility, escrow ownership acquisition, starvation/recovery, and provider-loss/runtime details remain open.
  - Owner: research lifecycle plus resource-control integration; runtime execution remains user-owned.

- [x] Source-graph `load-random` and explicit .xs boundary.
  - Active `load-random` now requires explicit deterministic target materialization; runtime RNG/weight behavior remains OPEN.
  - Active `.xs` entrypoints and `#load` targets fail closed with `SOURCE-GRAPH-017`; no .xs↔.per state bridge is modeled.
  - Focused source-graph coverage plus the full Compiler verification gate cover the boundary.
  - Muse: `implementation_map.md`, `community_knowledge_coverage.md`, `native_unknowns.md`.
  - Gate: deterministic compiler policy for load-random and an explicit unsupported/typed boundary for .xs.

- [ ] Game-data manifest completion.
  - [x] Authoritative manifest is parsed and count-checked at CI time.
  - [x] Coverage is explicitly classified into modeled, verified-unavailable, and unmodeled nodes.
  - [x] Current 185872 machine-readable technology snapshot is pinned at revision `3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f` and blob `c4f7da961e82a8231b1ba49459949c4d6e479bc8`.
  - [x] Focused enrichment proves unresolved existing technology cost/research-time fields can be filled without synthesizing providers, prerequisites, effects, or civ availability.
  - [x] All 14 authoritative manifest `NotAvailable` rows are surfaced as explicit unavailable facts with manifest provenance.
  - Current Byzantine snapshot: 86 modeled, 14 explicitly unavailable, 73 unmodeled.
  - Muse: `compiler_coverage_baseline.md`, `player_knowledge_matrix.md`.
  - Owner: `ir/civ_profile.py`, patch overlays, 145-node manifest.

- [ ] Strategy runtime observation closure.
  - [x] Fact-only `up-can-search` is bound as `DUC_SEARCH_AVAILABILITY`.
  - [x] Escrow-aware affordability/build/research facts are bound as `ESCROW_CAPABILITY`.
  - [x] `attack-now` remains fail-closed as an Action, not a strategic observation.
  - Remaining: attack/controller observations, retained DUC state, escrow same-pass/runtime semantics, and broader observation policy audit.
  - `up-train-site-ready` is bound as `TRAIN_PROVIDER_READINESS`; it remains distinct from `can-train` feasibility and does not claim provider busy/queued runtime behavior.
  - SN 74 (`sn-maximum-town-size`) is bound as `TOWN_SIZE_CONTROL` for exact `up-compare-sn` observations; controller attribution remains evidence-only and no attack semantics are promoted.
  - SN 42 (`sn-number-explore-groups`) is bound as `EXPLORATION_GROUP_CONTROL` for exact `up-compare-sn` observations, with the documented non-negative range enforced; exploration-controller interactions remain evidence-only.
  - SN 61 (`sn-number-boat-explore-groups`) is bound as `BOAT_EXPLORATION_GROUP_CONTROL` for exact `up-compare-sn` observations, with the documented non-negative range enforced; no water-map or runtime controller behavior is inferred.
  - SN 18 (`sn-total-number-explorers`) is bound as `TOTAL_EXPLORER_CAP`, preserving the documented `-1` ignore value and rejecting lower values.
  - SN 3 (`sn-cap-civilian-explorers`) is bound as `CIVILIAN_EXPLORER_CAP`, preserving the documented `-1` ignore value without inferring the underlying villager-allocation scheduler.
  - SN 264 is now specialized as `PRODUCTION_QUEUE_CAPACITY_CONTROL` when its exact `up-compare-sn 264 == <0..15>` contract is present; generic SN observations remain `PERSISTENT_CONTROL_STATE` and no DE enforcement is inferred.
  - Muse: `compiler_coverage_baseline.md`, `player_knowledge_matrix.md`.
  - Owner: DUC/attack/escrow observation primitives plus policy-vs-semantics audit of native token validation.

## Mandatory verification discipline

- [x] Every new emitted capability gets an actual source-to-.per test. The release-only escrow slice uses a checked-in source fixture plus a pinned native validator; synthetic semantic fixtures are supplementary only.
- [x] Every native promotion must pass NATIVE_KNOWN → NATIVE_TYPED → SEMANTICALLY_ADAPTED → ENGINE_SEMANTICS_MAPPED → EXECUTABLE_SAFE.
- [x] Open engine facts remain fail-closed and explicitly labeled OPEN/UNKNOWN.
- [ ] Community lineage is discounted when evidence is duplicated through snapshots.
- [ ] Reproducibility is measured from artifact bytes and binding manifests, not test counts or provisional coverage percentages.
