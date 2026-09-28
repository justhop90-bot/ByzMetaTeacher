# Construction Lifecycle Cross-Check and Implementation Checklist — 2026-09-28

## Evidence cross-check

- [x] AIRef/UserPatch identifies `up-pending-objects` as a comparison Fact over pending build/train work.
- [x] AIRef/UserPatch identifies `up-pending-placement` as a Boolean Fact that is true while native placement is attempting to place the requested building.
- [x] UserPatch later repaired simultaneous-building behavior for `up-pending-placement`; the compiler may therefore use it as a native placement witness for the supported UP/DE contract.
- [x] `up-pending-placement` syntax is exactly `(up-pending-placement <typeOp> <BuildingId>)`; it has no comparison operator or numeric threshold.
- [x] `up-pending-objects` syntax is comparator-based and reports pending construction/production work.
- [x] `building-type-count` is the completed-world-state witness used by the existing compiler.
- [x] Community build rules pair `can-build` with `up-pending-objects` to suppress duplicate build requests.
- [x] Community scripts configure builder counts with `up-assign-builders`; this is persistent native builder policy, not the per-pass build mutex.
- [x] UserPatch documents one successful `build`/`up-build` per AI rule pass; later build commands silently fail.
- [x] UserPatch documents `up-reset-placement` as clearing placement requests that are blocked without a foundation.
- [x] Pending state is not completion and action issuance is not completion.

## Semantic rules to implement

- [x] Preserve generic lifecycle states: `ACTIVE -> ISSUED -> PENDING -> COMPLETE`.
- [x] Add typed construction phase beneath `PENDING`: `NONE`, `PLACEMENT_PENDING`, `FOUNDATION_PENDING`, `COMPLETE`.
- [x] Enforce observation precedence: invalidation, COMPLETE, FOUNDATION_PENDING, PLACEMENT_PENDING, retry.
- [x] COMPLETE witnesses `building-type-count`; it is terminal construction evidence.
- [x] FOUNDATION_PENDING witnesses `up-pending-objects`; it is not completion.
- [x] PLACEMENT_PENDING witnesses `up-pending-placement`; it is not completion.
- [x] Retry requires all three stronger observations to be false and returns the original demand to `ACTIVE`.
- [x] Retry does not create a new demand identity or retry counter.
- [x] BUILD_PASS_SINGLETON remains a separate transient rule-pass exclusion.
- [x] Placement pending suppresses a new build request until the native placement request clears.
- [x] Construction completion may be observed directly from ISSUED or PENDING; the compiler must not require an intermediate pending phase.
- [x] Resource arbitration/escrow ownership is untouched by construction phase observation.

## Compiler implementation

- [x] Add executable native adapter for `up-pending-placement`.
- [x] Add contracted engine-semantic mapping for `up-pending-placement`.
- [x] Add typed construction IR and deterministic transition function.
- [x] Attach construction lifecycle metadata to `build` demands.
- [x] Emit construction-specific observation rules instead of unconditional `ISSUED -> PENDING` for build demands.
- [x] Emit retry guards using both pending facts.
- [x] Preserve existing generic lifecycle behavior for train/research/non-construction actions.
- [x] Add native zero-findings fixture covering all construction phase predicates.
- [x] Add deterministic emitter regression coverage for construction rule ordering.
- [ ] Keep `up-build`, builder allocation, controlled placement policy, and `up-reset-placement` as the next execution-control surface; do not silently invent them in the phase-observation tranche.

## Explicit non-goals

- [x] Do not model a numeric construction-progress percentage; current documented ObjectData progress values describe training/research, not generic building construction.
- [x] Do not treat builder allocation as a strategic demand.
- [x] Do not reuse BUILD_PASS_SINGLETON as persistent construction ownership.
- [x] Do not infer foundation existence from the build action itself.
- [x] Do not infer completion from timing or from pending-state disappearance alone.
