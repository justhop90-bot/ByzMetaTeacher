# Module Map

LearnerAI is organized around one player loop. The directories are ownership boundaries, not arbitrary software packages.

## Repository shape

    LearnerAI/
      NORTH_STAR.md       target player
      SOURCE_MAP.md       information authorities
      BUILD_ROADMAP.md    implementation order
      README.md           entry point
      GOAL.md             product requirements
      MODULE_MAP.md       ownership and dependencies
      INTERFACES.md       cross-module contracts
      SCHEMAS.md          demand/capability/action/witness model
      LIFECYCLE.md        common execution lifecycle
      OWNERSHIP.md        persistent-state rules
      LEARNING_PATH.md    build/teaching sequence
      ENGINEERING.md      static/runtime verification
      EXAMPLES.md         canonical behavior traces
      PER_PRIMITIVE_MAP.md engine primitive reference index
      Compiler/           semantic compiler and native adapter
      Engine/             native engine facts/actions and versioned references
      State/              persistent intent and execution memory
      Information/        observations and interpretation
      Strategy/           strategic posture and demand creation
      Economy/             resource/workforce policy
      Construction/       building capability and construction lifecycle
      Production/         production capability and queue execution
      Military/           defense, composition, attack, siege, recovery
      Engineering/        verification and diagnostics

## Dependency flow

    Engine/reference
         |
    Information ---> Strategy
         |              |
         |              v
         +-------> persistent demands
                        |
                 +------+------+
                 |      |      |
              Economy Construction Production
                 |      |      |
                 +------+------+
                        |
                     Military
                        |
                    world state
                        |
                    Information

Engineering observes and validates this loop. It is not a gameplay manager.

Compiler turns semantic specifications into deterministic .per and asks the native backend to verify native language legality.

## Module responsibilities

| Module | Owns | Consumes | Produces |
|---|---|---|---|
| Engine | native facts, actions, SNs, timers, IDs | AIRef, engine reference, DE data | engine capability vocabulary |
| Information | scouting and interpretation | engine observations, Basilisk patterns | threat/map/opening facts |
| Strategy | strategic posture and demand creation/cancellation | information, economy/army state | persistent strategic intent |
| State | persistent goals and local execution memory | Strategy/domain lifecycle | durable state representation |
| Economy | worker/resource allocation and recovery | Strategy demands, current shortages | resource posture and economic capability |
| Construction | building capability/action lifecycle | demands, prerequisites, builders | completed infrastructure |
| Production | queues, unit/tech production, capacity | military/economic demands | units and research |
| Military | minimum defense, counters, attack, siege, retreat | information + strategy | military demands and execution |
| Engineering | static/runtime verification | all modules + compiler output | diagnostics and regression evidence |
| Compiler | semantic validation + deterministic emission | schemas + engine primitive profile | auditable .per |

## First vertical slice

The first executable learner player must connect these modules end-to-end:

    Dark economy
      -> Feudal transition
      -> minimum defensive military
      -> Castle admissibility
      -> Castle prerequisites
      -> Castle construction
      -> Castle witness
      -> economic expansion
      -> production scaling
      -> reassessment

Do not implement every module broadly before this trace exists.

## Source location

Use SOURCE_MAP.md for the authoritative source behind every module.

Use Basilisk/Basilisk.per for proven implementation patterns.

Use docs/reference/ for engine facts.

Use validation/ for known lifecycle and regression contracts.

Use LearnerAI/Compiler/ for compiler semantics and native validation.

## Ownership rule

A module may read broadly.

A persistent state variable has one semantic owner.

If a new state has no clear owner, do not add it.
