# DUC Target Consumer Semantics Checklist

Date: 2026-09-28
Base: main at eef52a4c0fc302864c577879eb801ae78d218050

## Native cross-check

- [x] `up-target-objects` has four arguments and Option is restricted to 0 or 1.
- [x] Option 1 targets only the object established by `up-set-target-object`.
- [x] Option 0 uses the local search results as the acting unit set and does not require a selected target object.
- [x] `up-clean-search` can reorder a retained search list by ObjectData/SearchOrder.
- [x] A list-index target is therefore dependent on list ordering after `up-set-target-object`.
- [x] UserPatch explicitly introduced Option 1 as the selected-object mode.
- [x] Community examples predominantly use Option 0 for local-list -> remote-list targeting and establish object targets separately for point/data reads.

## Current compiler gap

- [x] Semantic DUC handling currently treats every `up-target-objects` invocation as if a selected object target were required.
- [x] Option 0 therefore produces a false missing-target diagnostic.
- [x] Option values are not semantically validated.
- [x] `up-clean-search` SORT currently marks a list-index target's coordinate unstable but leaves target validity/proof VALID.
- [x] A subsequent Option 1 consumer can therefore consume a target whose list-coordinate identity is no longer provable.

## Scope

- [ ] Add a first-class native contract for `up-target-objects` consumer mode.
- [ ] Validate Option 0/1 in DUC semantics.
- [ ] Require initialized local search state for Option 0.
- [ ] Require an object target only for Option 1.
- [ ] Preserve direct native-ID target handling for Option 1.
- [ ] Degrade list-index targets to UNKNOWN after SORT.
- [ ] Keep DEDUPE and REMOVE_MATCHES behavior unchanged except where the consumer now distinguishes mode.
- [ ] Add deterministic consumer provenance/effect metadata.

## Hostile tests

- [x] Option 0 succeeds with local+remote searches and no selected object.
- [x] Option 0 rejects absent local search state.
- [x] Option 1 accepts a selected search-derived target.
- [x] Invalid Option is rejected.
- [x] SORT before Option 1 degrades a list-index target to UNKNOWN.
- [ ] Option 1 with a directly specified native object ID remains a liveness-unknown target rather than a list-index failure.
- [ ] Same behavior survives recurrent/branch analysis.

## Verification

- [ ] Observed red CI run on the tests-only commit.
- [ ] Focused DUC tests pass after implementation.
- [ ] Full compiler test suite passes.
- [ ] Native zero-findings acceptance passes.
- [ ] All 9 native-support determinism jobs pass.
- [ ] Aggregate native-support comparison passes.
- [ ] Compiler verification gate passes.

## Sources

- https://airef.github.io/commands/commands-details.html#up-target-objects
- https://airef.github.io/commands/commands-details.html#up-clean-search
- https://airef.github.io/tables/up-patch-notes.html
- https://github.com/lewisc64/aoe2ai
