# Authoritative Goal

## Product goal

Build a competent stock-style 1v1 Byzantine AoE2DE heuristic AI for ordinary random-map play.

The player should not be land-only. It must understand enough of the common AoE2 ruleset to behave like a normal stock AI across open land, closed land, hybrid, and meaningful water situations.

This includes conditional use of:

- docks and fishing;
- naval combat and transport;
- walls, gates, Outposts, watch/Guard Towers, Castles, and late Bombard Towers;
- Siege Workshops and appropriate siege units;
- Monasteries, Monks, healing/conversion, and relic collection/denial;
- Markets, Town Centers, Blacksmiths, Universities, and other ordinary infrastructure.

The requirement is **competence and conditional use**, not maximum utilization of every building.

## Behavioral requirements

### Economy

The economy must continuously support the current strategic posture.

It should answer the binding shortage rather than maintain decorative ratios.

It must:

- keep villagers working;
- establish and replace farms before food collapse;
- maintain houses and dropsites;
- fund the current age objective;
- protect capital investments such as Castle, Town Centers, docks, and major infrastructure;
- recover from raids and resource shortages;
- recognize when water economy is valuable and when it should be abandoned.

### Map-aware play

The player must derive strategy from the map and current position.

It must recognize at least these broad cases:

- open land;
- closed land;
- hybrid;
- meaningful fishing water;
- island/transport problems;
- defensively exposed resource areas.

Map context should modify demand creation.

A land map with no worthwhile water should not trigger pointless dock construction.

A hybrid or water map where fish, transport, or naval control materially affect the position should create the appropriate demand.

### Military and infrastructure

The military system must distinguish:

- minimum defensive force;
- tactical counter demand;
- attack reserve;
- production capacity;
- readiness;
- attack execution;
- retreat;
- reinforcement;
- siege support.

Infrastructure must follow capability demand.

A Range exists because ranged production is needed.

A Siege Workshop exists because siege capability is needed.

A Monastery exists because Monk/relic/healing/conversion capability is useful.

A dock exists because water economy, naval control, trade, or transport is strategically relevant.

A Bombard Tower exists because late defensive artillery is economically and strategically justified.

### Recovery

Temporary execution failure must not erase legitimate intent.

The player must survive:

- resource shortages;
- construction delays;
- failed research starts;
- enemy composition changes;
- raids;
- military losses;
- naval setbacks;
- transport setbacks;
- obsolete plans.

## Architectural requirements

Use:

OBSERVE -> INTERPRET -> STRATEGIC POSTURE -> PERSISTENT DEMAND -> CAPABILITY -> FEASIBILITY -> ACTION -> WORLD-STATE WITNESS -> RELEASE/INVALIDATE -> REASSESS

Strategy owns why.

Domains own how.

Engine owns feasibility and execution.

World state proves completion.

Engineering validates the chain.

## Compiler requirements

The compiler should make semantic defects visible before runtime.

It must eventually detect:

- missing demand owners;
- unfed demands;
- capability dead ends;
- feasibility/action confusion;
- repeated actions;
- missing pending lifecycle;
- impossible witnesses;
- open-loop release;
- stale execution claims;
- conflicting writers;
- broken dependency chains;
- persistent intent that disappears on temporary execution failure;
- source-order defects where precedence is intentional;
- missing capability paths for ordinary player surfaces such as docks, siege, fortifications, and Monks.

The compiler is not required to replace the native .per parser.

## Scope

Phase 1 scope:

- 1v1;
- ordinary random-map land/hybrid/water situations;
- Byzantines;
- contemporary DE rules/data.

Later expansion may add other civilizations, broader map families, or more specialized strategies.

## Non-goals

Do not build:

- a generic scheduler;
- a universal manager;
- a full AoE2 simulator;
- a replacement native parser;
- an optimized build-order generator for every opening;
- a universal multi-civilization architecture before the Byzantine player works.

## Completion standard

The goal is achieved only when the new player can handle the ordinary game surface without collapsing into a special-case script.

It must demonstrate coherent economic and military behavior, conditional infrastructure use, meaningful map adaptation, recovery from interruption, and traceable demand/capability/feasibility/action/witness/release lifecycles.

Static validity is necessary.

Runtime evidence is mandatory.
