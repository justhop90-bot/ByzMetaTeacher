# Construction Lifecycle Cross-Check and Implementation Checklist — 2026-09-28

Status legend: `[x]` verified; `[~]` partially implemented but not fully connected/verified; `[ ]` unfinished or blocked. Status labels identify the specific failure mode where relevant.

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
- [~] [FUNCTIONALLY-DISCONNECTED] Add typed construction phase beneath `PENDING`: `NONE`, `PLACEMENT_PENDING`, `FOUNDATION_PENDING`, `COMPLETE`; the IR and pure transition function exist, but the transition model is not the executable lowering source.
- [~] [PARTIAL] Enforce observation precedence: invalidation, COMPLETE, FOUNDATION_PENDING, PLACEMENT_PENDING, retry; the emitter reproduces this order, but the typed transition function is not wired into lowering and same-pass behavior is not yet covered.
- [ ] [UNFINISHED] COMPLETE must be canonically witnessed by `building-type-count` for the requested `BuildingId`; the current implementation accepts the demand's arbitrary `witness` expression.
- [x] FOUNDATION_PENDING witnesses `up-pending-objects`; it is not completion.
- [x] PLACEMENT_PENDING witnesses `up-pending-placement`; it is not completion.
- [~] [OPEN-LOOP] Retry requires completion false, pending-objects zero, and pending-placement false and returns the demand to `ACTIVE`; the subsequent action-issuance rule can observe that new `ACTIVE` state in the same pass, so the later-pass-only retry contract is not yet enforced.
- [x] Retry does not create a new demand identity or retry counter.
- [x] BUILD_PASS_SINGLETON remains a separate transient rule-pass exclusion.
- [~] [PARTIAL] Placement pending suppresses a new build request while the native placement witness remains true, but same-pass retry/reissue behavior is not yet closed.
- [~] [PARTIAL] Construction completion may be observed directly from ISSUED or PENDING; the emitter does so, but canonical construction-witness enforcement is still missing.
- [x] Resource arbitration/escrow ownership is untouched by construction phase observation.

## Compiler implementation

- [x] Add executable native adapter for `up-pending-placement`.
- [x] Add contracted engine-semantic mapping for `up-pending-placement`.
- [~] [FUNCTIONALLY-DISCONNECTED] Add typed construction IR and deterministic transition function; the implementation exists in `ir/construction.py` and `semantic/construction.py`, but executable lowering does not call the transition function.
- [x] Attach construction lifecycle metadata to `build` demands.
- [x] Emit construction-specific observation rules instead of unconditional `ISSUED -> PENDING` for build demands.
- [~] [OPEN-LOOP] Emit retry guards using both pending facts; the guards are present, but same-pass Goal visibility allows retry to fall through into the issuance rule in the same pass.
- [x] Preserve existing generic lifecycle behavior for train/research/non-construction actions.
- [ ] [BLOCKED] Add a native zero-findings fixture covering all construction phase predicates. The fixture exists, but the latest native gate reports 7 `undefined-constant` findings for `c: <BuildingId>` operands such as `castle`.
- [ ] [BLOCKED] Define and validate native `ObjectId` typing/binding for `c: <BuildingId>` operands, including the binding path used by `up-pending-objects` and `up-pending-placement`; do not silence the native validator warnings.
- [ ] [UNFINISHED] Enforce the canonical build-completion witness at semantic analysis time and reject a build demand whose witness is not a `building-type-count` observation for its own target.
- [ ] [FUNCTIONALLY-DISCONNECTED] Wire `transition_construction()` into executable semantic lowering/emission, or explicitly replace it with a single shared transition representation consumed by both.
- [ ] [OPEN-LOOP] Define the intended same-pass retry behavior and enforce the chosen contract. The current rule order permits RETRY to write ACTIVE and a later ACTION ISSUANCE rule to observe ACTIVE in the same pass.
- [ ] [UNFINISHED] Add order-sensitive emitter regression coverage asserting COMPLETE > FOUNDATION_PENDING > PLACEMENT_PENDING > RETRY > ACTION ISSUANCE and explicitly testing same-pass Goal visibility.
- [ ] [x] Keep `up-build`, builder allocation, controlled placement policy, and `up-reset-placement` as the next execution-control surface; do not silently invent them in the phase-observation tranche.

## Explicit non-goals

- [x] Do not model a numeric construction-progress percentage; current documented ObjectData progress values describe training/research, not generic building construction.
- [x] Do not treat builder allocation as a strategic demand.
- [x] Do not reuse BUILD_PASS_SINGLETON as persistent construction ownership.
- [x] Do not infer foundation existence from the build action itself.
- [x] Do not infer completion from timing or from pending-state disappearance alone.
