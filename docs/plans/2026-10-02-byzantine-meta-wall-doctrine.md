# Byzantine Meta Wall Doctrine - 2026-10-02

## 1. Purpose

This document defines the walling doctrine for the Byzantine community-native bot.

The objective is not to maximize wall count, enclose the starting base, or reproduce an old scripted perimeter. The objective is to make each defensive wall segment buy measurable strategic time by changing the path an enemy must take, while using already-existing defensive buildings as structural anchors.

The wall system therefore owns one tactical problem:

> When meaningful enemy pressure exists and two useful defensive buildings already exist, connect them with the smallest native wall action that creates a durable defensive bridge.

The wall system is subordinate to age progression, military production, starvation recovery, essential technology, siege, and active defense. A wall that destroys Castle timing is not a defensive success.

## 2. Behavioral contract

### Observation

Observe only signals that can be represented safely in the current compiler:

- enemy mounted pressure;
- enemy ranged pressure;
- enemy infantry pressure;
- existence of defensive anchor buildings;
- current age;
- wall construction capability;
- selected wall world-state presence;
- selected anchor world-state presence;
- pending wall placement.

The current contract intentionally does not claim a full spatial simulation, exact wall closure, path connectivity, or optimal geometric distance. Those are still engine/runtime questions that require stronger evidence.

### Arbitration

Choose a pair of two distinct defensive building types from this fixed native inventory:

| Priority class | Anchor | Native ID | Normal wall tier |
|---|---|---:|---|
| Strong | Castle | 82 | Stone |
| Strong | Keep | 235 | Stone |
| Strong | Bombard Tower | 236 | Stone |
| Standard | Guard Tower | 234 | Palisade |
| Standard | Watch Tower | 79 | Palisade |
| Standard | Outpost | 598 | Palisade |

The pair is selected deterministically from the compiler's candidate order. The first viable pair is used.

Strong anchors are Castle, Keep, and Bombard Tower. Any pair containing one strong anchor uses Stone Wall and therefore requires Castle Age. A pair containing only tower/outpost anchors uses Palisade Wall and may be used from Feudal Age.

The system currently requires two distinct anchor types. It does not infer that the second element of a same-type search is the second physical building because exact post-search result ordering is not proven by the compiler evidence. This is deliberate fail-closed behavior.

### Execution

For each selected pair:

1. Find the first local object of the first defensive building type.
2. Read its point into a GoalSpan.
3. Find the first local object of the second defensive building type.
4. Read its point into a second GoalSpan.
5. Issue one native `up-build-line` from the first point pair to the second point pair.
6. Record that the geometry request is in flight.
7. Wait for a world-state witness before releasing the plan.

The native line command is used because the engine schema explicitly defines `up-build-line` as a building-line action taking two Point Goal operands. The compiler does not synthesize a second .per wall language around it.

### Witness

A successful issue is not treated as completion.

The current witness is deliberately conservative:

- a selected wall type exists;
- the selected wall placement is no longer pending;
- both selected anchors still exist.

This proves that the engine has a completed wall object of the selected type and that the placement request is no longer pending. It does not prove that the line is geometrically sealed end-to-end.

That distinction is mandatory.

### Recovery

There are two different failures:

1. Wall loss while both anchors survive.
   - Reissue the same bridge after pending-placement/pending-object guards clear.

2. Anchor loss.
   - Retire the old pair.
   - Clear the completion latch.
   - Return to pair arbitration.
   - Select another viable defensive pair.
   - Rebuild using the new pair's wall tier.

A destroyed anchor is therefore a geometry invalidation event, not merely a missing building.

### Reassessment

Once a pair succeeds, the bot does not continuously rebuild the same line every script pass. A persistent completion latch retires the request until an anchor is lost.

This is the important control-plane difference between a defensive system and a wall spam loop.

## 3. Why this matches the community meta

### The useful community principle is funneling, not perimeter completion

Community walling practice repeatedly favors using buildings and forests to reduce the amount of wall required. The strategic objective is to make a route expensive or slow to cross with as little construction as possible, not to draw a complete square around every resource.

Recent community discussion continues to identify efficient walling with buildings and natural terrain as the useful pattern, while calling out gaps, overextended perimeters, and self-trapping as recurring AI failure modes. citeturn601727reddit48turn601727reddit47

The current DE AI itself now sometimes attempts a few funnel walls using buildings or palisades between starting forests and the Town Center. This is direct evidence that the current engine's AI direction has moved toward short building-anchored funnels rather than indiscriminate perimeter walls. citeturn352798view1

### The useful native scripting principle is explicit geometry

The compiler already uses the native pattern:

`search -> select object -> get point -> consume GoalSpan`

and the native command inventory documents `up-build-line` as:

`(up-build-line <Point> <Point> <typeOp> <BuildingId>)`

The current implementation therefore stays inside the project's existing DUC/GoalSpan and native control-plane vocabulary.

### Defensive buildings should be structural assets

A Castle, Keep, Bombard Tower, Guard Tower, Watch Tower, or Outpost already performs a defensive job. Connecting two of them makes the wall an extension of existing fortification rather than a separate perimeter project.

This also follows the project's own capability matrix:

- Palisade walls are a cheap delay/shape tool.
- Stone walls are a larger attack-delay investment that competes with Castle resources.
- Towers are defensive observation/response infrastructure, not reasons to build towers indiscriminately.

The wall system therefore does not ask the economy to create decorative anchor buildings solely so that a wall can exist.

## 4. The deliberate improvement over ordinary community practice

### Dynamic defensive lattice

The main improvement is not more wall. It is re-anchoring.

A normal scripted wall tends to have a fixed answer such as:

`TC -> woodline`

or:

`base -> perimeter`

That answer becomes stale when a tower falls, an anchor is destroyed, a defensive building is moved by strategy, or the enemy changes the relevant route.

This system instead stores the identity of the current anchor pair and treats anchor loss as invalidation.

The resulting loop is:

`existing fortifications -> bridge -> witness -> hold -> anchor loss -> retire -> select new bridge`

That makes the wall plan persistent without making it permanent.

It also avoids the classic scripted-AI failure of repeatedly rebuilding the same obsolete wall after the map has changed.

### Material is tied to defensive infrastructure

The second deliberate improvement is material arbitration.

A pair of ordinary towers/outposts gets a cheap Palisade bridge. A pair containing a Castle, Keep, or Bombard Tower gets a Stone bridge.

This is intentionally simpler than a simulated resource optimizer. It uses the fortification tier already represented by the anchors as the strongest available strategic signal.

The resulting policy is:

- Feudal + standard tower anchors -> Palisade.
- Castle + strong anchor -> Stone.
- Strong anchor unavailable -> do not force Stone merely because Stone Wall exists.
- Stone is never the default wall simply because the bot can afford it.

That keeps Stone competing against Castle and other Castle-age demands exactly as the existing Byzantine economic doctrine requires.

## 5. Anchor selection contract

### Current deterministic ordering

The candidate sequence is:

1. Castle + Keep
2. Castle + Bombard Tower
3. Castle + Guard Tower
4. Castle + Watch Tower
5. Castle + Outpost
6. Keep + Bombard Tower
7. Keep + Guard Tower
8. Keep + Watch Tower
9. Keep + Outpost
10. Bombard Tower + Guard Tower
11. Bombard Tower + Watch Tower
12. Bombard Tower + Outpost
13. Guard Tower + Watch Tower
14. Guard Tower + Outpost
15. Watch Tower + Outpost

The compiler intentionally does not promise that this ordering is a geometric ranking. It is an arbitration order.

The first viable pair wins because the native evidence currently supports presence/type filtering more strongly than spatial optimization.

### Why first-object selection is deliberate

The current DUC evidence proves:

- search reset;
- local search;
- search-local list;
- selection of index 0;
- point extraction from the selected object.

The evidence does not prove the exact numeric meaning of an arbitrary second search result well enough to use it as a compiler invariant.

Therefore the system selects one object from each of two different building types instead of pretending two same-type buildings are safely addressable by an unproven result offset.

## 6. Pressure admission

The current wall trigger remains intentionally simple:

- enemy Knights >= 3, or
- enemy Archers >= 4, or
- enemy Militia-line >= 5.

This preserves the current Byzantine bot's existing threat vocabulary rather than inventing another pressure classifier.

Walling is not activated by time alone.

The bot should not spend Feudal wood or Castle stone on a defensive bridge merely because the clock says it is old enough.

## 7. Wall-type arbitration

### Palisade bridge

Use Wall ID 72 when both anchors are standard tower/outpost infrastructure.

Purpose:

- buy raid time;
- shape movement;
- close an exposed route cheaply;
- preserve wood relative to Stone Wall;
- create a tactical funnel for the army or TC.

Palisade is the default defensive bridge for Feudal pressure.

### Stone bridge

Use Wall ID 117 when at least one anchor is Castle, Keep, or Bombard Tower.

Purpose:

- create a durable extension of major fortification;
- deny a route around a high-value anchor;
- protect a Castle-age strategic position;
- increase the time required for ordinary army access.

Stone is only admitted in Castle Age in the current contract.

### Fortified Wall

Fortified Wall ID 155 is deliberately not used in this first implementation.

The engine supports the object, but the current bot does not yet have a sufficiently explicit geometry/value contract for choosing Fortified Wall over ordinary Stone Wall. Adding it now would be more building vocabulary without improving arbitration quality.

## 8. What this wall system deliberately does not do

- It does not build a square around the TC.
- It does not wall every exposed resource.
- It does not create anchors solely to justify walling.
- It does not assume the first discovered wall object proves geometric closure.
- It does not assume the nearest resource or nearest defensive structure can be identified from unsupported search ordering.
- It does not use timers as a completion witness.
- It does not continuously reissue an already-completed segment.
- It does not sacrifice Castle timing merely to upgrade a wall tier.
- It does not trap the bot by inventing a mandatory gate or sealed exit.
- It does not claim full pathfinding simulation.

## 9. Native/compiler implementation checklist

### Geometry storage

- [x] Persistent wall request GoalSlot.
- [x] Persistent anchor-pair GoalSlot.
- [x] Persistent completion latch.
- [x] One GoalSpan per candidate defensive-building type.
- [x] GoalSpan width 2.
- [x] Point-pair native contract.
- [x] Native point bounds 41..15998.

### DUC observation

- [x] Castle anchor search.
- [x] Keep anchor search.
- [x] Bombard Tower anchor search.
- [x] Guard Tower anchor search.
- [x] Watch Tower anchor search.
- [x] Outpost anchor search.
- [x] Full search reset before each anchor acquisition.
- [x] First local result selected explicitly.
- [x] Object-to-point conversion explicit.
- [x] Zero cross-plan GoalInput claims.
- [x] Existing Castle target DUC preserved.

### Arbitration

- [x] 15 distinct-type candidate pairs represented.
- [x] Strong/standard anchor tiers represented.
- [x] Palisade/Stone material choice tied to tier.
- [x] Feudal/Castle age gate tied to material.
- [x] Existing enemy-pressure evidence reused.
- [x] Pair identity persists across passes.
- [x] Same-type pair selection remains OPEN rather than guessed.

### Execution

- [x] `up-build-line` native semantic mapping.
- [x] GoalSpan operands enforced by native control validator.
- [x] Wall BuildingId carried as native numeric ID.
- [x] Source order places DUC point writers before native control execution.

### Witness/recovery

- [x] World wall-count witness, scoped to the selected pair's wall tier.
- [x] Per-pair release rules keep emitted boolean clauses within native line budgets.
- [x] Pending-placement guard.
- [x] Anchor-presence guard during recovery.
- [x] Anchor loss invalidates the pair.
- [x] Completion latch suppresses repeated reissue.
- [ ] Geometric closure witness.
- [ ] Precise breach location.
- [ ] Route connectivity witness.
- [ ] Army-exit validation.
- [ ] Builder-safe placement witness.

The unchecked items remain explicitly OPEN rather than being replaced with synthetic compiler claims.

## 10. Acceptance scenarios

### Arabia, Feudal pressure

- Enemy Knights/Archers/Militia pressure crosses the configured threshold.
- At least two standard defensive buildings exist.
- Bot selects the first valid distinct-type pair.
- Bot captures their point pairs.
- Bot issues one Palisade line.
- Bot does not continually reissue the same line.

### Castle defensive bridge

- Castle + defensive tower both exist.
- Enemy pressure is active.
- Bot selects the strong pair.
- Bot issues Stone Wall only after Castle Age is available.
- Existing Castle strategic economy remains the first-order constraint.

### Strong-anchor transition

- A standard tower pair is available during Feudal.
- Bot creates a Palisade bridge.
- Later a Castle becomes available and the old pair remains valid.
- Bot does not replace a valid completed Palisade merely to chase a Stone upgrade.
- This avoids destructive re-wall churn.

### Anchor loss

- One anchor of the selected pair is destroyed.
- Completion state becomes invalid.
- The old geometry is retired.
- Another viable pair is selected.
- A new line is issued only after the new point pair is captured.

### Wall loss without anchor loss

- Existing anchors survive.
- Wall object disappears.
- Pending state clears.
- Bot reissues the same bridge once, instead of forgetting the defense.

### Closed map

- No meaningful enemy pressure exists.
- Wall system remains dormant even if defensive buildings exist.

### Pressure at a single fortified position

- The bot's wall system can shape an approach around an existing defensive anchor.
- Army logic remains responsible for actually defending the position.
- Walling does not substitute for siege or army control.

### Pathing / gap caveat

- Test on terrain with elevation changes.
- Test around forest edges.
- Test with narrow resource routes.
- Do not promote the witness from “wall exists” to “route sealed” until an engine-native closure signal is proven.

## 11. Verification gates

Every wall change must clear:

1. Python/compiler unit tests.
2. Strategy integration tests.
3. Native control-plan validation.
4. Native zero-findings strategy fixture.
5. Rule element and source-line budget checks.
6. Determinism checks across supported OS/Python combinations.
7. Generated artifact comparison.
8. In-game scenarios covering pressure, strong anchors, anchor loss, wall loss, and pathing.

No green CI result is inferred from code inspection.

## 12. Evidence register

Primary engine evidence:

- AoE II DE Update 185872, September 22, 2026: Extreme AI sometimes builds a few funnel walls with buildings or palisades between starting forests and the Town Center; the same update also fixes several pathfinding/building edge cases. citeturn352798view1
- AoE II DE Update 81058: AI considers how closed the map is before committing to walls and may wall-in a forward tower with palisades when it has a large local advantage. citeturn601727search0
- AoE II DE Update 61321: defensive building wall behavior was explicitly introduced as an AI feature. citeturn601727search2

Community evidence:

- Current community discussion repeatedly identifies efficient building/terrain integration as the hard part of walling and identifies holes and self-trapping as common problems. citeturn601727reddit48turn601727reddit47
- Community reports continue to identify elevation-induced one-tile wall gaps and recommend explicit gap checking rather than trusting visual continuity. citeturn601727reddit44turn601727reddit45
- AI-Scripters practice demonstrates the community's normal approach of iterating on small native snippets, testing them in actual games, and changing builder/placement behavior based on observed failures. citeturn444426search0

Repository evidence:

- `CAPABILITY_MATRIX.md`: walling is a delay/shape capability; Stone Wall competes with Castle resources.
- `ARABIA_THRESHOLDS.md`: exposed resources and enemy pressure justify defensive structures.
- `BYZANTINES_manifest.txt`: current verified defensive building IDs.
- `native_building_catalog.py`: current explicit native object identity overrides, including Town Center expansion object 621.
- `native_hygiene.py` and the DUC state model: local search semantics, bounded search, and explicit OPEN treatment of uncertain result-order behavior.
- `engine_semantics.py`: `up-build-line` is an explicitly contracted native control-plane action.
- `emitter/per.py`: GoalSpan control-plane operands lower to their bound numeric Goal IDs.

## 13. Definition of done

The wall subsystem is done for this tranche when:

- the bot can detect meaningful pressure using existing evidence;
- it can identify two existing defensive buildings of distinct types;
- it captures both points through native DUC;
- it chooses Palisade versus Stone according to anchor tier and age;
- it issues a single native wall line;
- it witnesses a completed wall object conservatively;
- it does not repeatedly reissue the same line;
- it can recover a lost wall;
- it can retire a pair when an anchor is destroyed;
- all compiler/native/determinism gates pass;
- the remaining geometric limitations are documented as OPEN rather than hidden.

The next wall tranche should only add spatial intelligence when the engine contract proves a specific new geometric primitive. The correct progression is evidence -> native primitive -> minimal policy -> test, not another pile of rules pretending to be a map model.