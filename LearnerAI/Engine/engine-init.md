# Engine Init

Defines the initialization contract for the player.

## Must cover

- constants;
- strategic numbers;
- timers;
- initial goals/state;
- default resource-control posture;
- initial information/scouting state.

## Source

Use AIRef, docs/reference/inventories/, docs/reference/engine/, and the verified initialization patterns in Basilisk/Basilisk.per.

## Acceptance

Initialization must produce a known starting state without creating permanent claims, duplicate writers, or accidental strategy decisions.
