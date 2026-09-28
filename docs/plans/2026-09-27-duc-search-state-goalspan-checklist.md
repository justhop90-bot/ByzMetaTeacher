# DUC Search-State GoalSpan Closure Checklist

Date: 2026-09-27
Target: `up-get-search-state` concrete four-Goal output-span semantics.

## Cross-check before implementation

### Native engine / AIRef
- [x] `up-get-search-state` is an Action with one OutputGoalId input in the checked-in AIRef command schema.
- [x] AIRef documents the command as a four-consecutive-Goal writer.
- [x] AIRef data limits establish that the four-goal block must fit inside the native Goal namespace; start 15996 is the highest safe width-4 start.
- [x] AIRef distinguishes the command's output Goal block from ordinary single Goal storage.
- [x] UserPatch history explicitly records a correction to the direction of the `up-get-search-state` output parameter.
- [x] Community `aoe2ai` source contains real recurrent DUC chains using `up-get-search-state` after searches and then consuming its Goal results in later rules.

### Current compiler
- [x] `runtime_storage_contracts.py` already derives `up-get-search-state.OutputGoalId` as a width-4 `GoalSpan` contract with explicit bounds.
- [x] `runtime_binding.py` already understands four-goal spans and interval occupancy.
- [x] `DucGoalOutputSpan` already carries generation and overwrite provenance, but incorrectly assumes width 1.
- [x] `DucSearchStateObservation` already records the symbolic output GoalId but has no concrete span object.
- [x] `analyze_duc()` already has the correct state location for persistent output-span provenance.
- [x] Group-size output already demonstrates the desired generation/overwrite provenance pattern.
- [x] Recurrent firing is already coupled to DUC state transitions, so impossible search-state writers will not create phantom spans after this tranche.

### Architectural boundary
- [x] Do not invent a second DUC DSL.
- [x] Do not simulate search results beyond existing cardinality ranges.
- [x] Do not fold DUC output spans into ordinary persistent Goal ownership.
- [x] Keep native parser legality authoritative.
- [x] Treat non-numeric OutputGoalId identifiers as unresolved at this semantic layer rather than pretending to resolve defconsts without the effective constant environment.

## Implementation

### IR
- [ ] Allow `DucGoalOutputSpan` widths 1 and 4 with native range validation.
- [ ] Preserve generation, overwrite-generation, writer provenance, and pass identity for width-4 outputs.
- [ ] Add concrete `output_span` metadata to `DucSearchStateObservation`.
- [ ] Keep existing width-1 group-size behavior unchanged.

### Semantic analysis
- [ ] Derive the search-state output width/range from the shared native storage contract.
- [ ] Validate numeric OutputGoalId against the four-goal contract.
- [ ] Create and persist a concrete width-4 span in `goal_output_spans`.
- [ ] Record previous writer generation/provenance when the same output span is rewritten.
- [ ] Preserve the observation's existing cardinality fields unchanged.
- [ ] Fail closed with a deterministic DUC diagnostic when a numeric start cannot fit the width-4 contract.
- [ ] Leave symbolic OutputGoalId unresolved rather than manufacturing a GoalId.

### Tests
- [ ] Width-4 span is created for a valid numeric OutputGoalId.
- [ ] Span provenance names `up-get-search-state`.
- [ ] Repeated writes to the same four-goal block advance generation and preserve overwrite provenance.
- [ ] Start 15996 is accepted.
- [ ] Start 15997 is rejected with deterministic DUC diagnostics.
- [ ] Existing group-size width-1 tests remain unchanged.
- [ ] Existing branch/loop/recurrent DUC tests remain unchanged.

### Verification
- [ ] Focused DUC semantic suite passes.
- [ ] Full compiler test suite passes.
- [ ] Native zero-findings fixtures pass.
- [ ] Cross-platform native-support determinism jobs pass.
- [ ] Aggregate snapshot comparison passes.
- [ ] Only then merge to `main`.

## Evidence-backed acceptance

The compiler should be able to answer deterministically for `up-get-search-state 41`:

1. It writes four consecutive Goals, 41..44.
2. The output span has native contract identity and source/rule provenance.
3. A second write to the same start overwrites the prior span generation.
4. The operation does not silently become ordinary one-slot Goal storage.
5. A start of 15997 is not accepted because the fourth output would exceed Goal 16000.
6. The compiler makes no claim about the actual search counts beyond the existing conservative cardinality ranges.

## Sources

- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/parameters/parameters-index.html
- https://airef.github.io/tables/up-patch-notes.html
- https://github.com/lewisc64/aoe2ai
