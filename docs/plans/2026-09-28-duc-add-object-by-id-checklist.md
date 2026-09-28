# DUC `up-add-object-by-id` Repair Checklist

Date: 2026-09-28
Scope: bounded compiler support for Action-only `up-add-object-by-id`.

## Native contract

- [x] AIRef schema records `(up-add-object-by-id <SearchSource> <typeOp> <Id>)`.
- [x] Supported SearchSource values are `search-local` and `search-remote`.
- [x] Supported typeOp forms are `c:`, `g:`, and `s:`.
- [x] Native command is registered as an Action in the engine semantic mapping.
- [x] Native citation `airef:duc:add-object-by-id` is pinned in the command catalog.
- [x] Local/remote capacity is inherited from the existing native DUC list contracts: 240/40.
- [x] Exact runtime object liveness and duplicate behavior remain outside the compiler proof boundary.

## Compiler semantics

- [x] Add `DucListMutationKind.ADD_OBJECT`.
- [x] Model object-id append as a distinct DUC mutation, not as clean/remove/search.
- [x] Preserve the existing search cursor and filter state.
- [x] Preserve an existing object target because append-at-end does not shift existing list indices.
- [x] Concrete `c:` IDs increase known cardinality by one when the list is not proven full.
- [x] Dynamic `g:`/`s:` IDs do not receive fabricated cardinality proof.
- [x] Reject negative or malformed concrete IDs with `DUC-017` diagnostics.
- [x] Reject Fact evaluation with `DUC-005` because exact native Fact truth is unresolved in the available evidence.
- [x] Reject appends to compiler-proven full lists with `DUC-014`.
- [x] Do not infer object existence, visibility, uniqueness, or runtime success from the ID alone.

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
- Duplicate-ID behavior when the object is already retained.
- Exact Fact truth semantics, pending stronger native evidence.
- Remaining unpromoted DUC source/selection surfaces.
