# Production Queue Capacity Native Evidence Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a typed, fail-closed compiler contract for the AIRef-backed Definitive Edition training-queue capacity control without promoting the documented control into an execution-authorizing queue-capacity fact.

**Architecture:** Treat `sn-enable-training-queue` (SN 264) as a native control input, not as another queue-state observation. The compiler may bind an exact equality observation of that SN to a typed production lifecycle record, derive the documented capacity as current-training unit plus configured additional queued units, and preserve the result as OPEN until direct DE runtime evidence proves that the current engine build enforces the documented capacity. Existing `can-train`, `unit-type-count-total`, `building-type-count`, and `up-pending-objects` contracts remain unchanged.

**Tech Stack:** Python compiler IR/semantic analysis, pinned AIRef JSON inventories, GitHub Actions Compiler/native gates, AoE2DE .per/AIRef semantics.

## Global Constraints

- AIRef vocabulary and the repository-pinned DE Strategic Number inventory are reference inputs; they do not by themselves establish closed-engine runtime behavior.
- SN 264 is `sn-enable-training-queue`, DE-supported, default 0, range 0..15, and documents the value as the number of additional units that can be queued after the currently training unit.
- The derived documented total pipeline capacity is therefore `additional_queue_slots + 1` when the native controller semantics are honored.
- `unit-type-count-total` remains an occupancy observation, not a capacity oracle.
- `building-type-count` remains provider presence, not provider readiness/idle state.
- `up-pending-objects` remains duplicate/pending protection and does not prove capacity or completion.
- `can-train` remains native admission and does not expose a queue-full reason.
- No production action may become authorized from the new evidence.
- Non-exact SN comparisons, wrong SN identifiers, out-of-range values, and unknown sources must fail closed.
- Direct DE runtime confirmation that a current build honors SN 264 at the configured value remains OPEN and user-owned.

---

### Task 1: Record the cross-reference and native contract

**Files:**
- Create: `docs/plans/2026-09-28-production-queue-capacity-native-evidence.md`
- Existing evidence: `docs/reference/inventories/airef-strategic-number-inventory.json`
- Existing evidence: `docs/reference/inventories/airef-command-schema.json`
- Existing evidence: `A-native_command_semantics.csv`
- Existing evidence: `native_unknowns.md`
- Existing evidence: `E-compiler_gap_matrix.md`

**Interfaces:**
- Consumes: pinned AIRef DE Strategic Number record for `sn-enable-training-queue`
- Produces: one auditable compiler contract and a reproducible runtime proof checklist

- [ ] **Step 1: Capture the documented native facts**

Record SN 264, name, DE support, default, range, and the documented meaning of its value. Cross-reference `unit-type-count-total`, `can-train`, `up-pending-objects`, and the separate DUC training path so the ordinary `train` path cannot inherit DUC capacity semantics accidentally.

- [ ] **Step 2: Define the runtime proof boundary**

Require a controlled DE test varying SN 264 across 0, a middle value, and 15 while keeping resources, housing, and provider state non-blocking. Record configured SN value, `unit-type-count-total`, `up-pending-objects`, `can-train`, successful `train` issuance count, and the first rejected queue position.

---

### Task 2: Add typed queue-capacity control evidence

**Files:**
- Modify: `LearnerAI/Compiler/ir/production.py`
- Modify: `LearnerAI/Compiler/primitives/registry.py`
- Test: `LearnerAI/Compiler/tests/test_production_queue_capacity_native_contract.py`

**Interfaces:**
- Consumes: exact `up-compare-sn` native SN observation for SN 264
- Produces: `ProductionQueueCapacityControlEvidence` with OPEN disposition

- [ ] **Step 1: Add the focused failing tests**

Assert that `(up-compare-sn sn-enable-training-queue == 3)` resolves to typed OPEN evidence with native SN id 264, additional queue slots 3, documented total capacity 4, and semantic id `controller.production.queue-capacity.sn264`. Assert that non-exact comparisons and values outside 0..15 are rejected.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI.Compiler.tests.test_production_queue_capacity_native_contract`
Expected: import/attribute failure because the typed evidence class and resolver do not yet exist.

- [ ] **Step 3: Implement the minimum behavior**

Add `ProductionQueueCapacityControlEvidence` with fail-closed invariants. Bind only the documented SN 264 name/id, require exact equality, parse an integer 0..15, derive documented total capacity as `value + 1`, and keep disposition OPEN. Do not emit a new guard or alter `train` admission.

- [ ] **Step 4: Verify the focused pass**

Run the same focused unittest command.
Expected: all new queue-capacity contract tests pass.

---

### Task 3: Thread the evidence through production analysis

**Files:**
- Modify: `LearnerAI/Compiler/semantic/analyzer.py`
- Modify: `LearnerAI/Compiler/ir/production.py` if lifecycle field integration requires it
- Test: `LearnerAI/Compiler/tests/test_production_queue_capacity_native_contract.py`
- Test: existing production lifecycle/observation suites

**Interfaces:**
- Consumes: `ProductionQueueCapacityControlEvidence`
- Produces: `ProductionLifecycle.queue_capacity_control` with OPEN status preserved

- [ ] **Step 1: Add analyzer red coverage**

Compile a production demand containing an exact SN 264 equality and assert the resulting `ProductionLifecycle` retains the typed evidence while the demand still uses ordinary `can-train` admission.

- [ ] **Step 2: Verify the relevant failure**

Run the focused production test suite.
Expected: lifecycle field is absent or unresolved before implementation.

- [ ] **Step 3: Implement the minimum wiring**

Recognize only the exact SN 264 equality expression in the production demand's requirements, resolve it through the registry, attach it to `ProductionLifecycle`, and preserve OPEN state. Unknown or non-exact SN expressions must not be silently reclassified as capacity evidence.

- [ ] **Step 4: Verify the focused pass**

Run the focused production lifecycle and observation suites.
Expected: typed evidence survives semantic analysis and never changes the emitted action guard set.

---

### Task 4: Native artifact and documentation acceptance

**Files:**
- Create: `LearnerAI/Compiler/tests/fixtures/production_queue_capacity.perdsl`
- Create: `LearnerAI/Compiler/tests/assert_production_queue_capacity_native.py`
- Modify: `LearnerAI/Compiler/E-compiler_gap_matrix.md` or its authoritative production row only after tests are green
- Modify: `LearnerAI/Compiler/MUSE_NEXT_IMPLEMENTATION_CHECKLIST_2026-09-28.md` only to record the newly connected evidence seam

**Interfaces:**
- Consumes: production fixture containing exact SN 264 configuration plus normal `can-train`/train lifecycle
- Produces: deterministic .per artifact and native zero-findings evidence showing the new source remains syntactically/semantically valid, while the runtime-capacity claim remains OPEN

- [ ] **Step 1: Add the native fixture/acceptance test**

Compile the fixture twice, assert byte-identical artifacts, assert the expected SN 264 source survives emission, and run the pinned native zero-findings validator.

- [ ] **Step 2: Verify native acceptance**

Run the focused acceptance script.
Expected: deterministic artifact plus zero native findings.

- [ ] **Step 3: Update the gap/checklist state**

Mark only the compiler evidence-binding sub-boundary as connected. Keep actual engine-enforced capacity, provider idle/readiness, and birth timing OPEN until DE runtime evidence is recorded.

- [ ] **Step 4: Run full verification**

Run the repository's required Compiler test and native/determinism gate commands.
Expected: no regressions, zero native findings, deterministic output, and all affected focused suites green.

---

## Runtime Evidence Gate Still Open

The compiler implementation must not promote `ProductionQueueCapacityControlEvidence` to EXECUTABLE_SAFE solely from AIRef or community documentation. A current target DE build must demonstrate the configured SN 264 value by controlled queue-fill behavior. The runtime witness must distinguish ordinary `train` from DUC training, keep provider/resource/housing constraints non-blocking, and record the first queue-full boundary.

## Explicit Unresolved Decisions

- Exact current-build behavior when a provider disappears while units remain queued.
- Whether any DE/provider/unit/civilization-specific condition changes the documented `SN 264 + 1` total capacity.
- Whether `can-train` exposes queue-full state indirectly in a way the compiler can safely use as a separate typed fact.
- Exact birth/queue-exit timing relative to `unit-type-count-total` and `unit-type-count`.

