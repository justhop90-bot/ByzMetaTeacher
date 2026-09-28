# DUC Report Surface Cross-Reference and Witness Plumbing Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure DUC target Fact observations and target-consumer effects produced during control-flow analysis remain connected to the final `DucAnalysisReport` instead of disappearing at the report aggregation boundary.

**Architecture:** The existing linear analyzer already produces `target_fact_observations` and `target_consumers` on each per-rule `DucAnalysisReport`. The whole-execution `analyze_duc()` aggregation must concatenate those immutable observations in rule order, exactly as it already does for searches, mutations, targets, target-data observations, and effects. No new state model, persistence layer, or native contract is required.

**Tech Stack:** Python 3.11+; immutable dataclasses; unittest; GitHub Actions compiler suite.

## Global Constraints

- Preserve existing `DucAnalysisReport` interfaces and tuple ordering.
- Do not change native target semantics or promote any UNKNOWN target-lifetime boundary.
- Preserve fail-closed Fact results and target-consumer diagnostics.
- Aggregate observations only from rule reports that actually ran through `_analyze_duc_linear`.
- Maintain deterministic ordering by ascending `rule_order`.
- Add focused regression coverage before production changes.
- Update this plan with observed verification results after implementation.

---

### Task 1: Connect target Fact observations through whole-execution aggregation

**Files:**
- Modify: `LearnerAI/Compiler/semantic/duc.py:3650-3715`
- Test: `LearnerAI/Compiler/tests/test_duc_semantics.py`

**Interfaces:**
- Consumes: per-rule `DucAnalysisReport.target_fact_observations` emitted by `_analyze_duc_linear()`.
- Produces: whole-execution `DucAnalysisReport.target_fact_observations` containing the same observations in ascending rule order.

- [x] **Step 1: Add the focused failing test**

Construct a two-rule `RuleExecutionReport` with explicit reachability:
- Rule 1 has a Fact-form `(up-set-target-object search-local c: 0)` with no initialized search list.
- Rule 2 is a no-op rule reachable from rule 1.
- Run `analyze_duc(execution)`.
- Assert `len(report.target_fact_observations) == 1`.
- Assert the observation result is `DucTargetFactResult.GUARANTEED_FALSE`.

This test must fail on the current implementation because `analyze_duc()` currently omits the aggregation field.

- [x] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI/Compiler/tests/test_duc_semantics.py -k target_fact`

Observed limitation: GitHub has not surfaced a workflow run for the red-phase commit, so the expected failure was not independently executed in CI. The failing condition is established by the pre-repair aggregation code path.

- [x] **Step 3: Implement the minimum behavior**

In `analyze_duc()`, after collecting `targets`, add a deterministic aggregation:

```python
target_fact_observations = tuple(
    observation
    for rule_order in sorted(rule_reports)
    for observation in rule_reports[rule_order].target_fact_observations
)
```

Pass that tuple into the final `DucAnalysisReport(...)`.

Do not alter linear analysis, Fact classification, or target state transitions.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest LearnerAI/Compiler/tests/test_duc_semantics.py -k target_fact`

Expected: all target-Fact tests pass, including the new whole-execution case.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI/Compiler/tests/test_duc_semantics.py`

Expected: the complete DUC semantic suite passes without changing existing diagnostics.

- [x] **Step 6: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/semantic/duc.py LearnerAI/Compiler/tests/test_duc_semantics.py docs/plans/2026-09-28-duc-report-surface-crossref.md
git commit -m "fix: preserve DUC target Fact observations"
```

---

### Task 2: Connect target-consumer effects through whole-execution aggregation

**Files:**
- Modify: `LearnerAI/Compiler/semantic/duc.py:3650-3715`
- Test: `LearnerAI/Compiler/tests/test_duc_semantics.py`

**Interfaces:**
- Consumes: per-rule `DucAnalysisReport.target_consumers`.
- Produces: whole-execution `DucAnalysisReport.target_consumers` containing the same consumer effects in ascending `rule_order`.

- [x] **Step 1: Add the focused failing test**

Construct a two-rule `RuleExecutionReport`:
- Rule 1 finds a local object and invokes `up-target-objects 0 action-default -1 -1`.
- Rule 2 is a reachable no-op.
- Run `analyze_duc(execution)`.
- Assert exactly one `target_consumers` entry.
- Assert its mode is `DucTargetConsumerMode.LOCAL_SEARCH_RESULTS`.
- Assert its local list generation is `1`.

This tests the same report-surface boundary for consumer effects.

- [x] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI/Compiler/tests/test_duc_semantics.py -k target_objects_option_zero_records_local_search_consumer_effect`

Observed limitation: GitHub has not surfaced a workflow run for the red-phase commit, so the expected failure was not independently executed in CI. The failing condition is established by the pre-repair aggregation code path.

- [x] **Step 3: Implement the minimum behavior**

In `analyze_duc()`, aggregate:

```python
target_consumers = tuple(
    consumer
    for rule_order in sorted(rule_reports)
    for consumer in rule_reports[rule_order].target_consumers
)
```

Pass the tuple into the final `DucAnalysisReport(...)`.

Do not alter target-consumer semantic checks.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest LearnerAI/Compiler/tests/test_duc_semantics.py -k target_consumers`

Expected: all target-consumer tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI/Compiler/tests/test_duc_semantics.py`

Expected: complete DUC semantic suite passes.

- [x] **Step 6: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/semantic/duc.py LearnerAI/Compiler/tests/test_duc_semantics.py docs/plans/2026-09-28-duc-report-surface-crossref.md
git commit -m "fix: preserve DUC target consumer effects"
```

---

### Verification status

The production repair is committed on the branch, but GitHub has not yet exposed a CI run for the current head. No green claim is made until the compiler workflow reports the focused and full-suite results.

### Cross-reference matrix

| Producer | Intermediate surface | Final surface | Current status before tranche | Repair |
|---|---|---|---|---|
| `_analyze_target_object_fact()` | per-rule `DucAnalysisReport.target_fact_observations` | whole-run `DucAnalysisReport.target_fact_observations` | FUNCTIONALLY-DISCONNECTED | aggregate in `analyze_duc()` |
| `up-target-objects` semantic branch | per-rule `DucAnalysisReport.target_consumers` | whole-run `DucAnalysisReport.target_consumers` | FUNCTIONALLY-DISCONNECTED | aggregate in `analyze_duc()` |
| `up-set-target-object` native Fact contract | `NativeDucTargetContract` | `DucTargetFactObservation` | CONNECTED | no change |
| Failed target Action | target static state + `DUC-007` | final target state | CONNECTED, runtime claim OPEN | no promotion |
| List mutation target transition | `DucListMutationEffect.target_transition` | whole-run mutations | CONNECTED | no change |
| Native oracle candidates | candidate JSON | promotion gate | CONNECTED, UNVERIFIED | no promotion |

### Acceptance criteria

- Whole-execution reports expose target Fact observations instead of losing them.
- Whole-execution reports expose target-consumer effects instead of losing them.
- Existing linear analysis behavior is unchanged.
- No target-lifetime UNKNOWN boundary is upgraded without native evidence.
- The complete DUC semantic test suite remains green.
