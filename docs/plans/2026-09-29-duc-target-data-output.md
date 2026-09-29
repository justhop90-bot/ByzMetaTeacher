# DUC target-data Goal output lowering

Community/AIReref basis:
- AIRef lists `up-get-object-data` and `up-get-object-target-data` as Very High Fact/Action DUC commands.
- AIRef patch notes document historical fixes specifically for their Fact/Action parameter handling, so the compiler must preserve their native arity and output position rather than approximating them as facts.
- Existing compiler contracts already model both commands as selected-target / selected-target-target readers with width-1 Goal output contracts and pinned evidence.

Scope:
- Promote the two Fact/Action output commands through the normal GoalSlot storage allocator.
- Validate OutputGoalId at argument index 1 against each native output contract.
- Rewrite only OutputGoalId during emission.
- Preserve target-data semantic observations/provenance already implemented.
- Do not infer returned object-data values, object liveness, or same-pass numeric visibility.

Acceptance:
- Focused DUC binder/registry/emission tests for both commands.
- Native deterministic DUC zero-findings fixture.
- Full Compiler regression, 9-way determinism, snapshot comparison, and aggregate verification gate.
