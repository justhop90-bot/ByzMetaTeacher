# State Transition

Defines deliberate transitions between persistent strategic states.

## Rule

A transition must have:

- triggering observation or condition;
- owning strategy;
- explicit precedence;
- target state;
- invalidation or recovery path.

## Examples

Opening posture -> Anti-Rush.

RUSH -> Castle conversion.

Defense -> recovered economic posture.

Castle conversion -> Imperial conversion.

## Requirement

Transitions represent meaningful changes in what position the player is trying to create.

They are not a queue of build steps.

## Source

Read docs/project/BotDirection.txt, docs/project/Basilisk-Controller-Specification.md, Basilisk/Basilisk.per, and validation/strategy-rush-checklist.md.
