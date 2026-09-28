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
- [ ] Focused test suite verified on the final implementation head.
- [ ] Full Compiler workflow verified on the final implementation head.
- [ ] Native zero-findings acceptance verified on the final implementation head.
- [ ] All nine native-support determinism jobs verified on the final implementation head.
- [ ] Aggregate native snapshot comparison verified on the final implementation head.
- [ ] Compiler verification gate verified on the final implementation head.

## Explicitly open

- Exact native truth semantics for `up-can-search` beyond compiler-proven scan exhaustion/capacity.
- Exact runtime relationship between availability and world-object visibility/order.
- Any target-lifetime consequence, because this Fact is observational and does not mutate target state.
- `up-add-object-by-id` remains the next broader DUC source-expressiveness slice.

## Verification record

Implementation commits:
- `24fa0586b3045912d6baea918421c0ec77226a2a`
- `4b8ab886a82996cbc0614f4b62347fc0d4e06e63`
- `de761a5749f45fcaae3dfe3ba223e14a66a141fa`
- `a6d814aca5f6da0634dd8a2ddf86616237961581`
- `6089edad03849d82802f3233b622ae37639da632`
- `ae5592fe83a011086a23ebb6ac86f98d419e1ca8`
- `6900032b52d1184f6591757156fb797660fb28f2`
- `313bfe487d4e5dcf335349f33726870f93965fd8`
- `bf5e60eb3a1055dc77ce75aab697ded8b6f77754`
- `2a2db4c086ffb910e8cce12554093a0d03320086`

Verification is intentionally left open until the Compiler workflow for the final head produces fresh evidence.
