# DUC Semantic Implementation Checklist

Date: 2026-09-27

Purpose: turn the practical DUC knowledge used by experienced AoE2 .per authors into compiler-visible semantic state. This is a generic community-meta compiler layer, not a civilization strategy implementation. The immediate downstream use is a Byzantine bot; future strategy clients can reuse the same native knowledge.

Evidence baseline:
- AIRef command contracts and data limits:
  - search-local capacity 240
  - search-remote capacity 40
  - `up-full-reset-search` resets search/filter/target state
  - `up-reset-search` selects list/index state to clear
  - `up-reset-filters` clears retained filter state
  - `up-find-local`, `up-find-remote`, `up-find-resource`
  - `up-set-target-object`, `up-set-target-point`
  - `up-target-objects`, `up-target-point`
  - `up-get-search-state`, `up-get-point`
- UserPatch and community scripting practice:
  - retained filters affect later searches until reset
  - repeated searches build/modify current search lists
  - full reset is the common recurrent-search hygiene boundary
- Community .per examples:
  - lewisc64/aoe2ai DUC chains
  - practical search -> filter -> target -> action sequences
- Repo contracts:
  - `EffectiveRule` supplies effective source order, source instance identity, source slice ordinal, within-rule action order, and recurrent/one-shot behavior.
  - native GoalSpan contracts already cover search-state and point storage.
  - persistent-state analysis already establishes source-order/state-lineage precedent.

## Vertical slice A: typed DUC state IR

- [x] Add typed list identity: LOCAL / REMOTE.
- [x] Add typed target identity: OBJECT / POINT.
- [x] Add search-list generation lineage.
- [x] Keep list capacity explicit: 240 local / 40 remote.
- [x] Track retained filter state and filter generation.
- [x] Capture filter snapshots at search time.
- [x] Track target source-list generation and source-filter generation.
- [x] Preserve target lifetime as VALID / STALE / UNKNOWN.
- [x] Track point-target GoalSpan identity separately from object-target identity.
- [x] Record rule/source/pass provenance on DUC state mutations.
- [x] Record DUC effects and source visibility.
- [x] Record search-state observations as typed semantic objects rather than anonymous Goal writes.

Primary modules:
- `LearnerAI/Compiler/ir/duc.py`
- `LearnerAI/Compiler/semantic/duc.py`

## Vertical slice B: native DUC contracts

- [x] Contract search commands and their destination list.
- [x] Contract list capacity.
- [x] Contract that searches append to current list lineage rather than inventing per-command list replacement.
- [x] Contract retained-filter consumption.
- [x] Contract filter retention and resetability.
- [x] Contract partial search reset semantics.
- [x] Contract full search reset semantics.
- [x] Contract object-target source requirements.
- [x] Contract point-target state.

Current implementation location:
- `LearnerAI/Compiler/semantic/duc.py`

Next consolidation:
- [ ] promote `NativeDucContractCatalog` into the shared native contract catalog/registry instead of keeping the first slice local to the DUC semantic module.

## Vertical slice C: recurrent .per behavior

- [x] Preserve effective rule order from `EffectiveRule`.
- [x] Preserve within-rule action order.
- [x] Mark recurrent rules as potentially repeating.
- [x] Detect recurrent search accumulation when no same-rule list reset precedes the search.
- [x] Detect retained filters left active by recurrent rules.
- [x] Propagate DUC state across the existing `RuleExecutionReport` control-transfer graph.
- [x] Join local and remote search-list generations path-sensitively.
- [x] Join retained filters path-sensitively and mark divergent retained-filter lineage as ambiguous.
- [x] Join pre-existing object targets so valid-vs-absent or valid-vs-stale paths become `UNKNOWN`.
- [x] Record branch predecessors and merged DUC fields in typed `DucBranchMerge` metadata.
- [x] Preserve compiler/native source provenance through the joined state.
- [ ] model cross-pass target reuse as a distinct proof state rather than a static final-state reuse.
- [x] integrate backward-jump recurrence with finite loop widening: bounded three-edge iterations, field-local canonicalization, and stable recurrent state convergence without linearizing the loop.
- [x] emit deterministic DUC loop-widening diagnostics with loop head, back-edge source, iteration bound, and widened fields.

## Vertical slice D: reset and invalidation semantics

- [x] `up-reset-filters` invalidates filter predicates only.
- [x] `up-reset-search` clears selected list/index state without automatically claiming filter reset.
- [x] `up-full-reset-search` clears both search lists, filters, and DUC targets.
- [x] Redundant empty filter reset is idempotent and does not churn lineage.
- [x] Object targets become invalid/unknown when dependent list contents are explicitly mutated.
- [ ] distinguish native-proven STALE from compiler UNKNOWN for every list-mutating command.
- [ ] add explicit contracts for `up-clean-search`, `up-remove-objects`, and list-index operations.
- [ ] add native evidence for exact target lifetime after object death, disappearance, or list mutation.

## Vertical slice E: provenance

- [x] Carry source file identity.
- [x] Carry source slice ordinal.
- [x] Carry effective rule order.
- [x] Carry within-rule action order.
- [x] Carry recurrent/one-shot behavior.
- [x] Carry consumed state generations.
- [x] Carry native semantic contract identity.
- [x] Carry evidence identifiers.
- [ ] add explicit effective-source-graph fixture proving #load provenance survives into DUC diagnostics.

## Vertical slice F: diagnostics

Implemented/defined:
- [x] LIST-UNINITIALIZED
- [x] TARGET-UNSCOPED
- [x] TARGET-UNKNOWN
- [x] target invalidation path
- [x] recurrent list accumulation warning
- [x] retained-filter warning/information

Still required:
- [ ] integrate DUC diagnostics into `RuleDiagnosticReport`
- [ ] add stable `DUC-* ` diagnostic enum values to the shared diagnostics taxonomy
- [ ] add source-location and related-rule metadata for cross-rule diagnostics
- [ ] make unknown-state diagnostics advisory rather than silently promoting assumptions to facts
- [ ] add explicit list-capacity diagnostics
- [ ] add DUC performance/cost diagnostics

## Vertical slice G: hostile tests

- [x] same-rule search -> search-state -> target -> action provenance
- [x] backward up-jump-rule loop converges without DUC-013 and records finite widening metadata.
- [x] loop widening is field-local for local search lineage and abstracts retained filter lineage.
- [ ] retained filter crosses rule boundary and is consumed by later search
- [ ] filter reset removes retained predicate
- [ ] partial search reset invalidates only selected list
- [ ] full reset invalidates both lists, filters, and target
- [ ] target use without initialized list
- [ ] target use after list invalidation
- [ ] list mutation after target creation produces UNKNOWN target lifetime
- [ ] recurrent search without reset raises accumulation warning
- [ ] repeated search after same-list reset starts a fresh generation
- [ ] point-target set/read/use chain
- [ ] search-state GoalSpan remains storage metadata, not target identity
- [ ] load-file DUC provenance uses effective source instance identity
- [ ] local/remote capacity bounds are enforced
- [ ] deterministic fingerprints remain stable across repeated analysis

Primary test file:
- `LearnerAI/Compiler/tests/test_duc_semantics.py`

## Integration order

1. [x] Create typed DUC IR.
2. [x] Implement first abstract-state interpreter.
3. [ ] Finish hostile state-transition fixtures.
4. [ ] Move native DUC contracts into the shared native registry.
5. [ ] Integrate DUC into rule diagnostics.
6. [ ] Run generic compiler native-zero acceptance with DUC-bearing .per fixtures.
7. [ ] Add effective-source-graph provenance fixtures.
8. [ ] Add DUC cost/cardinality analysis from AIRef performance evidence.
9. [ ] Integrate DUC effects with recurrent pass analysis.
10. [ ] Expose the completed DUC knowledge to downstream Byzantine strategy compilation.

## Explicit scope boundary

This tranche does not add a DUC DSL, a generic scheduler, a unit simulator, or civilization policy. It teaches the compiler what practical native .per authors already have to know about DUC state. The compiler records and reasons about engine-visible state; AoE2 remains the final runtime authority.
