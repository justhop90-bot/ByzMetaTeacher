# Strategic Number Semantics Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a typed, source-ordered Strategic Number mutation model with faithful UserPatch arithmetic, recurrent same-pass visibility, dependency diagnostics, hostile tests, and native-parser acceptance.

**Architecture:** Keep the new semantics in two focused layers. The IR module represents native SN mutations and operand dependencies; the semantic module parses/validates expressions and evaluates them. Existing persistent-state analysis consumes the semantic access view, while the recurrent scheduler reuses the same evaluator for runtime visibility tests.

**Tech Stack:** Python 3.11+, unittest, existing Compiler IR/semantic modules, pinned `aoe2-ai-parser` native lint in GitHub Actions.

## Global Constraints

- Generic compiler only; do not modify or depend on strategy/Basilisk runtime behavior.
- Preserve `c:`, `g:`, and `s:` operand typing exactly.
- Preserve action order and same-pass visibility.
- Fail closed on malformed SN expressions.
- Keep native validation deterministic and attached to compiler CI.
- Do not reinterpret `min`/`max` from legacy descriptions; use corrected UserPatch semantics.
- Do not claim repository-wide success from unrelated validator workflows.

---

### Task 1: Add typed Strategic Number IR and semantic parser

**Files:**
- Create: `LearnerAI/Compiler/ir/strategic_number.py`
- Create: `LearnerAI/Compiler/semantic/strategic_number_semantics.py`
- Modify: `LearnerAI/Compiler/ir/__init__.py`
- Modify: `LearnerAI/Compiler/semantic/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_strategic_number_semantics.py`

**Interfaces:**
- Consumes: `Expression`, `EffectiveRule`, native operator text.
- Produces: `StrategicNumberMutation`, `StrategicNumberOperand`, `StrategicNumberDependency`, `parse_strategic_number_mutation()`, `analyze_strategic_number_expressions()`, `evaluate_strategic_number_mutation()`.

- [ ] **Step 1: Add the focused failing tests**
  - Parse assignment, arithmetic, min/max, negation, percentage operators.
  - Assert `c:` yields CONSTANT, `g:` yields GOAL, `s:` yields STRATEGIC_NUMBER.
  - Reject bad arity, unknown operator, malformed numeric constant, invalid prefix, and constant zero divisor.
  - Assert dependency records for Goal/SN operands.

- [ ] **Step 2: Verify the relevant failure**
  - Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_number_semantics`
  - Expected: import/attribute failures proving the new typed interface is absent.

- [ ] **Step 3: Implement the minimum behavior**
  - Define the enums/dataclasses.
  - Parse native `up-modify-sn` and `set-strategic-number`.
  - Validate 16-bit literal/defconst operand bounds; Goal/SN state values remain signed 32-bit.
  - Map all 12 native math operators.
  - Implement engine-compatible evaluator using integer arithmetic and explicit zero-divisor handling.
  - Keep dynamic Goal/SN divisors runtime-valid but statically unknown.

- [ ] **Step 4: Verify the focused pass**
  - Run the focused unittest command.
  - Expected: all parser/operator/dependency tests pass.

- [ ] **Step 5: Run the affected compiler tests**
  - Run: `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"`
  - Expected: existing suite plus new SN tests pass.

- [ ] **Step 6: Commit the passing deliverable**
  - Commit: `feat(compiler): add typed strategic number semantics`

---

### Task 2: Integrate SN dependencies with persistent-state and recurrent scheduler

**Files:**
- Modify: `LearnerAI/Compiler/semantic/persistent_state.py`
- Modify: `LearnerAI/Compiler/semantic/pass_scheduler.py`
- Test: `LearnerAI/Compiler/tests/test_strategic_number_scheduler.py`

**Interfaces:**
- Consumes: `StrategicNumberMutation` and existing `PersistentStateAccess`.
- Produces: same-pass SN state mutation and explicit target/dependency access records.

- [ ] **Step 1: Add the focused failing tests**
  - Rule 1 modifies SN; Rule 2 reads SN and fires in the same pass.
  - `min/max`, `/`, `z/`, `%*`, `%/` operate through the scheduler using the same evaluator.
  - Goal-to-SN and SN-to-SN dependencies are visible at action execution time.
  - A modification with a source state written later in the same rule is rejected by semantic ordering.

- [ ] **Step 2: Verify the relevant failure**
  - Run the focused scheduler unittest.
  - Expected: unsupported scheduler fact/action errors or missing typed dependencies.

- [ ] **Step 3: Implement the minimum behavior**
  - Add SN/Goal stores to `PassScheduler`.
  - Evaluate `strategic-number` and `up-compare-sn`.
  - Apply `set-strategic-number` and `up-modify-sn` sequentially.
  - Reuse the semantic evaluator, never duplicate operator logic.
  - Preserve timer/jump/self-disable behavior.
  - Extend persistent-state extraction so `up-modify-sn` is a target writer plus explicit source dependency.

- [ ] **Step 4: Verify the focused pass**
  - Run the focused scheduler/order tests.
  - Expected: all same-pass and dependency cases pass.

- [ ] **Step 5: Run the affected compiler tests**
  - Run the full compiler unittest suite.
  - Expected: no regressions.

- [ ] **Step 6: Commit the passing deliverable**
  - Commit: `feat(compiler): integrate strategic number pass semantics`

---

### Task 3: Add hostile native fixture and CI gate

**Files:**
- Create: `LearnerAI/Compiler/tests/assert_strategic_number_native.py`
- Create: `LearnerAI/Compiler/tests/fixtures/strategic_number.per`
- Modify: `.github/workflows/compiler-tests.yml`
- Test: `LearnerAI/Compiler/tests/test_strategic_number_native.py`

**Interfaces:**
- Consumes: checked-in SN fixture and pinned `aoe2_ai_lab` validator.
- Produces: deterministic `.per` fixture and zero-findings native validation report.

- [ ] **Step 1: Add the failing native acceptance test**
  - Generate rules covering all operators, c/g/s operands, negative values, sequential mutations, and guarded reads.
  - Assert the fixture is deterministic.
  - Assert the native validator reports zero findings when the pinned parser is installed.

- [ ] **Step 2: Verify the relevant failure**
  - Run the fixture/unit test before workflow integration.
  - Expected: missing fixture/semantic support failures identify unsupported constructs.

- [ ] **Step 3: Implement the native gate**
  - Generate the fixture from checked-in source text.
  - Run `python -m aoe2_ai_lab lint <fixture> --profile default --json`.
  - Fail on nonzero exit, malformed JSON, or nonzero finding count.
  - Add one compiler workflow step after the existing generic fixture native gate.
  - Generate the fixture deterministically and reject stale checked-in fixture content.
  - Upload the fixture and report with existing native evidence.

- [ ] **Step 4: Verify the native pass**
  - Run the dedicated script where the pinned parser is installed.
  - Expected: JSON `finding_count=0`.
  - Run the full compiler unittest suite.

- [ ] **Step 5: Commit the passing deliverable**
  - Commit: `test(compiler): add strategic number native acceptance gate`

---

### Task 4: Finalize semantic invariants and documentation

**Files:**
- Modify: `docs/specs/2026-09-26-strategic-number-semantics-design.md`
- Create: `docs/plans/2026-09-26-strategic-number-semantics.md`

**Interfaces:**
- Consumes: final implementation interfaces and verification results.
- Produces: design and plan records matching the final code.

- [ ] **Step 1: Reconcile the design and implementation**
  - Record any final naming changes while preserving the approved semantic contract.

- [ ] **Step 2: Self-review**
  - Check specification coverage, placeholders, contradictions, and interface-name consistency.

- [ ] **Step 3: Verify documentation references**
  - Confirm all paths and exported names exist.

- [ ] **Step 4: Commit passing documentation**
  - Commit: `docs(compiler): finalize strategic number semantics`

---
