# DUC Post-Search Cursor Semantics Checklist

Date: 2026-09-27

Target: exact abstract semantics for `up-find-local` and `up-find-remote`, including Fact/Action use, cursor advancement, repeated searches, resets, and `up-get-search-state` observation.

## Native cross-check

- [x] AIRef command contract confirms `up-find-local` and `up-find-remote` use four search predicate operands; the final value is part of the predicate, not a result-count budget.
- [x] UserPatch documents both commands as valid Facts or Actions.
- [x] UserPatch documents zero-result find-local/find-remote as a false Fact result.
- [x] UserPatch documents the search-index offset as persistent state used by subsequent find commands.
- [x] UserPatch documents query/type/class changes as search-index resets.
- [x] UserPatch documents focus-player changes as a remote-search-index reset.
- [x] UserPatch documents filter changes as both local and remote index resets.
- [x] UserPatch documents a crash fix when the search list reaches its end, establishing that end-of-scan is a native boundary that must be represented explicitly.
- [x] UserPatch documents `up-get-search-state` as exposing total local/remote list counts and the number added by the most recent search.
- [x] AIRef data limits establish the local list capacity at 240 and remote list capacity at 40.
- [x] Native command-performance evidence supports early termination when the search list reaches capacity; exact runtime scan position remains world-state dependent.
- [x] Community `.per` usage confirms recurrent find chains, explicit resets, and subsequent search-state reads.

## Semantic contract

- [x] Search index is modeled as a scan frontier, not as list cardinality.
- [x] Initial search state starts at offset 0 with a distinct INITIAL disposition.
- [x] Query/type changes reset the relevant index to offset 0 before the next scan.
- [x] Focus-player mutation resets only the remote index.
- [x] Explicit search resets restore the relevant index to offset 0.
- [x] A normal find operation records that the native scan advanced from the current frontier, while the exact numeric post-search offset remains UNKNOWN without runtime object ordering.
- [x] A search beginning at a proven end-of-scan state is modeled as a guaranteed-empty result and remains AT_END.
- [x] A search against a destination list already known to be full is modeled as guaranteed-empty and BLOCKED_BY_CAPACITY.
- [x] Numeric index_after remains absent when the engine's runtime scan endpoint cannot be statically proven.
- [x] Repeated same-query searches preserve the accumulated cursor context rather than spuriously resetting it.
- [x] `up-get-search-state` observes the resulting list cardinality/last-search cardinality and compiler-tracked cursor disposition without mutating the cursor.
- [x] Search Facts and Actions use the same native search-state transition.
- [x] Search Facts explicitly record runtime-dependent truth or guaranteed-false truth when the result is provably empty.
- [x] No artificial result-count parameter is inferred from the final `up-find-*` predicate operand.

## Implementation

- [x] Add cursor disposition and search-result disposition to the DUC IR.
- [x] Add Fact-vs-Action result provenance to `DucSearchOperation`.
- [x] Bind the native search contracts to a scan-frontier model and Fact support.
- [x] Centralize search-state transitions so local and remote searches cannot drift semantically.
- [x] Run the same centralized transition for Fact-form searches before rule actions.
- [x] Preserve focus-player provenance through the cursor transition.
- [x] Preserve cursor state through branch joins and loop widening.
- [x] Extend `up-get-search-state` observations with compiler-side cursor disposition.

## Hostile regression coverage

- [x] First local search advances from initial state.
- [x] Repeated identical local searches consume the prior runtime cursor state.
- [x] First remote search advances from the native focus-player default.
- [x] Focus-player mutation resets remote cursor before the next search.
- [x] Explicit reset returns the cursor to offset 0.
- [x] Query change resets the cursor.
- [x] Filter/reset interactions preserve reset-before-search behavior.
- [x] Proven end-of-scan produces guaranteed-empty / guaranteed-false Fact behavior.
- [x] A known-full list produces guaranteed-empty / capacity-blocked behavior.
- [x] Fact-form find-local mutates search state and reports runtime-dependent truth.
- [x] Fact-form find-remote mutates search state and can then be reset by an action.
- [x] `up-get-search-state` sees post-search last-search cardinality and cursor disposition.
- [x] Branch/loop widening cannot fabricate a single concrete cursor after divergent runtime paths.
- [x] Native contract integration asserts Fact support and the scan-frontier/capacity model.

## Verification gate

- [ ] Focused DUC semantic tests execute on the exact final head.
- [ ] Full compiler regression executes on the exact final head.
- [ ] Native zero-findings acceptance executes on the exact final head.
- [ ] All native-support determinism jobs execute on the exact final head.
- [ ] Cross-platform aggregate snapshot comparison executes on the exact final head.
- [ ] Compiler verification gate passes on the exact final head.
- [ ] Only then merge into `main`.

## Deliberate runtime boundaries

The compiler does not invent a numeric post-search cursor when the runtime object ordering and visibility set are not statically known. It also does not claim that `up-get-search-state` directly exposes the cursor: the engine exposes list counts and last-search counts, while cursor disposition is retained as compiler-side provenance. Runtime object identity, exact scan endpoint, and exact success/failure for an unconstrained live-world search remain runtime-dependent unless the abstract state already proves end or capacity exhaustion.

## Evidence

- https://airef.github.io/tables/up-patch-notes.html
- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/resources/articles/command-performance.html
- https://userpatch.aiscripters.net/reference.html
- https://github.com/lewisc64/aoe2ai
