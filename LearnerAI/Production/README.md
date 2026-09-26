# Production Module

Production converts legitimate demand into executable queues.

## Owns

- villager production;
- land-unit production;
- naval-unit production;
- siege production;
- Monk production;
- technology production;
- production-building capability;
- queue state;
- current plus queued counts;
- replacement;
- completion witnesses.

## Product rule

Production capacity follows current demand.

The player should not build production buildings because the strategy name says so. It builds them because standing requirements, replacement rates, naval requirements, siege requirements, or strategic capability require capacity.

## Required capability families

Land units.

Ships, including fishing, warship, and transport roles.

Siege units.

Monks.

Technology packages associated with those capabilities.

## Arabia timing-window reactions

`LearnerAI/ARABIA_ECONOMIC_REACTIONS.md` defines when worker packets and timing evidence may open or close Feudal production targets, second-production capacity, and Fast Castle production shutdown.

Do not overproduce Feudal military.

Maintain a defensible standing floor, then increase production capacity when actual demand requires it.

## Sources

Read Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/audits/Basilisk-Lifecycle-Audit-2026-09.md, LearnerAI/Production/, and SOURCE_MAP.md.

## Boundary

Production does not own the strategic reason for production.
