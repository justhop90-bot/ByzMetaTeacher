# Strategic Number Controller Arbitration Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a typed Strategic Number arbitration layer that deterministically mediates shared native SN ownership across age, strategy, temporary, action, and recovery controllers without turning the compiler into a runtime scheduler.

**Architecture:** Keep `StrategicNumberMode` as the existing strategy-facing input. Normalize modes and new override declarations into `StrategicNumberArbitrationPlan`, validate ownership/lifetime/conflict invariants in a dedicated semantic module, then lower the plan into the existing `NativeControlPlan` plus narrow action attachments. Physical native SN storage remains one slot per documented SN ID.

**Tech Stack:** Python 3, immutable dataclasses, existing AST `Expression`, `NativeControlPlan`, native command registry, unittest, GitHub Actions native zero-findings and deterministic compiler gates.

## Global Constraints

The compiler must remain fail-closed for undocumented native SN IDs. Precedence is fixed and cannot be user-configured. Multiple controllers may target one physical SN, but only one highest-precedence compatible controller may be effective at a time. Lower controllers resume by reasserting their current intent after a higher controller releases; the compiler must never pretend it captured and can restore a historical runtime value. Action-scoped SN writes remain separate from the dedicated attack lifecycle contract. Timer cadence is never treated as world-state completion. Lowering must be deterministic and must not depend on source declaration order for semantics.

---

### Task 1: Add the arbitration IR and focused contract tests

**Files:**
- Create: `LearnerAI/Compiler/ir/strategic_number_arbitration.py`
- Modify: `LearnerAI/Compiler/ir/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_strategic_number_arbitration.py`

**Interfaces:**
- Produces `StrategicNumberControllerLayer`, `StrategicNumberControllerScope`, `StrategicNumberRestorationPolicy`, `StrategicNumberReleaseEvidence`, `StrategicNumberController`, `StrategicNumberActionAttachment`, and `StrategicNumberArbitrationPlan`.
- `StrategicNumberArbitrationPlan.controllers_for_sn()` groups controllers by physical SN ID.
- Derived names use one physical `sn-native-{id}` storage name and deterministic activation-state names for non-persistent controllers.

- [ ] **Step 1: Add the failing tests**
  - Assert fixed precedence is RECOVERY > ACTION > TEMPORARY > STRATEGY > AGE_BASE > DEFAULT_BASE.
  - Assert invalid layer/scope/release/action combinations raise `ValueError`.
  - Assert only one physical SN identity exists even when several controllers target the same SN.
  - Assert action attachments require exact action identities.
  - Assert controller ordering is deterministic.
  - Assert same-layer equal-priority conflicting values are rejected at plan validation time.

- [ ] **Step 2: Verify the relevant failure**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_arbitration -v`
  Expected: import/API failures because the new arbitration types do not yet exist.

- [ ] **Step 3: Implement the minimum IR**
  Add immutable enums/dataclasses, structural validation, deterministic precedence, controller lookup/grouping, and action attachment identity rules. Keep semantic overlap validation out of the dataclass layer.

- [ ] **Step 4: Verify the focused pass**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_arbitration -v`
  Expected: all IR contract tests pass.

- [ ] **Step 5: Run the affected integration check**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_native_control_plane -v`
  Expected: existing native-control tests remain green.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `feat: add Strategic Number arbitration IR`

### Task 2: Normalize strategy SN modes and implement semantic arbitration validation

**Files:**
- Create: `LearnerAI/Compiler/semantic/strategic_number_arbitration.py`
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Modify: `LearnerAI/Compiler/semantic/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_strategic_number_arbitration.py`

**Interfaces:**
- `strategic_number_mode_to_controller(mode, profile_id)` converts existing age modes to AGE_BASE controllers and posture modes to STRATEGY controllers.
- `build_strategic_number_arbitration_plan(profile, extra_controllers=())` returns a canonical `StrategicNumberArbitrationPlan`.
- `validate_strategic_number_arbitration(plan, documented_native_ids, action_identities=())` validates cross-controller semantics.

- [ ] **Step 1: Add failing normalization/validation tests**
  - Existing Byzantine age modes normalize to AGE_BASE.
  - Existing posture modes normalize to STRATEGY.
  - Same-SN different-layer overlap is allowed.
  - Same-layer equal-priority incompatible overlap is rejected.
  - Equal-value same-layer overlap is coalesced.
  - Temporary/action/recovery controllers require release guards.
  - Persistent underlay controllers cannot have release guards.
  - ACTION controllers require an exact known action identity.
  - Undocumented SN IDs fail closed.

- [ ] **Step 2: Verify the expected failure**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_arbitration -v`
  Expected: missing normalization/validation API failures.

- [ ] **Step 3: Implement semantic validation**
  Normalize existing `StrategicNumberMode` records without breaking their public shape. Use conservative activation-domain overlap rules based on existing deterministic age/posture guards. Group conflict checks by physical SN and effective layer/priority. Coalesce identical claims.

- [ ] **Step 4: Verify the focused pass**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_arbitration -v`
  Expected: all normalization/validation tests pass.

- [ ] **Step 5: Run existing SN regressions**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_sn_modes -v`
  Expected: existing 1,333-test-era SN behavior remains unchanged.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `feat: validate Strategic Number controller arbitration`

### Task 3: Lower arbitration into the existing native control plane

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Modify: `LearnerAI/Compiler/semantic/native_control.py`
- Modify: `LearnerAI/Compiler/compiler.py` only if a validation-threading seam is required
- Modify: `LearnerAI/Compiler/emitter/per.py` only if action attachment output requires an existing emission seam
- Test: `LearnerAI/Compiler/tests/test_strategic_number_arbitration.py`

**Interfaces:**
- `lower_strategic_number_arbitration(plan, profile_id, documented_native_ids, action_identities=())` returns `StrategicNumberArbitrationLowering`.
- Persistent controllers lower to guarded `set-strategic-number` rules.
- Non-persistent controllers receive persistent activation Goal state and explicit release rules.
- Lower-priority controllers are suppressed by higher-priority activation conditions and active-state Facts, avoiding reliance on same-pass Goal visibility.
- Action attachments remain a separate output consumed only by an existing dedicated action-lowering boundary.

- [ ] **Step 1: Add failing lowering tests**
  - Higher-precedence controller suppresses lower-precedence write.
  - Activation guard suppression works on the activation pass itself.
  - Releasing a controller does not emit a stale captured-value restore.
  - Current underlay is reasserted after release.
  - Underlay changes while an override is active are reflected after release.
  - One physical native state is emitted per SN.
  - Deterministic rule order is identical for reordered input declarations.

- [ ] **Step 2: Verify red**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_arbitration -v`
  Expected: lowering API or expected-plan assertion failures.

- [ ] **Step 3: Implement lowering**
  Construct native guards using existing binary logical-folding rules. Allocate only the necessary Goal activation states. Generate release rules and guarded SN writes. Keep action attachment generation separate from generic `NativeControlPlan` actions.

- [ ] **Step 4: Verify green**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_arbitration -v`
  Expected: all focused lowering tests pass.

- [ ] **Step 5: Run compiler/native regressions**
  Run: `python -m unittest LearnerAI.Compiler.tests.test_native_control_plane LearnerAI.Compiler.tests.test_strategy_sn_modes -v`
  Expected: existing native-control and SN-mode suites remain green.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `feat: lower Strategic Number arbitration into native control`

### Task 4: Add the integrated Byzantine acceptance fixture

**Files:**
- Create: `LearnerAI/Compiler/tests/assert_strategy_sn_arbitration_native.py`
- Modify: `.github/workflows/compiler-tests.yml`
- Test: existing `test_strategic_number_arbitration.py`

**Interfaces:**
- Fixture uses documented SN 227 with AGE_BASE, STRATEGY, TEMPORARY, and ACTION ownership.
- Fixture checks deterministic bytes, one physical SN alias, ownership suppression, restoration to the current underlay, and no compiler-owned zero initialization.
- Native acceptance runs `aoe2_ai_lab lint --profile default --json` and requires `finding_count == 0` and `findings == []`.

- [ ] **Step 1: Add the failing acceptance assertions**
  Require the expected 75/50/25/100 controller rules, current-underlay restoration semantics, deterministic output, and zero-findings result.

- [ ] **Step 2: Verify red**
  Run: `python LearnerAI/Compiler/tests/assert_strategy_sn_arbitration_native.py --output /tmp/strategic-number-arbitration.per --report /tmp/strategic-number-arbitration.json`
  Expected: fixture assertions fail until the arbitration lowering is integrated.

- [ ] **Step 3: Implement fixture/workflow**
  Compile the real Byzantine Castle strategy twice and add one explicit temporary/action controller fixture path without weakening the existing attack lifecycle boundary.

- [ ] **Step 4: Verify green**
  Run the fixture command above.
  Expected: deterministic artifact, `finding_count == 0`, empty findings.

- [ ] **Step 5: Run final project regression**
  Run: `python -m unittest discover -s LearnerAI/Compiler/tests -p 'test_*.py' -v`
  Expected: complete focused compiler suite passes.

- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `test: add native Strategic Number arbitration acceptance`

---

## Unresolved product decisions

None for this slice. Precedence, lifetime, restoration, action-scoping, and evidence semantics are fixed by the design above.
