# Timer Symbolic Allocation Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect compiler-owned symbolic timer declarations to deterministic TimerId allocation and native .per emission without inventing timer countdown behavior the engine has not established.

**Architecture:** Reuse the existing `TimerRequest`/`TimerSlot` storage boundary and recurrent timer state machine. Add a small compiler-owned timer declaration parallel to existing Strategic Number declarations, collect the resulting requests through the convergent compiler storage path, emit deterministic `defconst` aliases, and prove the exact artifact through the pinned native validator.

**Community cross-reference:** AIRef defines `timer-triggered` and `up-timer-status` as native timer-state reads and documents timer operations as persistent engine state. Community .per implementations independently use named timer constants plus `enable-timer`, `timer-triggered`, `disable-timer`, and explicit re-arming loops rather than hard-coding timer identifiers throughout rules. Current compiler evidence in `B-community_per_idiom_catalog.csv` classifies this timer idiom as current community practice with high confidence but marks compiler support as partial specifically because DSL Timer allocation is missing. The implementation therefore promotes storage allocation only; it does not promote countdown cadence or timer-reuse semantics. 

## Global Constraints

- No raw numeric TimerId is allocated by semantic source.
- Compiler-owned timer declarations use the existing symbolic-storage model and lower to deterministic `defconst` aliases.
- TimerIds remain in the native 1..50 range.
- Allocation remains lowest-free and collision-aware through the existing `RuntimeBinder`.
- Initialization policy is explicit in `TimerRequest`; the first compiler-owned policy is `DISABLE_BEFORE_FIRST_USE`.
- Timer reuse remains disabled unless an explicit lifetime model exists.
- Existing recurrent timer semantics remain authoritative for compiler analysis: DISABLED/RUNNING/TRIGGERED with staged expiry and generation checks.
- No source-language timer duration is introduced by this tranche. Duration remains an argument to native `enable-timer`/`up-set-timer` expressions.
- Existing symbolic timer names must be emitted as native-resolvable `defconst` aliases before any emitted rule references them.
- Equivalent source/plan inputs must produce byte-identical artifacts and equivalent binding manifests.
- The pinned native validator is the artifact acceptance authority.
- Actual engine countdown/pass granularity remains OPEN unless supported by runtime evidence; scheduler tests are not promoted to engine fact.

---

### Task 1: Add timer declarations and typed Timer IR

**Files:**
- Modify: `LearnerAI/Compiler/ast.py`
- Modify: `LearnerAI/Compiler/parser.py`
- Modify: `LearnerAI/Compiler/ir/recurrent.py`
- Modify: `LearnerAI/Compiler/ir/model.py`
- Modify: `LearnerAI/Compiler/ir/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_timer_allocation.py`

**Interfaces:**
- Consumes: existing demand source grammar and `SourceLocation`.
- Produces: `DemandNode.timer_states`, `TimerRequest`, and `TimerState` with deterministic ownership/provenance.

- [ ] **Step 1: Add focused failing tests**
  - Parse `timer cooldown` inside a demand.
  - Reject duplicate timer declarations in one demand.
  - Reject duplicate compiler-owned timer names across demands.
  - Analyze a timer declaration into `TimerState` with purpose `timer:cooldown`, role `EXECUTION_MEMORY`, explicit policy `DISABLE_BEFORE_FIRST_USE`, and deterministic stability key.
  - Reject an empty/invalid timer name.
  - Preserve location metadata.

- [ ] **Step 2: Implement minimum typed state**
  - Move/re-export the existing `TimerRequest` definition into `ir/recurrent.py` so timer request ownership is part of the IR rather than a runtime-only type.
  - Add immutable `TimerState(name, request, location)`.
  - Keep `TimerRequest` fields exactly: `request_id`, `initialization_policy`, `stability_key`, `role=EXECUTION_MEMORY`.
  - Require non-empty initialization policy and stability key.
  - Require request purpose `timer:<name>` from `TimerState`.
  - Add `timer_states` to `DemandNode` and `SemanticDemand`.
  - Parse `timer <name>` as a declaration only; do not introduce duration syntax.

- [ ] **Step 3: Verify focused pass**
  - Run: `python -m unittest LearnerAI/Compiler/tests/test_timer_allocation.py`
  - Expected: timer parsing/IR tests pass while existing Strategic Number tests remain unchanged.

- [ ] **Step 4: Run affected parser/runtime regression**
  - Run: `python -m unittest LearnerAI/Compiler/tests/test_runtime_binding.py LearnerAI/Compiler/tests/test_timer_semantics.py LearnerAI/Compiler/tests/test_pass_scheduler.py`
  - Expected: existing timer storage and recurrent semantics remain unchanged.

---

### Task 2: Thread TimerRequest through semantic analysis and compiler storage binding

**Files:**
- Modify: `LearnerAI/Compiler/semantic/analyzer.py`
- Modify: `LearnerAI/Compiler/compiler.py`
- Modify: `LearnerAI/Compiler/runtime_binding.py`
- Modify: `LearnerAI/Compiler/RUNTIME_BINDING_CONTRACT.md` if the moved type ownership requires wording correction.
- Test: `LearnerAI/Compiler/tests/test_timer_allocation.py`
- Test: `LearnerAI/Compiler/tests/test_runtime_binding.py`

**Interfaces:**
- Consumes: `TimerState.request`.
- Produces: `_storage_requests()` entries that bind to `TimerSlot`; binding manifests already support TimerSlot and require no schema redesign.

- [ ] **Step 1: Add failing binding tests**
  - A declared timer allocates the lowest free TimerId.
  - Occupied IDs are skipped deterministically.
  - Out-of-range inventory remains rejected.
  - A compiler-owned timer always receives `TimerSlot`, never Goal/SN storage.
  - Binding manifest round-trip preserves timer request identity, slot, and initialization policy.
  - Two equivalent timer declarations produce identical binding material.

- [ ] **Step 2: Implement compiler threading**
  - Import `TimerRequest` and `TimerSlot` from the new IR/runtime boundary.
  - Extend `_storage_requests()` to collect `demand.timer_states[*].request`.
  - Keep the existing Strategic Number inventory path untouched.
  - After binding, assert each timer state resolved to `TimerSlot`; fail closed otherwise.
  - Preserve existing package inventory collision checks and timer reuse prohibition.
  - Keep the timer allocation path independent of the generic control-plane scheduler.

- [ ] **Step 3: Verify focused and runtime binding suites**
  - Run: `python -m unittest LearnerAI/Compiler/tests/test_timer_allocation.py LearnerAI/Compiler/tests/test_runtime_binding.py`
  - Expected: symbolic timers bind deterministically and existing Goal/SN/Timer manifest tests remain green.

---

### Task 3: Deterministic native emission and source-to-artifact acceptance

**Files:**
- Modify: `LearnerAI/Compiler/emitter/per.py`
- Create: `LearnerAI/Compiler/tests/fixtures/timer_allocation.perdsl`
- Create: `LearnerAI/Compiler/tests/assert_timer_native.py`
- Modify: `LearnerAI/Compiler/tests/test_timer_allocation.py`
- Test: native artifact gate

**Interfaces:**
- Consumes: `SemanticDemand.timer_states` and `TimerSlot` bindings.
- Produces: deterministic `(defconst <timer-name> <TimerId>)` aliases in the final .per artifact.

- [ ] **Step 1: Add failing emitter/acceptance tests**
  - One timer emits exactly one `defconst` alias.
  - Two timers emit in deterministic source-identity order independent of collection construction order.
  - Symbolic timer references in `timer-triggered`/`up-timer-status` remain source-preserved and resolve through the emitted `defconst`.
  - `TimerSlot` is required; Goal/SN bindings fail closed.
  - No `enable-timer`/disable/rearm action is synthesized merely because a timer was declared.
  - Duplicate compilation produces byte-identical output and identical artifact SHA-256.

- [ ] **Step 2: Implement deterministic emission**
  - Collect compiler-owned timer states before demand emission.
  - Validate unique names.
  - Resolve each request through `BindingResult`.
  - Emit `(defconst <name> <slot.id>)` in deterministic `(source_unit, demand_name, purpose)` order.
  - Do not emit synthetic initialization actions; the initialization policy remains binding metadata and the recurrent timer model remains the runtime semantic authority.
  - Feed the complete artifact through the existing artifact-budget validator.

- [ ] **Step 3: Add checked-in source fixture and acceptance gate**
  - Fixture declares a timer symbol and consumes it through `up-timer-status`.
  - Acceptance compiles the fixture twice, compares bytes/SHA-256, checks the emitted alias and symbolic use, writes binding-manifest evidence, and invokes the pinned `aoe2_ai_lab` validator.
  - Require `finding_count == 0` and `findings == []`.

- [ ] **Step 4: Verify focused/native acceptance**
  - Run: `python -m unittest LearnerAI/Compiler/tests/test_timer_allocation.py`
  - Run: `python LearnerAI/Compiler/tests/assert_timer_native.py --output /tmp/timer-allocation.per --report /tmp/native-reports/timer-allocation.json`
  - Expected: deterministic artifacts and native zero findings.

---

### Task 4: Update MUSE roadmap and full verification

**Files:**
- Modify: `LearnerAI/Compiler/MUSE_NEXT_IMPLEMENTATION_CHECKLIST_2026-09-28.md`
- Modify: `compiler_coverage_baseline.md`
- Modify: `implementation_map.md`
- Modify: `native_unknowns.md` only to distinguish allocation connectivity from still-open engine countdown/pass-granularity evidence.
- Modify: `.github/workflows/compiler-tests.yml`

- [ ] Add the timer acceptance fixture to Compiler CI alongside the existing native DUC/attack/escrow gates.
- [ ] Mark Timer allocation as connected/verified in MUSE checklist only for symbolic allocation + emission + native artifact validity.
- [ ] Keep actual countdown pass granularity explicitly OPEN.
- [ ] Keep timer reuse/lifetime beyond compiler-owned first-use allocation explicitly OPEN.
- [ ] Run the complete compiler test suite and cross-platform native-support matrix.
- [ ] Verify no existing DUC, attack, escrow, Goal, SN, or control-plane artifact changes occur when no timer declarations are present.
- [ ] Record final artifact SHA-256 and binding-manifest fingerprint in the audit/checklist.

## Explicit Open Boundaries

- Actual engine countdown/pass granularity remains OPEN.
- Automatic reuse of a TimerId after timer lifetime remains disabled.
- Runtime discovery of externally-authored timer occupancy remains an integration boundary.
- Timer declaration does not imply `enable-timer`, rearm, reset, or completion behavior.
