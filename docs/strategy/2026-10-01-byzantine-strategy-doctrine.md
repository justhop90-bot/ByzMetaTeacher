# Byzantine Strategy Doctrine

Date: 2026-10-01

## Scope

The first strategic target is a contemporary 1v1 standard-land Byzantine controller, with Arabia, Arena, and generic land maps as the initial map envelope. Water and transport remain later extensions.

The intended personality is adaptive counterweight: scout the question, answer the threat cheaply, preserve options, and convert the surviving position into the next advantage.

This is not a Cataphract bot, a permanent trash bot, a static turtle, or a fixed build-order compiler.

## Layered strategic model

1. Environment. Map class, starting geometry, exposed resources, opening signals, and water/transport eligibility establish the strategic envelope.
2. Observation. Scouting asks decision-changing questions: cavalry commitment, ranged commitment, infantry mass, siege, forward infrastructure, expansion, exposed economy, and whether earlier pressure actually persists.
3. Arbitration. Persistent posture selects the current trajectory: BOOM for safe economy and option preservation, FLUSH for active counter investment, RUSH for short exposed windows, and CASTLE-POWER for protecting and exploiting the Castle transition.
4. Counter package. Select the cheapest credible response first. Escalate only when the threat persists, the map permits the response, and its resource opportunity cost is justified.
5. Execution. Existing production, construction, DUC, attack, Strategic Number, timer, escrow, and lifecycle systems perform the selected intent. Strategy never becomes a second scheduler.
6. Witness and recovery. Completion is world-state evidence. Temporary capability loss blocks execution without destroying strategic intent. Bad fights trigger withdrawal, reinforcement, and reassessment rather than army deletion by optimism.

## Age doctrine

### Dark Age

Protect the economic trajectory while obtaining enough information to avoid blind commitment. Establish food and wood continuity, make only the infrastructure required by the current plan, scout for the opponent's first meaningful investment, and preserve the Feudal transition.

Follow(deer) is a useful explicit relationship when the food plan and map support it. It is not a universal opening requirement.

### Feudal Age

Feudal is the first major counterweight window. Maintain a standing defensive floor instead of waiting for a crisis. Prefer the cheapest credible counter to the opponent's discovered commitment, using discounted spear, skirmisher, and camel families as tools rather than as a mandatory composition.

Feudal aggression is opportunistic. The objective is to make the opponent spend, idle, retreat, or reveal a transition, not to convert every resource into cheap units merely because the civilization allows it.

Community-policy control recipes are now explicit: RANGED_HOLD, MOBILE_LOCAL_DEFENSE, STRICT_RAID, PROTECT_SIEGE, and DEER_PUSH. These are policy precedents, not engine facts.

### Castle Age

Castle is where Byzantine optionality becomes leverage. Maintain at least one credible answer to the enemy's current army while choosing whether the next investment should be counter reinforcement, ranged transition, Heavy Camel against sustained mounted pressure, Cataphract against infantry-heavy targets, Varangian Guard where the current roster and target set justify it, Monks and relic control, or siege.

The September 22, 2026 game update added Elite Varangian Guards to Byzantines, increased Cataphract infantry bonus damage, and expanded Logistica trample to Cataphracts and Varangian Guards. Those changes increase the value of the premium Castle toolkit, but they do not turn either premium line into an unconditional strategy. The compiler therefore keeps target set, economy, and opportunity cost as separate strategy inputs.

### Imperial Age

Imperial Byzantine strategy is attritional flexibility. Cheap counter families stabilize exchanges; premium ranged, siege, cavalry, infantry, and gunpowder packages are added when their opportunity cost is justified.

The cheaper Imperial transition is a timing tool, not permission to age blindly. Imperial should be favored when the age changes the set of executable strategic packages enough to justify its resource cost.

Late-game production is derived from standing army demand and replacement rate, not arbitrary building counts.

## Economy doctrine

Resource control answers one question: what shortage is currently preventing the selected strategy from functioning?

Food supports villagers, farms, and food-heavy counter packages. Wood supports farms, houses, ranged infrastructure, production capacity, siege infrastructure, and Town Centers. Gold supports premium counters, upgrades, Monks, siege, and the next strategic transition. Stone appears when the selected plan actually requires Castle or fortification investment.

Opportunity cost remains explicit. A useful technology is not automatically the correct next purchase.

## Military doctrine

Military composition is role-based:

- Screen: cheap anti-mounted or anti-melee floor.
- Ranged core: disciplined damage source that should not chase into bad ground.
- Mobile response: cavalry or camel element for interception, raiding, and repositioning.
- Premium shock: Cataphract or Varangian transition when the target set and economy justify it.
- Siege support: introduced when the enemy composition or position makes siege materially change the fight.
- Recovery: heal, reinforce, reassess, and return.

Army quality is not unit count. The long-term compiler should account for composition role, upgrade state, replacement capacity, positioning, and whether the intended fight is actually favorable without building a combat simulator.

## Scouting doctrine

Scouting is decision-grade information, not merely enemy detection.

Prioritize observations that can change posture: actual cavalry mass instead of one cavalry unit, actual ranged commitment, siege appearance, forward infrastructure, expansion, exposed resource investment, production changes, and whether previously detected pressure has actually cleared.

An observation that changes nothing is lower-value than a smaller observation that changes a decision.

## Recovery doctrine

The controller retains the lifecycle:
OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT

Capability loss does not erase persistent strategic intent. A bad engagement changes execution posture before it destroys the strategic plan. Withdrawal, healing, reinforcement, and a new scouting pass are strategy, not exceptional error handling.

## Anti-patterns

- Permanent pure-trash composition.
- Permanent Cataphract fixation.
- Blind boom because a timer expired.
- Treating unit count as combat power.
- Treating feasibility as completion.
- Attacking every discovered enemy because a target exists.
- Releasing strategic intent because a provider is temporarily unavailable.
- Using timing primitives as strategic truth.
- Promoting community idioms directly into engine facts.
- Building a second scheduler inside the strategy layer.

## Evidence boundary

Contemporary Byzantine facts belong in the pinned game-data and native-reference layers. Community practice is precedent, not proof. A policy recipe becomes executable only when its native mechanisms are supported and its evidence status is explicit.

Primary cross-references include BotDirection.txt, the Byzantine capability and game-data audits, AIRef command and Strategic Number inventories, the community .per idiom catalog, The Duke and Niek/Atilla source corpus, and current community discussions of Byzantine counter-unit and defensive play.

## Land threat taxonomy and arbitration

The land controller now treats the major military threat classes explicitly:

| Threat class | Primary signal | Byzantine response | Arbitration role |
|---|---|---|---|
| Mounted | sustained scout/knight-line mass | Spear screen in Feudal; Camels in Castle | one mounted package at a time |
| Ranged | sustained archer-line mass | discounted Skirmisher package | may coexist with mounted/siege |
| Infantry | sustained militia-line mass | Castle Cataphract package | premium response only when mass is real |
| Siege | sustained mangonel-line mass | mobile Castle response | high-priority support threat |
| Mixed | two or more orthogonal classes | preserve each required counter role | select one primary, retain supporting roles |

The compiler deliberately does not collapse mixed threats into a single “best counter.” A mounted+ranged position needs both anti-mounted and anti-ranged coverage. A same-class overlap is different: when two packages describe the same threat class, the deterministic highest-priority package wins and the lower package is explicitly suppressed.

`CounterArbitrationMode` is therefore `NONE`, `SINGLE`, or `MIXED`. The selected package set is part of runtime state and the fingerprint, so a change in observed composition produces a real reassessment signal instead of silently changing production underneath the strategy layer.

Siege is treated as a threat class rather than as a universal answer. The current Castle siege package uses a mobile Knight-line response because siege pressure changes the tactical problem from “add another static counter” to “restore mobility and attack the siege before it dictates the fight.” The compiler does not claim that every siege composition should be answered identically; this is the first typed land package and remains extensible.

The current population of packages is therefore: `MOUNTED_PRESSURE_FEUDAL`, `RANGED_PRESSURE_FEUDAL`, `MOUNTED_PRESSURE_CASTLE`, `INFANTRY_PRESSURE_CASTLE`, and `SIEGE_PRESSURE_CASTLE`.

These package thresholds are compiler policy over verified native observations. They are not presented as engine truths or as a universal human build order.

## Architectural consequence

The compiler should therefore grow breadth by adding more evidence-backed strategic packages and more decision-grade observation, not by creating a second strategy language. Policy recipes describe intent. StrategyProfile and StrategyRuntimeState own strategic continuity. Existing execution layers own production, construction, DUC, attack, SN, timers, escrow, witness, release, and recovery.

## Threat-to-counter doctrine

The strategy does not react to every discovered unit. It reacts to decision-grade pressure.

In Feudal, three or more enemy scout-cavalry units can activate the mounted screen package, while three or more enemy archers can activate the ranged counter package. In Castle, sustained knight pressure activates a Camel package, while a five-unit infantry mass can activate a Cataphract response.

Those thresholds are compiler policy, not engine facts. They are deliberately typed through native observation references so they can be changed without changing the execution layer.

The package is not the army. It is the strategic demand trigger. Once activated, the ordinary demand lifecycle still owns admissibility, capability, feasibility, production, witness, release, and recovery.

The important distinction is therefore:

`OBSERVATION -> THREAT INTERPRETATION -> COUNTER PACKAGE -> DEMAND -> EXECUTION -> WITNESS -> RECOVERY`

rather than:

`OBSERVATION -> TRAIN UNIT`

The first is a strategy system. The second is a macro script wearing a strategy-shaped hat.
