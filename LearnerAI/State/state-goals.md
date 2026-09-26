# State Goals

Defines which goals are legitimate persistent state for the Byzantine player.

## Candidate strategic state

- strategic posture;
- durable opening interpretation;
- durable Castle/boom commitment;
- minimum military intent when it must survive a pass.

## Candidate execution state

- active pending operation;
- live capability claim;
- bounded backoff;
- explicit preemption memory when genuinely required.

## Avoid

Do not create a goal for a value the engine can derive directly.

Do not create phase labels that merely restate current age.

Do not create a retry counter where a transient cooldown is enough.

## Source

LearnerAI/OWNERSHIP.md, SCHEMAS.md, LIFECYCLE.md, and the removable-state audit.
