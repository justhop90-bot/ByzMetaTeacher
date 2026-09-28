# Native DE Same-Pass Escrow Visibility Fixture — 2026-09-28

Status: SPECIFIED / RUNTIME PROOF OPEN

Purpose: prove or falsify the narrow native engine contract that an earlier `release-escrow <Resource>` action makes the released resource visible to a subsequent ordinary `research` action in the same executable rule/pass.

This fixture does not promote escrow ownership, starvation recovery, `set-escrow-percentage`, UP `EscrowState` actions, or any non-research action family.

## 1. Frozen test identity

Repository: `justhop90-bot/ByzMetaTeacher`
Compiler main at specification time: `9c1cba88d2bfac2102cb7d0de1e519b2317deecf`
Target engine: Age of Empires II: Definitive Edition
Target research: `ri-loom`
Research status domain:
- `1 = research-available`
- `2 = research-pending`
- `3 = research-complete`
- `0 = research-unavailable`

The tested ordinary action is exactly:

`lisp
(research ri-loom)
`

The tested release is exactly:

`lisp
(release-escrow gold)
`

The escrow seed is supplied by the isolated test harness:

`lisp
(up-modify-escrow gold c:= 75)
`

The compiler must not synthesize the setup mutation. It exists only to construct the native runtime precondition.

## 2. Scenario invariants

Every fresh run must establish:

`text
gold = 100
escrow_gold = 75
normal_visible_gold = 25
escrow_included_gold = 100

research-status(ri-loom) = 1
research-completed(ri-loom) = false

can-research(ri-loom) = false
can-research-with-escrow(ri-loom) = true
`

The scenario must contain exactly one usable research provider for Loom, no competing research rules, no market/resource income, no other escrow mutation, and no unrelated rule capable of consuming gold.

If the exact precondition split is not observed, terminate the run as `INVALID_PRECONDITION`. No timing conclusion is permitted.

## 3. Fixture variants

### 3.1 NORMAL_BASELINE

No escrow seed.

Expected status path:

`text
1 -> 2 -> 3
`

Expected resource transaction:

`text
gold decreases exactly by the known Loom cost
escrow_gold remains 0
`

Terminal result must be `PASS`.

Failure classes:
- `BASELINE_NO_ADMISSION`
- `BASELINE_NO_ISSUANCE`
- `BASELINE_BAD_RESOURCE_DELTA`
- `BASELINE_NO_COMPLETION`
- `BASELINE_STATUS_REGRESSION`
- `BASELINE_UNCONTROLLED_SIDE_EFFECT`

### 3.2 ESCROW_BLOCKED_NO_RELEASE

Escrow seed is present. No release action and no alternate escrow-inclusive research action are permitted.

Expected terminal state:

`text
status = 1
research-completed = false
gold = 100
escrow_gold = 75
`

No status transition is allowed.

Terminal result is `PASS` only if all four values remain unchanged.

Failure classes:
- `BLOCKED_CONTROL_LEAK`
- `BLOCKED_RESOURCE_LEAK`
- `BLOCKED_ESCROW_MUTATION`
- `BLOCKED_EXTERNAL_ACTION`

### 3.3 ESCROW_SAME_PASS_POSITIVE

Probe rule action order is fixed:

`lisp
(release-escrow gold)
(research ri-loom)
`

At rule entry:

`text
status = 1
can-research = false
can-research-with-escrow = true
gold = 100
escrow_gold = 75
`

Immediately after release:

`text
escrow_gold = 0
gold = 100
`

The ordinary research action must then be accepted in the same rule execution/pass.

Required world-state result:

`text
status = 2
research-completed = false
gold = 50
escrow_gold = 0
`

Later completion:

`text
2 -> 3
research-completed = true
`

Allowed status sequence is:

`text
1 -> 2
2 -> 2*
2 -> 3
`

No transition outside that sequence is permitted.

Terminal result is `PASS` only when all of the following hold:
1. the initial escrow feasibility split is exact;
2. release changes escrow 75 -> 0;
3. ordinary research is accepted after release in the same rule/pass;
4. status reaches 2;
5. gold decreases by exactly the research cost;
6. escrow remains 0;
7. status later reaches 3 and `research-completed` becomes true.

Failure classes:
- `POSITIVE_PRECONDITION_FAILURE`
- `RELEASE_NOT_OBSERVED`
- `SAME_PASS_VISIBILITY_FAILURE`
- `RESEARCH_REJECTED_AFTER_RELEASE`
- `RESOURCE_CONSUMPTION_FAILURE`
- `RESEARCH_STATUS_REGRESSION`
- `COMPLETION_WITNESS_FAILURE`
- `UNCONTROLLED_SIDE_EFFECT`

`SAME_PASS_VISIBILITY_FAILURE` is the expected classification when release succeeds but the ordinary research action does not enter status 2 during the same rule/pass, provided the later-pass control subsequently succeeds.

### 3.4 ESCROW_SAME_PASS_REVERSED

Probe rule action order is reversed:

`lisp
(research ri-loom)
(release-escrow gold)
`

At the first action, ordinary research must not be accepted because the protected 75 gold is still escrowed.

Expected end-of-probe-pass state:

`text
status = 1
research-completed = false
gold = 100
escrow_gold = 0
`

A later rescue rule may then research normally.

Required later sequence:

`text
1 -> 2 -> 3
`

Terminal result is `PASS` only when:
1. precondition split is exact;
2. research-before-release does not start research;
3. release changes escrow 75 -> 0;
4. status remains 1 through the reversed probe pass;
5. no gold is consumed by the failed first action;
6. later-pass rescue enters status 2;
7. later completion reaches status 3.

Failure classes:
- `REVERSED_ORDER_ACCEPTED`
- `REVERSED_RESOURCE_CONSUMED`
- `REVERSED_SAME_PASS_LEAK`
- `REVERSED_RESCUE_FAILURE`
- `RESEARCH_STATUS_REGRESSION`

`REVERSED_SAME_PASS_LEAK` means the first action appears to have been deferred/replayed after release. This does not count as proof of normal order-sensitive visibility.

### 3.5 ESCROW_LATER_PASS_CONTROL

Release and research are in separate rules.

Pass N:

`lisp
release-escrow gold
`

Pass N+1 or later:

`lisp
research ri-loom
`

Expected pass boundary:

`text
Pass N:
    status = 1
    escrow 75 -> 0
    research not started

Later pass:
    status 1 -> 2

Later:
    status 2 -> 3
`

Terminal result is `PASS` only when:
1. release is observed in pass N;
2. status remains 1 during pass N;
3. research starts in a later pass;
4. resource consumption is exact;
5. completion reaches 3.

Failure classes:
- `LATER_PASS_NO_RELEASE`
- `LATER_PASS_UNEXPECTED_SAME_PASS`
- `LATER_PASS_RESEARCH_FAILURE`
- `LATER_PASS_STATUS_REGRESSION`

`LATER_PASS_UNEXPECTED_SAME_PASS` is only emitted if pass identity is instrumented incorrectly. Separate source rules are not sufficient evidence of separate passes.

## 4. Allowed research-status transitions

The oracle is intentionally stricter than “eventually Loom completed.”

Globally allowed transitions in this fixture are:

`text
1 -> 1
1 -> 2
2 -> 2
2 -> 3
3 -> 3
`

The following are failures unless explicitly caused by a controlled fixture reset, which these tests never perform:

`text
1 -> 3
2 -> 1
3 -> 2
3 -> 1
0 -> 2
0 -> 3
1 -> 0
2 -> 0
3 -> 0
`

`research-completed` is false until the status reaches 3 and must never be used as a same-pass issuance witness.

## 5. Required trace schema

Record one row at rule entry, after each tested action, at end-of-pass, at first research-pending observation, and at completion.

Fields:

`text
run_id
fixture_variant
scenario_id
de_build
script_sha256
scenario_sha256
pass_id
tick
rule_index
rule_name
action_index

food_amount
wood_amount
gold_amount
stone_amount
escrow_food
escrow_wood
escrow_gold
escrow_stone

normal_gold_visible
escrow_included_gold_visible

can_research_ri_loom
can_research_with_escrow_ri_loom

research_status_ri_loom
research_pending_ri_loom
research_completed_ri_loom

escrow_test_state

release_escrow_gold_issued
research_ri_loom_issued

gold_delta_since_previous_row
escrow_gold_delta_since_previous_row

world_resource_transaction_observed
world_research_transaction_observed
`

Derived values:

`text
normal_gold_visible = gold_amount - escrow_gold
escrow_included_gold_visible = gold_amount
`

The trace must identify controller events and world events separately. Rule execution proves command issuance; resource and research-state changes prove engine-side effects.

## 6. Terminal-result precedence

Every fresh run receives exactly one terminal result. Apply this precedence:

1. `NATIVE_ENGINE_ERROR`
2. `CONTROL_CONTAMINATION`
3. `INVALID_PRECONDITION`
4. `NONDETERMINISTIC`
5. `STATUS_LIFECYCLE_FAILURE`
6. `RESOURCE_CONSUMPTION_FAILURE`
7. `ORDERING_FAILURE`
8. `SAME_PASS_VISIBILITY_FAILURE`
9. fixture-specific baseline/control failure
10. `PASS`

Do not report multiple terminal classifications for one run.

## 7. Repetition gate

Use ten fresh runs per variant with identical frozen inputs.

Required matrix:

| Variant | Required outcome |
|---|---|
| NORMAL_BASELINE | PASS |
| ESCROW_BLOCKED_NO_RELEASE | PASS |
| ESCROW_SAME_PASS_POSITIVE | PASS |
| ESCROW_SAME_PASS_REVERSED | PASS |
| ESCROW_LATER_PASS_CONTROL | PASS |

Any non-`PASS` result blocks native promotion.

Any differing terminal result for byte-identical input across repeated runs is `NONDETERMINISTIC` and blocks promotion.

## 8. Native promotion gate

The native fact may be promoted only when all five fixture variants pass for ten fresh runs each and the traces establish:

`text
release-escrow gold
    ->
escrow_gold becomes 0
    ->
ordinary research is accepted in the same rule/pass
    ->
research enters status 2
    ->
exact research cost is consumed
    ->
status eventually reaches 3
`

The reversed fixture must simultaneously establish that ordinary research does not become accepted before release.

Promoted statement:

> On the tested DE build, `release-escrow <Resource>` is same-pass visible to a later ordinary `research` action in the same executable rule, and action order is material.

Do not generalize this result to build, train, age-up, starvation release, ownership handoff, or UP `EscrowState` actions.

## 9. Evidence artifact

The runtime evidence package must contain:

`text
fixture source
scenario identity/hash
engine build
input/state setup record
raw trace
normalized trace
oracle result
run repetition summary
failure classification, if any
promotion decision
`

Static compiler/native-parser validation remains separate. Existing `assert_escrow_native.py` proves deterministic release emission and zero native parser findings; this fixture proves engine execution timing. Neither artifact substitutes for the other.

## 10. Current state

This specification closes the experiment design gap but does not close the native unknown.

Current MUSE status remains:

`text
NATIVE_ESCROW_SAME_PASS_VISIBILITY = OPEN
`

The next promotion action after successful runtime execution is to update `native_unknowns.md`, the MUSE escrow execution checklist, and the evidence record together from the same frozen DE build/run set.
