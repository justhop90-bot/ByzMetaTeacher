# Production Provider Readiness Native Evidence

Goal: connect the documented AIRef/UserPatch `up-train-site-ready` fact to the compiler's production lifecycle as a typed, fail-closed provider-readiness signal without changing training authorization.

Cross-reference:
- AIRef command schema: `up-train-site-ready`, UP Fact, syntax `(up-train-site-ready <typeOp> <UnitId>)`.
- AIRef/UserPatch notes: the fact checks whether a unit's training site is ready and available, without checks for cost or unit availability; it is intended to distinguish whether another training building is needed.
- Existing compiler boundary: `can-train` remains the training feasibility/admission fact; `building-type-count` remains provider-presence observation only.
- New semantic identity: `admissibility.train.site-ready`.
- Runtime status: OPEN until current target DE execution confirms the fact's behavior and its interaction with provider busy/queue state.

## Checklist

- [x] Cross-reference pinned AIRef schema and external command description.
- [ ] Add failing focused resolver/lifecycle/analyzer tests.
- [ ] Register native fact and engine semantic mapping.
- [ ] Add typed IR evidence with fail-closed invariants.
- [ ] Add registry resolver requiring literal `c:` UnitId and canonical numeric emission.
- [ ] Thread evidence through production analyzer/lifecycle without changing `can-train`.
- [ ] Add deterministic source-to-.per fixture and native zero-findings acceptance.
- [ ] Reconcile MUSE/gap/unknown documentation.
- [ ] Run focused tests and full Compiler verification.
- [ ] Merge after verification.

## Explicit non-goals

No promotion of `up-train-site-ready` to executable-safe training authorization. No queue-capacity change. No provider-building idle abstraction inferred from `building-type-count`. No birth/completion semantics.

## Remaining runtime boundary

The compiler records that the engine exposes a provider-readiness fact, but direct current-build verification remains necessary to determine exact behavior while a provider is busy, while queued work exists, and across queue exit/birth timing.
