# Basilisk Prior-Art Reuse Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the strongest proven compiler mechanisms from AgeScript, AgeOfPython, and aoe2ai into Basilisk without changing Basilisk's semantic strategy architecture.

**Architecture:** Extend the existing semantic-to-native binding boundary rather than replacing it. Storage requests remain symbolic; the binder becomes capable of allocating scalar Goals and explicit contiguous Goal spans from disjoint pools, package occupancy becomes interval-aware, and a small volatile Goal pool supplies deterministic scratch storage for future native operations. Binding manifests become first-class reproducibility artifacts. No new strategy syntax is introduced in this tranche.

**Tech Stack:** Python 3.12, unittest, GitHub Actions, pinned aoe2-ai-parser native backend, checked-in AIRef command schema.

## Global Constraints

- Preserve Basilisk's lifecycle semantics and existing generated output for the current three-demand fixture.
- Do not build a second native .per parser.
- Do not introduce a universal scheduler, strategy manager, optimizer, simulator, or Python-like source language.
- Do not infer GoalSpan storage merely from a command having multiple Goal parameters.
- Native GoalId legality remains 1..16000; span bounds must come from explicit native storage contracts.
- GoalSlot and GoalValue remain distinct concepts.
- Existing bindings are reused before new allocation.
- Allocation is deterministic and transactional.
- Package occupancy is explicit input, never guessed from one generated file.
- The pinned native backend remains the final native syntax authority.

---

### Task 1: Capture prior-art decisions in the repository

**Files:**
- Modify: `LearnerAI/Compiler/RESEARCH_CHECKLIST.md`
- Create: `docs/plans/2026-09-26-basilisk-prior-art-reuse.md`

**Interfaces:**
- Consumes: current compiler research checklist and the GitHub prior-art audit.
- Produces: explicit adoption/non-adoption decisions and implementation checklist.

- [x] Record AgeScript's typed compilation/assembly split and Goal-backed memory model as backend precedent.
- [x] Record AgeOfPython's AIRef-derived metadata and Goal memory allocation as typed-native precedent.
- [x] Record aoe2ai's named Goal allocation, volatile Goal/Point reuse, staged state, and rule-budget handling as runtime-storage precedent.
- [x] Explicitly reject copying their Python-like language, generalized staged syntax, or optimizer into Basilisk.

---

### Task 2: Add explicit GoalSpan and package-occupancy binding

**Files:**
- Modify: `LearnerAI/Compiler/runtime_binding.py`
- Modify: `LearnerAI/Compiler/ir/model.py`
- Test: `LearnerAI/Compiler/tests/test_runtime_binding.py`

**Interfaces:**
- Consumes: `GoalSlotRequest`, `NativeStorageContract`, `BindingContext`.
- Produces: `GoalSpanRequest`, `GoalInterval`, generalized `BindingRecord`, interval-aware `BindingContext`, deterministic scalar/span allocation.

- [x] Add `GoalSpanRequest` with explicit width, shape, contract bounds, and symbolic provenance.
- [x] Represent occupied external Goal spans as intervals.
- [x] Reject scalar/span overlap, invalid contract ranges, zero-width spans, and duplicate storage identities.
- [x] Allocate scalar lifecycle state from the existing scalar pool and extended spans from their contract pool without aliasing.
- [x] Preserve existing scalar manifest bindings and existing span bindings across recompilation.
- [x] Round-trip both scalar and span bindings through deterministic JSON manifests.
- [x] Verify current lifecycle fixture still allocates exactly one GoalSlot per demand.

---

### Task 3: Steal aoe2ai's volatile-storage lifetime pattern

**Files:**
- Modify: `LearnerAI/Compiler/runtime_binding.py`
- Test: `LearnerAI/Compiler/tests/test_runtime_binding.py`

**Interfaces:**
- Consumes: a deterministic range of compiler-owned GoalIds.
- Produces: `VolatileGoalPool.checkout()`, `release()`, and `using()` lifetime helper.

- [x] Allocate scratch Goals from a compiler-owned range disjoint from lifecycle/scalar persistent storage and GoalSpan ranges.
- [x] Reuse only explicitly released Goals.
- [x] Reject double release and release of foreign/unknown Goals.
- [x] Provide deterministic first-fit checkout.
- [x] Keep the pool independent of semantic truth and lifecycle witnesses.

---

### Task 4: Make binding manifests first-class compiler artifacts

**Files:**
- Modify: `LearnerAI/Compiler/compiler.py`
- Modify: `LearnerAI/Compiler/tests/test_compiler.py`
- Modify: `LearnerAI/Compiler/tests/test_compiler_native_integration.py`

**Interfaces:**
- Consumes: `BindingResult` produced by compilation.
- Produces: optional manifest output alongside the .per artifact after semantic/native validation.

- [x] Add an internal compilation path that returns both emitted .per and `BindingResult`.
- [x] Add an optional `--binding-manifest PATH` CLI output.
- [x] Write the manifest only after semantic validation and, when enabled, native validation succeeds.
- [x] Preserve the existing output artifact if native validation rejects the staged .per.
- [x] Verify repeated compilation with the same inputs produces byte-identical .per and manifest output.

---

## Next semantic tranche after this implementation

- [ ] Capability-provider graph and provider admissibility diagnostics.
- [ ] Demand ownership and first-writer/first-consumer contracts.
- [ ] Prerequisite dependency graph with cycle/dead-end/unfed diagnostics.
- [ ] Resource/conflict relations beyond the existing build-pass singleton.
- [ ] Action-issuance failure versus pending-state distinction.
- [ ] Castle vertical slice using actual Basilisk capability and resource semantics.
- [ ] Source-order analysis and same-pass visibility diagnostics.
- [ ] StrategicNumberSlot and TimerSlot allocation after native contracts are catalogued.

## Verification record

The storage reuse tranche is implemented on `main`. Compiler workflow run 123 passed native validation and the full unittest suite after the storage fixes. The subsequent commits changed documentation only; no compiler/runtime files changed after that verification.
