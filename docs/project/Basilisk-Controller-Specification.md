# Basilisk Controller Specification

## 1. What Basilisk is

Basilisk is a rule-driven heuristic controller for 1v1 standard-land Byzantine play.

It is NOT a global finite-state machine.

The controller continuously re-evaluates the game and maintains a small amount of persistent strategic intent. Most operational state is derived from current engine facts. Small stateful lifecycles are permitted only where the .per engine cannot express the required memory directly, such as a contested research/build transaction, a temporary placement override, or bounded failure backoff.

The governing loop is:

OBSERVE -> INTERPRET -> SET PERSISTENT INTENT -> DERIVE DEMAND -> REQUIRE CAPABILITY -> CHECK ENGINE FEASIBILITY -> ISSUE ACTION -> OBSERVE WORLD-STATE CHANGE -> REASSESS

The command is never the proof. The world is the proof.

## 2. The architecture balance

The correct balance is not a fixed percentage of stateless versus stateful code. It is a separation of responsibilities.

### Persistent strategic state

Persistent state answers questions that should remain true until the position changes.

Examples:
- strategy-goal: boom, rush/flush, castle-power, or another defined posture
- unit-goal: the army role currently wanted
- attack-goal: whether an attack cycle is active
- train-civ-goal: whether normal villager production is currently permitted
- a threat/pressure interpretation that cannot be reconstructed reliably from one engine fact

A persistent state variable must represent INTENT or a durable INTERPRETATION.

It must not merely mirror a command such as "build barracks."

### Derived state

Derived state should normally be recalculated from facts rather than stored.

Examples:
- current army counts
- queued production
- housing headroom
- resource shortage
- whether a Range/Stable/Barracks is required
- whether a technology is affordable
- whether a counter is currently needed
- whether an army is above or below its standing floor

Do not store a value just because it is convenient if the engine can calculate it safely from world-state.

### Execution state

Execution state exists only for an operation whose lifecycle cannot be expressed by ordinary facts.

Examples:
- a temporary resource claim while an age-up or premium technology is being started
- a temporary dropsite placement override while a camp foundation exists
- a research/build watchdog where the engine does not expose a sufficient failure witness
- a bounded retry cooldown

Execution state must be local to the operation. It must never become the definition of overall strategy.

### Failure memory

Failure memory is allowed when the engine can return the same failed action to the script indefinitely.

Failure memory must be:
- bounded
- local to the failed capability/action
- automatically cleared by success or meaningful state change
- incapable of permanently deleting strategic demand

A failure timer is a recovery tool, not a state machine.

## 3. State ownership rules

Every meaningful state has an owner.

For persistent intent:
1. One primary writer establishes the intent.
2. Any additional writer must have an explicit transition condition and precedence reason.
3. There must be a clear release or replacement condition.
4. The consumer must actually change behavior because the state exists.

For execution claims:
1. One executor acquires the claim.
2. The claim protects a real resource/capability conflict.
3. The owner performs the action.
4. A world-state witness proves completion.
5. Failure releases the claim into bounded backoff.
6. Completion releases the claim.
7. Strategic invalidation may preempt the claim when its opportunity cost is no longer justified.

A goal with no consumer is dead state.

A goal with multiple competing writers and no precedence is unstable state.

A claim with no release witness is a deadlock risk.

## 4. What a normal Basilisk action looks like

The preferred shape is:

1. Observe a meaningful condition.
2. Interpret it into an existing strategic posture or demand.
3. Determine what capability is missing.
4. Check engine-native feasibility.
5. Issue exactly the engine action required.
6. Let the resulting world-state become the completion witness.
7. Reassess on the next pass.

Example:

enemy archers detected
-> ranged threat interpretation becomes active
-> standing Skirmisher demand rises
-> Archery Range becomes required capability
-> pending/current Range count is checked
-> can-build archery-range
-> build archery-range
-> completed Range becomes the capability witness
-> military production may now train Skirmishers
-> reassess enemy composition and standing army

The production rule must not silently replace the missing capability rule.

A target without its capability is unfinished demand.

A capability without a consumer is unnecessary infrastructure.

## 5. What each kind of variable means

### Goals

Use goals for strategic memory and explicit execution state that must persist across rule passes.

Good:
- strategy-goal
- unit-goal
- housing demand
- a bounded project claim
- a failure-backoff state

Bad:
- caching every obvious count that can be queried directly
- mirroring a one-shot command with no downstream consumer
- using a goal as an opaque semaphore when ordinary predicates can prove availability

### Strategic numbers

Use engine strategic numbers primarily for engine policy.

Good:
- gatherer percentages
- camp distance behavior
- attack-group behavior
- engine-owned production/scouting settings
- documented engine controls

Custom strategic-number storage is permitted only when the identifier is verified unused and the state cannot be represented more clearly as a goal.

Do not turn strategic numbers into a second hidden database.

### Timers

Timers are for:
- attack/recon cadence
- controlled re-evaluation
- bounded retry delays
- watchdogs where no direct completion/failure witness exists

Timers must not be used to make the entire economy advance because "it is minute 8 now."

## 6. Resource arbitration

The normal economy is not a lock-based scheduler.

The default condition is:

resources are available to the strategy that currently needs them.

A resource claim is justified only when two otherwise-valid actions can contend for the same finite bank and the strategy genuinely needs to reserve that bank.

Good candidates:
- age-up resource bank
- an explicitly protected premium military package
- a one-time prerequisite purchase with hard strategic timing

Poor candidates:
- ordinary houses
- ordinary lumber camps
- ordinary farms
- ordinary army replacement
- any action where engine affordability already provides sufficient arbitration

The fewer global locks the controller needs, the closer it is to the intended heuristic style.

If a new feature requires a new global claim, first ask whether the conflict can be solved by:
- a stronger demand predicate
- a can-* feasibility test
- a pending-object guard
- current + queued counts
- a lower-priority consumer simply not being requested

Only introduce state when facts are insufficient.

## 7. Strategy selection

Strategy is a persistent policy, not a timed phase machine.

A strategy should change when meaningful evidence changes:
- age and economic readiness
- observed enemy pressure
- enemy composition
- battlefield condition
- strategic opportunity
- resource opportunity cost
- survival of the army supporting the posture

Strategy should have hysteresis.

The bot must not oscillate because a single resource crosses a threshold for one rule pass.

A strategy transition should change a small number of high-level intents. The lower layers should derive the consequences.

Bad:

strategy = rush
-> set 11 building flags
-> set 7 research flags
-> set 9 gatherer percentages
-> set 6 timers
-> set 4 production locks

Good:

strategy = pressure
-> desired army role changes
-> standing army target changes
-> production capability follows demand
-> resource allocation follows the resulting shortage

## 8. Military model

The military controller maintains two distinct concepts:

### Standing army requirement

The army that must exist for survival, deterrence, and continued strategic operation.

### Attack package

The subset that can safely leave the base and execute an attack.

The attack system must never consume the entire standing army merely because an attack trigger exists.

Military production is driven by the gap between desired usable force and current + queued force.

The desired force must be role-aware.

Unit counts alone are insufficient when the role is counter-dependent. Relevant signals include:
- enemy composition
- unit upgrades
- technology state
- siege requirement
- current production capacity
- replacement rate
- whether the intended fight is actually favorable enough to justify the commitment

No combat simulator is required. The target is practical heuristic judgment, not numerical omniscience.

## 9. Economy model

The economy exists to make the chosen strategic posture function.

At any pass, the key question is:

"What resource shortage is currently preventing the chosen plan from operating?"

Food supports:
- villager production
- age advancement
- food-based army
- food-based technology

Wood supports:
- houses
- farms
- production infrastructure
- economic infrastructure
- support buildings
- Town Centers

Gold supports:
- premium army
- key technologies
- age transitions

Stone is strategic and should not become a default sink.

Gatherer allocation should therefore respond to binding demand rather than attempt to maintain a permanently "perfect" ratio.

Fixed percentage bands are acceptable when they are used as practical heuristics and are changed only when a real strategic condition changes.

## 10. Buildings are capabilities, not strategy

A building should exist because some current demand requires the capability it provides.

Examples:
- enemy ranged pressure -> Skirmisher demand -> Range capability
- cavalry pressure -> anti-cavalry demand -> Barracks/Stable capability as required by the chosen counter
- siege demand -> Workshop capability
- premium research demand -> required production/research building capability
- more TC economy -> TC capability

Do not create a building merely because the strategy label says the building is associated with that strategy.

The strategy chooses the outcome.

The capability layer makes the outcome possible.

The executor performs the action.

## 11. Completion witnesses

Every important action needs a world-state witness.

Examples:
- build house -> building-type-count-total house increases
- build Range -> completed Range count exists
- research technology -> research-complete
- train unit -> current + queued unit count changes
- age up -> current-age changes
- establish dropsite -> completed camp exists and the engine resource-drop state changes
- start attack -> attack-state/group witness exists
- retreat -> attack state is actually reset and units are no longer committed

A timer expiring is not a completion witness.

A goal changing is not a completion witness.

A command having executed is not a completion witness.

## 12. The allowed local lifecycle

When a stateful lifecycle is genuinely necessary, its legal shape is:

IDLE
-> DEMANDED
-> FEASIBLE
-> ACTION-ISSUED
-> PENDING/IN-FLIGHT
-> COMPLETE

or

ACTION-ISSUED
-> FAILED/BLOCKED
-> BOUNDED BACKOFF
-> DEMAND REMAINS
-> RETRY

The lifecycle returns to ordinary heuristic control after completion or bounded recovery.

This local state machine is acceptable.

A global graph in which the entire AI can be only one state at a time is not the target.

## 13. Anti-patterns

The following are considered architecture failures unless there is specific evidence that the engine requires them:

- strategy labels directly issuing every action
- multiple unrelated global semaphores
- a persistent goal whose only purpose is to tell another rule to set another goal
- capability rules that have no consumer
- demands that never release
- commands without can-* or equivalent feasibility when the engine exposes one
- build rules without pending-object protection
- production rules that count only completed units and ignore queued production
- research rules that infer completion from the act of calling research
- timers used as substitutes for world-state witnesses
- resource reservations that survive the reason they were created
- failure backoff that deletes the strategic demand instead of delaying execution
- duplicated executors for the same target/action
- fixed gatherer ratios that ignore the current binding shortage
- strategy transitions driven solely by game time
- a new state variable introduced because the existing predicates are inconvenient to write

## 14. The exact acceptance test

A subsystem is finished only when all of the following are true.

SIGNAL:
A real game fact can be named.

INTERPRETATION:
The code explains what the signal means strategically.

INTENT:
The desired persistent outcome has one clear owner.

DEMAND:
The system expresses what must become true.

CAPABILITY:
The required building/unit/technology capability has a consumer.

FEASIBILITY:
The engine's can-* or equivalent condition is checked at the action boundary.

ACTION:
One executor is responsible for issuing the command.

WORLD-STATE RESULT:
A real engine fact changes.

COMPLETION:
The system can prove success from the world state.

FAILURE:
A failed attempt does not destroy the underlying demand.

RELEASE:
Temporary state is cleared by completion, invalidation, or bounded backoff.

REASSESSMENT:
The next pass can change the decision when the game changes.

If one link is missing, the subsystem is not complete.

## 15. The five tests for controller balance

### No starvation

A valid persistent strategy cannot be permanently starved by a lower-priority subsystem.

Example:
A Castle bank cannot be consumed indefinitely by farm infrastructure or low-value upgrades if Castle is the active strategic commitment.

### No deadlock

One subsystem cannot wait forever for state owned by another subsystem that is waiting for the first subsystem.

### No thrash

Small resource or threat fluctuations cannot cause repeated strategic reversals.

### No phantom completion

The controller cannot mark a project complete unless the world proves it.

### No orphan demand

A persistent demand cannot exist without a consumer that can eventually act on it or a rule that can invalidate it.

## 16. The target mental model

Think of Basilisk as a veteran player repeatedly asking:

"What is happening?"
"What does it mean?"
"What am I trying to make true?"
"What is preventing that?"
"What is the cheapest engine-native step that removes the blocker?"
"Did the world actually change?"
"What changed while I was doing it?"
"What should I want now?"

That is the controller.

The bot does not need to remember every step it took.

It needs to remember only the decisions that matter after the world has changed.

## 17. How to use this document during development

Every new feature must be reviewed against this specification before code is added.

The implementation review should ask:

1. Is this persistent strategy, derived demand, capability, or execution state?
2. Can the state be derived from existing facts instead?
3. Who owns the intent?
4. Who consumes it?
5. What capability does it require?
6. What exact engine feasibility condition gates the action?
7. What world-state fact proves success?
8. What happens when the action fails?
9. What clears temporary state?
10. What higher-priority demand can preempt it?
11. What resource opportunity cost does it impose?
12. Does adding it introduce another global lock?
13. Does it cause strategy, economy, or production to oscillate?
14. Can a strong player explain why this action is occurring right now?

The last question is deliberately included. If the answer is "because another rule set a flag three passes ago," the code is probably beginning to write fiction.

## 18. The target architecture in one line

Basilisk is a persistent-intent, demand-driven, engine-native heuristic controller with small local transaction lifecycles.

That is the exact target.

It is not a global finite-state machine.
It is not a stateless rule pile.
It is not a simulation.
It is not a general-purpose scheduler.

It is a continuously reassessing player model expressed through .per.
