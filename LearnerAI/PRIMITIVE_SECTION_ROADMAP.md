# PER Primitive Section Roadmap

This roadmap expands the engine literacy needed by the player. It is not the product roadmap.

The primitive curriculum exists so implementation authors understand what AoE2 can actually observe and execute before inventing semantic machinery around it.

## Completed boundary

Sections 37-41 are documented.

## Remaining

42. Shared goals and allied coordination.

43. Map and game context plus conditional loading.

44. Advanced cost and search data.

45. Dynamic targeting, groups, and tactical state.

46. Package composition and learner-scale engineering.

## Curriculum rule

Every section must connect:

COMMUNITY PATTERN -> ENGINE PRIMITIVES -> MINIMAL VALID PATTERN -> WHY IT WORKS -> FAILURE MODE -> BASILISK-SCALE VARIANT -> HARD INVARIANTS

Each section must:

- verify relevant primitives against current AIRef;
- cross-reference community practice where available;
- identify version-sensitive behavior;
- preserve module ownership;
- identify whether the primitive is observation, admissibility, capability, feasibility, action, witness, or release support.

## Important distinction

The primitive roadmap supports the player. It is not permission to delay player implementation until every primitive family has been documented.

The next player milestone remains the Dark -> Feudal -> Castle Byzantine vertical slice.

## Information source

Use LearnerAI/SOURCE_MAP.md and LearnerAI/PER_PRIMITIVE_MAP.md to locate the authoritative engine material.
