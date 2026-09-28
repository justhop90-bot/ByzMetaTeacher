# Native Controller Semantics Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first typed, evidence-backed Native Controller Graph so the compiler can represent the native AI subsystems controlled by persistent `.per` state without pretending community practice is executable engine fact.

**Architecture:** Introduce a small semantic catalog that separates native control surfaces such as Strategic Numbers, timers, and direct control commands from the higher-level native controllers they influence. The catalog records controller domains, control-surface ownership, community/evidence status, and explicitly evidenced controller-to-controller interactions. It is descriptive and fail-closed: it does not alter lowering or invent a scheduler.

**Tech Stack:** Python 3.11-3.13, dataclasses/enums, unittest, existing compiler semantic registry conventions, GitHub Actions compiler gate.

## Global Constraints

- The native AoE2 engine remains runtime authority.
- AIRef/native parser evidence outranks community practice; community practice cannot by itself create executable native semantics.
- Do not add source-language syntax.
- Do not create a generic scheduler or simulator.
- Do not collapse Strategic Numbers, Goals, Timers, DUC state, and native controller state into one generic variable model.
- Preserve deterministic ordering and fail-closed validation.
- Keep the new catalog independent from client-specific Byzantine strategy.
- The initial controller interaction set is evidence-backed and intentionally incomplete.
- The tranche must not promote evidence-only controller relationships to executable support.

---

### Task 1: Establish the Native Controller Graph contract

**Files:**
- Create: `LearnerAI/Compiler/semantic/native_controller.py`
- Test: `LearnerAI/Compiler/tests/test_native_controller_semantics.py`
- Modify: `LearnerAI/Compiler/semantic/__init__.py`

**Interfaces:**
- Produces `NativeControllerDomain`, `NativeControlSurfaceKind`, `NativeControllerRelation`.
- Produces immutable `NativeController`, `NativeControlSurface`, `NativeControllerEdge`, and `NativeControllerCatalog`.
- Produces `default_native_controller_catalog()`.
- Produces `NativeControllerCatalog.resolve_surface(kind, native_identifier)`, `controller(controller_id)`, and `validate()`.
- Produces `NativeControllerCatalog.require_executable_surface(...)`, which must reject non-contractual/evidence-only control surfaces.

- [x] **Step 1: Add the focused failing tests**

Add tests for:
1. seeded Strategic Number surface resolution;
2. duplicate controller rejection;
3. duplicate control-surface rejection;
4. edge references to unknown controllers rejection;
5. self-interaction rejection;
6. evidence-only surfaces rejected by the executable gate;
7. deterministic catalog ordering/fingerprint representation;
8. expected controller relationships such as attack-group control requiring exploration and town-size control affecting attack targeting.

- [x] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI/Compiler/tests/test_native_controller_semantics.py`

Expected: import failure for the not-yet-created `Compiler.semantic.native_controller` module. This is the intended red state, not a setup failure.

- [x] **Step 3: Implement the minimum behavior**

Implement typed enums/dataclasses, reference validation, deterministic tuple ordering, surface lookup, and the executable-support fail-closed gate. Allow feedback/control graphs to remain cyclic at the controller level, but reject self-edges and unknown references.

- [x] **Step 4: Verify the focused pass**

Run the same focused command.

Expected: all Native Controller Graph tests pass.

- [x] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI/Compiler/tests/test_community_engine.py`

Expected: existing community-engine tests remain green and importing the new semantic module causes no cycle.

- [x] **Step 6: Commit the passing deliverable**

Commit message: `feat(compiler): add native controller graph substrate`

---

### Task 2: Cross-reference and seed the first community controller corpus

**Files:**
- Modify: `LearnerAI/Compiler/semantic/native_controller.py`
- Modify: `LearnerAI/Compiler/semantic/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_native_controller_semantics.py`
- Create: `LearnerAI/Compiler/NATIVE_CONTROLLER_SEMANTICS_CHECKLIST_2026-09-28.md`

**Interfaces:**
- Extends `default_native_controller_catalog()` with evidence-backed controller/surface records.
- Preserves `PracticeStatus.EVIDENCE_ONLY` for community-derived relationships until a native semantic contract exists.
- Keeps every seeded surface attributable to explicit AIRef/community sources.

Seed:
- civilian task allocation;
- exploration control;
- attack-group control;
- town-size defense/targeting;
- resource/escrow control;
- DUC search-state control.

Use only surfaces that are directly evidenced by the consulted AIRef/community material, including named SNs, `attack-now`, escrow controls, and DUC search/reset/search-state commands. Do not infer undocumented coupling merely because two values appear in the same script.

- [x] **Step 1: Add failing seed assertions**

Assert exact seeded controller IDs, representative surface IDs, evidence status, and the two initially contracted interaction claims.

- [x] **Step 2: Verify red**

Run the focused Native Controller Graph test.

Expected: seed lookup assertions fail because the catalog currently lacks the corpus.

- [x] **Step 3: Implement the corpus**

Add the evidence-backed records and sources. Store relationship evidence independently from controller evidence so a community interaction does not accidentally promote the underlying native command.

- [x] **Step 4: Verify focused green**

Run the focused Native Controller Graph test.

Expected: all seed and validation assertions pass.

- [x] **Step 5: Update the semantic gap/checklist**

Cross-reference:
- AIRef Strategic Numbers index;
- AIRef performance/reference resources;
- UserPatch scripting reference;
- lewisc64/aoe2ai;
- Niek/The Duke;
- attack-group community documentation.

Mark the controller graph as SUBSTRATE IMPLEMENTED / CONTROLLER CORPUS PARTIAL, not complete.

- [x] **Step 6: Commit the passing deliverable**

Commit message: `docs(compiler): record native controller semantic corpus`

---

### Task 3: Connect the controller graph to Strategic Number semantic analysis without changing lowering

**Files:**
- Modify: `LearnerAI/Compiler/semantic/strategic_number_semantics.py`
- Modify: `LearnerAI/Compiler/semantic/rule_diagnostics.py`
- Test: `LearnerAI/Compiler/tests/test_strategic_number_semantics.py`
- Test: `LearnerAI/Compiler/tests/test_rule_diagnostics.py`

**Interfaces:**
- Adds a deterministic controller-surface resolution step for parsed Strategic Number accesses.
- Produces controller identity metadata for resolved surfaces.
- Produces deterministic controller-binding metadata for known surfaces. Evidence-only status is carried in the binding metadata and does not create a new warning class or alter ordinary native compilation.
- Unknown SN identifiers remain governed by the existing native/schema diagnostics.

- [x] **Step 1: Add failing integration assertions**

Verify that known SN writes such as `sn-number-explore-groups` resolve to the exploration controller and that `sn-maximum-town-size` resolves to the town-size controller.

Verify that the diagnostic path distinguishes:
`known native surface + evidence-only controller semantics`
from
`unknown native identifier`.

- [x] **Step 2: Verify red**

Run focused Strategic Number and rule-diagnostics tests.

Expected: the new controller-binding assertions fail because no controller metadata is produced.

- [x] **Step 3: Implement the resolver hookup**

Keep controller binding metadata orthogonal to mutation/comparison semantics. Do not change evaluation of SN arithmetic or rule-order diagnostics. Do not make evidence-only relationships block ordinary native .per compilation.

- [x] **Step 4: Verify focused green**

Run the two focused test files.

Expected: existing SN semantics stay green and the new controller metadata/diagnostic behavior is deterministic.

- [x] **Step 5: Run the full compiler regression suite**

Run: `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"`

Expected: zero failures.

- [x] **Step 6: Commit the passing deliverable**

Commit message: `feat(compiler): bind strategic-number state to native controllers`

---

### Task 4: Verify the tranche against native and community boundaries

**Files:**
- Modify: `LearnerAI/Compiler/README.md`
- Modify: `LearnerAI/Compiler/COMMUNITY_PER_PRACTICE_SPEC.md`
- Modify: `LearnerAI/Compiler/NATIVE_PER_SEMANTIC_GAP_MAP_2026-09-26.md`
- Test: existing compiler regression suite

**Interfaces:**
- Documentation states that Native Controller Semantics is the control-plane layer between native state effects and recurrent execution semantics.
- Documentation explicitly distinguishes controller knowledge from executable native mappings.
- Gap map records DUC, attack, economy, exploration, defense, and SN-controller interactions as the next expansion corpus.

- [x] **Step 1: Add documentation assertions where practical**

Extend tests only where the repository already tests documentation contracts. Do not create brittle line-oriented documentation tests solely to increase coverage.

- [ ] **Step 2: Run the full verification**

Run the compiler regression suite and the repository's native acceptance/zero-findings gate through GitHub Actions.

Expected: no regressions and unchanged native validation behavior.

- [x] **Step 3: Review the checklist against the implementation**

Every implemented item must point to a concrete file, test, or catalog contract. Remaining controller families are explicitly partial rather than falsely marked complete.

- [x] **Step 4: Commit the verification/documentation deliverable**

Commit message: `docs(compiler): define native controller semantic boundary`

## Unresolved externally observable decisions

- Whether the controller corpus should become a required compiler gate or remain advisory until enough controller families are native-contract mapped.
- Which individual Strategic Numbers have sufficiently documented coupling to graduate from evidence-only controller metadata to executable semantic mappings.
- Whether performance metadata belongs directly on each control surface or in a separate evidence relation, pending the broader cost-model tranche.
