# Production Birth and Queue-Exit Timing Native Evidence

Goal: add a typed, fail-closed compiler representation for production birth and queue-exit timing observations without claiming that a state transition, same-pass visibility, or exact engine timing has been proven.

Native evidence:
- DE update documentation states `unit-type-count-total` includes additional objects in the unit queue and `up-pending-objects` also counts additional queued objects.
- UserPatch documents `up-train-site-ready` as provider readiness, but does not define birth/queue-exit pass timing.
- Existing compiler semantics keep `unit-type-count` as the world-state completion/birth boundary, `unit-type-count-total` as current+queued observation, `up-pending-objects` as pending-work observation, and `game-time` as timing evidence.

Implementation boundary:
- `ProductionBirthTimingEvidence` records a `game-time` sample paired with a target `unit-type-count` observation.
- `ProductionQueueExitTimingEvidence` records a `game-time` sample paired with target `unit-type-count-total` and `up-pending-objects` observations.
- Both remain `OPEN`.
- They are observational records only. They do not become completion witnesses, do not authorize `train`, and do not infer a transition merely because a pending predicate is false.
- Symbolic source UnitIds are canonicalized in the analyzer before lifecycle records are created; direct registry timing resolvers consume canonical native IDs, matching the existing production observation boundary.

## Checklist

- [x] Cross-reference DE queue-count behavior and existing production lifecycle semantics.
- [x] Add failing focused lifecycle/resolver/analyzer tests.
- [x] Add typed OPEN birth-boundary and queue-exit timing IR.
- [x] Add fail-closed registry resolvers.
- [x] Thread timing evidence through `ProductionLifecycle`.
- [x] Add deterministic source fixture and native zero-findings gate.
- [x] Record the timing practice as PARTIAL/OPEN runtime evidence.
- [ ] Run the focused suite and full Compiler verification on the exact final main SHA.
- [ ] Merge after verification.

## Explicit non-goals

No timer scheduling, no event callback abstraction, no automatic pass-order inference, no "pending became zero therefore completion" rule, no queue-capacity change, and no promotion of timing evidence to executable-safe semantics.

## Runtime evidence gate

A controlled current-build DE experiment must record multiple passes around the first training completion with:
- `game-time`
- `unit-type-count`
- `unit-type-count-total`
- `up-pending-objects`
- `can-train`
- provider readiness
- emitted train rule execution markers where observable

The experiment must distinguish:
1. admission/queue insertion,
2. queued-only state,
3. active training state if separately observable,
4. object birth,
5. queue exit,
6. next-pass visibility.

Until that evidence exists, all timing records in the compiler remain OPEN.
