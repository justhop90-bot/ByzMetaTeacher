# Compiler next implementation checklist — Muse cross-reference
Date: 2026-09-28
Research pin: 51489706c54ce5c0680d295169ac72a24467e36a
Implementation base: main dca0458986d0e50e2ae26889d89f863a3c2ff923
Post-merge compiler verification: 915 tests; native zero-findings; deterministic cross-platform matrix.

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

- [ ] Implement Timer allocation using the same symbolic-storage boundary.
  - Muse: `compiler_coverage_baseline.md`, `implementation_map.md`, `native_unknowns.md`.
  - Owner: `ir/recurrent.py`, `semantic/analyzer.py`, `compiler.py:_storage_requests`, `runtime_binding.py`.
  - Gate: explicit initialization policy plus measured countdown pass granularity.

## Tier 1 — largest evidence-backed lowering gaps

- [~] Escrow/resource-control executable lowering.
  - PR #94 merged the typed `NativeEscrowReleasePlan`, release-plan validation, registry native arity/type checks, and forwarding through all six public compiler surfaces.
  - Remaining executable gap: dedicated native binder, engine-semantics mapping, registry promotion, deterministic `release-escrow` emission, source-to-.per fixture, and native zero-findings acceptance.
- [x] Escrow ownership/order/lifetime semantic gate.
  - Added typed ordered `EscrowOperation` IR plus contract-set ownership validation and execution-order validation.
  - Acceptance coverage: same-rule release-before-consume, reversed ordering, escrow-aware consume, post-release stale consumption, policy-reset cleanup, and hostile owner mismatch/resource contention.
  - Deliberately does not claim native DE same-pass visibility or starvation/handoff runtime proof.
  - Checklist: `LearnerAI/Compiler/MUSE_ESCROW_EXECUTION_CHECKLIST_2026-09-28.md`.
  
  - Muse: `compiler_undercoverage.md` identifies 10.9k escrow hits as the largest volume gap. The affordability/resource-view formula and mutation/ownership/lifetime model are now closed in the research repair; same-pass visibility, starvation recovery, and multi-owner handoff remain open runtime questions.
  - Owner: `semantic/resource_conflicts.py`, analyzer/emitter escrow paths, native contracts.
  - Gate: admission, claim, release, starvation/recovery, and hostile competing-owner tests.

- [x] DUC binder and emission.
  - Muse evidence remains the same: `implementation_map.md`, `compiler_undercoverage.md`, `compiler_coverage_baseline.md`; corpus gives 11.6k `up-find` and 11.9k `up-set-target` hits.
  - Typed internal path implemented with no new source syntax: `ir/native_duc.py`, `primitives/native_binder.py`, `primitives/engine_semantics.py`, `primitives/registry.py`, `emitter/per.py`, compiler threading in `compiler.py`.
  - Promoted executable slice: search, filter, reset, list mutation, direct/object/point target establishment, and `up-target-objects`.
  - Deliberate boundary: Goal-output DUC commands, target-data readers, and group output/storage remain unpromoted until their GoalSpan/storage bindings are connected to the internal plan.
  - Native proof: `assert_duc_native.py` compiles the internal plan twice, checks artifact determinism and required emitted commands, and runs the pinned native parser zero-findings gate.
  - Full compiler/native verification: current mainline compiler regression suite is 915 tests OK; all native-support determinism jobs and the aggregate compiler verification gate pass.

- [~] Native controller attack lifecycle (issue-only slice connected; lifecycle remains open).
  - Muse: `implementation_map.md`, `compiler_undercoverage.md`, `native_unknowns.md`; `attack-now` is only 47 corpus hits and the corpus says attack is largely mediated by persistent SN/town-size/group state.
  - Connected issue path: typed `ir/native_attack.py`, dedicated attack binder promotion, deterministic `emitter/per.py` lowering, compiler threading, and pinned native artifact gate `tests/assert_attack_native.py`.
  - Deliberate open boundary: attack completion, release, target acquisition, group membership, exploration/town-size coupling, and attack Strategic Number control remain non-executable.
  - Owner: `semantic/native_controller.py`, `semantic/native_controller_interactions.py`, typed attack IR/binder/emitter.
  - Gate: admission/completion/release/reassess model before lifecycle-complete promotion; current tranche proves only issue connectivity with completion `UNOBSERVED`.

- [ ] Production queue semantics.
  - Muse: `compiler_coverage_baseline.md`, `player_knowledge_matrix.md`, `native_unknowns.md`; current+queued is corroborated but queue capacity/provider-idle/birth timing remain open.
  - Owner: production async semantics and witness layer.

- [ ] Research escrow/in-progress semantics.
  - Muse: `compiler_coverage_baseline.md`, `community_knowledge_coverage.md`, `native_unknowns.md`.
  - Owner: research lifecycle plus resource-control integration.

- [ ] Source-graph `load-random` and explicit .xs boundary.
  - Muse: `implementation_map.md`, `community_knowledge_coverage.md`, `native_unknowns.md`.
  - Gate: deterministic compiler policy for load-random and an explicit unsupported/typed boundary for .xs.

- [ ] Game-data manifest completion.
  - Muse: `compiler_coverage_baseline.md`, `player_knowledge_matrix.md`.
  - Owner: `ir/civ_profile.py`, patch overlays, 145-node manifest.

- [ ] Strategy runtime observation closure.
  - Muse: `compiler_coverage_baseline.md`, `player_knowledge_matrix.md`.
  - Owner: DUC/attack/escrow observation primitives plus policy-vs-semantics audit of native token validation.

## Mandatory verification discipline

- [ ] Every new emitted capability gets an actual source-to-.per test. Synthetic `EffectiveRule` fixtures do not count as emission coverage.
- [ ] Every native promotion must pass NATIVE_KNOWN → NATIVE_TYPED → SEMANTICALLY_ADAPTED → ENGINE_SEMANTICS_MAPPED → EXECUTABLE_SAFE.
- [ ] Open engine facts remain fail-closed and explicitly labeled OPEN/UNKNOWN.
- [ ] Community lineage is discounted when evidence is duplicated through snapshots.
- [ ] Reproducibility is measured from artifact bytes and binding manifests, not test counts or provisional coverage percentages.
