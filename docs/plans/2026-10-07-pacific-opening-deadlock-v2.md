# Pacific Opening Deadlock Repair v2 Implementation Plan

> For agentic workers: execute this plan task-by-task. Each task is independently testable.

**Goal:** Break the observed Pacific Dark-Age deadlock at the actual ownership boundaries: Feudal resource-claim rollback, transport-load liveness, and first fishing-ship feasibility.

**Architecture:** Preserve the existing Byzantine lifecycle and Pacific controllers. Do not add a second planner or duplicate fishing/transport ownership. `can-*` remains capability/permission, research completion remains a world-state witness, timers are only reconsideration cadence, and transient claims must be released on failed action paths.

**Tech Stack:** AoE2DE `.per`, Python compiler/runtime synchronizer, unittest, GitHub Actions, canonical checked-in `Byzantine.per`.

## Global Constraints

- Preserve `ENGINE FACT / COMMUNITY EVIDENCE / COMPILER POLICY / UNKNOWN` separation.
- Preserve `OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT`.
- Preserve existing Pacific fishing and transport controller ownership.
- Do not use timers as completion truth.
- Do not weaken `can-research-with-escrow(feudal-age)` on the actual Feudal research action.
- Do not add speculative Dark-Age building prerequisites solely to paper over the Feudal failure.
- Standard Arabia behavior remains a regression boundary.

## Task 1: Release the Feudal transient claim on failed issuance

Modify `tools/synchronize_byzantine_runtime.py` and `LearnerAI/Compiler/tests/test_byzantine_runtime_sync.py`.

The Feudal action acquires `byzantine-resource-claim = 1` and moves to issued state 83. If native research is no longer pending and Feudal has not been witnessed, release the claim before retrying. The new synchronizer rule is idempotent and guarded by `not (up-research-status c: 101 >= 2)` and `not (current-age >= feudal-age)`.

Focused regression: synchronize twice and prove the rollback rule appears exactly once with `set-goal byzantine-resource-claim 0`.

## Task 2: Repair Pacific transport LOAD liveness

Modify `LearnerAI/Compiler/ir/water.py` and `LearnerAI/Compiler/tests/test_water_transport_execution.py`.

Replace the Pacific LOAD failure recovery guard `up-pending-objects c:904 == 0` with `up-pending-objects c:545 == 0`. 904 is the villager class; 545 is the Transport Ship object. The transport recovery state, load-count witness, timer cadence, and rearm lifecycle remain unchanged.

Focused regression: assert c:545 is used and the old c:904 guard is absent.

## Task 3: Give the existing fishing-continuity owner a Dark-Age first-boat fallback

Modify `LearnerAI/Compiler/ir/community_strategy_packs.py` and `LearnerAI/Compiler/tests/test_strategy_opening_economy.py` plus the synchronized `Byzantine.per` action block.

Do not add a second demand. The existing `water-fishing-continuity` owner already has a Pacific Dark-Age bootstrap controller. Add a first-boat branch requiring `wood-amount >= 75` and native `can-train fishing-ship`; when one fishing ship exists, preserve the existing `can-train-with-escrow fishing-ship` path for later continuity.

Focused regression: prove both first-boat and subsequent escrow paths are present.

## Task 4: Synchronize and verify

Synchronize the checked-in `Byzantine.per`, run focused tests, canonical Byzantine build, deterministic semantic shadow, native zero-findings on generated and checked-in artifacts, cross-platform determinism, and full compiler regression. Merge only after fresh CI on the exact PR head SHA.

## Runtime acceptance matrix

1. Pacific Dark Age reaches Feudal without a stale self-owned resource claim.
2. A failed Feudal research issuance can retry instead of remaining blocked by claim=1.
3. The starting transport can leave LOAD recovery without waiting for the entire villager class to become non-pending.
4. The first fishing ship can issue from a live dock before Feudal.
5. Subsequent fishing continuity still respects escrow and production arbitration.
6. Standard Arabia remains on its existing baseline path.

Runtime match results remain empirical evidence; compiler/native CI does not prove gameplay success.