# DUC `up-can-search` Availability Repair Checklist

Date: 2026-09-28
Scope: bounded semantic support for the native Fact `up-can-search`.

## Native contract

- [x] AIRef command schema identifies `up-can-search` as a UP Fact with exactly one `SearchSource`.
- [x] Accepted sources are `search-local` and `search-remote`.
- [x] The command does not create or mutate a search list, filter, target, or cursor.
- [x] Contract evidence is pinned as `airef:duc:can-search`.

## Compiler boundary

- [x] Add a typed search-availability observation to DUC IR.
- [x] Record source list, modeled cursor disposition, initialization state, current cardinality when available, and provenance.
- [x] Return `GUARANTEED_FALSE` only for compiler-proven `AT_END` or `BLOCKED_BY_CAPACITY` states.
- [x] Leave all other availability outcomes `RUNTIME_DEPENDENT`.
- [x] Do not invent a guaranteed-true condition from initialization, cardinality, or a non-terminal cursor.
- [x] Reject invalid SearchSource values through `DUC-005`.
- [x] Reject Action-side use because the native command is Fact-only.
- [x] Preserve control-flow aggregation of availability observations.

## Implementation surface

- [x] `LearnerAI/Compiler/ir/duc.py`
- [x] `LearnerAI/Compiler/primitives/native_hygiene.py`
- [x] `LearnerAI/Compiler/primitives/engine_semantics.py`
- [x] `LearnerAI/Compiler/primitives/__init__.py`
- [x] `LearnerAI/Compiler/semantic/duc.py`
- [x] `LearnerAI/Compiler/tests/test_duc_semantics.py`

## TDD coverage

- [x] Uninitialized local source remains runtime-dependent.
- [x] Proven end-of-scan produces guaranteed false.
- [x] Remote source reads only remote search state.
- [x] Invalid SearchSource is rejected deterministically.
- [x] Focused DUC semantic tests are covered by the full Compiler regression on the verified code head.
- [x] Compiler workflow #2134 passed on the verified code head.
- [x] Native zero-findings acceptance passed.
- [x] All nine native-support determinism jobs passed.
- [x] Aggregate native-support snapshot comparison passed.
- [x] Compiler verification gate passed.

## Explicitly open

- Exact native truth semantics for `up-can-search` beyond compiler-proven scan exhaustion/capacity.
- Exact runtime relationship between availability and world-object visibility/order.
- Any target-lifetime consequence, because this Fact is observational and does not mutate target state.
- `up-add-object-by-id` remains the next broader DUC source-expressiveness slice.

## Verification record

Verified code-bearing main SHA: `5b4352cb2d0b4d7a7dacc117b9b9634affa185c9`.

Compiler workflow: **#2134**
Workflow result:
- 958 compiler tests passed.
- Native zero-findings acceptance passed.
- Focused persistent-state regression passed.
- All nine native-support determinism jobs passed.
- Aggregate native-support snapshot comparison passed.
- Compiler verification gate passed.

The implementation sequence included the DUC IR, native contract catalog, engine-semantic registry, DUC analyzer, semantic tests, and the native citation inventory repair required by the full hygiene suite.

Main may move ahead of this verified code SHA with documentation-only bookkeeping commits; no code change is required for verification evidence already recorded here.
