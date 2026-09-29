# DUC cost-delta executable GoalSpan lowering

Scope: connect the existing semantic `up-get-cost-delta` four-Goal output span to the typed native DUC execution path.

Implemented:
- native engine semantic mapping: `duc.output.cost-delta`
- DUC command inventory admission for `up-get-cost-delta`
- typed `GoalSpanRequest` using the existing `cost-data-4-goal-span` contract, width 4, start 41..15996
- registry validation at OutputGoalId argument 0
- deterministic emitter rewrite through the existing `GoalSpan` binding
- focused binder/registry/emission tests
- native DUC acceptance fixture covering cost-delta with search-state and group-size output writers

Explicit non-goals:
- no `up-setup-cost-data` state machine
- no cost-data mutation commands
- no resource arithmetic or numeric cost-delta values
- no runtime cost measurement claims

Runtime values remain engine-produced and outside compiler proof.
