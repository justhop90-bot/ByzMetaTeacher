# Engineering Module

Engineering proves that the player specification and generated rules are internally coherent.

It is not a strategy module and not a universal manager.

## Owns

- static lifecycle diagnostics;
- ownership/dependency analysis;
- native compiler integration;
- regression fixtures;
- runtime acceptance matrices;
- recovery analysis.

## Product role

Engineering asks whether the intended player behavior is actually connected:

observation -> strategy -> demand -> capability -> feasibility -> action -> witness -> release -> reassess

## Sources

Read LearnerAI/ENGINEERING.md, SOURCE_MAP.md, validation/basilisk-validator.js, validation/basilisk-validator-selftest.js, validation/repair-lifecycle-replay.js, and Compiler/.

## Acceptance

A behavior is not accepted merely because it parses.

Static and runtime evidence must agree.
