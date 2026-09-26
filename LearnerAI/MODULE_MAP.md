# Module Map and Workspace Structure

The learner workspace uses nine conceptual modules. The structure is intentionally recognizable to AoE2 AI community practice while remaining small enough to teach.

## Proposed structure

LearnerAI/
- README.md
- GOAL.md
- MODULE_MAP.md
- INTERFACES.md
- SCHEMAS.md
- LIFECYCLE.md
- OWNERSHIP.md
- LEARNING_PATH.md
- ENGINEERING.md
- EXAMPLES.md
- LearnerAI.per — eventual entry/load map; specification placeholder only
- Engine/ — engine configuration, constants, initialization, engine primitives
- State/ — persistent goals/state, timers, transitions
- Information/ — scouting, enemy/map observations, threat facts
- Strategy/ — strategic selection, posture, transitions, adaptation
- Economy/ — worker allocation, resources, farms, economic technologies, arbitration
- Construction/ — building requirements, feasibility, construction lifecycle
- Production/ — villagers, production buildings, unit queues, upgrades
- Military/ — defense, army composition, readiness, attack, siege, recovery
- Engineering/ — validation, witnesses, diagnostics, recovery discipline

## Conceptual flow

Engine → State primitives → Information → Strategy → domain demands → Economy/Construction/Production/Military → Engine actions → world state → Information → reassessment.

Engineering observes and validates the lifecycle across all domains. It is not a gameplay manager.

## File-design rule

Directories represent ownership boundaries, not a requirement that every concept become a large file. Small, purpose-specific files are preferable to giant utility modules.

## Dependency rule

Read broadly when necessary; write narrowly. A module may consume facts from another domain when legitimate, but semantic ownership of persistent state remains singular.
