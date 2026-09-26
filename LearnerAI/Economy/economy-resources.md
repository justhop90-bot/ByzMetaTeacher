# Economy Resources

Defines how Economy answers the current binding shortage.

## Required resource questions

Food: Is villager production or required military food-starved?

Wood: Are farms, houses, dropsites, production, or capital buildings blocked?

Gold: Is the selected technology or premium composition blocked?

Stone: Is there a real Castle or capital demand that justifies protecting stone?

## Rule

Resource allocation follows live strategic demand and opportunity cost.

Do not create a generic economic scheduler.

## Source

Use Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/audits/Basilisk-BOOM-Patch-Checklist-2026-09.md, and engine primitive references.

## Acceptance

A temporary military or construction demand may change allocation without destroying the higher-level strategic intent that created the work.
