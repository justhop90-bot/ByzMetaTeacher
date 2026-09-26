# Information Module

Information turns engine observations into decision-useful interpretation.

## Owns

- scouting;
- enemy composition;
- map/game context;
- terrain/water context;
- threat categories;
- relic opportunity;
- observation freshness;
- re-observation.

## Map-profile responsibility

Information produces the observations consumed by `LearnerAI/MAP_PRIORITY_RULES.md`: openness, enclosure, choke density, water value, disconnected destinations, resource exposure, landing viability, naval threat, and relic opportunity. It does not assign the strategic priority itself.

## Product role

Information must answer decisions:

- Is cavalry actually being committed?
- Is ranged pressure temporary or sustained?
- Is the opponent expanding?
- Where is dangerous army mass?
- Does the map make fishing or naval control worthwhile?
- Is transport required?
- Is a relic worth contesting?
- Is the economy exposed enough to justify walls or towers?
- Is a late fortification needed?
- What changed since the previous interpretation?

Information should not collect facts nobody reads.

## Sources

Use docs/reference/engine/, PER_PRIMITIVE_MAP.md, Basilisk/Basilisk.per, docs/project/BotDirection.txt, and the community examples identified in SOURCE_MAP.md.

## Boundary

Information informs Strategy and domains.

It does not directly spam counters or build orders.
