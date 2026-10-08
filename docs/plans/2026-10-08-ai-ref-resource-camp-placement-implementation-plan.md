# AIRef Resource-Camp Placement Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make lumber, gold, and stone camp placement compiler-owned, AIRef-native, deterministic, and synchronized into `Byzantine.per` without weakening the existing Byzantine lifecycle or introducing a second camp controller.

**Architecture:** Reuse the existing `StrategyProfile.duc_plan` / `NativeDucPlan` channel for resource-front discovery and point placement. Keep strategic demand, counts, opportunity-cost policy, and Strategic Number geometry in the existing camp controller; add only the DUC execution needed to turn a selected resource object into a placement point and `up-build place-point` action. Preserve the existing construction lifecycle for pending/complete/retry semantics and retain the Dark Age first-lumber direct fallback as a compiler-policy recovery path.

**Tech Stack:** Python 3, `unittest`, typed compiler IR, native DUC binder/emitter, AoE2 UP/.per, checked-in `Byzantine.per`, GitHub Actions native zero-findings/parser gates.

## Global Constraints

- AIRef is the only external evidence source for the placement implementation. Do not import Naga, Stock-AI, community `.per`, or undocumented engine behavior into the implementation contract.
- `up-find-resource` is the resource-front discovery primitive; `up-set-target-object` selects a zero-based DUC search-list index; `up-get-point position-object` captures the selected object's position; `up-set-target-point` establishes the placement point; `up-build place-point` executes point-oriented construction.
- `up-get-search-state` writes a four-goal output span and is used only as an observation of search state. It must not be treated as proof that a specific resource object is selected until the requested index is known to exist.
- Remote DUC capacity is 40. Do not assume more than the native list can represent.
- Resource-front selection is distinct from `dropsite-min-distance`. The latter is a distance observation, not a resource-object selector.
- `can-build` is admission/capability evidence only. `up-pending-objects` is pending/in-flight evidence only. `building-type-count` is the completed-world-state witness.
- Resource-front failures remain retryable. Empty search, invalid/out-of-range selection, placement failure, or temporary build infeasibility must not falsely release the demand or manufacture a completion witness.
- Camp floors are zero-based at the DUC object-selection boundary: floor N selects remote index N-1 after proving that index exists.
- Desired Byzantine floors remain: wood 1-6, gold 1-5, stone 1-5. First wood/gold floors remain active for the existing opening policy; later floors retain their current released/support/optional policy and the stone opportunity-cost protection.
- Existing Strategic Number geometry remains authoritative in `LearnerAI/Compiler/ir/camp_control.py`. The DUC planner chooses the resource front; the SN controller governs placement-distance policy.
- No hard-coded Goal IDs are permitted in compiler policy. Point pairs, search-state spans, and remote-count storage must come through the existing runtime binder.
- `Byzantine.per` must remain synchronized with the compiler-owned output. The synchronization script must not silently preserve an obsolete manual resource-front implementation once compiler ownership is established.

---

### Task 1: Define the compiler-owned resource-front DUC contract

**Files:**
- Modify: `LearnerAI/Compiler/ir/native_duc.py`
- Modify: `LearnerAI/Compiler/ir/strategy.py` at `_default_byzantine_duc_plan` and the Byzantine profile construction path
- Modify: `LearnerAI/Compiler/ir/camp_control.py` only where the existing camp policy needs to expose deterministic floor metadata
- Test: `LearnerAI/Compiler/tests/test_native_duc_plan.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`

**Interfaces:**
- Consumes: existing `NativeDucPlan`, `NativeDucRule`, `NativeDucOutputRequest`, `NativeDucGoalInputRequest`, `StrategyProfile.camp_controller`, and the existing runtime binder.
- Produces: a deterministic resource-front subset of `StrategyProfile.duc_plan` with named rules for each resource/floor and binder-owned storage requests.

- [ ] **Step 1: Add the focused failing tests**

Assert that the Byzantine DUC plan contains deterministic resource-front rule identities for:
  - `wood` floors 1-6
  - `gold` floors 1-5
  - `stone` floors 1-5

For every floor, assert:
  - an active-resource filter is present;
  - `up-find-resource c: <resource> ...` is present;
  - the search state is captured through `up-get-search-state`;
  - the action path uses the correct remote index `floor - 1`;
  - point capture uses `up-get-point position-object`;
  - placement uses `up-set-target-point` followed by `up-build place-point 0 c: <building>`;
  - storage requests are unique and binder-owned.

Assert that the first lumber floor retains a separate direct-build recovery path and that the DUC path does not replace it.

- [ ] **Step 2: Verify the relevant failure**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_native_duc_plan LearnerAI.Compiler.tests.test_strategy_compiler_integration -v
```

Expected: the new resource-front assertions fail because the current generic camp demands do not yet own the placement DUC plan.

- [ ] **Step 3: Implement the minimum IR/planning behavior**

Extend the existing Byzantine DUC-plan construction rather than creating a parallel placement planner.

For each camp floor, create deterministic native DUC rules with this lifecycle:

```text
ADMISSIBILITY
  demand active
  + camp capacity unmet
  + can-build
  + no conflicting pending placement
        ↓
TARGET
  full/scoped search reset
  + active-resource filter
  + up-find-resource
        ↓
PICKUP_WITNESS
  up-get-search-state
        ↓
DISPATCH
  prove remote index exists
  + up-set-target-object search-remote floor-1
  + up-get-point position-object
  + up-set-target-point
        ↓
EXECUTION
  up-build place-point 0 c: camp
        ↓
RETURN / RECOVERY
  construction lifecycle owns pending/complete/retry
```

Use `NativeDucOutputRequest` for the four-goal search-state span and two-goal point pair. Use `NativeDucGoalInputRequest` where a later rule must consume a binder-assigned GoalSlot. Do not assign numeric storage IDs manually.

Keep the strategic count guards in `community_strategy_packs.py`; the DUC plan should not become the owner of strategic policy.

- [ ] **Step 4: Verify the focused pass**

Run the same two test modules.

Expected: all new plan-order, resource/floor coverage, storage-binding, and lifecycle assertions pass.

- [ ] **Step 5: Run the affected integration check**

Run:

```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_strategy_camp_controller -v
```

Expected: existing camp controller geometry tests remain green and the DUC additions do not alter SN ownership.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/native_duc.py LearnerAI/Compiler/ir/strategy.py LearnerAI/Compiler/ir/camp_control.py LearnerAI/Compiler/tests/test_native_duc_plan.py LearnerAI/Compiler/tests/test_strategy_compiler_integration.py
git commit -m "feat: model Byzantine resource-front DUC placement"
```

---

### Task 2: Compile lumber, gold, and stone floors through the AIRef placement chain

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py`
- Modify: `LearnerAI/Compiler/ir/camp_control.py` only for placement-policy metadata if required by Task 1
- Test: `LearnerAI/Compiler/tests/test_strategy_camp_controller.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py`

**Interfaces:**
- Consumes: the existing `economy-<resource>-camp-floor-N` demands and their `ConstructionLifecycle`.
- Produces: deterministic DUC placement rules bound to each camp demand without changing strategic floor policy.

- [ ] **Step 1: Add the focused failing tests**

For every wood/gold/stone floor assert that the emitted demand retains:
  - `building-type-count-total < floor` for admissibility;
  - `can-build <camp>` for capability;
  - `building-type-count <camp> >= floor` as completion witness.

For DUC execution assert:

```lisp
(up-filter-status c: status-resource c: list-active)
(up-find-resource c: <resource> c: 40)
(up-compare-goal <remote-count> > <floor-1>)
(up-set-target-object search-remote c: <floor-1>)
(up-get-point position-object <point>)
(up-set-target-point <point>)
(up-build place-point 0 c: <camp>)
```

For floor 1, permit a search size of 1 where the existing opening path intentionally uses it. For floors 2-5 of gold/stone, require the 40-result remote search and zero-based index sequence 0,1,2,3.

Assert that floor 2 no longer uses the incorrect old pattern of `remote-count > 1` with `search-remote c: 1`.

- [ ] **Step 2: Verify the relevant failure**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_strategy_camp_controller LearnerAI.Compiler.tests.test_byzantine_artifact_wood_camps LearnerAI.Compiler.tests.test_byzantine_arabia_artifact -v
```

Expected: the new compiler-to-artifact placement assertions fail where the compiler still emits only generic `(build ...)` execution.

- [ ] **Step 3: Implement the minimum behavior**

Keep `community_strategy_packs.py` responsible for the strategic demand:

```text
resource active
+ floor not satisfied
+ build capability
→ camp demand
```

Do not embed resource coordinates or DUC mechanics directly into the strategy-pack function.

Attach the appropriate DUC placement rule identity to each floor's execution path. The DUC rule must consume the demand's current lifecycle admission and must not become an independent, always-on camp builder.

Preserve the existing opportunity-cost contract for stone. A valid stone resource object does not override the protected Castle trajectory floor except where the existing emergency posture explicitly permits it.

- [ ] **Step 4: Verify the focused pass**

Run the three focused test modules again.

Expected: all resource/floor coverage and zero-based indexing assertions pass.

- [ ] **Step 5: Run the affected integration check**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy -v
```

Expected: existing first-camp admission, Feudal banking, and stone-opportunity-cost tests remain green.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/community_strategy_packs.py LearnerAI/Compiler/ir/camp_control.py LearnerAI/Compiler/tests/test_strategy_camp_controller.py LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py
git commit -m "feat: bind Byzantine camp demands to resource-front placement"
```

---

### Task 3: Enforce pending, completion, and recovery semantics

**Files:**
- Modify: `LearnerAI/Compiler/ir/construction.py` only if a camp-specific placement phase needs an existing typed field rather than a new subsystem
- Modify: `LearnerAI/Compiler/semantic/analyzer.py` only if DUC placement needs to be validated against the existing `ConstructionLifecycle`
- Modify: `LearnerAI/Compiler/emitter/per.py` only where compiler-owned DUC placement must be ordered relative to construction lifecycle rules
- Test: `LearnerAI/Compiler/tests/test_compiler_native_integration.py`
- Test: existing construction lifecycle tests discovered under `LearnerAI/Compiler/tests/test_*construction*`

**Interfaces:**
- Consumes: `ConstructionLifecycle` with `pending_foundation_fact`, `pending_placement_fact`, and completed `building-type-count` witness; compiler-owned Native DUC rule plan.
- Produces: one bounded camp attempt, pending suppression, completion release, and retry on failure.

- [ ] **Step 1: Add the focused failing tests**

Cover these exact cases:

1. A pending mining camp blocks a second issuance for the same floor.
2. `building-type-count-total` is not accepted as a completion witness.
3. `building-type-count` releases the demand only after completion.
4. An empty remote search leaves the demand active.
5. An out-of-range `up-set-target-object` does not manufacture a new target.
6. A failed placement leaves the construction lifecycle retryable.
7. A later floor cannot fire while the earlier floor is still incomplete.

- [ ] **Step 2: Verify the relevant failure**

Run:

```bash
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "ConstructionLifecycle or NativeDuc" -v
```

Expected: new camp-specific lifecycle assertions fail before the placement/action ordering is wired.

- [ ] **Step 3: Implement the minimum lifecycle coupling**

Use the existing construction lifecycle instead of creating a separate camp-pending state.

The required semantic separation is:

```text
can-build
    = capability/admission

up-pending-objects
    = action in flight

building-type-count
    = completed world-state witness
```

A failed search or placement must preserve the strategic demand and permit a later retry. A successful issuance must move the demand into its existing pending state. A completed camp must release exactly that floor and allow the next floor to become admissible.

The first Dark Age lumber fallback remains distinct from DUC placement: it is a recovery path for opening continuity, not evidence that the resource-search chain succeeded.

- [ ] **Step 4: Verify the focused pass**

Run the affected construction and DUC tests.

Expected: pending, completion, failure, and retry cases pass.

- [ ] **Step 5: Run the affected integration check**

Run:

```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_byzantine_bot_build -v
```

Expected: canonical Byzantine construction and lifecycle emission remain valid.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/construction.py LearnerAI/Compiler/semantic/analyzer.py LearnerAI/Compiler/emitter/per.py LearnerAI/Compiler/tests/test_compiler_native_integration.py
git commit -m "fix: close Byzantine camp placement lifecycle semantics"
```

---

### Task 4: Make the checked-in Byzantine runtime artifact compiler-synchronized

**Files:**
- Modify: `tools/synchronize_byzantine_runtime.py`
- Modify: `Byzantine.per`
- Test: `LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py`

**Interfaces:**
- Consumes: freshly generated `dist/byzantine/Byzantine.per` containing the compiler-owned camp DUC plan.
- Produces: checked-in `Byzantine.per` with exactly one authoritative copy of each camp placement lifecycle.

- [ ] **Step 1: Add a synchronization test**

Assert that the synchronization path either:
  - copies the compiler-generated resource-front DUC rules into `Byzantine.per`, or
  - preserves an already identical block without churn.

Also assert that the script refuses to continue when a required generated camp rule is missing instead of silently leaving stale runtime behavior.

- [ ] **Step 2: Verify the relevant failure**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_byzantine_arabia_artifact LearnerAI.Compiler.tests.test_byzantine_artifact_wood_camps -v
```

Expected: synchronization ownership assertions fail until the runtime script knows the new resource-front block.

- [ ] **Step 3: Implement deterministic synchronization**

Add one named synchronization section for the compiler-owned resource-front DUC rules.

The synchronizer must:
  - identify the compiler-owned camp rules by deterministic markers;
  - replace an obsolete copy rather than append duplicates;
  - preserve unrelated runtime overlay rules;
  - preserve file line endings and avoid whole-file churn;
  - fail loudly if the generated artifact lacks any required wood/gold/stone floor;
  - leave the runtime artifact byte-stable on a second synchronization pass.

Do not reimplement the DUC policy in the synchronization script. The script copies/installs compiler output only.

- [ ] **Step 4: Verify the focused pass**

Run the synchronization twice.

Expected:
  - first run updates only the intended camp-placement blocks when required;
  - second run reports no change;
  - artifact tests remain green.

- [ ] **Step 5: Run native acceptance**

Run:

```bash
python LearnerAI/Compiler/tests/assert_native_zero.py Byzantine.per --report /tmp/native-reports/byzantine-checked-in-camps.json
```

Expected: zero native findings.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add tools/synchronize_byzantine_runtime.py Byzantine.per LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py
git commit -m "build: synchronize Byzantine resource-front camp rules"
```

---

### Task 5: Add deterministic regressions for indexing, storage, and geometry boundaries

**Files:**
- Modify/create: `LearnerAI/Compiler/tests/test_byzantine_resource_fronts.py` (proposed new focused fixture if the existing artifact tests become too broad)
- Modify: `LearnerAI/Compiler/tests/test_strategy_camp_controller.py`
- Modify: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`

**Interfaces:**
- Consumes: the compiler-owned camp DUC plan and checked-in artifact.
- Produces: regression coverage for every failure that previously produced missing camps or skipped resource fronts.

- [ ] **Step 1: Add exact edge-case tests**

Required cases:

| Case | Required result |
|---|---|
| floor 1 | select remote index 0 |
| floor 2 | require result count > 1, select index 1 |
| floor 3 | require result count > 2, select index 2 |
| floor 4 | require result count > 3, select index 3 |
| floor 5 | require result count > 4, select index 4 |
| no resource result | stay active, no target, no false completion |
| list full at 40 | do not select index 40 |
| stale target | reset/research before new dispatch |
| duplicate pass | deterministic rule set, no duplicate lifecycle |
| camp already pending | suppress duplicate issuance |
| camp complete | release current floor only |
| remote resource farther away | DUC point selection still owns location; SN controls placement envelope |

- [ ] **Step 2: Verify the relevant failure**

Run the new focused test module alone.

Expected: any missing edge semantics fail without affecting the rest of the compiler suite.

- [ ] **Step 3: Implement only missing guards**

Do not add new timers or generic controller loops to solve deterministic DUC state problems. Fix storage, rule ordering, zero-based index guards, or lifecycle coupling at the narrowest layer that owns the defect.

- [ ] **Step 4: Verify focused pass**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_byzantine_resource_fronts LearnerAI.Compiler.tests.test_strategy_camp_controller LearnerAI.Compiler.tests.test_strategy_opening_economy -v
```

Expected: all camp-front regression tests pass.

- [ ] **Step 5: Commit the regression gate**

```bash
git add LearnerAI/Compiler/tests/test_byzantine_resource_fronts.py LearnerAI/Compiler/tests/test_strategy_camp_controller.py LearnerAI/Compiler/tests/test_strategy_opening_economy.py
git commit -m "test: lock Byzantine resource-front camp boundaries"
```

---

### Task 6: Full compiler/native verification and Arabia runtime gate

**Files:**
- No source changes unless verification exposes a defect.
- Runtime artifact: `Byzantine.per`

**Interfaces:**
- Consumes: merged compiler + synchronized runtime artifact.
- Produces: verified main artifact suitable for Arabia runtime testing.

- [ ] **Step 1: Run the canonical build regression**

```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_byzantine_bot_build -v
```

Expected: success.

- [ ] **Step 2: Run focused camp and economy regressions**

```bash
python -m unittest LearnerAI.Compiler.tests.test_strategy_camp_controller -v
python -m unittest LearnerAI.Compiler.tests.test_byzantine_artifact_wood_camps -v
python -m unittest LearnerAI.Compiler.tests.test_byzantine_arabia_artifact -v
python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy -v
```

Expected: all pass.

- [ ] **Step 3: Run canonical synchronization**

```python
PYTHONPATH=LearnerAI python tools/build_byzantine_semantic_manifest.py --input Byzantine.per --output /tmp/byzantine-semantic-manifest.json
PYTHONPATH=LearnerAI python tools/build_byzantine_semantic_manifest.py --input Byzantine.per --output /tmp/byzantine-semantic-manifest-repeat.json
cmp /tmp/byzantine-semantic-manifest.json /tmp/byzantine-semantic-manifest-repeat.json
```

Expected: identical manifests.

- [ ] **Step 4: Run native acceptance**

```bash
python LearnerAI/Compiler/tests/assert_native_zero.py Byzantine.per --report /tmp/native-reports/byzantine-checked-in.json
python -c "import aoe2_ai_lab; print('aoe2-ai-parser import: OK')"
```

Expected: zero findings and successful parser import.

- [ ] **Step 5: Run the full compiler regression**

```bash
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"
```

Expected: complete compiler suite passes.

- [ ] **Step 6: Runtime gate**

Test on standard Arabia with no artificial placement assistance.

Record, at minimum:
  - first lumber camp is placed;
  - first gold camp is placed;
  - later lumber/gold fronts cause new camps rather than repeated attempts at the original camp;
  - new gold and stone camps appear when the corresponding floor becomes admissible;
  - no duplicate camp spam while a foundation is pending;
  - camp placement does not consume the Castle transition bank improperly;
  - the bot still reaches Feudal/Castle on the established Arabia baseline;
  - no regression to Arena Fast Castle.

The runtime result is a witness, not a substitute for the compiler/native gates.

- [ ] **Step 7: Final merge gate**

Do not call the work complete until the main-branch workflow reports success for:
  - canonical build;
  - runtime synchronization;
  - deterministic semantic shadow;
  - native zero-findings for generated and checked-in `Byzantine.per`;
  - focused camp/geometry regressions;
  - parser import;
  - full compiler regression;
  - required cross-platform native-support comparison.

---

> **Implementation status (2026-10-08):** Compiler-side AIRef resource-front placement has been implemented on `main`; the remaining gate is the post-merge canonical build, runtime synchronization, native zero-findings, and runtime witness.

## Definition of Done

The implementation is complete only when all of the following are true:

1. Every wood/gold/stone camp floor has a compiler-owned AIRef DUC placement path.
2. Resource-object selection is zero-based and index-safe.
3. `dropsite-min-distance` is used only as a distance observation, never as the resource selector.
4. Point capture and point placement use the AIRef chain:
   `up-set-target-object → up-get-point → up-set-target-point → up-build place-point`.
5. Camp completion is witnessed by completed building state, not pending/total count.
6. Failed searches and failed placements retain the demand for retry.
7. No compiler-owned camp rule contains hard-coded Goal IDs.
8. Strategic Number camp geometry remains owned by `camp_control.py`.
9. The synchronized `Byzantine.per` contains one authoritative copy of each camp lifecycle.
10. Native zero-findings and parser checks remain clean.
11. Arabia runtime demonstrates continued camp expansion without regressing the already repaired Arabia/Arena age-up behavior.

## Unresolved Product Decisions

None are required to begin implementation. The existing Byzantine policy already defines the camp floors, opening priorities, stone opportunity-cost protection, and Strategic Number ownership. The remaining work is implementation and verification of the AIRef-native execution path.
