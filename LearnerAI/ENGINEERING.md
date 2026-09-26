# Engineering and Verification Standard

Engineering exists to prevent plausible-looking .per code from being mistaken for correct AI behavior.

## Static validation

Every implementation phase should check:

- parser syntax and balanced rule structure;
- logical operator arity;
- valid identifiers and command forms;
- rule element limits;
- source/load order;
- first writer versus first consumer;
- all readers and writers of important state;
- dead-end, unfed, blocked, functionally-disconnected, unfinished, duplicate/conflicting, and open-loop state;
- repeated actions without release;
- missing pending-state guards;
- missing feasibility checks;
- actions whose witnesses can never become true.

## Runtime verification

Runtime remains empirical. Static analysis cannot prove that the engine behaves exactly as assumed.

For each important behavior, capture:

1. demand creation;
2. capability becoming available/unavailable;
3. feasibility result;
4. action issuance;
5. world-state change;
6. witness;
7. release;
8. reassessment.

## Witness discipline

A witness must correspond to an observable engine/world fact. Comments, rule firing, action issuance, or a goal being set are not automatically witnesses of successful gameplay.

## Failure classification

Use precise classifications rather than vague bug labels:

- DEAD-END
- UNFED
- BLOCKED
- FUNCTIONALLY-DISCONNECTED
- OPEN-LOOP
- UNFINISHED
- DUPLICATE-CONFLICTING

A behavior may be syntactically valid and still fall into one of these categories.

## Recovery discipline

Persistent intent should normally survive temporary resource or timing failures. Use transient cooldown/backoff and explicit obsolescence/cancellation rather than multiplying persistent retry counters.

## Engineering boundary

Engineering reports failures and verifies lifecycle truth. It does not silently repair gameplay by becoming a universal manager.
