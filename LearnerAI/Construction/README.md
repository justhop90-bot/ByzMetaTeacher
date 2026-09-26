# Construction Module

Construction owns building capability and the construction lifecycle required by the Byzantine player.

## Product role

Construction turns legitimate building demands into infrastructure.

It must support:

- houses;
- resource dropsites;
- military production;
- Blacksmith/Market;
- Town Centers;
- Castle;
- Siege Workshop;
- Monastery;
- University;
- other infrastructure as Strategy and Production require them.

## Required lifecycle

demand -> prerequisites -> existing/pending check -> builder capability -> can-build feasibility -> build action -> pending -> completed world state -> release or invalidation

## First vertical-slice responsibility

Castle construction is the acceptance case.

A Castle demand must not die because Feudal military temporarily consumes wood or because a prior build attempt failed.

## Sources

Read SOURCE_MAP.md, validation/castle-capability-checklist.md, validation/repair-lifecycle-replay.js, docs/audits/Basilisk-Lifecycle-Audit-2026-09.md, Basilisk/Basilisk.per, and PER_PRIMITIVE_MAP.md.

## Boundary

A build request is not completion.

A pending foundation is not a completed building.

Construction does not own the strategic reason for the building.
