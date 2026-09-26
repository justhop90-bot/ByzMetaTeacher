# Map-Conditioned Priority Rules

This document turns the Byzantine capability matrix into concrete strategic priority rules for six common random-map situations:

1. Arabia/open land
2. Arena/closed land
3. Black Forest/chokepoint land
4. Hybrid maps
5. Full-water maps
6. Transport-critical starts

These are **position profiles**, not hard-coded build orders.

A named map can seed a profile, but the observed game state can promote, demote, or replace that profile. A hybrid seed that generates almost no useful water is not a water game. A nominally open map with a blocked starting landmass is a transport-critical game.

## 1. Common priority vocabulary

### P0: survival and continuity

Protect:

- villager production;
- current food supply;
- population capacity;
- immediate worker safety;
- minimum military floor when a real threat exists;
- an active transport/landing operation when loss would strand the player.

P0 can temporarily consume resources reserved for a higher-stage plan.

### P1: trajectory

Protect:

- the current age-up or age transition;
- the economy required for the selected Castle/Imperial trajectory;
- required core infrastructure;
- the minimum capability package for the active map profile.

P1 is the normal target once P0 is stable.

### P2: strategic response

Open only when an observed opportunity or threat justifies it:

- counter units;
- walls and towers;
- Dock/fishing;
- naval combat;
- transport;
- Siege Workshop/siege;
- Monastery/Monks/relics;
- extra production;
- strategic expansion.

### P3: conversion

Convert an established position:

- additional TCs;
- additional production;
- mass siege;
- relic package;
- sustained naval control;
- Castles/forward Castles;
- Keeps/Bombard Towers;
- Imperial military conversion.

### P4: optional

Do only when the position clearly pays for it.

Examples:

- redundant production;
- marginal upgrades;
- decorative or redundant fortification;
- naval upgrades after naval value has collapsed.

## 2. Global arbitration rules

These apply to every profile.

### Rule M1: survival overrides trajectory

If an enemy threat can destroy the current economy or invalidate the current strategic position before the next reassessment, minimum defense may consume resources otherwise reserved for Castle, TC, dock, or siege.

The defense demand must still be bounded.

Do not turn "minimum defense" into unlimited unit production.

### Rule M2: trajectory overrides optional capability

When the position is healthy and a major trajectory is active, optional P2/P3 purchases must not silently consume the resources needed to complete that trajectory.

Examples:

- do not buy unnecessary Feudal military while banking for Castle;
- do not add a second Dock when the first Dock is not producing;
- do not build a Monastery because Castle Age exists;
- do not buy towers when the same stone is explicitly needed for a near-term Castle.

### Rule M3: map profile opens capability; threat confirms quantity

The map profile can make a capability admissible.

It does not determine the final count.

Examples:

- hybrid can open Dock/fishing;
- enemy archers determine Skirmisher quantity;
- full water can open naval production;
- enemy navy determines naval quantity;
- closed map can make walls admissible;
- actual exposure determines whether walls are worth the wood.

### Rule M4: resource claims must protect the next conversion

At any time, Strategy may have one dominant conversion target:

- Feudal transition;
- Castle transition;
- extra TC;
- naval control;
- siege conversion;
- Imperial conversion.

Optional demands cannot repeatedly consume the protected resource without reassessing the dominant target.

### Rule M5: map profile can be overridden

A profile is replaced or suspended when one of these becomes true:

1. transport is required to continue the game;
2. water becomes strategically decisive;
3. the enemy creates a material threat that invalidates the normal trajectory;
4. the starting economy is displaced or destroyed;
5. the intended conversion becomes impossible or obsolete.

### Rule M6: capability must have an exit

Water, walls, towers, siege, Monks, relic contests, and forward infrastructure must each have a release/invalidation condition.

Temporary inability is not cancellation.

## 3. Profile selection

Use the following semantic tests before choosing priorities.

### Open-land test

Open land when:

- the starting economy has meaningful land access in multiple directions;
- there is no strategically important water route required for expansion;
- no major starting wall/chokepoint encloses the player.

Default profile: **Arabia/open land**.

### Closed-land test

Closed land when:

- the starting base is substantially enclosed;
- access is constrained to a small number of gates/chokes;
- early opponent access is materially delayed by the map.

Default profile: **Arena/closed land**.

### Chokepoint-forest test

Black Forest profile when:

- dense forest materially constrains military movement;
- one or more passes/chokepoints dominate access;
- control of the passage is more important than open-field maneuver.

Default profile: **Black Forest/chokepoint**.

### Hybrid-water test

Hybrid when:

- land remains a viable primary economy and military route;
- water contains meaningful food, transport, trade, or tactical access;
- water is valuable but does not completely determine expansion.

Default profile: **hybrid**.

### Full-water test

Full water when:

- water control determines meaningful access to resources, expansion, enemy approach, or the primary economy;
- land alone cannot support the intended strategic position efficiently;
- island separation or shoreline control is a central part of the game.

Default profile: **full water**.

### Transport-critical test

Transport-critical when:

- a required resource, mainland, expansion site, or enemy approach is separated by water;
- no practical land path currently connects the relevant areas;
- transport failure would materially strand the economy or army.

Transport-critical is an **override profile**. It can coexist with hybrid or full-water posture.

## 4. Arabia / open-land priority rules

For timing-confidence windows behind the Arabia profile, read `LearnerAI/ARABIA_TIMING_WINDOWS.md`. Timing changes interpretation confidence; it does not directly create production actions.

### Primary objective

Build a stable land economy, survive the first military interaction, reach Castle without unnecessary Feudal drag, then convert the Castle economy into production/siege/TC/Monk/relic capability as justified.

### Dark Age

P0:

1. Villager continuity.
2. Population headroom.
3. Food continuity.
4. Scouting sufficient to identify enemy opening and map resources.

P1:

1. Age-up resource trajectory.
2. Core dropsites.
3. Farms when natural food is becoming unsafe or insufficient.
4. Minimal wood infrastructure.

P2:

- only map-meaningful walling;
- emergency Outpost;
- early military if the observed threat warrants it;
- Dock only if water is genuinely economically or strategically meaningful.

Protected resources:

- do not bleed wood into unnecessary walls;
- do not bleed food/gold into uncontrolled Feudal units when Castle is the active trajectory.

### Feudal

Default P0:

- minimum defensive floor based on observed threat.

Default P1:

- Castle resource trajectory;
- farms/eco support;
- core military upgrade only when needed.

P2:

- Spear/Skirmisher counter package;
- Blacksmith;
- Market;
- selective ranged/cavalry pressure;
- wall/tower only for a concrete exposed point.

The Feudal military rule is **minimum response, not standing mass**.

### Castle

Default P1:

1. Castle completion if the strategic position supports it.
2. Food economy and farm scaling.
3. Core production capacity.

P2/P3:

- extra TC;
- Siege Workshop;
- Monastery/relics;
- additional military production;
- forward pressure;
- Castle/UU package.

### Arabia cancellation rules

Cancel or demote the normal Castle/boom trajectory when:

- sustained enemy pressure requires defensive stabilization;
- the main economy is damaged enough that additional production would idle;
- a map feature creates a newly valuable water or transport opportunity;
- a previously preferred military composition is being hard-countered.

Return to the normal trajectory once the blocking condition clears.

## 5. Arena / closed-land priority rules

### Primary objective

Exploit the safe starting position to accelerate economic and Castle conversion while avoiding pointless Feudal military expenditure.

Current official AI behavior itself uses map-closedness when deciding whether to commit to walls, which is the correct semantic pattern: closure is a strategic input, not a universal walling command.

### Dark Age

P0:

1. Villager continuity.
2. House/population continuity.
3. Food economy.

P1:

1. Age-up.
2. Wood economy sufficient for farms and Castle infrastructure.
3. Scouting beyond the immediate safe base.

P2:

- minimal Feudal defense only when enemy pressure or exposed resource demands it;
- early Market if it materially accelerates Castle;
- Dock only for a genuinely profitable water opportunity.

Default posture:

**Do not manufacture a Feudal army merely because Feudal exists.**

### Feudal

P0:

- defend exposed gates/resources if pressure exists.

P1:

- Castle resource bank;
- food/wood maturity;
- minimum production/infrastructure required for Castle.

P2:

- wall reinforcement;
- Outpost/tower for a specific approach;
- minimal counter units;
- Blacksmith/Market as required.

P3:

- optional forward pressure only if it is clearly profitable without delaying Castle.

### Castle

Priority order:

1. Castle;
2. economic expansion;
3. Monastery/relic package when relic access is safe and valuable;
4. Siege Workshop when fortified positions or enemy mass justify it;
5. additional TC/production;
6. Imperial conversion when the economy is mature.

Closed-map warning:

Do not convert "safe base" into "static-building addiction." Stone walls, towers, and redundant buildings must compete against Castle, TC, and siege budgets.

## 6. Black Forest / chokepoint priority rules

### Primary objective

Secure food/wood, preserve the economically decisive passage, and exploit siege and positional control.

### Dark Age

P0:

- villager continuity;
- house;
- food.

P1:

- wood supply;
- farming transition;
- scouting of the usable passage.

P2:

- palisade shaping at the actual choke;
- emergency Outpost;
- resource-node protection.

Do not wall the entire map merely because the forest makes it possible.

### Feudal

P0:

- minimum counter army;
- defend the choke or exposed resource.

P1:

- Castle trajectory;
- wood/farm economy;
- production sufficient to hold the passage.

P2:

- walls/gates at real chokepoints;
- tower on high-value defensive location;
- ranged/siege-support preparation;
- Market recovery if resources are badly skewed.

### Castle

P1:

- secure Castle or equivalent strategic conversion;
- food/wood expansion.

P2:

- Siege Workshop;
- Mangonel/Scorpion/Ram according to battlefield;
- Monastery if relics can be reached safely;
- TC expansion if protected.

P3:

- sustained siege;
- forward Castle/fortified position;
- additional production.

### Chokepoint rule

When one passage determines access to the majority of useful map space, its defense can become P1.

But the protected passage must be a real strategic corridor, not a convenient place to spend wood.

## 7. Hybrid-map priority rules

### Primary objective

Maintain a land-capable economy while taking water value when water creates enough incremental value to justify its wood, villager, and naval opportunity cost.

### Water admission test

Open a Dock demand when at least one of these is materially true:

1. Fish provides a meaningful additional food economy.
2. Naval control prevents enemy access to an important resource/economic route.
3. Transport opens otherwise inaccessible territory.
4. Water control materially improves expansion or trade.

Do not open the Dock merely because water is visible.

Official AI changes have repeatedly tightened this principle, including reducing unnecessary docks when ships are not planned and correcting cases where the AI selected a distant dock despite having nearby useful water.

### Dark/Feudal

P0:

- land economy remains alive regardless of water intent.

P1:

- normal age trajectory;
- one Dock when the water admission test passes.

P2:

- Fishing Ships;
- minimum naval defense if enemy water threat exists;
- transport only when access requires it.

Do not fund full naval control before the land economy can survive the investment unless water is already the primary economy.

### Castle

Maintain one of three states:

**Land-dominant**

- fishing remains supplemental;
- naval production limited to the amount required for defense/utility.

**Balanced**

- water and land both contribute materially;
- naval and land production grow together.

**Water-dominant**

- water is carrying a large part of the economy or access plan;
- naval production becomes P1/P2;
- land economy is deliberately reduced or redirected.

### Water shutdown

Shut down naval expansion when:

- fish is exhausted or no longer competitive;
- the enemy has lost meaningful naval presence;
- transport objectives are complete;
- ships are consistently idle;
- the land economy has become the better use of wood/food.

Retain enough naval/transport capability when future crossing remains possible.

## 8. Full-water priority rules

### Primary objective

Treat water access and control as a core economy and military domain, not a decorative side project.

### Opening

P0:

1. Villagers.
2. Food.
3. House/population.
4. Immediate shoreline survivability.

P1:

1. Dock capability.
2. Fishing economy when available.
3. Normal age trajectory.
4. At least one protected route between economic activity and shoreline.

P2:

- naval defense;
- fishing expansion;
- transport;
- landing/shoreline scouting;
- island resource access.

The official AI has received repeated fixes and improvements for water and island behavior, including transport across islands, fishing behavior, migration, and dock selection.

### Feudal

P0:

- preserve fishing and villager continuity;
- defend against enemy naval interruption.

P1:

- naval production if water is contested;
- fishing expansion if safe.

P2:

- naval counters;
- transport preparation;
- landing reconnaissance;
- land military sufficient to defend economic expansion.

### Castle

P1/P2:

- sustained naval control when strategically necessary;
- transport;
- water upgrades;
- land-side expansion;
- Siege/Monastery only where the land battlefield justifies them.

P3:

- multiple Docks when current naval production demand actually requires more capacity;
- naval siege;
- island expansion;
- trade when economically justified.

### Water-to-land rebalance

When water is secure:

1. reduce unnecessary naval queue growth;
2. increase land economy;
3. establish mainland/secondary resource access;
4. convert water advantage into land production/TC/siege.

Water control is a means of securing a position, not an excuse to keep producing ships forever.

## 9. Transport-critical priority rules

Transport-critical is the strictest profile because transport is infrastructure for survival or expansion rather than optional mobility.

### Entry condition

Enter transport-critical posture when:

- a required destination is disconnected by water;
- no current land route exists;
- losing access would strand resources, settlers, or military.

### Immediate priority

P0:

1. preserve current settlement;
2. secure the Dock/transport source;
3. maintain enough food/wood to execute the crossing;
4. protect the transport operation.

P1:

1. acquire or preserve transport capability;
2. identify a viable landing;
3. prepare a minimum landing force;
4. prepare first-stage economy/infrastructure on the destination.

P2:

- escort ships;
- naval clearance;
- landing military;
- secondary transport;
- emergency fallback landing.

P3:

- permanent expansion;
- trade;
- additional Docks;
- naval siege/control.

### Transport lifecycle

    NEED CROSSING
        ->
    TRANSPORT DEMAND
        ->
    DOCK CAPABILITY
        ->
    TRANSPORT FEASIBLE
        ->
    LOAD
        ->
    MOVE
        ->
    LAND
        ->
    DESTINATION WITNESS
        ->
    ESTABLISH LAND CAPABILITY
        ->
    RELEASE TRANSPORT DEMAND
        ->
    REASSESS WATER POSTURE

Do not clear the transport demand because a Transport Ship was produced.

The witness is successful transfer and usable destination access.

### Transport failure

A failed crossing does not automatically invalidate the strategic demand.

Preserve the demand when:

- the destination remains necessary;
- the Dock remains usable;
- another route/landing can be attempted.

Invalidate it only when:

- the destination is no longer strategically required;
- a stable land route appears;
- the strategic objective changes.

## 10. Cross-profile priority table

| Capability | Arabia | Arena | Black Forest | Hybrid | Full water | Transport-critical |
|---|---:|---:|---:|---:|---:|---:|
| Normal land economy | P0/P1 | P0/P1 | P0/P1 | P0/P1 | P1 | P0/P1 |
| Minimum land defense | P0/P2 | P0/P2 | P0/P2 | P0/P2 | P1/P2 | P0/P2 |
| Walls | P2 | P2 | P1/P2 at real choke | P2 | P2 | P2 |
| Towers | P2 | P2 | P2 at key position | P2 | P2 shore/landing defense | P2 dock/landing defense |
| Castle trajectory | P1 | P1 | P1 | P1 | P1/P2 | P1 |
| Siege | P2 | P2 | P1/P2 | P2 | P2 | P2 |
| Monastery/relics | P2/P3 | P2/P3 | P2/P3 | P2/P3 | P2/P3 | P2/P3 after crossing stability |
| Dock | Usually closed | Usually closed | Usually closed | P1/P2 | P1 | P1 |
| Fishing | Closed unless real water value | Conditional | Conditional | P1/P2 | P1 | P2 if available |
| Naval combat | Conditional | Conditional | Conditional | P2 | P1/P2 | P2 |
| Transport | Conditional | Conditional | Conditional | P2 | P1/P2 | P0/P1 |
| Extra TCs | P2/P3 | P2/P3 | P2/P3 | P2/P3 | P2/P3 | P2/P3 |
| Imperial conversion | P3 | P3 | P3 | P3 | P3 | P3 |

## 11. Threat overrides

Map profile never suppresses an immediate threat.

### Cavalry threat

Open:

- Spear/Pike/Halberdier demand;
- defensive production if required.

Do not automatically cancel:

- Castle,
- dock,
- transport,
- relic,

unless the threat makes the original objective infeasible.

### Ranged threat

Open:

- Skirmisher/other appropriate counter;
- defensive positioning;
- tower only when position-specific.

### Siege threat

Open:

- mobility/pressure;
- Monk capability where relevant;
- own siege if positional response requires it.

### Naval threat

On hybrid maps:

- increase naval defense only to the level required to preserve water value.

On full-water maps:

- treat naval defense as core military.

On transport-critical maps:

- treat naval defense as protection of infrastructure.

## 12. Resource protection rules by profile

### Arabia

Protect Castle trajectory from:

- unnecessary walls;
- excess Feudal military;
- redundant production.

### Arena

Protect Castle/boom trajectory from:

- pointless Feudal military;
- redundant walls;
- excessive static defense.

### Black Forest

Protect:

- wood for chokepoints;
- food for Castle/production;
- enough stone for strategic Castle/forward defense.

### Hybrid

Protect both:

- land Castle/economic trajectory;
- minimum water investment required to preserve the water opportunity.

Do not let either side grow without proving its value.

### Full water

Protect:

- Dock and fishing capability;
- naval replacement capacity while water is contested;
- enough land economy to exploit water control.

### Transport-critical

Protect:

- Dock;
- Transport capability;
- landing force;
- initial destination economy.

During a crossing, these can temporarily outrank otherwise normal age/boom spending.

## 13. Release rules

Every profile must periodically answer:

**Is the reason for this map-conditioned capability still true?**

Release:

- Dock expansion when water value falls;
- fishing expansion when fish value falls;
- naval expansion after water control is secured and no threat remains;
- transport after successful destination access is established;
- walls/towers after the threatened route is no longer material, unless they remain strategically useful;
- siege after the structural/battlefield target disappears;
- relic contest when safety/opportunity cost turns negative.

Release means **stop creating new obligations**.

It does not mean demolish useful infrastructure or throw away existing units.

## 14. Implementation contract

Information owns the observations:

- openness;
- enclosure;
- choke density;
- water value;
- disconnected destinations;
- resource exposure;
- enemy threat;
- relic opportunity;
- naval threat;
- landing viability.

Strategy owns the profile and demand:

    OBSERVE
      -> MAP PROFILE
      -> STRATEGIC POSTURE
      -> DEMAND

Domains own execution:

    DEMAND
      -> CAPABILITY
      -> FEASIBILITY
      -> ACTION
      -> WORLD-STATE WITNESS

State stores only what must survive the current rule pass.

The compiler validates that each demand has:

- an admissibility condition;
- a capability/provider;
- an engine feasibility path;
- an action;
- a world-state witness;
- release/invalidation semantics.

The map profile itself is not allowed to become a general-purpose scheduler.

## 15. Design intent

The desired player behavior is:

**same Byzantine player, different priorities because the position changed.**

Not:

**six separate build orders pretending to be one AI.**

The current stock AI direction supports treating map shape and water as strategic inputs. Recent official updates explicitly mention transport improvements on island maps, water/fishing behavior, map-closure checks for walls, and reducing unnecessary docks when ships are not planned. Those are precedent for the capability-gated approach used here.
