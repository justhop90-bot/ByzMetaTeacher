# Pacific Runtime Liveness v4 Implementation Plan

> **For agentic workers:** execute this plan task-by-task. Each task is independently testable.

**Goal:** Make the observed Pacific opening advance deterministically through the Feudal decision boundary and prevent the starting transport from becoming permanently trapped in recovery.

**Architecture:** Preserve the current Byzantine ownership model. The Pacific opening remains one controller surface with separate Feudal, fishing, and transport lifecycles. can-* remains capability evidence, current-age remains the Feudal completion witness, and transport recovery reuses the existing recovery/rearm state rather than creating a second transport planner.

**Tech Stack:** Python compiler IR, AoE2DE .per, unittest, GitHub Actions, checked-in Byzantine.per.

## Global constraints

- Keep OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT.
- Do not add timers as completion truth.
- Do not weaken can-research-with-escrow(feudal-age) on the actual Feudal research action.
- Preserve Arabia behavior.
- Preserve existing Pacific fishing and transport controller ownership.
- Checked-in Byzantine.per must remain synchronized with the compiler.

### Task 1: Pacific Feudal boundary

Files:
- LearnerAI/Compiler/ir/community_strategy_packs.py
- LearnerAI/Compiler/tests/test_strategy_opening_economy.py
- synchronized Byzantine.per

Behavior:
- On Pacific Islands, once Dark Age reaches 20 villagers, civilian production yields even when native Feudal research capability is temporarily false.
- Non-Pacific maps keep the existing affordability-based villager stop.
- Feudal research itself still requires can-research-with-escrow(feudal-age) and completes only on current-age >= feudal-age.

Focused acceptance:
- Pacific villager guard contains map-type pacific-islands.
- Pacific guard contains no can-research-with-escrow feudal-age.
- Feudal demand retains can-research-with-escrow feudal-age.

### Task 2: Pacific transport recovery handoff

Files:
- LearnerAI/Compiler/ir/water.py
- LearnerAI/Compiler/tests/test_water_transport_execution.py
- synchronized Byzantine.per

Behavior:
- LOAD failure remains gated by the Transport Ship pending-object witness c:545.
- On failed LOAD, lifecycle enters RECOVERY and explicitly sets pacific-transport-recovery = 1.
- Existing pacific-transport-lifecycle-rearm-after-loss then returns the lifecycle to LOAD when a transport still exists.
- Load count and transport identity are cleared before reacquisition.

Focused acceptance:
- LOAD recovery writes the recovery entitlement.
- Rearm consumes that entitlement and requires a live transport.
- No new timer-as-truth or second transport controller exists.

### Task 3: Full Pacific verification

Run:
- focused opening-economy tests,
- focused water transport tests,
- canonical Byzantine build,
- deterministic semantic shadow,
- native zero-findings on generated and checked-in artifacts,
- full compiler regression.

Runtime acceptance:
- Pacific reaches the Feudal decision without continuing villager issuance past the 20-villager boundary solely because research-provider readiness is false.
- Feudal research can issue once native capability becomes true.
- Starting transport can leave LOAD recovery and attempt acquisition again.
- Fishing continuity remains independently eligible after a completed dock.
- Arabia regression remains unchanged.