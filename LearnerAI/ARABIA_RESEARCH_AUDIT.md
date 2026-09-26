# Arabia Research Cross-Reference and Revision Audit

Date: 2026-09-26

This audit cross-references the recent Arabia capability, threshold, timing, and economic-reaction proposals against:

- current World's Edge AI and pathfinding changes;
- current community custom-AI coverage;
- community .per scripting patterns;
- current Arabia opening discussion;
- the LearnerAI compiler's semantic boundary.

## Research findings

### 1. Current official AI direction

World's Edge Update 185872 (September 22, 2026) is directly relevant.

It reports:

- Extreme AI transport improvements on island maps;
- occasional forward builders to support invasions;
- compressed early building placement;
- funnel walls using buildings/palisades;
- external-island resource use;
- market land trading on allied islands after water control;
- stuck Trade Cart recovery;
- reduced farming when wood is extremely expensive;
- less distant-tree gathering under gather-percentage allocation;
- cancellation of building foundations when a villager cannot path to them;
- escrow edge-case fixes;
- improved fishing/villager/transport pathfinding.

Implication for LearnerAI:

Map-conditioned execution, construction recovery, resource-price-aware worker allocation, and transport are not speculative "advanced features". They are normal current-AI concerns.

Reference:
https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/

### 2. Community custom-AI coverage

The current AI Database entry for Naga records support for:

- Arabia;
- Arena;
- Black Forest;
- Nomad/Land Nomad;
- Megarandom;
- Hideout;
- general open land;
- general closed land;
- general hybrid;
- general water;
- transport over water;
- strategy adaptation to the enemy;
- walling-related behavior;
- anti-tower-rush;
- multiple Feudal and Fast-Castle strategy families.

The database also records that some established AIs support broad map families while others deliberately omit water or transport. This is useful evidence that map breadth is a recognized capability dimension rather than an automatic property of being a "stock AI".

Reference:
https://aoeaidatabase.pythonanywhere.com/ai?name=Naga

The default/ordinary AI entry is narrower and lists Arabia, Arena, Black Forest, open/closed land and Fast Castle families while omitting general water and transport. That is useful precedent for treating water/transport as conditional capability rather than assuming every AI implements them by default.

Reference:
https://aoeaidatabase.pythonanywhere.com/ai?name=Ordinary%20AI

### 3. Community .per resource allocation practice

Community scripting examples use strategic-number gather percentages, current resource amounts, age, building counts, pending objects, dropsite distance, and resource-found conditions to change economic allocation.

This confirms that the correct abstraction is:

    strategic intent
      -> resource mode
      -> current-state evidence
      -> engine allocation

not:

    minute X
      -> permanent worker split

Community examples also use `sn-minimum-water-body-size-for-dock` to gate Dock behavior. That is stronger precedent for map/water-value gating than a universal fish-count law.

Reference:
https://github.com/lewisc64/aoe2ai
https://gist.github.com/Andygmb/1e3a6d9d444b2dfa8c40

### 4. Current Arabia pressure behavior

Recent community discussion reports MAA/drush as extremely common Arabia openings in 2026, including MAA into Archers, while older and current discussions distinguish Scout, Archer, MAA and tower pressure rather than treating them as one generic Feudal rush.

Recent community reports also describe Hard/Extreme AI producing MAA into Archers and tower pressure, confirming that a competent stock-style opponent can create compound pressure.

References:
https://www.reddit.com/r/aoe2/comments/1w2ysg8/arabia_every_opening_is_maa/
https://www.reddit.com/r/aoe2/comments/1r23us0/hard_ai_rush/
https://www.reddit.com/r/aoe2/comments/1753fbx/i_just_got_tower_rushed_by_ai_extreme/

### 5. Current pathfinding changes alter construction assumptions

Because Update 185872 improves builder pathing, foundation cancellation, transport unloading, villager collision handling, and fishing/path behavior, LearnerAI should not treat a failed build as proof that the strategic demand was wrong.

The correct lifecycle remains:

    demand
      -> capability
      -> feasibility
      -> action
      -> pending
      -> world-state witness
      -> release/retry/reassess

The engine may fail an action for placement/pathing reasons without invalidating the strategic intent.

## Revisions to the recent proposals

### Revision A: timing is advisory, not executable

KEEP.

The timing-window documents are consistent with community practice when interpreted as confidence bands.

The compiler now enforces this distinction:

- `game-time` is a TIMING primitive;
- timing-only requirements cannot open an action;
- timing cannot be a completion witness;
- timing-only release is rejected.

This prevents:

    time
      -> train unit

from becoming a hidden build order.

### Revision B: tower distance

CHANGE.

The previous "~12 tile" rule is too literal to be a semantic invariant.

New rule:

- use engine-derived spatial relation to the critical resource;
- use builder count, military escort, completion state and actual resource denial;
- keep any numerical distance as a tuning constant outside compiler semantics.

The compiler must not know that a tower rush is "12 tiles".

### Revision C: Dock/fishing threshold

CHANGE.

The previous "5 usable fish" rule remains a **strategy tuning starting point**, not a universal semantic truth.

Dock admission now has three layers:

1. water-value/map context;
2. economic safety/opportunity cost;
3. optional numeric tuning such as usable-fish count.

Transport necessity and naval contest remain direct overrides.

Community scripts' `sn-minimum-water-body-size-for-dock` pattern is the stronger engine-native precedent.

### Revision D: worker packets

KEEP, with refinement.

Worker reactions remain temporary packet adjustments, but the packet is subordinate to:

- resource price;
- current stock;
- worker count;
- active demand;
- current production capacity;
- construction feasibility.

This aligns with current official AI behavior around high wood prices and gather-percentage allocation.

### Revision E: MAA branch

STRENGTHEN.

Current 2026 community reports make MAA one of the most common Arabia pressure patterns. The player therefore needs a first-class MAA interpretation path.

The current documents already separate MAA from Scout/Archer counters. The timing/economic layer should therefore bias early Range readiness under MAA evidence rather than attempting to solve MAA with generic Spear/Skirmisher accumulation.

### Revision F: Feudal defensive ceiling

KEEP, but classify as a tuning policy.

The 4+4 D4 ceiling is a default defensive cap, not a game invariant.

Compound pressure, forward siege, tower denial, or an explicit Feudal strategic posture may exceed it.

The compiler should never hard-code the number 8.

### Revision G: Castle acceleration

KEEP.

Community and ordinary-AI patterns support Fast Castle as a strategic branch, while current Arabia pressure makes naked FC unsafe.

Opponent Castle confirmation with weak Feudal pressure should reduce unnecessary Feudal spending and accelerate the own Castle trajectory.

Opponent Castle plus actual forward pressure should suspend that acceleration until survival is restored.

## Compiler change

The semantic compiler now contains a `TIMING` role and the native `game-time` primitive.

New semantic invariants:

1. A timing-only demand is rejected.
2. A timing predicate can coexist with world-state evidence.
3. Timing cannot be a completion witness.
4. Timing-only release is rejected.
5. Native engine legality remains delegated to `aoe2-ai-parser`.

This is intentionally small.

No map scheduler, simulation layer, timing build-order language, or numeric Arabia strategy engine was added.

## Resulting architecture rule

The recent proposals should now be understood as:

    MAP PROFILE
      ->
    TIMING CONFIDENCE
      ->
    WORLD-STATE EVIDENCE
      ->
    STRATEGIC INTERPRETATION
      ->
    RESOURCE / PRODUCTION / CONSTRUCTION DEMAND
      ->
    FEASIBILITY
      ->
    ACTION
      ->
    WORLD-STATE WITNESS
      ->
    RELEASE / INVALIDATION
      ->
    REASSESS

The clock supplies prior information.

The map supplies context.

The world state supplies proof.

The strategic owner supplies intent.

The domain owner executes.

The compiler checks that those distinctions remain intact.

## Research conclusion

The recent LearnerAI proposals are directionally sound, but several numbers belong in strategy tuning rather than compiler semantics.

The strongest cross-source convergence is:

- current AI is map-aware;
- water/transport is a distinct capability;
- MAA/Archer/Scout/tower pressure are separate opening classes;
- gather-percent/resource modes are normal .per practice;
- walls are increasingly used as selective funnels rather than merely full perimeters;
- construction failure and pathing failure require recovery;
- current engine updates explicitly reward this kind of conditional, evidence-based behavior.

The compiler should therefore become stricter about semantic boundaries, not larger.


## MAA-path audit, September 26, 2026

The MAA response path was re-audited after the timing, worker, production, wall, tower, and resource-allocation revisions.

Result:

- Timing remains interpretive. The 06:30-08:30 MAA band is a readiness window only; it cannot create Archer production without world-state evidence.
- The first Archery Range is the protected response capability when MAA evidence appears. The worker packet temporarily favors wood until the Range and initial Archer queue are serviceable, while preserving the Castle gold floor.
- One Range is the default provider for 3-6 defensive Archers. A second Range is conditional on persistent pressure plus insufficient replacement capacity, not on MAA count alone.
- MAA do not automatically authorize towers. Tower admission remains an independent resource/position test. This prevents the MAA counter branch from turning into a static-defense branch.
- Transitioning the opponent toward Castle does not release the MAA demand by itself. The surviving MAA must also fall below the active pressure threshold or lose access to the economy.
- Timing-dependent release is now rejected by the compiler even when timing is combined with an observation predicate.
- Timing-only composite requirements are rejected, preventing a hidden "time window" build-order rule disguised as a logical expression.

Current external community evidence continues to describe MAA as a common Arabia opening and emphasizes early Range readiness and small resource walls as practical responses. Current official guidance and the September 22, 2026 update also reinforce conditional funnel walls, resource-aware worker behavior, and construction/pathing recovery rather than unconditional scripted reactions.

References:

- https://www.reddit.com/r/aoe2/comments/1w2ysg8/arabia_every_opening_is_maa/
- https://www.reddit.com/r/aoe2/comments/1voyj53/what_to_do_vs_menatarms_rushes/
- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/


## Wall/tower escalation audit, September 26, 2026

The Arabia wall/tower path was re-audited around three separate facts:

1. positional value / denial;
2. enemy builder commitment;
3. actual resource denial.

Revisions:

- A wall demand must protect a real resource or route. Enemy unit count raises urgency but does not create a wall demand by itself.
- A tower foundation is only strategically relevant when its completed position can materially deny a critical resource or route.
- Enemy builder count controls escalation urgency. Two or more builders shorten the response window, but builder count alone does not turn a harmless foundation into a tower-rush demand.
- Own builder count is construction feasibility. It controls how quickly the defensive structure can complete; it does not decide whether the structure is strategically justified.
- A completed tower is a stronger witness than a foundation because actual resource/route denial can be observed.
- A second tower/foundation must still pass the denial test. Multiple foundations are evidence of commitment, not automatic proof of threat.
- MAA presence does not authorize a tower by itself. MAA plus positional/resource denial can activate the combined pressure branch.

The native engine reference provides `dropsite-min-distance` as a real observation, so the compiler now includes that fact in its small semantic primitive profile. The compiler still does not invent an enemy-builder-count primitive because the current native reference exposes builder assignment as an action rather than a simple builder-count fact.

Current community discussion supports the same qualitative pattern: MAA pressure is commonly answered with early Archers and small resource walls, while tower reactions are positional and depend on whether the tower actually protects or denies important areas.

References:

- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- https://www.reddit.com/r/aoe2/comments/1w2ysg8/arabia_every_opening_is_maa/
- https://www.reddit.com/r/aoe2/comments/1voyj53/what_to_do_vs_menatarms_rushes/
- https://www.reddit.com/r/aoe2/comments/1t1josh/maa_rush_against_towers/
