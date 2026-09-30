# DUC Target-Lifetime Evidence and Repair Checklist

Date: 2026-09-28
Branch: duc-native-transition-contracts
Scope: outstanding DUC target-lifetime boundaries plus repairs justified by authoritative/public evidence.

## Evidence classification

### ENGINE_SEMANTICS_MAPPED

| Area | Finding | Evidence |
|---|---|---|
| Search-list identity | Local and remote DUC lists store object IDs; local capacity is 240 and remote capacity is 40. | AIRef Enmipho DUC tutorial |
| Target establishment | `up-set-target-object` selects an object from the search lists using a zero-based index. | AIRef Enmipho DUC tutorial; AIRef parameter/index inventory |
| Target-data access | `up-get-object-data` reads the selected object established by `up-set-target-object`; `up-get-object-target-data` reads the selected object's target. | AIRef command inventory / UserPatch patch notes |
| Invalid target index Fact | `up-set-target-object` returns false as a Fact when it cannot set the requested index. | UserPatch 20130302-150016 patch note |
| Zero-result search Fact | `up-find-local` / `up-find-remote` return false as Facts on zero results. | UserPatch 20130302-150016 patch note |
| Full reset | `up-full-reset-search` clears prior list IDs and search filters. | AIRef Enmipho DUC tutorial; UserPatch release history |
| Index resets | Filter changes reset local/remote search offsets; changed type/class resets the relevant index; focus-player change resets remote. | UserPatch 20130305-140519 patch note |
| Clean-search mutation | `up-clean-search` sorts a retained local/remote list. | AIRef command schema and performance benchmark |
| Remove mutation | `up-remove-objects` mutates retained lists by removing matching entries. | AIRef DUC tutorial and performance benchmark |
| Search/target workflow | Community and AIRef examples consistently establish a search list, select an object, then read/use that target. | AIRef DUC tutorial; lewisc64/aoe2ai |

### DOCUMENTED_BUT_NOT_TARGET_LIFETIME_PROOF

- Community scripts show `up-clean-search` followed by `up-set-target-object ... c:0`, but this documents re-selection after sorting, not preservation of an already-selected target.
- Community scripts use `up-reset-search`, `up-remove-objects`, and subsequent target establishment, but do not state whether an existing target survives those mutations.
- Performance benchmarks prove that sorting/removal are real list operations, not how the selected-target reference is represented.

### OPEN_NATIVE_BOUNDARIES

These remain UNKNOWN because no authoritative source or reproducible native observation found in this pass directly establishes the runtime effect:

1. Failed `up-set-target-object` Action with an existing target: preserve, invalidate, or replace.
2. Failed `up-set-target-object` Action against an uninitialized/empty list beyond documented Fact failure.
3. Target lifetime after query/type/class search-index reset.
4. Target lifetime after filter-triggered search-index reset.
5. Target lifetime after focus-player remote-index reset.
6. Target lifetime after `up-clean-search` reordering.
7. Target lifetime after `up-remove-objects`, including deletion before, after, or of the selected object.
8. Runtime liveness of a native-ID target after the underlying world object dies/disappears.
9. Historical edge behavior around DUC reset/mutation remains unsuitable for promotion without current-build observation; UserPatch notes document several DUC stability fixes but do not define target lifetime.

## Repairs

### R1 — Proven-empty target establishment

Status: IMPLEMENTED.

Rule:
- If the compiler has a current list generation with cardinality exactly `0..0` and the list path is not ambiguous, `up-set-target-object` cannot establish an object target at any index.
- The Action path emits `DUC-014` and leaves any existing target untouched when failed-action preservation is unresolved.
- The Fact path returns `GUARANTEED_FALSE`.

Reason:
- UserPatch documents zero-result search Facts as false.
- The compiler already represents proven empty search results as cardinality `0..0`.
- Allowing index 0 target establishment from that state would create impossible compiler state.

### R2 — Capacity boundary coverage

Status: IMPLEMENTED / COVERED.

- Local capacity: 240, first invalid index: 240.
- Remote capacity: 40, first invalid index: 40.
- Capacity checks remain native-contract driven and fail closed.

### R3 — Failed Action preservation

Status: NOT PROMOTED.

- Native target contract keeps `failed_action_preserves_previous_target = None`.
- Compiler may preserve its existing static state for analysis continuity, but emits `DUC-007` rather than claiming runtime preservation.
- Native capture candidate exists for the exact `search-local c:240` failure after an existing target.

### R4 — Clean-search target identity

Status: NOT PROMOTED.

- Native capture candidate exists.
- Candidate requires the selected object to actually move from index 0 to index 2 after descending sort.
- Only a native observation comparing pre/post native object IDs can distinguish preserved identity from retarget-by-index.

### R5 — Empty/uninitialized Action capture

Status: NOT PROMOTED.

- Native capture candidate exists.
- No compiler-side runtime claim is derived from the candidate.

### R7 — Explicit object-liveness boundary

Status: IMPLEMENTED / CLOSED AS COMPILER MODELING.

- `DucTargetStatus` remains the compiler-side reference state (`VALID`, `STALE`, `UNKNOWN`).
- `DucTargetProof` remains the provenance/proof reason for that reference state.
- `DucObjectLiveness` is a separate field and defaults to `RUNTIME_DEPENDENT`.
- Reset, mutation, filter-generation changes, branch joins, loop widening, and pass advancement do not silently convert reference invalidation into object death.
- `WITNESSED_ALIVE` / `WITNESSED_GONE` remain reserved for direct native/world-state evidence.

### R6 — Oracle guardrails

Status: IMPLEMENTED.

- `up-set-target-object` is now an allowed native-oracle command under the schema.
- Capture candidates live outside `fixtures/` and remain explicitly UNVERIFIED.
- Candidate regression tests prevent accidental promotion.

## Native capture promotion rule

A target-lifetime claim becomes `ENGINE_SEMANTICS_MAPPED` only when:
1. the exact AoE2DE build, patch, AI layer, and platform are recorded;
2. the setup creates a uniquely identifiable target;
3. the mutation/reset/failure under test is executed by the native runtime;
4. post-state target selection, native object ID, index, and target-data access are directly observed;
5. the relevant assertion is reproducibly PASS;
6. the native observation is promoted from `candidates/` to `fixtures/`.

Community usage, AIRef examples, and performance measurements are supporting evidence only and cannot close target-lifetime boundaries. They also cannot be used to populate `WITNESSED_ALIVE` or `WITNESSED_GONE`.

## Sources reviewed

- AIRef UserPatch patch notes: https://airef.github.io/tables/up-patch-notes.html
- AIRef Enmipho's Introduction to DUC: https://airef.github.io/resources/articles/enmipho-intro-to-duc.html
- AIRef AI Command Performance Benchmarks: https://airef.github.io/resources/articles/command-performance.html
- AIRef command/index and parameter inventories maintained in the repository.
- lewisc64/aoe2ai community scripting examples: https://github.com/lewisc64/aoe2ai
- AI Scripters community discussions and DUC examples surfaced during the research pass.
- Current repository native oracle schema/candidates and compiler semantics.

## Audit conclusion

The public evidence is sufficient to strengthen the compiler where it can prove impossibility. It is not sufficient to promote any outstanding target-lifetime mutation/reset behavior to a native preservation or invalidation contract. The remaining UNKNOWN states are therefore deliberate evidence gates, not unfinished guesses.
