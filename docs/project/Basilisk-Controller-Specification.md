# Basilisk Controller Specification
## Engineering Charter for the Target AI Controller

Project: ByzMetaTeacher  
Controller: Basilisk  
Target battlefield: 1v1 standard-land Byzantine play  
Purpose: define the exact code-level behavior we are trying to build so future changes are judged against a fixed target rather than against whichever subsystem was edited most recently.

---

# 0. THE TARGET, WITHOUT AMBIGUITY

Basilisk is a **persistent-intent, demand-driven, engine-native heuristic controller with small local transaction lifecycles**.

That sentence is the target.

Basilisk is **not** a global finite-state machine.

Basilisk is **not** a stateless pile of unrelated rules.

Basilisk is **not** a spreadsheet trying to simulate the future economy.

Basilisk is **not** a universal scheduler.

The intended control loop is:

~~~text
WORLD STATE
    ↓
OBSERVATION
    ↓
INTERPRETATION
    ↓
PERSISTENT STRATEGIC INTENT
    ↓
DERIVED DEMAND
    ↓
REQUIRED CAPABILITY
    ↓
ENGINE-NATIVE FEASIBILITY
    ↓
ENGINE ACTION
    ↓
WORLD-STATE CHANGE
    ↓
REASSESSMENT
~~~

Only operations that genuinely require memory may insert a small local lifecycle:

~~~text
DEMANDED
    ↓
FEASIBLE
    ↓
ACTION ISSUED
    ↓
PENDING / IN FLIGHT
    ↓
COMPLETED

or

ACTION ISSUED
    ↓
FAILED / BLOCKED
    ↓
BOUNDED BACKOFF
    ↓
DEMAND SURVIVES
    ↓
RETRY WHEN CONDITIONS CHANGE
~~~

The controller therefore has three kinds of information:

1. Strategic memory: decisions that remain relevant after one rule pass.
2. Derived state: answers that the current world can already provide.
3. Execution memory: temporary state required to manage a real engine lifecycle or contention problem.

The engineering objective is to keep strategic memory and execution memory small, explicit, local, and justified.

Community practice supports this shape. The official HD AI uses goals for persistent concepts such as strategy and housing, while also clearing several derived threat, housing, and attack values so later rules reconstruct them from current conditions. It also relies on ordinary can-* feasibility predicates and queue-aware counts rather than assuming that procedural intent equals successful execution.

---

# 1. WHAT BASILISK IS

## Target

Basilisk is a heuristic player model expressed in the AoE2 AI expert-system language.

A human continuously receives observations, interprets them, maintains a strategic intention, and uses available actions to move the position toward that intention. Basilisk should perform the same conceptual loop with rules, facts, goals, strategic numbers, timers, and engine actions.

The strategy layer answers:

> What kind of position am I trying to create?

The demand layer answers:

> What must become true for that position to function?

The capability layer answers:

> What infrastructure or prerequisite is currently missing?

The execution layer answers:

> Can the engine perform the required action right now?

The world answers:

> Did it actually work?

## Code consequence

A value such as strategy-goal = BOOM is justified because a strategy can survive a temporary resource shortage.

A live enemy cavalry signal is different. The engine can tell us whether cavalry exists now, so that signal should normally be derived.

A research claim is different again. The engine needs memory of which operation currently owns a provider/resource interaction.

The target mixture is therefore deliberate:

- persistent high-level posture,
- stateless derived tactical interpretation,
- local stateful execution.

## Expert test

For every persistent variable, answer:

1. What fact cannot safely reconstruct this information?
2. What decision remains valid after the current pass ends?
3. Who owns the value?
4. Who consumes it?
5. What changes or releases it?
6. What happens when its original reason disappears?

If these questions have no clean answer, the state probably should not exist.

---

# 2. THE ARCHITECTURE BALANCE

There is no sacred percentage of stateful versus stateless code. The target is functional separation.

### Persistent strategic state

Use it for:

- strategy/posture,
- durable army intent,
- durable opening interpretation,
- meaningful economic commitment,
- an operation that must persist across passes,
- bounded failure memory.

### Derived state

Prefer current facts for:

- unit counts,
- queued production,
- building counts,
- enemy composition,
- resource shortages,
- current age,
- housing headroom,
- current capability,
- technology feasibility.

### Execution state

Use it only when:

- an operation needs exclusive ownership,
- the engine provides no adequate direct witness,
- multiple valid actions contend for a single operation,
- or a temporary engine policy must persist while a project is pending.

The desired code character is:

~~~text
many current facts
+
few durable decisions
+
few local execution claims
+
direct engine actions
~~~

The dangerous form is:

~~~text
fact
→ goal A
→ goal B
→ claim C
→ timer D
→ goal E
→ action
→ timer F
→ release G
~~~

That is not forbidden. It is simply expensive. Every extra state transition creates another synchronization point that can become stale.

The community examples are instructive because they often use a simple rule repeatedly against current state instead of building a procedural chain for routine work. The classic housing and dropsite examples are deliberately direct.

---

# 3. PERSISTENT STRATEGIC STATE

Strategy is policy, not a task queue.

A persistent strategy says:

> I currently favor this kind of position.

It does not mean:

> I must now perform this exact list of actions in this exact order.

For Basilisk:

- FLUSH means immediate pressure/defensive response has strategic priority.
- RUSH means controlled offensive pressure is worth maintaining.
- BOOM means economic expansion has priority while maintaining the necessary military floor.
- CASTLE-POWER means surviving pressure is being converted into Castle-age offensive value.

A strategy should change when meaningful evidence changes:

- actual threat,
- actual defensive requirement,
- age transition,
- army survival,
- economic opportunity,
- battlefield opportunity.

It should not change merely because a clock reached a phase boundary.

## Hysteresis

Small oscillations should not cause huge strategic reversals.

Bad:

~~~text
gold 99 → RUSH
gold 101 → BOOM
gold 99 → RUSH
gold 101 → BOOM
~~~

Good heuristic control uses:

- threshold separation,
- persistent strategy,
- explicit recovery conditions,
- meaningful evidence before reversal.

## Rule order

AoE2 AI runs repeated rule passes and community references document that rule ordering can affect which action is attempted first. Therefore source order is part of the controller's behavior, not cosmetic formatting.

That means:

> If precedence matters, it must be intentional, documented, and tested.

Do not allow “the later rule happened to overwrite the earlier rule” to be the only explanation of strategy.

---

# 4. DERIVED STATE

Derived state answers:

> What is true now?

Examples:

- enemy currently has cavalry,
- army is below floor,
- Range currently exists,
- Crossbow current + queued count is below target,
- gold is currently the binding shortage,
- a dropsite is currently too far away.

Derived values should generally be cleared and rebuilt from current facts when their meaning is live.

This is already visible in the Basilisk threat layer, where threat categories are reset and reconstructed from current enemy composition.

That is correct.

The key distinction is:

~~~text
DERIVED:
"What is true now?"

PERSISTENT:
"What do I still want despite temporary changes?"

EXECUTION:
"What operation currently owns this resource/capability?"
~~~

If those questions are collapsed into one goal, the controller becomes brittle.

---

# 5. EXECUTION STATE

Execution state is allowed when the engine needs memory.

Valid examples:

- research claim,
- prerequisite construction claim,
- temporary dropsite override,
- watchdog,
- bounded failure backoff,
- attack-cycle state.

The local lifecycle is:

~~~text
IDLE
→ DEMANDED
→ FEASIBLE
→ ACTION
→ PENDING
→ COMPLETE
~~~

or:

~~~text
ACTION
→ FAIL/BLOCK
→ BACKOFF
→ DEMAND SURVIVES
→ RETRY
~~~

The critical invariant is:

> Execution failure changes timing, not strategic truth.

If Basilisk wants Crossbows, a failed Range build does not make Crossbows unwanted.

If Basilisk wants a research package, a failed research attempt should not destroy that package.

If a temporary placement override fails, the override should release without destroying the resource demand that caused the camp to be needed.

---

# 6. STATE OWNERSHIP

Every meaningful state has an owner.

Ownership means:

> this subsystem is responsible for creating, maintaining, and releasing the semantic truth represented by the value.

## Persistent intent

Normally one primary writer should establish the intent.

Additional writers may perform explicit transitions:

- opening plan establishes initial posture,
- emergency threat preempts,
- safe recovery exits emergency,
- age transition replaces an obsolete posture.

## Execution claim

One executor should own the claim.

It:

1. acquires it,
2. performs the operation,
3. observes completion,
4. handles failure,
5. releases it.

## Orphan test

A state is defective if:

- no writer remains,
- no consumer remains,
- no release remains,
- its capability disappears and its claim stays live,
- or it can remain true forever after its reason disappears.

## Duplicate writer test

Multiple writers are not automatically bad.

They become bad when:

- they express incompatible precedence,
- they write incompatible values,
- they are unaware of each other,
- or their behavior depends only on accidental source order.

This is why a validator should distinguish:

- legitimate transition writers,
- conflicting unconditional writers,
- duplicate executors,
- missing completion releases.

---

# 7. DEMAND

Demand says:

> Something desirable or necessary is currently missing.

Examples:

- houses,
- Skirmishers,
- second Town Center,
- Castle Age,
- Horse Collar,
- siege response,
- extra production throughput.

Demand is not action.

The desired pattern is:

~~~text
DEMAND = durable
EXECUTOR = conditional
ACTION = one-shot
WORLD = witness
~~~

Example:

~~~text
enemy cavalry
→ cavalry-response demand
→ standing Spear target
→ Barracks required
→ can-build Barracks
→ build Barracks
→ Barracks becomes real
→ train Spears
→ reassess
~~~

The demand should survive temporary execution failure.

It should disappear when:

- the target is reached,
- the strategic reason disappears,
- another strategy replaces it,
- or the capability is no longer strategically relevant.

If a demand disappears merely because the executor failed once, the architecture is backwards.

---

# 8. CAPABILITY

Capabilities are the infrastructure that makes current demand executable.

Examples:

- Barracks,
- Range,
- Stable,
- Siege Workshop,
- Blacksmith,
- Market,
- University,
- Monastery,
- Castle.

A capability is not strategy.

“BOOM” does not intrinsically mean “build two Town Centers.”

It means that if Town Centers are the strategic requirement, the capability layer should make them possible.

Likewise:

~~~text
enemy Archers
→ counter demand
→ Range capability missing
→ Range becomes required
→ build Range when feasible
→ production can now proceed
~~~

## Capability consumer requirement

Every new building rule must have a known consumer.

If no current demand consumes the building, the capability is probably premature infrastructure.

## Scaling requirement

Additional production buildings must be justified by throughput:

- target,
- current + queued army,
- production speed,
- replacement requirement,
- resource availability.

The building is a means, not the objective.

---

# 9. FEASIBILITY

The engine owns permission.

The strategy can want something.

The demand can require it.

The capability can make it possible.

But the final action boundary should use the engine's own feasibility fact whenever one exists.

Community scripting documentation explicitly distinguishes facts from actions and presents can-build, can-train, and can-research as the appropriate execution gates. It also notes that can-* checks engine conditions such as buildings and resources.

Therefore:

~~~text
WANT X
≠
CAN DO X
≠
DID X
~~~

A proper executor combines:

- strategic authorization,
- capability,
- duplicate/pending protection,
- resource arbitration where genuinely needed,
- engine feasibility,
- action.

A missing can-* gate is therefore not cosmetic. It is a broken execution boundary.

---

# 10. ACTION AND WORLD-STATE WITNESS

Actions are requests.

World-state is proof.

Examples:

| Intent | Action | Completion witness |
|---|---|---|
| more houses | build house | actual house/building state and housing recovery |
| Range capability | build archery-range | Range exists or is pending |
| Crossbow production | train crossbowman | current + queued Crossbows |
| technology | research technology | research-complete |
| age transition | research age | current-age changes |
| dropsite | build mining-camp | camp construction state |
| attack | attack-now | attack-group / soldier witness |
| retreat | reset attack | attack lifecycle actually clears |

A timer expiring is not completion.

A goal changing is not completion.

An action command being issued is not completion.

## Queue-inclusive thinking

For production, the relevant question is:

> Is enough work already completed or committed?

The community scripting guide notes that total building/unit counts include queued objects. Basilisk should use that distinction whenever the strategic decision is about already-committed work.

This prevents:

~~~text
target = 6
current = 4
queued = 2
→ train 2
~~~

which manufactures duplicate work.

The correct decision is:

~~~text
current + queued >= target
→ no additional training
~~~

---

# 11. RESOURCE ARBITRATION

The economy is not a global transaction scheduler.

Default rule:

> resources are available to the highest-priority currently valid demand.

A global claim is justified only when ordinary heuristic demand and engine feasibility cannot adequately resolve a genuine competition.

Good claim candidates:

- age-up bank,
- premium strategic package,
- high-value prerequisite with hard timing,
- real mutual exclusion.

Poor claim candidates:

- ordinary houses,
- ordinary farms,
- normal lumber camps,
- routine military replacement,
- every technology.

Before adding a new claim ask:

1. Can a better demand predicate stop the lower-priority action?
2. Can current + queued counts stop it?
3. Can can-* stop it?
4. Can escrow already provide sufficient protection?
5. Does the conflict actually exist in gameplay?

If yes to one of the first four, prefer that.

The existing sn-resource-control should remain a scarce arbitration mechanism, not become a generic transaction manager.

---

# 12. MILITARY MODEL

Basilisk must distinguish:

### Standing army

Force that must remain available for survival, deterrence, defense, and strategic continuity.

### Attack package

Force that can safely leave the base and spend itself on an attack.

The attack package must not consume the standing floor.

## Role-aware target

Military demand should be based on role:

- anti-cavalry,
- anti-ranged,
- anti-infantry,
- ranged pressure,
- mobile pressure,
- siege,
- support,
- premium regional unit.

Unit count alone is too crude.

Ten Spears and ten Knights are both ten units, but the roles are different.

## No simulator

We do not need a combat simulator.

We do need heuristics that account for:

- enemy role,
- friendly role,
- upgrade state,
- current and queued force,
- production capacity,
- replacement rate,
- siege/support requirements,
- strategic value of taking the intended fight.

The target is practical battlefield judgment, not numerical perfection.

## Military chain

~~~text
enemy observation
→ threat interpretation
→ standing role deficit
→ unit target
→ production capability
→ production capacity
→ unit training
→ standing-force witness
→ attack eligibility
~~~

Every link is independently auditable.

---

# 13. ECONOMY MODEL

The economy exists to make the strategic posture function.

The controlling question is:

> **What resource shortage is currently preventing the plan from operating?**

Not:

> What resource percentage looks pretty?

## Food

Supports:

- villagers,
- age-up,
- food-heavy army,
- food technology.

## Wood

Supports:

- farms,
- houses,
- economic buildings,
- production,
- siege infrastructure,
- Town Centers,
- prerequisites.

## Gold

Supports:

- premium military,
- technologies,
- age transitions.

## Stone

Appears when a current strategic objective actually requires it.

## Gatherer percentages

Fixed percentage bands are acceptable heuristic controls. The community scripting guide uses strategic-number percentage allocations as a basic economic control surface.

The correct hierarchy is:

~~~text
strategic demand
→ binding shortage
→ resource mode
→ gatherer policy
~~~

not a permanent rigid economy schedule.

The existing Basilisk resource-mode variable is acceptable as a derived scratch state if it is rebuilt from live conditions every pass. It should not become the definition of the strategy.

---

# 14. BUILDINGS ARE CAPABILITIES, NOT STRATEGY

A building should exist because current work requires its capability.

Examples:

~~~text
enemy ranged pressure
→ counter demand
→ Range capability
~~~

~~~text
siege demand
→ Siege Workshop capability
~~~

~~~text
premium research demand
→ provider capability
~~~

A strategy label must not directly imply an unconditional building list.

For production buildings, scaling follows throughput:

~~~text
required army target
− current + queued army
− current production throughput
= capability deficit
~~~

When that deficit is large enough to matter, an additional production building becomes justified.

---

# 15. STRATEGY SELECTION

Strategy answers:

> **What kind of game am I playing right now?**

Basilisk already has an explicit strategy layer with FLUSH, RUSH, BOOM, and CASTLE-POWER. That is directionally correct.

The danger is phase-machine behavior.

Good strategy changes because:

- threat appears or disappears,
- defense is satisfied,
- pressure survives,
- pressure dies,
- age changes,
- economic opportunity changes,
- army survival changes.

Bad strategy changes because:

- minute X was reached,
- one resource fluctuated,
- a particular building exists,
- a timer expired.

Time is a signal, not a strategic truth.

## Current Basilisk finding

The current strategy section has explicit emergency entry and recovery logic, which is good.

It also relies in places on source order and mutually exclusive predicates. That is valid only if deliberate.

The future standard is:

Every strategy transition must identify:

- incoming posture,
- exact trigger,
- exit posture,
- competing transitions,
- block conditions,
- source-order dependency where relevant,
- regression case.

---

# 16. UNIT-GOAL / COMPOSITION

Unit-goal answers:

> **What composition should production make?**

The layers must remain:

~~~text
STRATEGY = posture
UNIT-GOAL = composition
PRODUCTION = capacity
TRAINING = execution
~~~

## Desired behavior

Single threat:
- choose the cheapest credible response.

Multiple threats:
- move toward mixed composition.

No immediate threat:
- use the current strategy's offensive or economic default.

Pressure survives:
- preserve the role that creates strategic value.

The system should increasingly account for:

- existing army,
- queued army,
- upgrades,
- production capacity,
- enemy mass,
- premium package commitments.

## Multiple writers

The current Basilisk unit-goal system has several composition writers. That is acceptable only when priority is explicit.

A unit-goal variable with many writers must not rely solely on “the last rule in the file wins.”

Either conditions are mutually exclusive or precedence is explicitly designed and validated.

---

# 17. RESEARCH POLICY

Research is an investment, not a checklist.

The question is:

> Is this technology worth its current resource opportunity cost for the position we are actually in?

Correct lifecycle:

~~~text
strategic need
→ provider capability
→ technology admissibility
→ opportunity-cost check
→ can-research-with-escrow
→ research
→ research-complete
→ release claim
~~~

## Package model

Research should be grouped by useful strategic package:

- cavalry response,
- ranged response,
- food economy,
- siege,
- monastery,
- premium regional unit.

The package is strategic intent.

The local research claim is execution ownership.

Do not build a new scheduler for every technology.

## Failure

A failed research start should create bounded local backoff.

It should not erase the demand unless the strategic reason vanished.

## Invalidation

A technology can be strategically invalidated if the battlefield changes before execution actually begins.

Once research is genuinely underway, completion semantics become the authority unless the engine supports explicit cancellation behavior.

---

# 18. TIMERS, RETRIES, AND FAILURE RECOVERY

Timers manage time.

They do not define strategy.

Valid:

- scouting pulse,
- attack cadence,
- research fairness backoff,
- construction watchdog,
- retry delay.

Invalid by default:

- “at 10:00 become Castle mode forever,”
- “timer expired, therefore building completed,”
- “failed three times, delete demand permanently.”

## Bounded recovery

For every failure:

1. What failed?
2. Why is the underlying demand still valid?
3. What should change before retry?
4. What is the maximum retry suppression?
5. What world-state event clears it?
6. What strategic event invalidates it?

The retry belongs to the operation.

It must not infect the whole controller.

---

# 19. THREE-SPEED CONTROL

A useful way to balance Basilisk is by decision speed.

## Fast: seconds / passes

- emergency defense,
- queue deficits,
- pending objects,
- resource starvation,
- attack eligibility,
- immediate counter response.

## Medium: tens of seconds / minutes

- composition changes,
- production scaling,
- technology packages,
- dropsite scaling,
- economic mode shifts.

## Slow: strategic horizon

- opening identity,
- BOOM versus pressure,
- Castle continuation,
- Imperial package direction.

Fast signals can correct slow policy.

Slow policy should not panic over every fast fluctuation.

Medium logic bridges the two.

This is a much more accurate mental model than a single global FSM.

---

# 20. STATE BUDGET

There is no magic numeric ratio. However, Basilisk should enforce a strong qualitative state budget.

A new persistent state value must have a reason.

A new global claim must have stronger proof than a local claim.

A new timer must represent an actual temporal problem.

A new custom SN must be verified unused in the target DE build.

A new package cursor must justify why existing package state cannot be reused.

AIRef documents finite budgets for goals, strategic numbers, timers, rule elements, and line length. It also recommends verifying a custom strategic-number ID is genuinely unused before treating it as extra storage.

The project target is therefore not:

> use fewer goals because fewer is prettier.

It is:

> **Every state value must purchase real control capability.**

If a state variable does not buy control capability, remove it.

---

# 21. WHAT WE ARE COPYING FROM NAGA / COMMUNITY AI

We are not copying Naga line-for-line.

We are copying its practical instincts:

- repeatedly evaluating current conditions,
- using goals when memory is useful,
- direct engine predicates,
- pending/queue awareness,
- adaptive dropsite behavior,
- strategic-number controls,
- strategy selection from map and enemy context,
- simple rules for routine actions.

The official HD AI source shows this same philosophy in concrete form: persistent housing strategy, pass-reset threat state, direct can-* execution, queue-aware building counts, and dynamic camp-distance handling.

Naga is documented as a broad contemporary script with multiple strategy types and enemy-strategy-based adaptation, reinforcing that the intended community style is adaptive rather than a single fixed opening.

We copy the engineering instincts, not the historical machinery.

---

# 22. WHAT GOOD LOOKS LIKE IN CODE

A good subsystem reads approximately like this:

~~~text
Enemy cavalry is present.
        ↓
Cavalry response remains strategically required.
        ↓
Standing Spear target increases.
        ↓
Barracks capability is required if absent.
        ↓
No Barracks pending.
        ↓
can-build Barracks.
        ↓
build Barracks.
        ↓
Barracks becomes a real world-state fact.
        ↓
Current + queued Spears are compared with target.
        ↓
can-train Spear.
        ↓
train.
        ↓
Army target changes.
        ↓
Reassess.
~~~

Notice what is missing:

- no giant state machine,
- no timer pretending to be completion,
- no claim unless actual contention requires it,
- no goal for every intermediate fact,
- no hard-coded next step that ignores the world.

That is the house style.

---

# 23. WHAT BAD LOOKS LIKE

The following shape should trigger suspicion:

~~~text
strategy = cavalry defense
→ barracks-needed = 1
→ spear-project = 1
→ wood-lock = 1
→ train-lock = 1
→ research-lock = 1
→ retry-timer
→ timeout state
→ release state
→ complete state
→ reset strategy
~~~

It may be technically functional.

It is still probably over-modeled if engine facts can already express most of those transitions.

The rule is not “never use state.”

The rule is:

> **Do not store information that the engine already knows.**

---

# 24. OPPORTUNITY COST

A mature heuristic AI asks:

> What does spending this resource now prevent?

Suppose Basilisk has:

- a Castle bank in progress,
- a cavalry threat,
- under-produced Spears,
- Horse Collar available,
- enough food to buy either the upgrade or additional military/age progress.

The correct question is not:

> Can Horse Collar be bought?

It is:

> Does Horse Collar improve the position enough to justify displacing the current higher-value demand?

That is why resource arbitration and research policy belong below strategy but above raw execution.

The solution is coarse priority and veto logic, not a full economic simulator.

---

# 25. STRATEGIC HUMILITY

The controller must distinguish strong evidence from weak evidence.

Strong:

- Town Center is under attack,
- enemy has ten Knights,
- current + queued army is below target,
- Castle resources are actually banked,
- research is complete,
- required building exists.

Weak:

- one Knight was seen,
- one Range exists,
- wood happens to be high,
- a technology is affordable,
- a build command was issued.

The bot should not treat weak evidence as permanent strategic truth.

That is how heuristic systems become hysterical or rigid.

---

# 26. PERFORMANCE AND ENGINE LIMITS

AIRef currently documents limits including:

- up to 10,000 rules,
- 32 rule elements in DE,
- 50 timers,
- 512 strategic-number slots,
- 255 characters per line,
- finite load depth,
- and a practical performance concern if a script pass becomes too expensive.

These constraints matter.

They do not mean Basilisk should be small for aesthetic reasons.

They mean Basilisk should be economical in control structure:

- derive only information that matters,
- avoid duplicate decision paths,
- keep expensive searches controlled,
- use conditional loading where appropriate,
- keep rules parser-safe,
- eliminate redundant lifecycle state.

The recent multi-operand OR parser error is a good example of why readable binary logical composition matters.

---

# 27. VALIDATOR REQUIREMENTS

Static validation must go beyond syntax.

## Structural

Check:

- duplicate constants,
- duplicate goal IDs,
- duplicate custom SN IDs,
- undefined symbols,
- logical operator arity,
- rule element limits,
- line length,
- empty facts/actions.

## Lifecycle

For every claim:

- executor,
- completion release,
- failure/backoff release,
- capability-loss release when relevant,
- strategic invalidation when relevant.

## Demand

For every durable demand:

- writer,
- consumer,
- desired outcome,
- release condition,
- no permanent dead-end.

## Capability

For every capability:

- consumer,
- executor,
- feasibility gate,
- pending guard where needed.

## Production

For every production target:

- current + queued count,
- target witness,
- capability,
- training gate.

## Strategy

For every strategy:

- writers,
- transitions,
- recovery,
- competing transition precedence,
- downstream consumer.

Static analysis proves structure.

It does not prove gameplay.

---

# 28. ADVERSARIAL REVIEW STANDARD

Every meaningful change should answer:

### What if this condition remains true forever?
Does the bot spam?

### What if the action fails forever?
Does the demand survive without deadlocking the subsystem?

### What if the enemy changes immediately?
Does the controller reassess?

### What if the capability dies?
Does the claim release while the demand survives?

### What if another subsystem wants the same resource?
Is priority deterministic?

### What if the queue already contains the work?
Does the controller avoid duplicate production?

### What if two rules can write this state?
Is precedence deliberate?

### What if strategy becomes obsolete halfway through?
Can the operation be invalidated safely?

### What if the parser accepts the syntax?
Has engine behavior still been tested?

These are normal acceptance questions.

---

# 29. THE GOLD STANDARD FOR A NEW FEATURE

A subsystem is complete only when all of these exist:

### Signal
A real game fact.

### Interpretation
A meaningful strategic meaning.

### Intent
A clear owner.

### Demand
What must become true.

### Capability
What makes it executable.

### Feasibility
The engine says it can happen.

### Action
One executor issues it.

### Witness
The world proves it.

### Failure
Demand survives temporary failure.

### Release
Temporary state dies correctly.

### Reassessment
The next pass can adapt.

### Opportunity cost
Resource displacement is understood.

### Preemption
Higher-priority state can interrupt where justified.

### Regression
The feature has tests for happy path, missing capability, duplicate queueing, resource contention, failure, completion, and invalidation.

That is the complete subsystem contract.

---

# 30. CURRENT BASILISK: WHAT IS ALREADY RIGHT

The current controller already contains several strong patterns that should be preserved.

## Threat reconstruction
Threat categories are derived from current enemy composition rather than permanently remembered.

## Standing army versus attack package
The controller separates defensive force from attack-group force.

## Persistent strategic posture
Strategy survives individual failed actions.

## Demand-driven production capacity
Barracks, Range, and Stable scaling increasingly follow role targets.

## Queue-aware military targets
Current plus queued work is increasingly used to avoid duplicate production.

## Package-based research
Research demand is increasingly separated from provider execution.

## Local research recovery
Failure backoff is bounded and capability-local.

## Dropsite hygiene
Pending objects and temporary placement overrides are localized.

These are compatible with the target.

The risk is not that Basilisk has these mechanisms.

The risk is that each future feature adds another layer until all ordinary heuristics become transaction workflows.

---

# 31. CURRENT BASILISK: WHAT MUST BE WATCHED

The existing controller is large and has a substantial amount of explicit state.

That does not automatically mean it is wrong.

It does mean every new mechanism must face a higher burden of proof.

Particular watch areas:

### Strategy writer count
The strategy layer already has explicit emergency entry, recovery, Castle-Power promotion, and opening-derived strategy. New writers must not accidentally create conflicting transitions.

### Unit-goal writer count
Multiple legitimate composition writers exist. Their precedence must remain explicit.

### Resource mode
The resource mode should stay a derived scratch decision, not become another long-lived strategic phase.

### Research claims
Claims and backoff are useful, but repeated use should not become a universal scheduler.

### Global resource control
sn-resource-control should remain exceptional.

### Production capability
Buildings should continue to be derived from standing/production demand rather than from labels.

### Time-based rules
Game time may shape expectations, but the board should override the clock when evidence changes.

---

# 32. THREE SIMPLE QUESTIONS BEFORE ADDING STATE

Before writing a new goal, SN, timer, claim, or watchdog, ask:

1. Can current engine facts express the answer?
2. If not, does the answer need to survive a pass?
3. If it must survive, is it strategy memory or execution memory?

If it is neither, do not add it.

This single test should eliminate a large amount of accidental architecture.

---

# 33. THE FINAL CONTROLLER GRAMMAR

For new code, use this mental parser:

~~~text
OBSERVE
    ↓
WHAT DOES IT MEAN?
    ↓
DO I NEED TO REMEMBER THAT MEANING?
    ↓
WHAT DO I WANT TO BECOME TRUE?
    ↓
WHAT CAPABILITY IS MISSING?
    ↓
CAN THE ENGINE DO IT NOW?
    ↓
DO IT
    ↓
DID THE WORLD CHANGE?
    ↓
WHAT DOES THE NEW WORLD MEAN?
~~~

That is the entire controller.

Not:

~~~text
OBSERVE
→ enter phase
→ enter subphase
→ arm project
→ reserve project
→ arm executor
→ wait
→ release
~~~

unless the engine genuinely requires such a lifecycle.

---

# 34. FINAL DEFINITION OF BALANCE

A balanced Basilisk does not have perfectly tuned numbers.

It has correct control topology.

It can tolerate:

- delayed farms,
- a failed research start,
- a bad camp,
- temporary resource shortage,
- a lost unit,
- a delayed building,
- a changed enemy composition.

It cannot tolerate:

- permanent age starvation,
- permanent farm spam,
- infinite camp spam,
- military demand without capability,
- research claims that never release,
- strategic oscillation,
- attacks that consume the defensive army,
- state corruption after a failed command.

Therefore:

> **The target is graceful degradation and continuous recovery, not numerical perfection.**

That is what balance means at code level.

---

# 35. THE TARGET STRATEGIC PERSONALITY

Basilisk is Byzantine.

Its strategic personality should therefore be:

- observe the opponent,
- answer the commitment efficiently,
- preserve flexibility,
- maintain enough army to stay safe,
- exploit surviving pressure,
- spend premium resources selectively,
- change composition when the opponent forces the issue,
- use Byzantine optionality instead of committing to one permanent unit plan.

The identity is not “Cataphract bot.”

It is not “anti-cavalry bot.”

It is not “Crossbow bot.”

The identity is **adaptive counterweight**.

---

# 36. THE FINAL ARCHITECTURAL EQUATION

~~~text
PERSISTENT INTENT
+
CURRENT WORLD FACTS
+
ENGINE FEASIBILITY
+
LOCAL EXECUTION MEMORY WHERE REQUIRED
=
BASILISK
~~~

Remove persistent intent:
- the bot becomes twitchy.

Remove current world facts:
- the bot becomes rigid.

Remove engine feasibility:
- the bot spams impossible actions.

Remove local execution memory:
- difficult engine lifecycles become unreliable.

Add too much persistent state:
- the bot becomes an FSM.

Add too much execution state:
- the bot becomes a transaction engine.

Add too much arithmetic:
- the bot becomes a simulation.

The target is the middle.

---

# 37. NON-NEGOTIABLE DEVELOPMENT ORDER

When solving a new problem, prefer mechanisms in this order:

1. Existing engine fact.
2. Existing persistent strategic state.
3. Direct rule from current facts.
4. Engine-native can-* feasibility.
5. Current + queued / pending guard.
6. Local claim only for real contention.
7. Bounded watchdog/backoff if no direct witness exists.
8. New persistent state only when the first seven cannot express the required behavior.

This is the formal Basilisk style guide.

Every step downward increases complexity and therefore requires stronger proof.

---

# 38. THE UNMISSABLE TARGET

**We are building a heuristic player, not a state machine.**

**Strategy is persistent intent.**

**Demand is what must become true.**

**Capability is what makes that demand executable.**

**Feasibility belongs to the engine.**

**Actions are requests.**

**World-state changes are proof.**

**Failures delay execution; they do not erase valid intent.**

**State exists only where persistence or engine lifecycle genuinely requires it.**

**The economy follows the strategy's binding shortage.**

**Buildings follow capability demand.**

**Production follows current + queued requirements.**

**Research follows strategic value and opportunity cost.**

**Military separates standing force from expendable attack force.**

**Strategy changes because the position changes, not because the code reached a phase.**

**Global locks are exceptional.**

**Timers are temporal tools, not strategic truth.**

**Rule order is part of the control surface and must be intentional.**

**Static validation proves structure. Runtime/replay proves behavior.**

**The game is the final witness.**

Every future Basilisk change is either moving toward this controller or moving away from it.

No third category.
