# DUC Search-Index Transition Closure Checklist

Date: 2026-09-28
Branch: duc-native-transition-contracts

## Native contract

- [x] Shared `NativeDucSearchIndexTransitionContract` exists in `primitives/native_hygiene.py`.
- [x] Trigger kinds are explicit: `EXPLICIT_RESET`, `QUERY_CHANGE`, `FILTER_CHANGE`, `FOCUS_PLAYER_CHANGE`.
- [x] The contract records affected lists, reset-to-zero behavior, preservation claims, evidence IDs, and engine-version scope.
- [x] Explicit reset preservation fields are conditional because `up-reset-search` flags determine list/index invalidation.
- [x] Implicit query/filter/focus transitions preserve list contents and retained filters.
- [x] Target lifetime after implicit index reset remains `UNKNOWN`, not preserved by compiler policy.
- [x] Contract evidence is pinned to the UserPatch 20130305-140519 patch note.
- [x] Contract version scope is reconciled against the pinned citation scope during catalog construction.
- [x] Transition evidence participates in citation completeness and provenance validation.

## Semantic consolidation

- [x] Query-change reset logic consumes the shared transition contract.
- [x] Filter-triggered index reset logic consumes the shared transition contract.
- [x] Focus-player remote reset logic consumes the shared transition contract.
- [x] Existing `DucSearchIndexState` and `_reset_search_index()` remain the state representation and state transformer.
- [x] Hostile tests prove custom transition scopes alter semantic behavior instead of leaving native facts duplicated in `semantic/duc.py`.

## Evidence boundary

- [x] UserPatch documents filter-triggered local/remote index reset.
- [x] UserPatch documents query/type/class-triggered relevant-index reset.
- [x] UserPatch documents focus-player-triggered remote-index reset.
- [ ] Runtime/native evidence proving target lifetime after implicit index reset remains unresolved.
- [ ] Runtime/native evidence proving failed `up-set-target-object` Action preservation remains unresolved.

## Verification

- [x] TDD red observed for the missing shared catalog lookup.
- [x] Full compiler verification passed after Task 1: 811 tests, native zero-findings, all OS/Python determinism jobs, and aggregate verification gate.
- [x] TDD red observed for private transition knowledge: query/filter/focus custom-contract regressions failed before semantic wiring.
- [x] Task 2 production refactor passed the full compiler verification gate.

## Scope rule

A transition is not promoted to `ENGINE_SEMANTICS_MAPPED` merely because it is common in community code. Native/version-scoped evidence remains the promotion boundary.
