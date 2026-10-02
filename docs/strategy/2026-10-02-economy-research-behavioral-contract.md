# Economy and Research Behavioral Contract

## Purpose

Encode the recurring community pattern that economy exists to keep the chosen strategic position affordable, while research exists only when its strategic value exceeds competing uses of the same resources.

## Core state

`EconomyState` is interpreted from current strategic demands, protected resource floors, provider capability, and observed world state. It is not an income simulator.

The required chain is:

`economic reason -> protected floor -> admissibility -> escrow/affordability -> action -> witness -> release/recovery`

## Resource owners

Every protected stockpile has one semantic owner:

- age transition;
- military production;
- production capacity;
- research;
- construction;
- water;
- emergency recovery.

Claims from different owners arbitrate through the existing resource/escrow plane.

## Community-derived economic rules

1. Preserve villager and population continuity before discretionary investment.
2. Expand farms when food continuity, not a fixed timer, justifies more wood expenditure.
3. Build dropsites and capital buildings because a resource or strategic demand needs them.
4. Use Market as an imbalance/recovery capability, not as an unconditional trade command.
5. Preserve Castle/Imperial resource banks when those age transitions remain strategically valid.
6. Release research or expansion reserves only when their owner completes, invalidates, or explicitly loses precedence.
7. Do not turn worker allocation into a universal scheduler. Demand should shape the resource posture.

## Research package

The Byzantine stock package may synthesize verified technologies such as:

- Wheelbarrow;
- Double-Bit Axe;
- Horse Collar;
- Gold Mining;
- Fletching;
- Hand Cart;
- Bow Saw;
- Gold Shaft Mining;
- Heavy Plow;
- Bodkin Arrow;
- Two-Man Saw;
- Conscription;
- Chemistry.

Availability and age come from EffectiveCivData. A technology not available to Byzantines remains excluded.

## Opportunity cost

A technology is not admitted simply because it is available.

The controller must preserve enough resources for the active higher-priority demand unless emergency policy explicitly overrides the floor.

## Recovery

A failed research start creates a blocked execution state, not permanent invalidation.

A temporary resource shortage delays the action.

Completion is witnessed from research state.

## Acceptance

Required evidence:

- typed reason and owner;
- current technology/provider facts;
- escrow-aware feasibility;
- completion witness;
- deterministic release;
- recovery after temporary resource loss;
- native zero-findings fixture;
- deterministic output.

Open runtime questions remain OPEN.
