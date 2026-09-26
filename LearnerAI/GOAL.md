# Authoritative Goal

## Product goal

Build a competent 1v1 standard-land Byzantine AoE2DE heuristic AI through the LearnerAI semantic model and compiler.

This is a real-player target, not merely a teaching exercise.

The player must sustain a coherent economic and military position through Dark, Feudal, Castle, and Imperial while adapting to observed threats and recovering from interrupted plans.

## Behavioral requirements

### Economy

The economy must continuously support the current strategic posture.

It should answer the binding shortage rather than maintain decorative ratios.

It must:

- keep villagers working;
- establish and replace farms before food collapse;
- maintain houses and dropsites;
- fund the current age objective;
- protect capital investments such as Castle and additional Town Centers;
- recover from raids and resource shortages.

### Age progression

Dark -> Feudal -> Castle is the first vertical slice.

Castle timing must be driven by position, resources, infrastructure, military requirements, and threat, not only by a clock.

Imperial must follow a mature Castle economy rather than prematurely starving the Castle boom.

### Military

The military system must distinguish:

- minimum defensive force;
- tactical counter demand;
- attack reserve;
- production capacity;
- readiness;
- attack execution;
- retreat;
- reinforcement.

The bot must not convert every observed counter-threat into uncontrolled Feudal military mass.

### Infrastructure

Buildings are capability providers.

A production building exists because a live production demand requires it.

A Castle exists because a strategic Castle demand has become admissible and executable.

A Monastery, University, Siege Workshop, Town Center, Blacksmith, Range, Stable, or Barracks must have a traceable strategic or domain purpose.

### Recovery

Temporary execution failure must not erase legitimate intent.

The player must survive:

- resource shortages;
- construction delays;
- failed research starts;
- enemy composition changes;
- raids;
- military losses;
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
- source-order defects where precedence is intentional.

The compiler is not required to replace the native .per parser.

## Scope

Phase 1 scope:

- 1v1;
- standard land maps;
- Byzantines;
- contemporary DE rules/data.

Later expansion may add other maps, civilizations, or broader generalization.

## Non-goals

Do not build:

- a generic scheduler;
- a universal manager;
- a full AoE2 simulator;
- a replacement native parser;
- an optimized build-order generator for every opening;
- a universal multi-civilization architecture before the Byzantine vertical slice works.

## Completion standard

The goal is achieved only when the new player is behaviorally coherent enough to survive ordinary variation and interruption, and its important behaviors can be traced from observation through demand, capability, feasibility, action, witness, release, and reassessment.

Static validity is necessary.

Runtime evidence is mandatory.
