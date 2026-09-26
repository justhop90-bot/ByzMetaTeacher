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

## Phase 1 — Dark Age vertical slice

Build one coherent Byzantine Dark Age:

- villager continuity;
- houses and dropsites;
- food/wood/gold allocation;
- farms and economic technology decisions;
- scouting;
- opening/posture selection;
- pressure recognition;
- minimum defensive response;
- Feudal-up preparation.

Do not optimize every opening.

Exit condition: Feudal arrives without a self-inflicted economic deadlock, and the player has enough information to choose what happens next.

## Phase 2 — Feudal survival and Castle trajectory

Build:

- minimum credible Feudal military;
- anti-rush response;
- controlled military escalation;
- required Blacksmith/Market capability;
- persistent Castle demand;
- Castle resource protection;
- builder/construction lifecycle;
- Castle completion witness.

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
- siege capability where justified;
- technology opportunity cost;
- monastery/university capability where justified;
- continued worker production.

Exit condition: Castle Age materially improves economy and military power rather than producing a large stockpile.

## Phase 4 — Interruption and recovery

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
- obsolete strategy.

Exit condition: execution failure changes timing or posture without corrupting persistent intent.

## Phase 5 — Military conversion

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

## Phase 6 — Imperial conversion

Build:

- sustainable food throughput;
- adequate production;
- relevant upgrade packages;
- siege/anti-building capability;
- continued expansion;
- strategic conversion of accumulated advantage.

Exit condition: Imperial produces pressure or positional conversion.

## Phase 7 — Competitive hardening

Only after the vertical loop works:

- repeated runtime testing against Extreme;
- comparison against community AI behavior;
- standard-land variation;
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
7. source-order and first-writer/consumer analysis;
8. domain-aware diagnostics;
9. high-level declarations only when native .per becomes unmaintainable.

The next meaningful milestone is the Dark -> Feudal -> Castle Byzantine vertical slice.

## Hard stops

Do not build a general-purpose parser, universal scheduler, full AoE2 simulator, every-civilization framework, or compiler syntax with no complete player behavior behind it.
