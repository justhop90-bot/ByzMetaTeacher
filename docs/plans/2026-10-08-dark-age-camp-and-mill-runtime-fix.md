# Dark Age Camp and Mill Runtime Liveness Fix Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore reliable Dark Age lumber-camp and mill execution by isolating compiler-owned camp DUC storage from the hybrid Byzantine runtime namespace and locking an explicit early-economy liveness contract.

**Architecture:** Keep strategic camp ownership and existing construction lifecycles unchanged. Fix the synchronization boundary so compiler-generated DUC search-state and point spans are deterministically relocated when they collide with pre-existing `Byzantine.per` Goal storage, then add a narrow Dark Age economy regression/safety valve around first lumber and first mill issuance without creating a second scheduler.

**Tech Stack:** Python 3, `unittest`, typed compiler IR, runtime synchronization script, AoE2 UP/.per, checked-in `Byzantine.per`, GitHub Actions compiler/native gates.

## Global Constraints

- Do not modify the working house lifecycle.
- Do not replace the native camp DUC architecture or create a second camp controller.
- No hard-coded compiler Goal IDs may be introduced.
- Compiler-owned DUC output spans must not overlap any pre-existing hybrid-runtime Goal slot, GoalSpan, point pair, or search-state span.
- `can-build` remains capability/admission evidence; `up-pending-objects` remains in-flight evidence; `building-type-count` remains completion evidence.
- First Dark Age lumber and mill actions must remain retryable and must not release demand from action issuance alone.
- The checked-in `Byzantine.per` must be synchronized from compiler output and remain byte-stable on a second synchronization pass.
- Runtime testing is the final behavioral witness. Compiler and native checks are necessary but do not substitute for the game runtime.

---

### Task 1: Prove the current camp DUC namespace collision

**Files:**
- Modify: `LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py`

**Interfaces:**
- Consumes: checked-in `Byzantine.per`.
- Produces: a deterministic assertion that compiler-owned camp DUC storage does not overlap existing hybrid runtime storage.

- [ ] **Step 1: Add the focused failing test**

Parse `defconst` values plus DUC commands in the checked-in artifact. Extract:
- `up-get-search-state` spans of width 4.
- `up-get-point position-object` spans of width 2.

Build occupied runtime intervals from the artifact's existing Goal/point/search-state uses and assert every compiler-owned camp DUC interval is disjoint.

Also assert the known current bad ranges are rejected, including the first wood search span overlapping Goal 468..471.

- [ ] **Step 2: Verify red**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_byzantine_artifact_wood_camps -v
```

Expected: the new collision assertion fails on the current artifact because the first camp DUC search span overlaps existing Byzantine wall-controller storage.

- [ ] **Step 3: Commit the red test**

```bash
git add LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py
git commit -m "test: expose Byzantine camp DUC storage collision"
```

---

### Task 2: Relocate compiler-owned camp DUC storage during hybrid synchronization

**Files:**
- Modify: `tools/synchronize_byzantine_runtime.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py`

**Interfaces:**
- Consumes: generated `Byzantine.per` camp DUC rules and the pre-existing hybrid runtime artifact.
- Produces: a deterministic camp DUC block whose Goal spans are disjoint from runtime-owned storage.

- [ ] **Step 1: Add synchronizer-focused assertions**

Require synchronization to preserve:
- search-state width 4;
- point-pair width 2;
- deterministic one-to-one remapping;
- zero overlap with runtime storage;
- stable output on a second synchronization pass.

- [ ] **Step 2: Verify red**

Run the focused artifact/synchronizer test.

Expected: collision or missing remap assertion fails before implementation.

- [ ] **Step 3: Implement minimum relocation**

Add a helper that:
1. extracts all compiler-owned camp `up-get-search-state N` and `up-get-point position-object N` outputs from the generated camp block;
2. constructs deterministic occupied intervals from the runtime overlay;
3. allocates free spans from the upper Goal range downward;
4. reserves each allocated span before choosing the next span;
5. rewrites only numeric references belonging to those original spans inside the camp DUC block;
6. leaves all non-camp runtime state untouched.

The relocation must occur before `_replace_resource_camp_section()` installs the generated camp block. Voice remapping must continue to run afterward so it sees the newly installed camp allocations.

- [ ] **Step 4: Verify focused green**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_byzantine_artifact_wood_camps -v
```

Expected: collision tests pass, remapping is deterministic, and a second synchronization produces no further changes.

- [ ] **Step 5: Commit**

```bash
git add tools/synchronize_byzantine_runtime.py LearnerAI/Compiler/tests/test_byzantine_artifact_wood_camps.py
git commit -m "fix: isolate camp DUC storage from Byzantine runtime Goals"
```

---

### Task 3: Lock Dark Age lumber and mill liveness

**Files:**
- Modify: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`
- Modify: `LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py`
- Modify: `Byzantine.per` only through the synchronization path if an explicit runtime safety-valve rule is required.

**Interfaces:**
- Consumes: existing first lumber demand/fallback, existing first mill demand/executor, Feudal transition demand.
- Produces: an explicit regression proving the opening cannot stall before the first lumber camp and mill are both available for the Feudal economy.

- [ ] **Step 1: Add failing liveness assertions**

Assert the canonical artifact contains:
- a Dark Age first-lumber issuance/recovery path with `can-build lumber-camp`, `resource-found wood`, and a completion witness;
- a Dark Age first-mill issuance path with `can-build mill`, a valid food-front witness, and a completion witness;
- Feudal research remains independently gated by `can-research-with-escrow feudal-age`, not by a stale camp or mill Goal.

Add a regression fixture that would fail if both first lumber and first mill issuance are absent while the bot remains Dark Age.

- [ ] **Step 2: Verify red**

Run:

```bash
python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy LearnerAI.Compiler.tests.test_byzantine_arabia_artifact -v
```

Expected: the new liveness assertion fails against the current artifact if the first-build dependency chain is not guaranteed.

- [ ] **Step 3: Implement the narrowest missing behavior**

First, retest after the DUC storage relocation. If the existing lumber fallback and first-mill executor become live again, do not add redundant policy.

If the mill remains unissuable in Dark Age because the existing distance guard is too strict, add one narrow Dark Age first-mill safety valve in the same existing economy/runtime section with:
- Dark Age;
- zero completed mills;
- valid food resource witness;
- `can-build mill`;
- no pending mill;
- build-pass arbitration clear;
- minimum food-source/front evidence;
- normal `build mill` action;
- existing demand state advanced to pending.

Do not alter the second-mill DUC path or Castle/Imperial mill policy.

- [ ] **Step 4: Verify focused green**

Run the two opening/economy test modules and confirm the generated artifact still contains the existing second-mill forage-search lifecycle.

- [ ] **Step 5: Commit**

```bash
git add LearnerAI/Compiler/tests/test_strategy_opening_economy.py LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py Byzantine.per tools/synchronize_byzantine_runtime.py
git commit -m "fix: restore Dark Age lumber and mill liveness"
```

---

### Task 4: Regenerate and validate the runtime artifact

**Files:**
- `Byzantine.per`
- `dist/byzantine/Byzantine.per` if generated by the canonical build
- existing synchronization/build scripts

**Interfaces:**
- Consumes: canonical compiler output plus hybrid runtime overlay.
- Produces: checked-in `Byzantine.per` suitable for runtime testing.

- [ ] **Step 1: Run synchronization/build**

Run the repository's canonical Byzantine build/synchronization path used by CI.

Expected: generated and checked-in artifacts are synchronized without duplicate camp DUC blocks.

- [ ] **Step 2: Verify parser/native gates**

Run the focused native zero-findings and parser checks used by the repository.

Expected: zero native findings and successful parser import.

- [ ] **Step 3: Verify deterministic rebuild**

Run the canonical Byzantine build twice and compare outputs.

Expected: byte-identical output.

- [ ] **Step 4: Commit generated artifact**

Only after the verification above, commit the regenerated checked-in artifact.

---

### Task 5: Runtime-test gate

**Files:**
- No source changes unless runtime evidence identifies a second causal defect.

- [ ] **Step 1: Run focused compiler regression**

```bash
python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy LearnerAI.Compiler.tests.test_strategy_camp_controller LearnerAI.Compiler.tests.test_byzantine_artifact_wood_camps LearnerAI.Compiler.tests.test_byzantine_arabia_artifact -v
```

Expected: zero failures.

- [ ] **Step 2: Run full compiler regression and native acceptance**

Use the repository's canonical full compiler, generated-artifact, checked-in-artifact, parser, and native zero-findings commands.

- [ ] **Step 3: Runtime witness on standard Arabia**

Record:
- first lumber camp appears early;
- first mill appears early;
- villagers continue producing until the intentional Feudal transition bank;
- Feudal is actually clicked;
- no camp DUC storage corruption is observed;
- no regression to the known-good Arabia Castle timing envelope.

- [ ] **Step 4: Runtime follow-through**

Only after Dark Age liveness is restored, retest Arena Fast Castle and the established water-map regression separately. Do not conflate those scenarios with the Arabia opening fix.

---

## Definition of Done

The fix is complete only when:
- camp DUC storage has no overlap with hybrid runtime storage;
- first lumber and first mill have a witnessed Dark Age path;
- Feudal transition is not blocked by stale camp/mill lifecycle state;
- checked-in `Byzantine.per` is synchronized and deterministic;
- focused and full compiler/native checks pass;
- and the Arabia runtime reaches Feudal with the first lumber and mill built.
