# LearnerAI Build Roadmap

The implementation order is vertical. We are building a player, not nine isolated folders and a prayer.

## Phase 0 — Semantic and compiler foundation

Deliver:

- source map and stable module contracts;
- demand/capability/action/witness/release semantics;
- pending-state diagnostics;
- native parser backend;
- combined semantic/native validation;
- compiler regression tests.

Exit condition: the compiler can reject the core lifecycle defects we already know how to name.

## Phase 1 — Dark Age and map-context slice

Build one coherent Byzantine opening that can recognize the map context.

Required contexts:

- open land;
- closed land;
- hybrid;
- meaningful fish/water;
- transport/island requirements.

Build:

- villager continuity;
- houses and dropsites;
- food/wood/gold allocation;
- fishing/fish-trap opportunity recognition;
- dock admissibility;
- scouting;
- opening/posture selection;
- pressure recognition;
- minimum defensive response;
- Feudal-up preparation.

The player may correctly choose not to use water.

It must not fail merely because water exists.

Exit condition: Feudal arrives without a self-inflicted economic deadlock and the player has chosen a coherent land/water posture.

## Phase 2 — Feudal survival and Castle trajectory

Build:

- minimum credible Feudal military;
- anti-rush response;
- controlled military escalation;
- required Blacksmith/Market capability;
- persistent Castle demand;
- Castle resource protection;
- builder/construction lifecycle;
- Castle completion witness;
- conditional towers/walls/gates where defensive demand is real.

The Feudal military must not destroy the Castle economy.

Exit condition: the bot can defend itself and still reach Castle on a coherent trajectory.

## Phase 3 — Castle conversion

Castle must immediately become a stronger position.

Build:

- Castle-age economic reallocation;
- Town Center expansion when economically admissible;
- farm scaling;
- production-capacity scaling;
- counter-composition;
- Siege Workshop and meaningful siege demand;
- Monastery capability;
- Monk/relic demand where admissible;
- water/naval continuation or shutdown based on current map state;
- technology opportunity cost;
- University capability where justified;
- continued worker production.

Exit condition: Castle Age materially improves economy and military power rather than producing a large stockpile.

## Phase 4 — Water and transport competence

Treat water as a first-class domain, not an optional afterthought.

Build:

- dock construction;
- fishing economy;
- fish traps;
- naval production;
- naval composition;
- naval upgrades;
- transport ships;
- landing/transport recovery;
- water-to-land economic rebalance;
- naval shutdown when water has lost strategic value.

Exit condition: the player can function on a meaningful hybrid/water situation without becoming a land-only bot that politely watches the ocean.

## Phase 5 — Fortification and defensive infrastructure

Build conditional:

- walls;
- gates;
- Outposts;
- watch/Guard Towers;
- Castles;
- late Bombard Towers.

Each must be demand-driven by map geometry, enemy pressure, exposed economy, age, resources, and opportunity cost.

Exit condition: defensive structures appear when they solve a real problem and do not starve higher-value economy/military demands.

## Phase 6 — Interruption and recovery

Required cases:

- raid;
- cavalry switch;
- ranged switch;
- lost military;
- failed building start;
- delayed research;
- wood shortage;
- gold shortage;
- Castle prerequisite stall;
- naval loss;
- transport failure;
- Monk/relic loss;
- obsolete strategy.

Exit condition: execution failure changes timing or posture without corrupting persistent intent.

## Phase 7 — Military conversion

Separate:

- standing defensive floor;
- tactical counter demand;
- attack reserve;
- production capacity;
- readiness;
- attack execution;
- retreat;
- reinforcement;
- siege;
- reassessment.

Exit condition: the player can build, preserve, replace, and redeploy useful military without attack consumption collapsing defense.

## Phase 8 — Imperial and late-game conversion

Build:

- sustainable food throughput;
- adequate production;
- relevant upgrade packages;
- siege/anti-building capability;
- continued expansion;
- Monks/relic use where useful;
- naval continuation when useful;
- late defensive structures where justified;
- strategic conversion of accumulated advantage.

Exit condition: Imperial produces pressure or positional conversion.

## Phase 9 — Competitive hardening

Only after the vertical loop works:

- repeated runtime testing against Extreme;
- comparison against established community AIs;
- open/closed/hybrid/water variation;
- opening variation;
- recovery cases;
- late-game conversion;
- regression tests from actual failures.

Comparison exists to expose missing behavior, not to cargo-cult a famous script.

## Compiler milestones

The compiler should grow only when the player requires semantic support:

1. lifecycle safety;
2. demand ownership;
3. capability providers;
4. dependency chains;
5. resource/conflict semantics;
6. cancellation and obsolescence;
7. map-conditional capability;
8. source-order and first-writer/consumer analysis;
9. domain-aware diagnostics;
10. high-level declarations only when native .per becomes unmaintainable.

The next meaningful milestone remains the Dark -> Feudal -> Castle Byzantine vertical slice, but that slice must include map-context awareness rather than assuming dry land.

## Hard stops

Do not build a general-purpose parser, universal scheduler, full AoE2 simulator, every-civilization framework, or compiler syntax with no complete player behavior behind it.
