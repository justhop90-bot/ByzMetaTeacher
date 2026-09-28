# DUC Search-Index Reset Closure Checklist

Date: 2026-09-27
Base: concrete four-Goal up-get-search-state tranche

## Evidence cross-check

### Native / AIRef
- [x] DUC Index is the zero-based offset into the local/remote search lists.
- [x] LocalIndex and RemoteIndex in up-reset-search clear their respective search offsets independently.
- [x] up-reset-filters clears search indices without clearing search results.
- [x] filter-include, filter-exclude, and filter-range automatically reset both local and remote search index offsets.
- [x] up-filter-distance and up-filter-garrison are documented as doing the same index-reset work as filter-range.
- [x] A find-local/find-remote query whose type/class changes resets the relevant search offset.
- [x] A change in remote focus-player resets the remote search offset, but the current generic compiler has no authoritative focus-player state input. That portion remains explicitly unresolved in this tranche.
- [x] Search lists remain bounded at 240 local / 40 remote objects.
- [x] Community code uses explicit reset/filter/search sequences around DUC loops rather than treating filters as pure stateless predicates.

### Current compiler
- [x] Search-list state tracks retained generation and filter lineage.
- [x] Filter state already survives across rules and passes.
- [x] up-reset-search already parses LocalIndex/LocalList/RemoteIndex/RemoteList and records index invalidation booleans.
- [x] Filter contracts already identify retained filters but do not yet expose index-reset semantics.
- [x] Search operations currently have no explicit search-index input/output/reset metadata.
- [x] Search state has no explicit offset/query-signature state.
- [x] Target proofs currently depend on list generation/index stability, so index-reset lineage is a prerequisite for stronger target identity.

## Architecture boundary
- [x] Do not simulate the engine's object iteration cursor or claim exact post-search offsets without evidence.
- [x] Record deterministic reset causes and the known pre-reset offset only where it is provable.
- [x] Query-signature changes are limited to authored find arguments; focus-player changes remain unknown until the compiler models the authoritative focus-player state writer.
- [x] Keep retained list contents separate from search cursor state.
- [x] Keep index reset semantics separate from full list reset semantics.

## Implementation

### IR
- [x] Add typed search-index state to each DUC list.
- [x] Track a deterministic query signature for the most recent find-local/find-remote family.
- [x] Track an index generation/epoch independent of list generation.
- [x] Track whether the current offset is known or unknown.
- [ ] Add search-index metadata to DucSearchOperation.
- [x] Record reset reason categories without pretending to know the exact post-find cursor.

### Native contracts
- [x] Extend NativeDucFilterContract with explicit resets_search_indices.
- [x] Mark all direct-unit filter commands that reset indices according to UserPatch evidence.
- [x] Preserve existing filter retention semantics.

### Semantic analysis
- [x] Initialize local/remote index state explicitly at zero.
- [x] On up-reset-search, reset only the requested offsets and retain lists unless list flags are also set.
- [x] On up-reset-filters, reset both offsets while retaining result lists.
- [x] On direct-unit filter mutations, reset both offsets before subsequent searches.
- [x] On find-local/find-remote query-family changes, reset the relevant offset before the search.
- [x] Preserve index reset lineage in search provenance and content fingerprints.
- [x] Leave exact post-search offset unknown rather than fabricating an increment.
- [x] Preserve existing list-generation cardinality behavior.

### Tests
- [x] Initial index state is explicitly zero/known.
- [ ] up-reset-search 1 0 0 0 resets only local index.
- [ ] up-reset-search 0 0 1 0 resets only remote index.
- [ ] up-reset-filters resets both indices without clearing list generations.
- [x] Every filter command that inherits filter-range reset semantics resets both indices.
- [x] Switching local query type/class resets local index.
- [x] Switching remote query type/class resets remote index.
- [x] Unchanged query signatures do not introduce a spurious reset.
- [x] Focus-player mutation remains explicitly unknown rather than inferred.
- [ ] Existing list-retention and target tests remain unchanged.

### Evidence boundary retained

- [x] Exact post-find cursor advancement and remote focus-player mutation remain unresolved and are not invented.

### Verification
- [ ] Focused DUC semantic tests pass.
- [ ] Full compiler test suite passes.
- [ ] Native zero-findings acceptance passes.
- [ ] Cross-platform native-support determinism passes.
- [ ] Aggregate snapshot comparison passes.
- [ ] Only then merge to main.

## Acceptance

For a sequence such as:

find-local villager -> find-local archer

the compiler must represent the second search as a query-signature transition and therefore a local index reset, while preserving the retained local result-list generation semantics.

For:

find-local villager -> filter-distance -> find-local villager

the filter action must reset the local and remote index epochs even though the retained result lists remain present.

For:

find-local villager -> reset-filters

the filter reset must not be confused with list reset.

The compiler must not claim where the engine cursor lands after the search. That is a runtime fact, not a decorative integer invented to make the IR look complete.

## Sources

- https://airef.github.io/parameters/parameters-index.html
- https://airef.github.io/tables/up-patch-notes.html
- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/resources/articles/command-performance.html
- https://github.com/lewisc64/aoe2ai