# Byzantine Expert Opponent Roadmap

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Make the Byzantine bot behave like a coherent expert opponent: it observes, predicts, arbitrates, executes, verifies world state, recovers, and reassesses. More rules are not the goal; better decisions are.

**Architecture:** Keep the existing ByzMetaTeacher compiler and native .per model. Use Naga and other community AIs as behavioral evidence, not templates. Use Sandy Petersen's documented test-driven design philosophy as a process reference: explicit rules, strong faction identity, observed play, rapid correction, repeated playtesting.

**Roadmap status as of 2026-10-04**

- **Completed/merged:** resource-front lumber placement lifecycle (PR #363); unified opening pressure + five-selector multi-fact emission and Feudal resource-front gating (PR #365); reinforcement-driven second production capacity (PR #366); production-commitment prediction with lower-priority Feudal counter floors, confirmed-pressure suppression, native fail-closed parity, and synchronized `Byzantine.per` lifecycle (PR #367 + corrective PR #370).
- **Still open:** the broader Phase 0 baseline freeze, continuous late-game spending envelope, exposed-economy/production-target prediction, stale-intel expiry, wall/geometry implementation, attack admission/force preservation/recovery, Byzantine breadth audit, and standardized runtime scenario verification.
- **Roadmap correction:** the static late-game objective ladder already implements the intended `siege -> defensive structures -> production -> Town Centers` sequence with reassessment. The next Phase 4 work should therefore focus on attack admission, force preservation, siege commitment, and recovery rather than reordering the target ladder without replay evidence.
- **Evidence boundary:** queue-capacity semantics remain `OPEN`; production-capacity repairs may use verified reinforcement/pressure policy, but must not fabricate queue-depth witnesses. Runtime replay validation remains a separate claim from parser/native/compiler CI.

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
- [x] Audit observation -> prediction -> counter transitions for Feudal mounted/ranged production commitment.
- [ ] Reduce redundant scout phase states when behavior is identical.
- [x] Predict enemy commitment from production buildings plus early-unit absence; confirmed unit pressure remains higher priority.
- [x] Distinguish expected composition from confirmed composition.
- [x] Pre-position small counters before full contact while keeping prediction fail-closed.
- [ ] Add exposed-economy and production-target decisions.
- [ ] Add intelligent wall/fortification handling and stale-intel expiry.

Acceptance: the bot changes counters because of meaningful enemy evidence and can turn information into a target or timing advantage.

## Phase 3.5: Walling, choke-point defense, and defensive geometry

Walling is a time-buying control system, not a cosmetic perimeter and not a substitute for an army. The bot should decide whether a wall closes a meaningful route, protects exposed economy, creates a defendable funnel, or preserves a strategic timing window. It should also understand when a wall is harmful because it blocks its own army, traps builders, creates a false sense of safety, or consumes resources needed for the next objective.

Evidence synthesis:
- **Naga:** the current community AI database lists Naga as supporting general closed-land maps and enemy-strategy adaptation, but explicitly lists **Walling** and **Playing vs walls** as unsupported features. Treat Naga as evidence for breadth, map variation, and adaptive strategy, not as a wall-placement authority. [AoE AI Database: Naga](https://aoeaidatabase.pythonanywhere.com/ai?name=Naga)
- **AoE2 community practice:** experienced players use walls to buy reaction time, protect external resources, and preserve an economic or age-up timing. Community reports also show how hard this is for AI: perimeter systems can leave gaps, misuse resource/blocker geometry, fail to prioritize the real entrance, or delay the army because the wall becomes an internal obstruction. Intelligent walling therefore requires map-aware placement, repair awareness, and an explicit escape/response route. [Age of Empires II: Building & Defending Your Empire](https://www.ageofempires.com/learn-to-play/defending-your-empires-aoe2/) and [AoE2 community walling/AI discussion](https://steamcommunity.com/app/813780/discussions/0/597398236592895380/?ctp=2)
- **Engine/official evidence:** Definitive Edition AI behavior has explicitly been changed to consider how closed a map is before committing to walls, and to build a forward tower enclosed by palisades when there is a large local advantage. This supports a conditional defense model rather than “always wall.” [AoE II DE Update 81058](https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-81058/)
- **Bruce Shelley:** Ensemble design material describes map-generated choke points as deliberate strategic locations, with walls tying into cliffs to form a defensible “great wall,” while warning that surrendering control of the center can lose the game. His AoE2-era answers also treat fixed fortifications as real tactical thresholds that normal units cannot simply solve without siege. The relevant principle is **control the route that matters, then use appropriate force to exploit or break it**, not “maximize wall length.” [Bruce Shelley: Remember Ensemble Studios](https://remember-ensemblestudios.com/ensemble-studios/ensemble-blogs-archive/bruce-shelley-page-3/) and [Bruce Shelley AoE2 Q&A](https://www.gamespot.com/articles/age-of-empires-ii-qanda/1100-2462320/)
- **Greg Street / Ghostcrawler:** Street's AoE work emphasizes random maps, exploration, and adapting to an unknown terrain layout. His later description of AoE's random maps stresses that players may not know whether terrain or water separates them and must explore to understand the problem. For this bot, that argues against fixed wall templates: defensive geometry must be derived from observed terrain, resources, enemy approach, and the routes that actually matter. His AoE3 design comments also explicitly resist strategies where players simply sit in their towns for twenty minutes before one decisive fight. [Greg Street: Why Blue Zones](https://www.fantasticpixelcastle.com/new-detail/?id=722) and [Greg Street AoE3 interview](https://www.mastersforum.de/index.php?page=Thread&postID=331676&s=76d136ad0032944bb0ad7c04ce211da9be9e25b4)

Implementation contract:
- [ ] Build a **defensive-geometry observation**: exposed resource, enemy approach, natural blocker, narrow pass/choke, existing wall/building edge, threatened production, and army-response route.
- [ ] Distinguish **full perimeter**, **resource wall**, **choke wall**, **building-anchor wall**, and **emergency gap closure**. Prefer the smallest structure that closes the strategically relevant route.
- [ ] Use terrain, forests, cliffs, shoreline, resources, houses, production buildings, and other legal blockers as wall anchors where the native engine makes that reliable.
- [ ] Never treat “wall requested” as “wall complete.” Witness the actual structure/building state and retain a recovery path for failed or partial walling.
- [ ] Preserve at least one intentional army/villager exit and avoid walling the bot's own builders or sealing the economy behind the defense.
- [ ] Add a **defense-window calculation**: the value of a wall is the time and positional advantage it buys relative to its wood/stone/build time and the threat arrival time.
- [ ] Make defense respond to pressure and map geometry. Do not spend early wood on a full wall when the map is already closed, the wall does not protect a meaningful route, or the next strategic demand has higher urgency.
- [ ] Under enemy pressure, prefer a short emergency segment that changes the path to a vulnerable resource over a complete perimeter that arrives too late.
- [ ] Make the wall cooperate with army defense: route enemy units into a controllable approach, keep siege/repair/building access meaningful, and avoid creating a sealed base that delays reinforcements.
- [ ] Add **choke ownership**: when a narrow approach matters, assign a persistent defensive objective to the approach rather than repeatedly requesting disconnected wall segments.
- [x] Add native **wall-breach recovery** for a witnessed loss of native-perimeter integrity: a gated perimeter below the 42% completion witness reopens the existing stone-wall demand and reuses the native perimeter builder.
- [ ] Extend this into **route-bypass reassessment**: detect a bypassed but still-existing segment, reassess the enemy route, and close/reposition the defense without rebuilding obsolete geometry.
- [ ] Add **attack-side wall reasoning**: when an enemy is fortified, recognize the protected approach, stop feeding ordinary units into the same route, and choose another route or escalate to siege.
- [ ] Keep wall construction subordinate to age-up, essential production, starvation prevention, and active military defense. A wall that preserves a Castle timing is strategic infrastructure; a wall that delays it for no meaningful protection is just expensive landscaping.

Focused acceptance scenarios:
- [ ] Open Arabia with exposed wood/gold: protect the economically valuable approach with the minimum effective closure.
- [ ] Natural choke / Black Forest style map: recognize that a full perimeter is unnecessary and defend the meaningful entrance instead.
- [ ] Closed map: suppress unnecessary walling investment and spend the saved resources elsewhere.
- [ ] Feudal mounted pressure: create or repair the shortest useful closure before the raid arrives; demonstrate that the army still has an exit.
- [ ] Enemy attack through a different route: retire stale wall demand, reassess geometry, and defend the new approach rather than rebuilding the old one.
- [x] Wall breach: witness native-perimeter integrity loss, reopen the stone-wall demand, and re-enter the existing builder lifecycle.
- [ ] Wall bypass: distinguish a route bypass from simple wall damage and change the defensive route instead of repeatedly rebuilding the same segment.
- [ ] Enemy fortified position: route army and siege around the defended approach where possible, or explicitly scale siege instead of repeatedly attacking the same funnel.
- [ ] Builder/army pathing: demonstrate that completed walls do not trap builders, block reinforcement routes, or create an avoidable internal choke.
- [ ] Late-game expansion: wall only strategically exposed new economy/production and do not reproduce the entire starting perimeter.

Acceptance: the bot uses walls and buildings to buy time, shape enemy routes, and protect economically meaningful positions; it does not blindly perimeter-wall, trap itself, repeatedly rebuild obsolete segments, or feed armies into predictable fortified chokes.

## Phase 4: Army control, attack, and recovery
- [x] Repair one verified attack-admission/execution mismatch: own military acquisition now scans 60 tiles while enemy-objective discovery remains bounded to 40; the attack-move actuator is unchanged.
- [ ] Complete the broader attack admission versus execution audit across staging, siege commitment, and objective reassessment.
- [ ] Establish screen/main/siege/raid/reserve roles.
- [ ] Add fortified-position handling and efficient siege use, using the Phase 3.5 defensive-geometry and route model when selecting approaches.
- [ ] Preserve armies under defensive fire where native control permits.
- [ ] Make army-loss recovery change production and attack posture.
- [ ] Reassess attack continuation after enemy strength changes.
- [ ] Expire obsolete counter packages.

Acceptance: fewer wasteful engagements, better siege use, coherent retreat/reposition/re-engage behavior, and meaningful recovery.

## Phase 5: Economy, construction, and technology coherence
- [ ] Treat houses, farms, dropsites, camps, mills, markets, starvation recovery, and defensive construction as one economy.
- [ ] Make wall/building placement preserve villager access, army exits, production paths, and resource routes.
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
- [ ] Run standardized scenarios and record first behavioral failure, including wall timing, choke selection, breach recovery, and fortified-route behavior.
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
