# AIRef + Community .per Meta Hygiene Master Checklist — 2026-09-26

## Purpose

This checklist defines the native-evidence and community-hygiene substrate that the LearnerAI compiler should create before it grows a larger MetaPattern catalog.

Authority boundary:

- AIRef: native command syntax, parameter typing, storage limits, documented engine behavior, version/patch notes, and benchmark observations.
- Community .per practice: recurring construction patterns, state hygiene, target representation, timers/cooldowns, pending guards, DUC search discipline, recovery idioms, and performance-aware usage.
- Compiler policy: deterministic ownership, provenance, promotion gates, fail-closed behavior, and semantic mappings derived from the above.

The compiler must never promote a community idiom into an engine fact merely because it is common.

## Cross-reference: community hygiene versus compiler design

| Hygiene requirement | AIRef evidence | Community evidence | Compiler treatment | Status |
|---|---|---|---|---|
| Named persistent targets use Goals rather than hidden compiler memory | Goals are persistent integer state with documented limits and comparisons | lewisc64/aoe2ai uses named Goal targets and unit-type-count-total; TheByzantineShadow composition policy writes a Goal target | NativeStorageUse.PERSISTENT_SCALAR; ownership remains compiler policy | IMPLEMENTED |
| Current + queued production is explicit | AIRef documents unit-type-count-total as including current/training/queued units in relevant UP semantics | TheByzantineShadow production materializes unit-type-count-total into cached Goal state | NativeWitness.UNIT_COUNT_TOTAL | IMPLEMENTED |
| Pending work suppresses duplicates but does not prove completion | AIRef documents pending-object state | Community production/build patterns use pending guards before another request | NativeWitness.PENDING_OBJECTS stays distinct from completion | IMPLEMENTED |
| can-* gates native action admission | AIRef documents Facts/Actions and can-* predicates | lewisc64/aoe2ai and TheByzantineShadow pair feasibility with action issuance | Native semantic mapping remains separate from action/completion | IMPLEMENTED |
| Policy target is separated from execution | AIRef gives low-level facts/actions, not strategic ownership | TheByzantineShadow explicitly separates composition policy from production authority | Future MetaPattern/ByzantinePolicy; no manager DSL | PARTIAL |
| Timers are cadence/throttle state, not truth | AIRef documents timers and timer-triggered facts | Community attack/DUC loops rearm timers explicitly | Native timer storage; no timer-as-completion witness | IMPLEMENTED |
| DUC lists/groups are mutable engine state | AIRef documents local/remote lists, groups, filters, Goal outputs, and hard capacities | lewisc64/aoe2ai DUC code resets/searches/targets explicitly; AIRef benchmarks document group reuse | Engine-managed storage types; full DUC lowering remains evidence-only | PARTIAL |
| DUC work is performance-budgeted | AIRef performance data is cardinality/context dependent | Community DUC code uses bounded searches and throttling | PerformanceEvidence is advisory only | IMPLEMENTED |
| Multi-Goal storage is span-based | AIRef documents multi-Goal commands and safe ranges | Community compiler prior art uses explicit storage allocation | NativeStorageUse.GOAL_SPAN + overlap validation | IMPLEMENTED |
| Hard per-pass constraints are distinct from benchmark cost | AIRef separately documents command restrictions and empirical benchmark results | Community code exposes loop hygiene but does not override engine legality | PassExecutionConstraint accepts documented native evidence only | IMPLEMENTED |
| Native behavior remains version-auditable | AIRef object tables and UserPatch notes are version/release scoped | Community scripts target concrete engine generations | VersionScope + immutable citation evidence | IMPLEMENTED |
| Source edits do not silently rewrite evidence | AIRef is a living, cumulative documentation corpus | Community projects preserve repository/source history | Excerpt hashes + source hashes + revalidation state | IMPLEMENTED |
| Benchmark observations are not semantic legality | AIRef benchmarks are empirical and contextual | Community performance practice is workload-dependent | Observation/generalization confidence split | IMPLEMENTED |
| State ownership and release are explicit | AIRef supplies mechanisms, not ownership doctrine | TheByzantineShadow separates execution, escrow, recovery ownership | Existing compiler ownership layer remains authoritative | PARTIAL |
| Recovery preserves valid intent | AIRef provides world-state observations rather than generic action-failure callbacks | TheByzantineShadow returns failed execution to reassessment | Existing recovery policy; native layer remains descriptive | PARTIAL |
| Source order is explicit | AIRef rules are recurrent native execution | Naga and other community scripts rely heavily on source order and persistent state | Existing source-order analyzer | IMPLEMENTED ELSEWHERE |
| No generic scheduler/manager language | AIRef is a rule/fact/action engine | Community bots use Goals/SNs/Timers/modules instead of a universal scheduler | Native contracts remain metadata; strategy stays above | ENFORCED |

## Implementation checklist

### Native evidence

- [x] Evidence kind distinguishes documented fact, inferred mapping, benchmark observation.
- [x] Confidence is separate from evidence kind.
- [x] Inferred mappings retain parent evidence and derivation.
- [x] Benchmarks cannot establish native legality or version scope.
- [x] VersionScope models AIRef version family and behavior-change boundaries.
- [x] Contradictory supported/excluded version families are rejected.
- [x] PerformanceEvidence records workload, cardinality, lag threshold, and context.
- [x] Observation confidence is separated from generalization confidence.
- [x] Performance metadata cannot become native legality.

### Native witnesses

- [x] Current count and current-plus-queued total are distinct types.
- [x] Pending work is distinct from completion evidence.
- [x] Research state is represented explicitly.
- [x] Witnesses require a native primitive and provenance.
- [x] Benchmark evidence cannot define native witness semantics.

### Native storage

- [x] Persistent scalar storage is distinct from engine-managed DUC state.
- [x] Goal/SN/Timer identifier ranges are enforced where represented.
- [x] Multi-Goal spans are explicit.
- [x] Documented safe Goal-span range is enforced.
- [x] DUC local-list capacity 240 and remote-list capacity 40 are enforced.
- [x] DUC groups do not consume Goal slots.
- [x] Goal spans cannot overlap.

### Pass execution

- [x] Documented per-pass command limits are represented.
- [x] Pass restrictions are separate from benchmark cost.
- [x] Hard pass constraints require documented native evidence.
- [x] Next-pass behavior is not encoded as a performance score.

### Citation auditability

- [x] Exact and normalized excerpt hashes are captured.
- [x] Full source snapshot hashes are supported.
- [x] Semantic locators are separate from URL identity.
- [x] Citation state transitions are explicit.
- [x] Source, locator, URL, excerpt, ambiguity, and outage results are distinct.
- [x] Existing promotion survives temporary source unavailability.
- [x] Changed or ambiguous excerpts block new promotion.
- [x] Historical citations remain immutable.

### Integration boundary

- [x] New substrate has focused unit tests.
- [x] Export native hygiene types from Compiler.primitives.
- [ ] Consume NativeWitness in capability completion contracts.
- [ ] Consume NativeStorageUse in package-storage binding for all namespaces.
- [ ] Consume PassExecutionConstraint in emission-time native validation.
- [ ] Consume VersionScope in patch-aware primitive support promotion.
- [ ] Replace string-only native evidence URLs with citation IDs.
- [ ] Add replayable AIRef evidence snapshots.
- [ ] Add community-practice fixtures for DUC, Goal/SN/Timer, and recovery.
- [ ] Promote NativeIdiom only after native contracts are consumed by lowering.
- [ ] Build MetaPattern only after native idiom coverage is sufficient.
- [ ] Bind ByzantinePolicy only after EffectiveCivData is the sole factual source.

## Acceptance gate

The substrate is accepted only if:

1. A documented AIRef fact cannot be represented as benchmark-only evidence.
2. A community-derived mapping retains parent evidence and derivation.
3. A performance observation cannot promote an unsupported native command.
4. Goal spans cannot overlap silently.
5. DUC lists cannot be represented as unlimited persistent memory.
6. Pending work cannot be typed as generic completion.
7. A full-source hash change does not invalidate an unchanged excerpt.
8. An excerpt change blocks new promotion.
9. Temporary AIRef source unavailability retains already-promoted evidence.
10. No scheduler, manager, or hidden compiler memory abstraction is introduced.

## Sources

AIRef:
- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/resources/articles/intro-to-commands.html
- https://airef.github.io/resources/articles/command-performance.html
- https://airef.github.io/resources/articles/enmipho-intro-to-duc.html
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/tables/objects.html
- https://airef.github.io/tables/up-patch-notes.html

Community:
- https://github.com/lewisc64/aoe2ai
- https://github.com/niektb/AI
- https://github.com/justhop90-bot/TheByzantineShadow
- https://github.com/justhop90-bot/Stock-Ai-
