# Recurrent Timer Generation Semantics Implementation Plan

> For agentic workers: Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Add a minimal, testable timer-generation model and recurrent pass scheduler that preserves AoE2 .per timer lifecycle, stale-trigger, self-disable, jump, and pass-boundary semantics.

**Architecture:** Keep the existing effective-rule parser authoritative for rule structure. Add timer lifecycle types under the validated IR, a focused timer/pass scheduler semantic module that consumes EffectiveRule, and extend persistent-state extraction for the native timer command family. Unknown native actions remain outside the scheduler rather than being invented.

**Tech Stack:** Python 3.11+ compiler code, unittest, existing GitHub compiler branch and checked-in AIRef schema.

## Global Constraints

- Generic compiler only; no downstream strategy or player-controller dependencies.
- Persistent timer state is distinct from world-state evidence.
- Same-pass persistent writes remain immediately visible.
- Expiry is pass-boundary visible.
- Timer generations are never reused.
- Pending expiries carry their generation and are discarded when stale.
- disable-self changes future rule eligibility without aborting the current action sequence.
- Native up-jump-rule semantics are preserved; zero-based target is current index + delta + 1.
- The scheduler uses explicit elapsed time between passes and does not pretend to model exact engine wall-clock timing inside a pass.

---

### Task 1: Add the timer-generation IR contract

**Files:**
- Create: LearnerAI/Compiler/ir/recurrent.py
- Modify: LearnerAI/Compiler/ir/__init__.py
- Test: LearnerAI/Compiler/tests/test_timer_semantics.py

**Interfaces:**
- Produces TimerStatus, TimerRuntimeState, PendingTimerExpiry, TimerReadKind, and generation/state transition helpers.
- Existing TimerSlot allocation remains the binding mechanism.

- [x] Add failing tests for initial disabled state, generation creation, invalidation, re-enable, current-generation reads, and stale-expiry rejection.
- [x] Run the focused timer test and observe missing symbols.
- [x] Implement binding-time DISABLED generation 0; enable increments generation; disable/reset increments generation and clears deadline/trigger; pending expiries carry generation; stale expiries are rejected; trigger reads require current-generation equality.
- [x] Run the focused timer test and require all cases to pass.
- [x] Run the affected compiler timer suite.
- [x] Commit the passing deliverable.

### Task 2: Implement the recurrent pass scheduler

**Files:**
- Create: LearnerAI/Compiler/semantic/pass_scheduler.py
- Modify: LearnerAI/Compiler/semantic/__init__.py
- Test: LearnerAI/Compiler/tests/test_pass_scheduler.py

**Interfaces:**
- Consumes tuple[EffectiveRule, ...] and timer runtime state.
- Produces deterministic pass traces with executed rule order, control transfers, timer mutations, staged expiries, and committed triggers.

- [x] Add failing tests for disabled-rule skipping, self-disable timing, same-pass timer writes, next-pass trigger visibility, stale expiry invalidation, and timer/jump interaction.
- [x] Run the focused scheduler test and observe the missing scheduler interface.
- [x] Implement pass start with pending-expiry commit; sequential rule scan; timer facts/actions; self-disable; native RuleDelta jump; explicit elapsed-time advancement; pass-end expiry staging.
- [x] Resolve up-jump-rule as current zero-based index + delta + 1.
- [x] Delegate unknown actions to an optional callback rather than inventing semantics.
- [x] Run the focused scheduler test and require all cases to pass.
- [x] Run existing rule-execution and persistent-state tests.
- [x] Commit the passing deliverable.

### Task 3: Complete native timer persistent-state extraction

**Files:**
- Modify: LearnerAI/Compiler/semantic/persistent_state.py
- Test: LearnerAI/Compiler/tests/test_persistent_state.py

**Interfaces:**
- Existing PersistentStateAccess remains authoritative.
- Standard and UserPatch timer commands produce TIMER read/write accesses with rule and within-rule order.

- [x] Add failing extraction tests for enable-timer, disable-timer, timer-triggered, up-timer-status, and up-set-timer.
- [x] Run the focused persistent-state tests and confirm standard timer operations are missing.
- [x] Extend the command specification table and timer reader predicates without changing Goal/SN behavior.
- [x] Run the focused persistent-state tests.
- [x] Run the full compiler unittest discovery suite.
- [x] Commit the passing deliverable.

### Task 4: Harden native edge cases

**Files:**
- Modify: LearnerAI/Compiler/ir/recurrent.py
- Modify: LearnerAI/Compiler/semantic/pass_scheduler.py
- Test: LearnerAI/Compiler/tests/test_timer_semantics.py
- Test: LearnerAI/Compiler/tests/test_pass_scheduler.py

**Interfaces:**
- Preserves all prior public timer and scheduler interfaces.

- [x] Add regressions for zero-second timers, repeated re-enable, stale expiry after disable/re-enable, trigger reads after re-enable, out-of-range jump targets, and deterministic repeated traces.
- [x] Run the focused timer/scheduler suites and inspect failures.
- [x] Preserve generation invalidation and keep zero-duration expiry next-pass visible.
- [x] Reject impossible jump targets.
- [x] Run the focused suites again.
- [x] Run the full compiler unittest discovery suite.
- [x] Commit the passing deliverable.

## Unresolved externally observable decisions

None for this tranche. Exact engine wall-clock timing within one script pass remains ENGINE_DEFINED; the semantic scheduler models explicit elapsed time between pass boundaries.
