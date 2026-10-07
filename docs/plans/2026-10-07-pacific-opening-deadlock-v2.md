# Pacific Opening Deadlock Repair v2 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Pacific opening deadlock so villagers continue through the Feudal transition, Feudal is actually issued, the starting transport can recover from a failed load, and fishing remains an independent Pacific bootstrap capability.

**Architecture:** Preserve the existing Byzantine lifecycle model and native AIRef facts. Repair ownership boundaries rather than introducing a second planner: affordability decides when civilian production may yield, native research feasibility remains the actual Feudal execution gate, Pacific transport gets an explicit failed-load recovery edge, and fishing/dock capability remains parallel to age advancement.

**Tech Stack:** AoE2DE `.per`, Python compiler IR/emitter, unittest, GitHub Actions, checked-in `Byzantine.per` synchronization.

## Global Constraints

- Keep `ENGINE FACT / COMMUNITY EVIDENCE / COMPILER POLICY / UNKNOWN` distinct.
- `can-*` remains permission/capability, not completion truth.
- Pending remains in-flight; world-state witnesses own completion.
- Do not replace the existing Pacific lifecycle or add a second planner.
- Preserve Standard Arabia behavior and the existing Pacific map classification.
- Keep `can-research-with-escrow(feudal-age)` on the actual Feudal research action. It must not be used as the civilian-production stop predicate.
- Pacific transport recovery must fail closed and re-enter the existing acquisition lifecycle rather than inventing a new transport command.

---

### Task 1: Decouple villager continuity from Feudal queue feasibility

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py:973-1023`
- Test: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py:263-365`
- Test: `LearnerAI/Compiler/tests/test_byzantine_runtime_sync.py`
- Runtime: synchronized `Byzantine.per` persistent civilian production section

**Interfaces:**
- Consumes: `civilian-villager-continuity` execution requirements and existing Feudal transition demand.
- Produces: villager continuity admission based on `can-afford-research feudal-age`, while Feudal execution continues to require `can-research-with-escrow feudal-age`.

- [ ] **Step 1: Update the focused regression**
  Assert the Dark-Age villager stop guard is:
  `(unit-type-count-total villager >= 20)` + `(can-afford-research feudal-age)`, and explicitly reject `can-research-with-escrow feudal-age`.

- [ ] **Step 2: Verify the relevant failure**
  Run the focused opening-economy test against the current branch before implementation.
  Expected failure: the existing assertion finds `can-research-with-escrow feudal-age` in the civilian demand.

- [ ] **Step 3: Implement the minimum behavior**
  Replace only the Dark-Age inner predicate in `civilian-villager-continuity`. Do not change the 20-villager threshold, action, lifecycle witness, or Feudal demand.

- [ ] **Step 4: Verify the focused pass**
  Run the focused villager-continuity tests.
  Expected: all selected tests pass and the Castle stop guard remains unchanged.

- [ ] **Step 5: Synchronize and verify runtime**
  Regenerate/synchronize `Byzantine.per`; verify its `Persistent civilian production` block contains the affordability guard and no Dark-Age `can-research-with-escrow(feudal-age)` villager stop.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `fix: decouple villager continuity from Feudal queue readiness`.

### Task 2: Harden Feudal execution against provider/issuance failure

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py` Feudal execution demand and its native control lowering.
- Modify: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`
- Modify: `LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`
- Runtime: synchronized Feudal transition block in `Byzantine.per`

**Interfaces:**
- Consumes: `feudal-transition`, existing escrow release, `can-research-with-escrow feudal-age`.
- Produces: a Feudal action path that selects a valid research provider before issuing `research feudal-age`, with the existing `current-age >= feudal-age` witness and retry path retained.

- [ ] **Step 1: Add/extend focused regression**
  Prove the Feudal demand keeps `can-research-with-escrow feudal-age` as execution capability, and that the lowered native control contains an explicit research-provider selection before the research action rather than relying on an unqualified `research` command.

- [ ] **Step 2: Verify the relevant failure**
  Run the focused strategy/control tests.
  Expected failure: no explicit provider-selection rule is currently present for Feudal research.

- [ ] **Step 3: Implement the minimum behavior**
  Add a native Feudal provider-selection rule modeled on Naga's validated TC selection, using existing target/search facilities already accepted by the compiler. The rule must ignore under-attack or already-progressing providers, select one deterministic nearest valid TC, and issue the research action only from that selected provider. Keep the native capability predicate as the final feasibility gate.

- [ ] **Step 4: Verify the focused pass**
  Run the Feudal control and compiler integration tests.
  Expected: provider-selection rule exists, Feudal action remains guarded by `can-research-with-escrow`, and current-age remains the completion witness.

- [ ] **Step 5: Synchronize and verify runtime**
  Regenerate `Byzantine.per`; verify Feudal transition contains provider selection plus research and does not add time-based completion truth.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `fix: harden Feudal research provider issuance`.

### Task 3: Add explicit Pacific transport LOAD failure recovery

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py` Pacific DUC control generation.
- Modify: `LearnerAI/Compiler/ir/water.py` Pacific transport lifecycle state/rules.
- Test: `LearnerAI/Compiler/tests/test_water_transport_execution.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`
- Runtime: synchronized Pacific transport controller in `Byzantine.per`

**Interfaces:**
- Consumes: `pacific-transport-lifecycle`, transport ID, load-count goal, existing transport recovery demand.
- Produces: a failed-load edge that reselects the transport/villager set after an absent load witness, without treating elapsed time as completion.

- [ ] **Step 1: Add focused regressions**
  Assert the lifecycle has a recover/retry state for LOAD when `garrison-count < 4` and no pending load action remains. Assert the recovery clears stale transport witness slots before re-entering LOAD.

- [ ] **Step 2: Verify the relevant failure**
  Run the focused Pacific transport tests.
  Expected failure: lifecycle currently has LOAD -> TRANSIT only through success and has no LOAD failure transition.

- [ ] **Step 3: Implement minimum recovery**
  Add a Pacific transport LOAD-RECOVERY state and native rule:
  current lifecycle = LOAD, transport still exists, load-count < 4, and the transport-load action is no longer in flight -> clear transport ID/load witness, return to the existing opening transport objective/lifecycle acquisition state.
  Reuse the existing transport acquisition and DUC selectors. Do not add another movement primitive or timer-as-truth.

- [ ] **Step 4: Verify focused pass**
  Run transport lifecycle and DUC compiler tests.
  Expected: both success path and failed-load recovery path are represented and deterministic.

- [ ] **Step 5: Synchronize and verify runtime**
  Verify `Byzantine.per` includes the new recovery state/rule and does not strand `pacific-transport-lifecycle` in LOAD after witness loss.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `fix: recover Pacific transport load failures`.

### Task 4: Make Pacific fishing a parallel bootstrap entitlement

**Files:**
- Modify: `LearnerAI/Compiler/ir/water.py` fishing controller/demand lowering.
- Modify: `LearnerAI/Compiler/ir/economic_control.py` only where Pacific allocation presently suppresses fishing-compatible wood/food continuity.
- Test: `LearnerAI/Compiler/tests/test_water_transport_execution.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`
- Runtime: synchronized dock/fishing lifecycle in `Byzantine.per`

**Interfaces:**
- Consumes: Pacific map classification, dock witness, `water-fishing-continuity`, existing train arbitration/escrow.
- Produces: a Pacific fishing bootstrap that can train the first two fishing ships in Dark Age when a dock and live fish capability exist, without waiting for Feudal or transport completion.

- [ ] **Step 1: Add focused regressions**
  Assert Pacific fishing continuity remains admissible in Dark Age, requires dock + fish capability, and is not gated by Feudal or the transport lifecycle state. Assert Pacific economy posture does not block the fishing demand.

- [ ] **Step 2: Verify the relevant failure**
  Run the focused water/fishing tests.
  Expected failure: current generated runtime has the demand, but the regression proving complete independence from Pacific transport/Feudal ownership is absent.

- [ ] **Step 3: Implement minimum behavior**
  Keep the current fishing demand and arbitration channel, but add an explicit Pacific bootstrap rule that raises fishing production entitlement when `map-type pacific-islands`, dock exists, no severe naval pressure exists, and fishing ships < 2. Do not require `pacific-transport-lifecycle`, `feudal-resource-island-transport-objective`, or Feudal Age.

- [ ] **Step 4: Verify focused pass**
  Run the water/fishing tests and opening-economy tests.
  Expected: Pacific fishing can begin independently while Feudal and transport proceed in parallel.

- [ ] **Step 5: Synchronize and verify runtime**
  Confirm `Byzantine.per` has a Pacific Dark-Age fishing bootstrap path, while the existing Feudal naval escalation and transport escort gates remain intact.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `fix: keep Pacific fishing bootstrap independent`.

## Integration verification

After Tasks 1-4 are individually green:

Run the repository's focused compiler suites, canonical Byzantine build, native zero-findings validation, deterministic semantic shadow, and full compiler regression from `.github/workflows/compiler-tests.yml` plus the Pacific/Feudal DUC gate.

Expected: zero parser/native findings; deterministic checked-in `Byzantine.per`; all focused Pacific, Feudal, strategy, and synchronization tests pass.

Then run the runtime acceptance matrix:
- Pacific start: villager production remains continuous through the Feudal decision boundary.
- Pacific start with Feudal resources: Feudal research issues without requiring a timer or prior transport completion.
- Pacific start with a starting transport: load witness or explicit LOAD recovery occurs; transport is not permanently idle.
- Pacific start with a dock: first fishing-ship entitlement can issue before Feudal.
- Standard Arabia: existing Moderate-win baseline remains unchanged.

Unresolved product decisions: none. The runtime match itself remains empirical acceptance evidence, not a compiler fact.
