# Construction Module

Construction owns building capability and the construction lifecycle required by the Byzantine player.

## Product role

Construction turns legitimate building demands into infrastructure.

It must support conditional capability for:

- houses;
- resource dropsites;
- military production;
- Blacksmith/Market;
- Town Centers;
- Castle;
- Siege Workshop;
- Monastery;
- University;
- docks;
- walls and gates;
- Outposts;
- watch/Guard Towers;
- Bombard Towers;
- other ordinary infrastructure when the strategic position requires it.

## Required lifecycle

    demand
      -> prerequisites
      -> existing/pending check
      -> builder capability
      -> can-build feasibility
      -> build action
      -> pending
      -> completed world state
      -> release or invalidation

## First vertical-slice responsibility

Castle construction is the first acceptance case.

Then extend the same lifecycle to dock, siege, monastery, and defensive-structure demands.

A failed or delayed building attempt must not kill the strategy that requested it.

## Sources

Read SOURCE_MAP.md, validation/castle-capability-checklist.md, validation/repair-lifecycle-replay.js, docs/audits/Basilisk-Lifecycle-Audit-2026-09.md, Basilisk/Basilisk.per, PER_PRIMITIVE_MAP.md, and the community examples.

## Boundary

A build request is not completion.

A pending foundation is not a completed building.

Construction does not own the strategic reason for the building.
