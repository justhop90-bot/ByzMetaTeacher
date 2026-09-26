# Strategy Module

Strategy decides what kind of position the Byzantine player is trying to create.

## Owns

- opening/posture selection;
- threat-driven strategy changes;
- BOOM/pressure/defense/Castle/Imperial posture;
- strategic demand creation;
- strategic demand cancellation and invalidation;
- opportunity-cost decisions.

## Product role

Strategy is not a build-order script.

A strategy says:

What position do I want, and does it remain worth pursuing?

It does not say:

Run these twelve actions in this order regardless of the board.

## Map-conditioned priority contract

Strategy reads `LearnerAI/MAP_PRIORITY_RULES.md` after Information produces map/context observations. The map profile changes admissibility and priority, not the identity of the player. Transport-critical status can override the normal map profile when disconnected access becomes necessary.

## First vertical-slice responsibility

Choose and maintain a Dark -> Feudal -> Castle trajectory.

Allow real pressure to temporarily override that trajectory when necessary.

Restore it when the battlefield permits.

Cancel it when it is genuinely obsolete.

## Sources

Read docs/project/BotDirection.txt, docs/project/Basilisk-Controller-Specification.md, Basilisk/Basilisk.per, validation/strategy-rush-checklist.md, and LearnerAI/SOURCE_MAP.md.

## Boundary

Strategy decides why.

It does not directly build, train, research, or attack.
