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

- [ ] Add a typed direct-object identity/proof state.
- [ ] Permit DucObjectRef to represent a direct object target without a search-list source.
- [ ] Store the zero-based native object ID as immutable target identity.
- [ ] Prevent search-list resets and list mutations from invalidating a direct-ID target merely because no list identity exists.
- [ ] Preserve direct-ID identity through branch joins when all paths agree on the same native object ID.
- [ ] Widen divergent direct IDs to UNKNOWN.
- [ ] Preserve current-pass proof semantics separately from native-ID identity.

## Native contract implementation

- [ ] Add up-set-target-by-id to NativeDucTargetContract.
- [ ] Encode its source requirement as no search list.
- [ ] Encode its target kind as OBJECT.
- [ ] Encode zero-based object-ID argument validation without fabricating a maximum range.
- [ ] Give it dedicated evidence/provenance identity.

## Semantic implementation

- [ ] Validate arity and typeOp/Id shape for up-set-target-by-id.
- [ ] Accept numeric non-negative IDs as concrete identity.
- [ ] Leave symbolic IDs unresolved rather than guessing.
- [ ] Set target validity to VALID with a dedicated native-ID proof when a concrete ID is authored.
- [ ] Preserve the direct target across list reset/filter/search mutations.
- [ ] Preserve direct target across search-list sort/dedupe/remove operations until the compiler has native evidence that the selected object itself was removed.
- [ ] Keep full native reset behavior authoritative.

## Hostile tests

- [ ] Direct target stores native object ID and has no list generation/index dependency.
- [ ] Direct target is not invalidated by up-reset-search local/remote flags.
- [ ] Direct target is not invalidated by up-reset-filters.
- [ ] Direct target survives list sort mutation.
- [ ] Direct target survives an unrelated remove-objects mutation.
- [ ] Direct target survives an unrelated list generation replacement.
- [ ] Divergent branch direct IDs widen to UNKNOWN.
- [ ] Same-ID branch joins preserve native-ID proof.
- [ ] Symbolic direct ID remains unresolved.
- [ ] Negative direct IDs are rejected deterministically.
- [ ] Existing search-index target behavior remains unchanged.
- [ ] Existing stale/unknown list-index mutation tests remain unchanged.

## Verification

- [ ] Focused DUC target-identity tests pass.
- [ ] Full compiler test suite passes.
- [ ] Native zero-findings acceptance passes.
- [ ] Cross-platform native-support determinism passes.
- [ ] Aggregate snapshot comparison passes.
- [ ] PR #71 prerequisite is green and merged before this tranche is merged.

## Explicitly unverified

- [ ] Runtime existence/liveness of a concrete native object ID.
- [ ] Exact engine semantics when an object with that ID dies, is removed, or leaves the targetable set.
- [ ] Any undocumented relationship between object IDs and player-specific object ownership over time.
- [ ] Exact target behavior after exotic engine-side target refresh operations.

## Sources

- https://airef.github.io/commands/commands-details.html#up-set-target-by-id
- https://airef.github.io/tables/up-patch-notes.html
- https://userpatch.aiscripters.net/reference.html
- https://github.com/lewisc64/aoe2ai