# Source Graph load-random deterministic materialization

Goal: replace the remaining source-graph dead-end for active `load-random` with an explicit, caller-supplied deterministic selection policy.

Contract:
- An active `load-random` remains rejected by default.
- A `LoadRandomSelection` identifies the exact directive by canonical source path + line + column and names the selected declared target.
- The resolver loads only that selected target and records a RANDOM edge with target/child provenance.
- A selected target must be one of the directive's declared entries.
- No weighted RNG, engine RNG, probability, or runtime selection semantics are inferred.
- The existing validator accepts an active RANDOM edge only when it has been materialized with a target; unmaterialized RANDOM edges remain rejected.

Verification:
- focused source-graph tests cover rejection without policy, successful deterministic materialization, validator acceptance, and rejection of undeclared targets.
- Full Compiler CI/native determinism remains the acceptance gate.
