# DUC Target Identity Closure Checklist

Date: 2026-09-28
Base: compiler-duc-search-index-resets

## Native cross-check

- [x] up-set-target-object selects the current target from a search-list source and zero-based index.
- [x] up-set-target-by-id selects the target directly from a zero-based object ID.
- [x] up-set-target-by-id is a distinct native targeting path and must not be forced through search-list generation semantics.
- [x] up-target-objects consumes the selected target state.
- [x] up-reset-search can discard search-list state, while full reset clears direct-unit targeting state.
- [x] Native patch history documents failures when a target index cannot be set and a historical bug involving target reads after discarded search objects.
- [x] Current engine/update documentation still treats target identity and search-list identity as separate concerns.

## Community cross-check

- [x] lewisc64/aoe2ai demonstrates search-local/search-remote -> up-set-target-object -> up-target-objects chains.
- [x] Community usage commonly re-establishes target from the current search list after DUC resets, reinforcing that list-index targets are not durable object identity.
- [x] The repository's own community-retained-search references distinguish search scope from target scope.

## Current compiler gap

- [x] DucObjectRef already has native_object_id but it is always unresolved for up-set-target-object.
- [x] Object target validity currently derives primarily from source-list generation, index stability, pass retention, and filter lineage.
- [x] up-set-target-by-id is present in the checked-in native command schema but absent from NativeDucTargetContract and semantic DUC handling.
- [x] This means the compiler cannot represent the strongest available target identity proof even when the authored script provides a direct object ID.

## Architecture boundary

- [x] Add direct object-ID identity only for up-set-target-by-id.
- [x] Do not invent a global object existence simulator or infer object death.
- [x] Do not claim that an object ID remains live forever. Native runtime remains authoritative.
- [x] Preserve list-index target behavior unchanged unless the target explicitly carries direct object identity.
- [x] Keep direct-ID targets independent of search-list generation and search-index epoch.

## IR implementation

- [x] Add a typed direct-object identity/proof state.
- [x] Permit DucObjectRef to represent a direct object target without a search-list source.
- [x] Store the zero-based native object ID as immutable target identity.
- [x] Prevent search-list resets and list mutations from invalidating a direct-ID target merely because no list identity exists.
- [x] Preserve direct-ID identity through branch joins when all paths agree on the same native object ID.
- [x] Widen divergent direct IDs to UNKNOWN.
- [x] Preserve current-pass proof semantics separately from native-ID identity.

## Native contract implementation

- [x] Add up-set-target-by-id to NativeDucTargetContract.
- [x] Encode its source requirement as no search list.
- [x] Encode its target kind as OBJECT.
- [x] Encode zero-based object-ID argument validation without fabricating a maximum range.
- [x] Give it dedicated evidence/provenance identity.

## Semantic implementation

- [x] Validate arity and typeOp/Id shape for up-set-target-by-id.
- [x] Accept numeric non-negative IDs as concrete identity.
- [x] Leave symbolic IDs unresolved rather than guessing.
- [x] Record concrete native-ID proof while leaving runtime target liveness UNKNOWN.
- [x] Preserve the direct target across list reset/filter/search mutations.
- [x] Preserve direct target across search-list sort/dedupe/remove operations until the compiler has native evidence that the selected object itself was removed.
- [x] Keep full native reset behavior authoritative.

## Hostile tests

- [x] Direct target stores native object ID and has no list generation/index dependency.
- [x] Direct target is not invalidated by up-reset-search local/remote flags.
- [x] Direct target is not invalidated by up-reset-filters.
- [x] Direct target survives list sort mutation.
- [x] Direct target survives an unrelated remove-objects mutation.
- [x] Direct target survives an unrelated list generation replacement.
- [x] Divergent branch direct IDs widen to UNKNOWN.
- [x] Same-ID branch joins preserve native-ID proof.
- [x] Symbolic direct ID remains unresolved.
- [x] Negative direct IDs are rejected deterministically.
- [x] Existing search-index target behavior remains unchanged.
- [x] Existing stale/unknown list-index mutation tests remain unchanged.

## Verification

- [ ] Focused DUC target-identity tests pass.
- [ ] Full compiler test suite passes.
- [ ] Native zero-findings acceptance passes.
- [ ] Cross-platform native-support determinism passes.
- [ ] Aggregate snapshot comparison passes.
- [ ] PR #71 prerequisite is green and merged before this tranche is merged.

## Explicitly unverified

- [x] Runtime existence/liveness of a concrete native object ID.
- [x] Exact engine semantics when an object with that ID dies, is removed, or leaves the targetable set.
- [x] Any undocumented relationship between object IDs and player-specific object ownership over time.
- [x] Exact target behavior after exotic engine-side target refresh operations.

## Sources

- https://airef.github.io/commands/commands-details.html#up-set-target-by-id
- https://airef.github.io/tables/up-patch-notes.html
- https://userpatch.aiscripters.net/reference.html
- https://github.com/lewisc64/aoe2ai