# LearnerAI

LearnerAI is the design, teaching, semantic-validation, and compilation workspace for a competent stock-style 1v1 Byzantine AoE2DE AI.

It is documentation-first while interfaces and source contracts are being established, but it is not documentation-only. The workspace exists to produce a real player. The compiler exists to make that player explicit, checkable, and maintainable. Runtime behavior remains the final authority.

## What we are building

The target player must:

- maintain a coherent Dark Age economy;
- adapt its plan to common open, closed, hybrid, and water contexts;
- transition through Feudal without wrecking the next strategic objective;
- maintain a minimum defensible military;
- build ordinary economic and military infrastructure when justified;
- use docks, fishing, naval units, and transport when water matters;
- use siege when the battlefield requires it;
- use Monks and contest relics when the position justifies it;
- use walls, gates, towers, Castles, and late defensive structures conditionally;
- reach Castle at sensible times for the position;
- expand its economy in Castle Age;
- adapt composition to observed enemy commitments;
- recover when the preferred plan is interrupted;
- reach Imperial with a functioning economy;
- convert Imperial resources into pressure.

The target is Byzantines first, on ordinary random-map situations. Generalization comes later.

## North-star loop

    OBSERVE
      -> INTERPRET
      -> STRATEGIC POSTURE
      -> PERSISTENT DEMAND
      -> CAPABILITY
      -> ENGINE FEASIBILITY
      -> ENGINE ACTION
      -> WORLD-STATE WITNESS
      -> RELEASE / INVALIDATE
      -> REASSESS

Strategy owns why. Domains own how. Engine predicates decide whether an action can execute. World state proves whether it actually happened.

## Governing documents

NORTH_STAR.md: exact target player and non-negotiable behavior.

CAPABILITY_MATRIX.md: complete stock-style Byzantine capability coverage, priority bands, map-conditioned branches, and lifecycle expectations.

SOURCE_MAP.md: where engine, community, Basilisk, compiler, and runtime information comes from.

BUILD_ROADMAP.md: implementation order and exit conditions.

Read these before adding a module, compiler feature, goal, timer, claim, or abstraction.

## Relationship to Basilisk

Basilisk remains the current production controller and strongest local implementation reference.

LearnerAI is not a hidden Basilisk rewrite. Learn from Basilisk, compare against it, and reuse verified mechanisms where appropriate. The new learner player must earn its behavior through explicit specifications and runtime evidence.

## Relationship to the native compiler ecosystem

LearnerAI does not replace the AoE2 native parser ecosystem.

The pinned aoe2-ai-parser backend validates emitted .per syntax and native command usage. LearnerAI owns semantic questions the native parser does not know about: demand intent, capability providers, lifecycle meaning, ownership, pending state, witnesses, release, cancellation, recovery, and map-conditional capability.

## Information boundary

The repository already contains the necessary information:

    docs/reference/AIREF-COMMAND-SOURCE.md
    docs/reference/inventories/
    docs/reference/engine/
    docs/reference/BYZANTINES_manifest.txt
    docs/project/BotDirection.txt
    docs/project/Basilisk-Controller-Specification.md
    Basilisk/Basilisk.per
    validation/
    LearnerAI/PER_PRIMITIVE_MAP.md

Use SOURCE_MAP.md to choose the correct authority rather than searching randomly.

## Current status

Semantic lifecycle compiler: implemented for the current slice.

Native .per backend adapter: implemented.

Combined semantic/native diagnostics: implemented.

Module specifications: established.

Full Byzantine player: not implemented yet.

Runtime tuning of the new player: not implemented yet.

The architecture exists to build the player next. It is not the product by itself.
