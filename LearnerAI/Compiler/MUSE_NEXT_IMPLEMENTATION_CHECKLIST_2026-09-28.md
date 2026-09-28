# Compiler next implementation checklist — Muse cross-reference
Date: 2026-09-28
Research pin: 51489706c54ce5c0680d295169ac72a24467e36a
Implementation base: main 51489706c54ce5c0680d295169ac72a24467e36a

This is the execution checklist derived from the Muse forensic package. Evidence is mapped to the actual compiler gap, not treated as a feature wishlist.

## Tier 0 — establish executable foundations

- [ ] Merge construction lifecycle hardening from PR #86.
  - Muse: `implementation_map.md`, `compiler_coverage_baseline.md`, `00-README.md`.
  - Current state: PR #86 remains unmerged; main lacks the final foundation/placement lifecycle hardening.
  - Owner: `semantic/action_issuance.py`, `semantic/completion_witness.py`, `semantic/release_state.py`, `semantic/resource_conflicts.py`, `ir/model.py`, `emitter/per.py`.
  - Gate: same-pass visibility proof plus runtime evidence for foundation/placement semantics.

- [x] Close the Strategic Number binding persistence boundary.
  - Muse: `compiler_coverage_baseline.md` says SN is analysis-safe/emission-open and explicitly calls out inventory, DSL allocation, and emission; `implementation_map.md` assigns SN allocation to `semantic/analyzer.py`, `compiler.py:_storage_requests`, and `runtime_binding.py`; `compiler_false_assumptions.md` warns that typed-native support is not executable support.
  - Implemented in this tranche: v4 manifest schema, request fingerprinting, integrity validation, migration rules, and manifest-focused regression tests.
  - Remaining SN work: compiler-owned request construction, explicit inventory/catalog, end-to-end allocation, numeric binding resolution, emitted fixture, native zero-findings gate.

- [ ] Implement Timer allocation using the same symbolic-storage boundary.
  - Muse: `compiler_coverage_baseline.md`, `implementation_map.md`, `native_unknowns.md`.
  - Owner: `ir/recurrent.py`, `semantic/analyzer.py`, `compiler.py:_storage_requests`, `runtime_binding.py`.
  - Gate: explicit initialization policy plus measured countdown pass granularity.

## Tier 1 — largest evidence-backed lowering gaps

- [ ] Escrow/resource-control executable lowering.
  - Muse: `compiler_undercoverage.md` identifies 10.9k escrow hits as the largest volume gap; `community_knowledge_coverage.md` marks escrow-age-up/commodity escrow/starvation as not lowerable; `native_unknowns.md` keeps gating formula and release/admission order open.
  - Owner: `semantic/resource_conflicts.py`, analyzer/emitter escrow paths, native contracts.
  - Gate: admission, claim, release, starvation/recovery, and hostile competing-owner tests.

- [ ] DUC binder and emission.
  - Muse: `implementation_map.md`, `compiler_undercoverage.md`, `compiler_coverage_baseline.md`; corpus gives 11.6k `up-find` and 11.9k `up-set-target` hits.
  - Owner: `primitives/registry.py`, `primitives/native_binder.py`, `emitter/per.py`, DUC semantic IR.
  - Gate: search/filter/reset/target/group state survives source-order and recurrent analysis, then lowers through typed native contracts.

- [ ] Native controller attack lifecycle.
  - Muse: `implementation_map.md`, `compiler_undercoverage.md`, `native_unknowns.md`; `attack-now` is only 47 corpus hits and the corpus says attack is largely mediated by persistent SN/town-size/group state.
  - Owner: `semantic/native_controller.py`, `semantic/native_controller_interactions.py`, new attack lifecycle validator.
  - Gate: admission/completion/release/reassess model before executable promotion.

## Tier 2 — compiler completeness after the control plane

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
