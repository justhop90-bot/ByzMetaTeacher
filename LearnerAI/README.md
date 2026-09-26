# Learner AI Framework

Status: framework/specification only. No executable AoE2 .per gameplay code belongs here yet.

Purpose: teach a beginner to build an AoE2DE AI to strong community scripting standards without turning the project into a competitive build-order bot, research simulator, or generic agent framework.

Core lifecycle:

OBSERVE → INTERPRET → STRATEGIC POSTURE → PERSISTENT DEMAND → CAPABILITY → FEASIBILITY → ENGINE ACTION → WORLD-STATE WITNESS → RELEASE/REASSESS

The workspace separates Engine, State, Information, Strategy, Economy, Construction, Production, Military, and Engineering by ownership.

Strategy owns why. Domain modules own how. The engine owns engine-native feasibility and execution. World state proves completion. Engineering verifies that the lifecycle is real.

## Documents

- GOAL.md — authoritative educational goal and scope
- MODULE_MAP.md — module map and workspace structure
- INTERFACES.md — ownership and cross-module contracts
- SCHEMAS.md — demand, capability, action, witness, and release schemas
- LIFECYCLE.md — universal execution lifecycle
- OWNERSHIP.md — state ownership and writer/reader rules
- LEARNING_PATH.md — progression from beginner to community-standard practice
- ENGINEERING.md — validation and verification standard
- EXAMPLES.md — planned worked examples, specification only

No file in this workspace is an executable AI module. It is the classroom and design contract for one.
