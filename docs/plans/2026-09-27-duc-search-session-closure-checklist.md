# DUC SearchSession Closure Checklist — 2026-09-27

## Cross-reference basis

- [x] Current `main` audited at `da59156b8b04ca2ae3a7819690c82424f3c434d2`.
- [x] Naga was cross-referenced through current public community testing reports; it remains an actively tested high-end AoE2 AI with documented DUC usage. citeturn611271search1turn611271search2
- [x] Niek/Atilla prior art checked for `up-full-reset-search`, chained `up-find-*` calls, target selection, and retained DUC state.
- [x] `aoe2ai` prior art checked for chained DUC searches and `up-get-search-state` use. citeturn972669search1
- [x] AIRef/UserPatch semantics checked: DUC lists are mutable retained state; filters affect subsequent searches; search-state exposes total and last-search counts. citeturn972669search2
- [x] AIRef performance evidence checked: search cost depends on list size/cardinality, and stored groups can avoid repeated searches. citeturn990122view1

## SearchSession tranche

- [x] Add typed conservative DUC cardinality ranges.
- [x] Distinguish retained list cardinality from the most recent search delta.
- [x] Make each search generation carry explicit input-generation lineage.
- [x] Include prior list fingerprint in search-generation content identity.
- [x] Preserve retained-list semantics across chained searches instead of treating each search as replacement state.
- [x] Expose total/last-search cardinality through `up-get-search-state` IR.
- [x] Preserve zero-cardinality state through full search reset.
- [x] Include cardinality state in branch-generation identity.
- [x] Promote DUC error diagnostics to compiler rejection.
- [x] Add regression fixtures for chained searches, search-state cardinality, and reset behavior.

## Remaining closure work

- [ ] Model search-index offsets and filter-triggered index resets explicitly.
- [ ] Model exact query/focus-player search cursor semantics where AIRef evidence permits it.
- [ ] Add first-class DUC group state and `up-create-group`/`up-set-group` semantics.
- [ ] Bind `up-get-search-state` to concrete four-Goal output-span allocation and Goal overwrite provenance.
- [ ] Strengthen target identity beyond list-generation/index proofs.
- [ ] Add cardinality-aware DUC performance diagnostics using evidence-backed bounds.
- [ ] Add composite recurrent + mutation + branch + target fixtures.
