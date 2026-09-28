# DUC Cardinality / Performance Diagnostic Repair Checklist

Date: 2026-09-28
Base: main at a624668a3ceafe070de8a382729bde0ea2c1678e
Scope: advisory DUC search cost diagnostics using existing native interaction evidence.

## Repair identification

The next bounded compiler repair is **DUC cardinality/performance diagnostics**.

The repository already has:
- typed local/remote DUC cardinality ranges;
- hard native capacities (local 240, remote 40);
- a reserved `DUC-COST` diagnostic code (`DUC-015`);
- a shared `NativeControllerInteractionCatalog` carrying `PerformanceClass` and `NativeInteractionCardinality` for local and remote DUC search.

The defect is that `semantic/duc.py` does not consume that existing evidence when analyzing recurrent retained-list searches. It emits generic accumulation warnings (`DUC-008`) but does not expose the evidence-backed performance class or cardinality bound.

This is a real semantic-surface gap, not an invented optimizer. The repair must remain advisory.

## AI/community cross-reference

### AIRef engine evidence
- AIRef command-performance measurements show `up-find-local` and `up-find-remote` costs vary with the number and availability of objects searched.
- The benchmark explicitly distinguishes list-size/cost cases, including local capacity-scale searches and remote-list searches.
- AIRef's performance guidance is empirical, not a correctness contract. It must therefore never become a blocking compiler error.

Source:
https://airef.github.io/resources/articles/command-performance.html

### Community .per evidence
- `lewisc64/aoe2ai` contains recurrent DUC sequences using repeated searches, explicit resets, filters, target establishment, and `up-get-search-state`.
- The same corpus demonstrates reusing stored groups to avoid repeated search work in appropriate loops.

Source:
https://github.com/lewisc64/aoe2ai

### Compiler boundary
Community repetition proves that these loops matter operationally, not that a particular cardinality or timing threshold is universally correct. The compiler therefore reports the native benchmark class and hard list bound, but does not invent a "too slow" threshold.

## Evidence classification

ENGINE_SEMANTICS_MAPPED:
- DUC list capacities and search command identities are already backed by checked-in AIRef/UserPatch data.
- Existing native interaction records already carry local 0..240 / remote 0..40 cardinality and MEDIUM/FAST benchmark classes.

ADVISORY_ONLY:
- Empirical performance class.
- Any warning based on recurrent retained search state.
- No compile rejection, resource budget, or scheduler policy.

OPEN:
- Exact runtime milliseconds for the current game state.
- World-population-dependent scan cost.
- Universal "safe iterations per pass" thresholds.
- Any claim that a warning predicts visible lag.

## TDD checklist

### Red phase
- [ ] Add failing local recurrent-search fixture requiring `DUC-015` with the existing local performance class and 0..240 bound.
- [ ] Add failing remote recurrent-search fixture requiring `DUC-015` with the existing remote performance class and 0..40 bound.
- [ ] Add failing regression proving a same-rule explicit reset suppresses the cost diagnostic.
- [ ] Add failing regression proving one-shot searches do not receive recurrent-cost diagnostics.
- [ ] Run the focused DUC suite and capture the red result.

### Implementation
- [ ] Resolve DUC search performance metadata from the shared native interaction catalog; do not duplicate benchmark facts in `semantic/duc.py`.
- [ ] Emit `DUC-015` only for recurrent searches operating on a retained prior list generation without an applicable same-rule list reset.
- [ ] Include list kind, native capacity, retained cardinality upper bound, and benchmark performance class in the diagnostic.
- [ ] Keep severity advisory (`WARNING`); never reject compilation.
- [ ] Fail closed to no cost diagnostic when the shared evidence mapping is unavailable.
- [ ] Leave `DUC-008` accumulation semantics unchanged.
- [ ] Do not add source syntax, runtime scheduling, thresholds, or automatic resets.

### Green / refactor
- [ ] Focused DUC performance tests pass.
- [ ] Complete DUC semantic suite passes.
- [ ] Full compiler regression passes.
- [ ] Existing native zero-findings fixtures pass unchanged.
- [ ] All 9 native-support determinism jobs pass.
- [ ] Cross-platform native snapshot comparison passes.
- [ ] Compiler verification gate passes on the exact final main SHA.

## Files

Primary:
- `LearnerAI/Compiler/semantic/duc.py`
- `LearnerAI/Compiler/tests/test_duc_semantics.py`
- `LearnerAI/Compiler/semantic/rule_diagnostics.py` only if the existing `DUC-015` taxonomy needs correction.

Documentation after green:
- update `E-compiler_gap_matrix.md` DUC TargetSession/groups/outputs/costs row;
- update this checklist with exact verification evidence.

## Acceptance

An expert reading a recurrent retained DUC search must be able to see:
1. the existing search accumulation diagnostic;
2. the evidence-backed local/remote capacity;
3. the existing benchmark performance class;
4. that the diagnostic is advisory rather than a correctness claim;
5. that an explicit same-rule reset removes the accumulation/cost condition.

No new engine fact may be inferred from community frequency alone.
