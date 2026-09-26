# Module Map

LearnerAI is organized around one stock-style Byzantine player loop. The directories are ownership boundaries, not arbitrary software packages.

## Repository shape

    LearnerAI/
      NORTH_STAR.md
      SOURCE_MAP.md
      BUILD_ROADMAP.md
      README.md
      GOAL.md
      MODULE_MAP.md
      INTERFACES.md
      SCHEMAS.md
      LIFECYCLE.md
      OWNERSHIP.md
      LEARNING_PATH.md
      ENGINEERING.md
      EXAMPLES.md
      CAPABILITY_MATRIX.md
      PER_PRIMITIVE_MAP.md
      Compiler/
      Engine/
      State/
      Information/
      Strategy/
      Economy/
      Construction/
      Production/
      Military/
      Engineering/

## Capability coverage

CAPABILITY_MATRIX.md is the complete stock-style Byzantine coverage contract. It is consulted before deciding that a capability is missing, optional, or incorrectly scoped.

## Player loop

    Engine/reference
         |
    Information ---> Strategy
         |              |
         |              v
         +-------> persistent demands
                        |
                 +------+-------+---------+
                 |      |       |         |
              Economy Construction Production Military
                 |       |       |         |
                 +-------+-------+---------+
                         |
                    world state
                         |
                    Information

Engineering observes and validates this loop.

Compiler turns semantic specifications into deterministic .per and asks the native backend to verify native language legality.

## Module responsibilities

| Module | Owns | Important capabilities |
|---|---|---|
| Engine | native facts/actions, SNs, timers, IDs | native game vocabulary |
| Information | scouting and interpretation | map, threat, enemy, water, relic, terrain context |
| Strategy | strategic posture and demands | land/water posture, Castle/boom/pressure/defense |
| State | persistent goals and execution memory | durable posture, pending work, justified transitions |
| Economy | workers/resources/recovery | farms, fishing, capital protection, arbitration |
| Construction | building lifecycle | land buildings, docks, towers, walls, Castle |
| Production | queues/capacity | villagers, land units, ships, siege, research |
| Military | defense/attack/siege | counters, readiness, retreat, siege, naval posture |
| Engineering | validation/verification | semantic, native, static, runtime evidence |
| Compiler | semantic translation | lifecycle diagnostics and auditable .per |

## First vertical slice

The first executable player must connect:

    map context
      -> Dark economy
      -> Feudal transition
      -> minimum defensive military
      -> Castle admissibility
      -> Castle prerequisites
      -> Castle construction
      -> Castle witness
      -> economic expansion
      -> production scaling
      -> reassessment

The slice must be structurally capable of branching when the map makes water strategically meaningful.

## Capability coverage

The eventual player must support ordinary conditional capability families:

- economic infrastructure;
- military production;
- siege;
- docks and ships;
- transport;
- Monasteries and Monks;
- relic collection/denial;
- walls and gates;
- Outposts and towers;
- Castles;
- late Bombard Towers;
- Town Centers and Markets;
- Universities and technology infrastructure.

Not every capability fires in every game.

## Ownership rule

A module may read broadly.

A persistent state variable has one semantic owner.

If a new state has no clear owner, do not add it.
