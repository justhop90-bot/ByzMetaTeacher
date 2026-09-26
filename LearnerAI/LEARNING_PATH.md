# Learning and Build Path

This path is both curriculum and implementation order. The point is to learn the engine while constructing a complete player.

## Stage 1 — Engine literacy

Learn:

- .ai versus .per;
- rules, facts, actions;
- constants and strategic numbers;
- timers;
- parser limits;
- engine-native feasibility;
- native completion evidence.

Use docs/reference, AIRef, and PER_PRIMITIVE_MAP.md.

## Stage 2 — Dark Age economic slice

Implement:

- villager continuity;
- houses;
- dropsites;
- food/wood/gold allocation;
- farms;
- economic technology;
- age-up preparation.

Every behavior must distinguish intent, capability, feasibility, action, witness, and reassessment.

## Stage 3 — Feudal and Castle trajectory

Implement:

- threat interpretation;
- minimum defensive military;
- limited Feudal escalation;
- Castle demand;
- Castle prerequisites;
- construction;
- Castle witness.

This is the first competitive vertical slice.

## Stage 4 — Castle conversion

Implement:

- farm scaling;
- Town Center expansion;
- production scaling;
- counter composition;
- siege;
- appropriate technology;
- monastery/university capability.

## Stage 5 — Interruption and recovery

Test:

- raids;
- enemy composition switches;
- lost army;
- resource shortages;
- failed construction;
- delayed research;
- obsolete plans.

Persistent strategy must survive transient execution problems.

## Stage 6 — Military conversion

Implement standing army, attack reserve, attack lifecycle, retreat, reinforcement, siege, and production-capacity feedback.

## Stage 7 — Imperial conversion

Implement mature economy -> Imperial -> upgraded production -> siege/anti-building -> strategic pressure.

## Stage 8 — Engineering hardening

Static checks:

- source order;
- first writer/consumer;
- rule limits;
- logical arity;
- invalid identifiers;
- dead-end/unfed/blocked/open-loop state;
- repeated actions;
- impossible witnesses.

Runtime checks remain mandatory.

## Stage 9 — Competitive hardening

Test against Extreme and compare with established community AIs.

The comparison question is:

What useful behavior are they doing that our player is not?

It is not:

How do we copy their entire script?
