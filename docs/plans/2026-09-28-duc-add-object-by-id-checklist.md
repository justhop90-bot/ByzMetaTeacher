# DUC `up-add-object-by-id` Repair Checklist

Date: 2026-09-28
Scope: bounded compiler support for Action-only `up-add-object-by-id`, with fail-closed list-state semantics pending native duplicate evidence.

## Native contract

- [x] AIRef schema records `(up-add-object-by-id <SearchSource> <typeOp> <Id>)`.
- [x] Supported SearchSource values are `search-local` and `search-remote`.
- [x] Supported typeOp forms are `c:`, `g:`, and `s:`.
- [x] Native command is registered as an Action in the engine semantic mapping.
- [x] Native citation `airef:duc:add-object-by-id` is pinned in the command catalog.
- [x] Local/remote capacity is inherited from the existing native DUC list contracts: 240/40.
- [x] Exact runtime object liveness, duplicate behavior, and already-present-ID behavior remain outside the compiler proof boundary.

## Compiler semantics

- [x] Add `DucListMutationKind.ADD_OBJECT`.
- [x] Model object-id insertion as a distinct DUC mutation, not as clean/remove/search.
- [x] Preserve the existing search cursor and filter state because this tranche does not claim a native cursor transition.
- [x] Treat list cardinality after the mutation as UNKNOWN because duplicate/already-present behavior is unproven.
- [x] Invalidate the list content fingerprint after the mutation.
- [x] Downgrade list-index targets on the affected list to UNKNOWN; direct native-ID targets are not list-derived and are left unchanged.
- [x] Dynamic `g:`/`s:` IDs receive no fabricated cardinality or membership proof.
- [x] Reject negative or malformed concrete IDs with `DUC-017` diagnostics.
- [x] Reject Fact evaluation with `DUC-005` because exact native Fact truth is unresolved in the available evidence.
- [x] Do not reject a full list solely from capacity; native full-list behavior is not established for this command.
- [x] Do not infer object existence, visibility, uniqueness, append position, or runtime success from the ID alone.

## Verification

Verified code-bearing head: `5aae6cbbf9164df5c67c00d9553a6d3cff65fdab`.

Compiler workflow **#2144**:
- 962 compiler tests passed.
- Native zero-findings acceptance passed.
- Focused persistent-state regression passed.
- All 9 native-support determinism jobs passed.
- Aggregate native-support snapshot comparison passed.
- Compiler verification gate passed.

The previous red TDD run (#2135) correctly failed on the unimplemented command. The next verification run (#2143) found one diagnostic-path defect for invalid concrete IDs; that defect was repaired and #2144 is the fresh green verification.

## Explicitly open

- Runtime truth for whether a requested object ID exists or is currently admissible to the engine.
- Duplicate/already-present-ID behavior: append, no-op, reposition/refresh, or other runtime behavior.
- Exact Fact truth semantics, pending stronger native evidence.
- Runtime oracle capture for local and remote duplicate-present cases.
- Remaining unpromoted DUC source/selection surfaces.

## Native oracle required before promotion

The runtime experiment must cover both `search-local` and `search-remote`: establish a known list, add a fresh concrete ID, add that same ID again, capture list contents/cardinality, and probe target identity/index before and after. The fixture must distinguish append, no-op, reposition/refresh, and failure/undefined outcomes. Corpus frequency is not proof of this branch.
