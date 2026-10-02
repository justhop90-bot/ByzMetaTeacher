# DUC Strategy Compilation Channel Implementation Checklist

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing typed NativeDucPlan through Byzantine strategy compilation so downstream strategy code can consume the already-built DUC execution substrate without creating a second API or DUC language.

**Architecture:** Reuse NativeDucPlan as the existing compiler-owned DUC execution surface. Carry it from StrategyProfile to StrategyCompilation, then through the existing normal/runtime strategy compiler entry points alongside the already-supported attack and escrow channels. Do not synthesize new native DUC behavior or promote runtime liveness claims in this repair.

**Tech Stack:** Python, typed compiler IR, GitHub Actions, native `.per` parser acceptance.

## Global Constraints
- `main` is authoritative.
- Production/train arbitration is already implemented on `main`; do not duplicate it.
- DUC search/target/group semantics remain compiler-owned typed IR plus native contracts; runtime object liveness stays OPEN.
- No second `.per` language, scheduler, simulator, or duplicate DUC manager.
- Existing public strategy compilation channels are extended rather than creating a parallel API.
- Explicit DUC plan overrides must behave deterministically in normal and runtime compilation.
- The default Byzantine strategy remains without a speculative DUC policy until its target/search semantics have evidence-backed strategic ownership.
- Native zero-findings remains the native acceptance authority.

## Audit Baseline
- [x] Confirm `main` is `b4caf29f3b832ddabd693d28caac7ecf5b1953fc` after PR #265.
- [x] Confirm PR #263 is stale/closed and PR #265 is the merged attack implementation.
- [x] Confirm production/train arbitration is implemented by `semantic/production_arbitration.py`, threaded from `compiler.py`, and covered by `test_production_arbitration.py`.
- [x] Confirm DUC typed state, recurrent coupling, target identity, target revalidation, group inputs, native lowering, and native acceptance fixtures already exist.
- [x] Confirm `StrategyProfile` / `StrategyCompilation` currently lack a `duc_plan` channel.
- [x] Confirm normal and runtime Byzantine strategy compilation currently threads attack and escrow but not DUC.
- [x] Confirm attack `AttackExecution` typing and operational bridge exist, while native attack completion/release remains explicitly OPEN.

## Task 1: Typed strategy DUC channel

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`

**Interfaces:**
- Consumes: existing `NativeDucPlan`
- Produces: `StrategyProfile.duc_plan`, `StrategyCompilation.duc_plan`, and `lower_strategy_profile(..., duc_plan=...)`

- [ ] Add a failing integration test that passes an explicit `NativeDucPlan` to `lower_strategy_profile()` and asserts object identity is preserved.
- [ ] Assert the same plan can be emitted through the normal and runtime strategy compilation paths.
- [ ] Run the focused strategy integration test and observe the expected missing-parameter/field failure.
- [ ] Add the type-only optional channel to both strategy dataclasses.
- [ ] Carry the field unchanged through `lower_strategy_profile()`.
- [ ] Do not attach a default Byzantine DUC plan in this task.
- [ ] Run the focused strategy integration test and confirm the channel passes.

## Task 2: Existing compiler channel threading

**Files:**
- Modify: `LearnerAI/Compiler/clients/basilisk/compiler.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`

**Interfaces:**
- Consumes: `StrategyCompilation.duc_plan`
- Produces: `compile_strategy_profile(..., duc_plan=...)` and `compile_strategy_runtime_profile(..., duc_plan=...)`

- [ ] Normal compilation uses the explicit override when supplied, otherwise the lowered profile's `duc_plan`.
- [ ] Runtime compilation uses the same precedence after runtime demand selection.
- [ ] Reuse the generic compiler's existing `duc_plan` argument; do not add a new generic compiler API.
- [ ] Confirm emitted DUC rules are byte-identical across repeated compilations.

## Task 3: Documentation/current-state reconciliation

**Files:**
- Modify: `LearnerAI/Compiler/ROADMAP.md`
- Modify: `LearnerAI/Compiler/PROJECT_STATE.md`
- Test: none beyond CI/document consistency review

- [ ] Remove production/train arbitration from the live next-implementation-target wording.
- [ ] Record the actual current DUC gap as downstream strategy exposure, not missing low-level DUC vocabulary.
- [ ] Keep DUC runtime liveness, retained-filter behavior, and exact native lifecycle boundaries explicitly OPEN.
- [ ] Record the remaining attack gap as executable completion/release/controller runtime semantics, not missing typed IR.

## Task 4: Acceptance and merge
- [ ] Focused strategy integration regression passes.
- [ ] Native DUC target/reacquisition/group fixtures remain zero-findings.
- [ ] Full compiler regression passes.
- [ ] 9/9 native-support determinism passes.
- [ ] Cross-platform snapshot comparison passes.
- [ ] Compiler verification gate passes.
- [ ] Merge only the verified branch into `main`.

## Actual remaining behavioral gaps after this repair
1. **DUC behavioral synthesis:** selecting concrete Byzantine discovery/target policies and connecting them to strategy intent is still needed. The compiler will not guess target classes or runtime object liveness from generic DUC primitives.
2. **Full attack execution:** `READY -> PREPARE -> ASSEMBLE -> ISSUE -> WITNESS -> RELEASE/RESET -> RECOVERY -> REASSESS` remains structurally typed but not fully natively executable. `attack-now` remains issue-only.
3. **Community strategy synthesis:** broad scouting, military parity/TSA, map adaptation, starvation recovery, water/transport, and additional strategy packs still need executable lowering through the existing substrate.