# Dropsite Resource-Front Liveness Repair

Date: 2026-10-09
Target: checked-in `Byzantine.per` on `main`, with regression coverage.

## Problem statement

Runtime observation: after the first lumberyard or mining camp is placed, later resource-front camps are not issued even when the relevant resource is distant. The current `.per` has resource searches followed by result-count gates, but the gates use GoalIds outside the four-Goal output span written by `up-get-search-state`. Therefore those conditions are not reading the search results produced by the immediately preceding search. Several camp floors also have candidate limits or indices that do not match the floor's prior-candidate history.

## Evidence classes

- **ENGINE FACT:** AIRef identifies `up-get-search-state` as a four-consecutive-Goal output, and the native Goal namespace ends at 16000. Sources: [AIRef command index](https://airef.github.io/commands/commands-index.html), [AIRef data limits](https://airef.github.io/resources/articles/data-limits.html), and [AIRef DUC guide, search-state output order](https://airef.github.io/resources/articles/enmipho-intro-to-duc.html#first-example-local-search-and-target-point).
- **COMMUNITY EVIDENCE:** the DUC example in [lewisc64/aoe2ai](https://github.com/lewisc64/aoe2ai) calls `up-get-search-state 1` and consumes Goals 1 and 3 in subsequent rules, supporting the conventional four-field local/remote search-state layout. AIRef's DUC guide defines the outputs as: local list total, latest local-search count, remote list total, latest remote-search count. The remote-list total is the third member (start + 2) and is the correct cardinality guard before indexing `search-remote`; the fourth member is a last-search count and must not be confused with current list size.
- **COMPILER POLICY:** each remote index must have a count gate proving the stored remote list contains that index; an incomplete search or build attempt must not release the camp demand.
- **OPEN / UNKNOWN:** the exact in-game order and spatial distribution of resource objects, placement success, and whether a selected resource point is a sufficiently distinct frontier require runtime observation.

## Task-by-task plan

### Task 1: Lock the output-slot and indexing contract
- [ ] Add a regression that maps every resource-camp `up-get-search-state` to its third output Goal (remote-list total).
- [ ] Assert that output spans do not overlap and remain within the native Goal limit.
- [ ] Assert candidate count and index sequence for wood, gold, and stone, accounting for the first-floor implementation rather than applying a blanket index shift.

### Task 2: Correct search-result Goal binding
- [ ] Remap each `*-search-remote-count-*` constant to `*-search-state-* + 2`.
- [ ] Include the Dark Age mill search because it uses the same mismatched output/count contract.
- [ ] Preserve separate storage for point pairs and other search-state spans.

### Task 3: Repair candidate count and index admission
- [ ] Keep gold's sequential DUC indices: floor 1 selects index 0; each subsequent floor advances to the next index.
- [ ] Make wood floor 2 search enough candidates to advance beyond floor 1's index 0, then select index 1 only when the third search-state output proves the remote list contains it.
- [ ] Since stone floor 1 uses native direct construction rather than an indexed DUC target, make stone floor 2 select index 0 and increment subsequent floors.
- [ ] Keep the existing singleton build claim, capability gate, pending/placement-pending guards, completion witness, and retry barrier intact.

### Task 4: Test construction semantics and preserve scope
- [ ] Confirm a failed search cannot satisfy the count gate or issue a point build.
- [ ] Confirm an issued build remains pending until a completed-building witness exists.
- [ ] Avoid a second camp scheduler, new timer, or strategic-number policy rewrite.

### Task 5: Verify and synchronize the runtime artifact
- [ ] Run focused resource-front and camp artifact tests.
- [ ] Run the compiler test suite and native zero-findings/parser validation.
- [ ] Inspect the diff for only the relevant Goal bindings, candidate guards, tests, and this plan.
- [ ] Confirm the artifact is still consistent with the relevant synchronizer path.

### Task 6: Merge and run the real-game acceptance matrix
- [ ] Merge only after the focused and repository CI gates are green.
- [ ] Test Arabia 1v1 against Moderate on the unchanged map/settings baseline.
- [ ] Verify the first lumberyard and mining camp still work, the next camp is issued after a newly available front meets the current admission policy, and failed placement retries without issuing duplicates.
- [ ] Verify Castle timing, early economy, and attack behavior are not regressed.

## Implementation boundary

This repair closes the immediately observed runtime-artifact defect. The broader compiler-owned DUC resource-front plan remains a separate source-synchronization task; this patch must not claim that compiler ownership is complete unless compiler output is independently shown to emit these exact rules.
