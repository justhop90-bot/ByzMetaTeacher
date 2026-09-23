### SAFE-DERIVED

The value is recomputed from current world facts in a way that is order-independent or deliberately rebuilt before consumers.

### ONE-PASS-LATENCY

A writer changes state that a consumer will observe on a later pass. This is acceptable only when the latency is intended and harmless.

A one-pass-late state must not become permission for a stale engine action. If the upstream state can be strategically invalidated later in the same pass, the final engine executor must re-check the live invalidation predicate before acting. In other words, one-pass latency is allowed for demand/package propagation, but not allowed to bypass current-pass strategic or resource safety.

Required pattern:

    earlier-pass writer
        ->
    persistent demand/package state
        ->
    later-pass consumer
        ->
    current-pass invalidation/feasibility witness
        ->
    engine action

A validator must distinguish harmless one-pass state propagation from stale-action leakage and assert the final executor's live guard where the distinction matters.

### ORDER-SENSITIVE

The final value depends on rule ordering. This is allowed only when the ordering is the policy and is documented.

### UNSAFE-FORWARD-DEPENDENCY

A consumer assumes a writer has already run in the same pass or assumes a value has already been cleared/initialized when source order does not guarantee that. This is a defect.
