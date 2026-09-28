# DUC SearchSession / TargetSession Semantics Implementation Plan

> For agentic workers: Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

Goal: Complete the next native DUC state-machine tranche by turning the existing search-index, filter, list-generation, target, Goal-output, recurrent, and cardinality evidence into one deterministic SearchSession/TargetSession semantic substrate.

Architecture: Extend the existing DUC IR and analyzer rather than introducing a second DUC abstraction. Treat local/remote search lists, retained filters, search cursors, targets, and output Goal spans as distinct native state domains linked by provenance and pass visibility. SearchSession establishes candidate state; TargetSession consumes a proof-carrying target established from that session. Unknown target lifetime remains fail-closed.

Tech Stack: Python 3.11-3.13, existing DUC IR/analyzer, Native Contract Catalog, recurrent execution report, GoalSpan binding, unittest, GitHub Actions.

## Global Constraints
- No new source syntax.
- No generic scheduler or simulator.
- Preserve native local/remote list distinctions.
- Search index is mutable state, not a derived stateless query.
- Filters persist until explicit or documented implicit reset.
- Query changes, filter changes, and focus-player changes must carry explicit reset provenance.
- Zero-result searches remain runtime-dependent facts unless a static empty bound is proven.
- Target consumers require valid target provenance.
- Goal outputs remain typed spans with overwrite-generation and writer provenance.
- Performance/cardinality metadata is advisory until a separate warning policy exists.

### Task 1: Normalize SearchSession state transitions
Files: modify ir/duc.py and semantic/duc.py; tests in test_duc_semantics.py.
- [ ] Add failing fixtures for filter mutation -> cursor reset, query mutation -> cursor reset, focus-player change -> remote reset, explicit reset -> generation increment, zero-result retention, and capacity widening.
- [ ] Verify red with focused DUC tests.
- [ ] Implement transition functions that preserve list generation, filter generation, cursor generation, reset reason, and provenance.
- [ ] Verify green.
- [ ] Run recurrent + DUC integration tests.
- [ ] Commit: feat(compiler): normalize DUC SearchSession state.

### Task 2: Establish proof-carrying target handoff
Files: modify ir/duc.py and semantic/duc.py; tests in test_duc_semantics.py.
- [ ] Add failing object-target and point-target fixtures for current-pass, preserved, stale, and path-ambiguous proof.
- [ ] Verify red.
- [ ] Implement explicit SearchSession -> TargetSession handoff records.
- [ ] Reject target consumers when list/filter/target provenance is stale.
- [ ] Verify green.
- [ ] Run native zero-findings strategic-number/DUC fixtures.
- [ ] Commit: feat(compiler): add proof-carrying DUC target handoff.

### Task 3: Complete Goal-span and cardinality propagation
Files: modify ir/duc.py, semantic/duc.py, runtime_binding.py; tests in test_duc_semantics.py and binding tests.
- [ ] Add failing width-4 search-state, width-2 point, and branch-widened output fixtures where evidence exists.
- [ ] Verify red.
- [ ] Preserve writer provenance, overwrite generations, pass identity, and path ambiguity through joins.
- [ ] Attach cardinality ranges to list generations and target sets.
- [ ] Verify green.
- [ ] Run full binding regression.
- [ ] Commit: feat(compiler): propagate DUC output spans and cardinality.

### Task 4: Feed performance and recurrent eligibility into SearchSession validation
Files: modify semantic/duc.py and recurrent integration points only if required; tests in test_duc_semantics.py and test_recurrent_execution.py.
- [ ] Add failing fixtures for repeated search in recurrent rules, bounded-group substitution, and target execution behind a never-runnable recurrent rule.
- [ ] Verify red.
- [ ] Implement advisory performance metadata and recurrent firing gates without converting performance evidence into blocking errors.
- [ ] Verify green.
- [ ] Run full compiler/native verification.
- [ ] Commit: feat(compiler): couple DUC cost evidence to recurrent eligibility.

## Acceptance
The tranche is complete only when an expert can trace Search command -> filter/query/focus state -> cursor generation -> search-list generation -> cardinality -> target proof -> target consumer -> Goal output provenance -> recurrent eligibility -> deterministic native validation.

## Unresolved externally observable decisions
- Whether DUC performance evidence becomes a warning-level diagnostic in a later tranche.
- Whether target-session state should become a first-class runtime-binding surface or remain purely semantic until more native commands require storage.