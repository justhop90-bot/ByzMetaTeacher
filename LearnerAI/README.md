# LearnerAI Framework

This directory is the framework and workspace for a comprehensive AoE2DE .per learner AI. It is documentation-first by design. No gameplay implementation belongs here until the framework is agreed and the lessons are ready.

The learner teaches community-standard AoE2 AI scripting craft: engine facts and actions, persistent state, scouting and interpretation, strategic intent, resource management, construction and production lifecycles, military adaptation, verification, recovery, and rule-order reasoning.

The learner is not a Basilisk implementation and is not intended to reproduce one community bot. It teaches recurring community patterns while keeping the architecture explicit enough for a beginner to inspect.

North-star lifecycle:

OBSERVE -> INTERPRET -> STRATEGIC INTENT -> DEMAND -> CAPABILITY -> FEASIBILITY -> ENGINE ACTION -> WORLD-STATE WITNESS -> RELEASE/CONTINUE -> REASSESS

Strategy owns why. Domain modules own how. The engine owns whether an operation can execute. World state proves whether it happened. Engineering verifies that the script understood all four.

## Workspace status

- Framework: established
- Module boundaries: established
- Interfaces: established
- Schemas: established
- Curriculum: established
- Gameplay code: intentionally absent
- Validation implementation: intentionally absent
- Runtime tuning: intentionally absent

See MODULE_MAP.md, OWNERSHIP.md, INTERFACES.md, SCHEMAS.md, LIFECYCLE.md, and LEARNING_PATH.md before adding implementation.
