# Byzantine Expert Opponent Roadmap

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Make the Byzantine bot behave like a coherent expert opponent: it observes, predicts, arbitrates, executes, verifies world state, recovers, and reassesses. More rules are not the goal; better decisions are.

**Architecture:** Keep the existing ByzMetaTeacher compiler and native .per model. Use Naga and other community AIs as behavioral evidence, not templates. Use Sandy Petersen's documented test-driven design philosophy as a process reference: explicit rules, strong faction identity, observed play, rapid correction, repeated playtesting.

**Global constraints**
- Byzantine behavior remains the product; the compiler is the substrate.
- Do not become a tournament-only bot, generic utility AI, simulator, or second .per language.
- Preserve DEMAND -> ADMISSIBILITY -> CAPABILITY -> FEASIBILITY -> ACTION -> WORLD-STATE WITNESS -> RELEASE.
- Preserve OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT.
- Engine fact, community evidence, compiler policy, and unknown remain distinct.
- Unknown native behavior remains OPEN/fail-closed.
- can-* means permission/feasibility, not completion.
- Pending is not a world-state witness. Timers are cadence, not truth.
- Source order and recurrent rules are real behavior.
- Every strategic change must have an observable behavioral reason and focused acceptance scenario.
- Distinguish parser/compiler verification, native validation, CI, and actual game behavior.

## Phase 0: Freeze the baseline and establish the behavioral contract
- [ ] Pin the exact Git artifact and record source fingerprint, rule count, constants, line count, and hard parser findings.
- [ ] Separate native grammar defects from semantic and behavioral defects.
- [ ] Build a scenario matrix covering Dark, Feudal, Castle, Imperial, pressure, defense, scouting, siege, relics, water, transport, recovery, and late-game spending.
- [ ] For each scenario record intended decision, execution, world witness, recovery, and current failure.
- [ ] Record food/wood/gold/stone banks, army composition, production, research, and idle states at fixed checkpoints.
- [ ] Record community reference patterns and known Naga limitations.
- [ ] Freeze this baseline before strategic tuning.

Acceptance: a deterministic baseline report exists and no strategic logic is changed in Phase 0.

## Phase 1: Native grammar and rule-shape hardening
- [ ] Remove the current 16-way logical expression without changing scouting semantics.
- [ ] Split or structurally reduce the 3-way Imperial farm arbitration.
- [ ] Normalize the 3-way siege-approach expression.
- [ ] Split the 34-element late-resource rule into independently meaningful decisions.
- [ ] Reduce all 32-element cliff-edge rules where practical.
- [ ] Add compiler fixtures for binary logical emission and rule-size budgeting.
- [ ] Re-run parser, semantic, native, determinism, and CI gates.

Acceptance: zero logical arity defects and zero rules above 32 elements.

## Phase 2: Strategic executive and continuous resource spending
- [ ] Deep-audit every current late-game spending rule before threshold changes.
- [ ] Separate surplus detection from spend selection.
- [ ] Turn fixed military targets into minimums, not terminal spend conditions.
- [ ] Add a continuous spending envelope driven by objective, enemy composition, production capacity, technology, and resource pressure.
- [ ] Add hysteresis and emergency consumption for extreme banks.
- [ ] Prevent spending from starving age-up, essential upgrades, defense, or recovery.

Acceptance: persistent late-game surplus is converted into relevant military/economic/technology/siege demand without oscillation or starvation.

## Phase 3: Scouting, prediction, and counter doctrine
- [ ] Audit observation -> prediction -> counter transitions.
- [ ] Reduce redundant scout phase states when behavior is identical.
- [ ] Predict enemy commitment from production buildings, upgrades, and early unit evidence.
- [ ] Distinguish expected composition from confirmed composition.
- [ ] Pre-position counters before full contact.
- [ ] Add exposed-economy and production-target decisions.
- [ ] Add intelligent wall/fortification handling and stale-intel expiry.

Acceptance: the bot changes counters because of meaningful enemy evidence and can turn information into a target or timing advantage.

## Phase 4: Army control, attack, and recovery
- [ ] Audit attack admission versus actual attack execution.
- [ ] Establish screen/main/siege/raid/reserve roles.
- [ ] Add fortified-position handling and efficient siege use.
- [ ] Preserve armies under defensive fire where native control permits.
- [ ] Make army-loss recovery change production and attack posture.
- [ ] Reassess attack continuation after enemy strength changes.
- [ ] Expire obsolete counter packages.

Acceptance: fewer wasteful engagements, better siege use, coherent retreat/reposition/re-engage behavior, and meaningful recovery.

## Phase 5: Economy, construction, and technology coherence
- [ ] Treat houses, farms, dropsites, camps, mills, markets, and starvation recovery as one economy.
- [ ] Align villager allocation with current strategic demand rather than only fixed percentages.
- [ ] Expand production capacity when bank pressure warrants it.
- [ ] Make research compete correctly with military production and infrastructure.
- [ ] Use the market as a pressure valve, not as a substitute for gathering control.
- [ ] Stop economic expansion when military/tech/siege requirements dominate.

Acceptance: economy follows strategy and changes posture when strategy changes.

## Phase 6: Byzantine identity and breadth
- [ ] Audit Cataphract, Varangian Guard, Halberdier, Arbalester, Camel, siege, monastery, relic, Keep, Bombard Tower, wall, naval, and transport transitions against current DE data.
- [ ] Verify water/transport execution and loss recovery.
- [ ] Verify map/opening variation without exploding state count.
- [ ] Make Byzantine bonuses and constraints change decisions materially.

Acceptance: Byzantine identity is visible across standard land, Arena, water/hybrid, siege-heavy, trash-war, mounted, ranged, infantry, and mixed-pressure scenarios.

## Phase 7: Scenario matrix, empirical tuning, release
- [ ] Run standardized scenarios and record first behavioral failure.
- [ ] Repair one causal defect at a time and preserve regression evidence.
- [ ] Repeat parser/native/compiler and gameplay verification.
- [ ] Freeze the release artifact with exact Git SHA, source hash, rule count, validation evidence, and package manifest.

Acceptance: deterministic, natively valid, behaviorally coherent, reproducible release.

## Operating rule for every future change
1. State the observed behavior.
2. Identify observation, arbitration, execution, witness, recovery, or reassessment.
3. Cross-reference engine evidence and community practice.
4. Make the smallest hypothesis-driven change.
5. Verify parser/semantic/native gates.
6. Verify the affected game scenario.
7. Record the result before adding another rule.

The bot is better only when its observed decisions become more coherent, timely, economical, adaptive, and recoverable.
