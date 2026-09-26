# PER Primitive Section Roadmap

Current completed boundary: Section 41.

Planned remaining sections: 5.

## Remaining

- [x] 37. Diplomacy and player stance: stance-toward, players-stance, set-stance; observation, policy, action, multiplayer/team implications.
- [x] 38. Randomness as a bounded control primitive: generate-random-number, random-number, goal storage, probability shaping, repeat guards, and why randomness must not replace strategy.
- [x] 39. Direct Unit Control and retained search state: up-find-local, up-find-remote, filters, search state, target selection, up-target-objects, up-target-point, reset and retained-state hazards.
- [x] 40. Events, signals, chat, and diagnostics: event-detected, acknowledge-event, signals, taunts, chat traces, DE logging; external synchronization versus strategy state.
- [x] 41. Spatial construction and wall placement: wall/gate placement, perimeter state, placement feasibility, completion percentage, and spatial witnesses.
- [ ] 42. Shared goals and allied coordination: shared-goal primitives, allied resource/goal observations, tribute, ownership and coordination boundaries.
- [ ] 43. Map/game context and conditional loading: map-type, map-size, game-type, civ-selected, load-if symbols, conditional script paths.
- [ ] 44. Advanced cost/search data: up-setup-cost-data, dynamic cost aggregation, object/research cost queries, and why derived cost data is not strategic demand.
- [ ] 45. Dynamic targeting, groups, and tactical state: search groups, target-object state, offensive priorities, garrison/ungarrison, defender counts, and tactical execution witnesses.
- [ ] 46. Package composition and learner-scale engineering: load, include, load-random, source/package boundaries, version gates, parser constraints, and the final end-to-end engineering trace.

## Completion rule

Each section must cross-reference AIRef for engine semantics and at least one real community script, tutorial, or established community discussion where available. Each section follows:

COMMUNITY PATTERN → ENGINE PRIMITIVES → MINIMAL VALID PATTERN → WHY IT WORKS → COMMON FAILURE → BASILISK-SCALE VARIANT → HARD INVARIANTS

The count is a roadmap, not permission to manufacture filler. A family may be split or expanded when research shows that doing otherwise would teach the engine inaccurately.

## Research gate

Before committing a new section:

1. Verify relevant primitives against current AIRef.
2. Cross-reference community practice.
3. Mark version-sensitive or uncertain behavior explicitly.
4. Preserve the semantic lifecycle and module ownership model.
5. Verify the section boundary on fresh main after commit.
