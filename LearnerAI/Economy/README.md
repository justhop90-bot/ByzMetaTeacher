# Economy Module

Economy keeps the selected strategy economically alive.

## Product role

The economy owns:

- worker allocation;
- food, wood, gold, stone pressure;
- farms;
- dropsite continuity;
- economic technologies;
- capital protection;
- resource recovery;
- temporary resource arbitration.

Its central question is:

What resource shortage currently prevents the chosen strategy from functioning?

## Strategic boundary

Economy does not choose BOOM, RUSH, Castle conversion, or military posture.

It allocates resources so those selected demands can function.

## First vertical-slice responsibility

Dark -> Feudal -> Castle economy.

The Feudal economy must preserve enough military defense without destroying the Castle trajectory.

Castle economy must immediately support farm expansion, production capacity, and economically admissible Town Center growth.

## Recovery responsibility

Economy must recover from:

- raid;
- temporary wood shortage;
- temporary gold shortage;
- delayed farm capacity;
- capital investment;
- military escalation.

## Sources

Read SOURCE_MAP.md, Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/audits/Basilisk-BOOM-Patch-Checklist-2026-09.md, and docs/reference/engine/.

The small files in this directory are the lesson/specification boundaries for the economic slice.
