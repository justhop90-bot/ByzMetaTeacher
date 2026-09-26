# AoE2DE `.per` Primitive Map

This is the hard-reference layer between the LearnerAI semantic model and actual Age of Empires II: Definitive Edition AI scripting primitives.

The semantic lifecycle is:

`DEMAND → ADMISSIBILITY → CAPABILITY → FEASIBILITY → ACTION → WORLD-STATE CHANGE → WITNESS → RELEASE → REASSESS`

AoE2DE does not implement those stages as typed runtime objects. They are a teaching model mapped onto goals, rule predicates, engine facts, commands, strategic numbers, timers, and observable world state. The engine primitives remain the implementation truth.

## Authority and use

Use these sources in this order:

1. **AIRef** for command/fact/parameter syntax and engine-facing semantics.
2. **Community scripts and tutorials** for recognizable patterns and practical idioms.
3. **LearnerAI/ENGINEERING.md** for lifecycle verification and failure classification.
4. **LearnerAI/SCHEMAS.md / LIFECYCLE.md** for the semantic vocabulary being taught.

AIRef: https://airef.github.io/  
AIRef repository: https://github.com/airef/airef.github.io  
Siege Engineers developer resources: https://github.com/SiegeEngineers/aoc-dev-resources  
Simple AI scripting tutorial: https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881

The examples below are teaching patterns, not drop-in production code. Exact command availability and behavior are version-sensitive and must be checked against the target DE build and current AIRef.

---

## 1. Semantic lifecycle → .per primitive mapping

| Semantic term | Typical .per representation | What it means | What it can prove | What it cannot prove |
|---|---|---|---|---|
| Demand | `goal`, goal value, strategic state, or persistent rule condition | Something the strategy/domain still wants accomplished | That a stored or derived intent condition is true | That the action is feasible or completed |
| Admissibility | `goal`, `current-age`, `strategic-number`, resource/threat predicates, other rule conditions | The demand is still justified now | That the rule's justification predicates currently hold | That the demand can be executed |
| Capability | Existing/pending prerequisites, counts, age, buildings, technologies, resource availability, engine facts | Means required to satisfy the demand exist or are developing | That required means are present/available according to the predicates used | That the engine will accept the exact action now |
| Feasibility | `can-build`, `can-train`, `can-research`, plus explicit resource/prerequisite/pending predicates | Engine permits the requested action now | That the relevant engine capability predicate is true at evaluation time | That the action will succeed or that the world state will change |
| Action | `build`, `train`, `research`, `attack-now`, `set-goal`, `set-strategic-number`, etc. | Request to change game/control state | That the rule issued the command | That the command completed successfully |
| World-state change | Building/unit/technology/resource/age/count facts | Observable result in the game state | Actual state transition when the fact reflects it | Strategic meaning by itself |
| Witness | `building-type-count-total`, `unit-type-count-total`, `current-age`, research/tech status, pending/foundation facts, resource/state observations | Evidence that an expected result exists | Completion when the observed fact uniquely corresponds to the expected result | That an action caused it unless causal context is controlled |
| Release | `set-goal ... 0`, goal transition, strategic-state change, or natural loss of rule eligibility | Ends or changes a demand | That the stored demand/state was changed | That all side effects or related commitments were cleaned up |
| Reassess | Later rule evaluation using current facts/goals | Feedback into strategy/domain logic | That the next evaluation sees current state | That an earlier action succeeded merely because later rules ran |

### Core teaching rule

Do not teach the learner that a semantic stage is a hidden engine object. Teach the mapping.

For example:

- **Demand:** a goal saying “we need a Castle.”
- **Capability:** Castle Age + required resources + builder/prerequisites + relevant construction state.
- **Feasibility:** `can-build castle`.
- **Action:** `build castle`.
- **Witness:** Castle exists in world state.
- **Release:** the Castle demand no longer evaluates as active or its goal is cleared.

That is an interpretation of ordinary `.per` primitives, not a new scripting language.

---

## 2. Goals and persistent intent

### Primitive family

Typical forms:

```
(defconst gl-example 1)

(defrule
    ...
=>
    (set-goal gl-example 1)
)

(defrule
    (goal gl-example 1)
    ...
=>
    ...
)
```

Related primitives include goal comparisons and goal modification mechanisms such as `up-compare-goal`, `up-modify-goal`, and `up-get-fact`, depending on the exact implementation.

### Semantic role

A goal is a mutable integer state primitive. It is often the cleanest representation of persistent intent, but it is not inherently a “demand object.”

One goal may represent:

- a demand;
- a threshold;
- a mode;
- a strategic posture;
- a transition state;
- a temporary control value.

The semantic owner gives the goal its meaning.

### Proves

A `goal` predicate proves only that the stored goal value currently matches the requested value.

### Does not prove

It does not prove:

- the desired world state exists;
- resources are available;
- `can-*` is true;
- an action has been issued;
- an action succeeded.

### Community pattern

Goals are commonly used to replace duplicated numeric thresholds and to carry strategic state between rules. Community tutorials demonstrate goals as mutable variables that can drive production thresholds. citeturn0search5

### Anti-pattern

Setting a goal immediately after an action and treating the goal as the completion witness.

Bad semantic model:

`build castle → set CastleComplete = 1`

The goal proves only that the rule set the goal.

Better:

`build castle → observe Castle exists → release Castle demand`.

### Ownership

The module that owns the semantic decision owns the goal meaning. Avoid generic “goal managers.”

### Caveat

Goal IDs are global integer slots. They need stable definitions, initialization discipline, and one semantic owner. Reusing a goal for unrelated meanings creates hidden coupling.

---

## 3. Rule conditions and admissibility

### Primitive family

`defrule` conditions:

```
(defrule
    <condition>
    <condition>
=>
    <action>
)
```

Conditions may use game facts, goals, strategic numbers, timers, player observations, resources, and engine capability predicates.

### Semantic role

Rule predicates are the normal .per implementation of admissibility and gating.

A rule can encode:

- age context;
- strategic posture;
- resource pressure;
- threat context;
- count thresholds;
- prerequisites;
- pending-state protection;
- ownership/focus-player context;
- timing.

### Proves

The conjunction/disjunction of the conditions proves only that those predicates are true when the rule is evaluated.

### Does not prove

The conditions do not prove the action's result.

### Anti-pattern

Treating the rule's firing as a transaction:

`conditions true → action must have happened`.

The engine is not an accountant. It does not hand you a receipt because your rule fired.

### Engineering caveat

Check logical operator arity, source order, identifier validity, and rule-size limits. Syntactically plausible condition trees can still be invalid for the actual parser or engine.

---

## 4. Engine-native feasibility: `can-*`

### Primitive family

Common examples:

```
(can-build castle)
(can-build house)
(can-train villager)
(can-train skirmisher-line)
(can-research ri-loom)
```

### Semantic role

This is the preferred implementation of the **FEASIBILITY** stage when the engine exposes an appropriate predicate.

The learner should understand:

`can-X = engine says the action is currently admissible`

not:

`can-X = strategy says we should do X`.

### Proves

At evaluation time, the relevant engine capability predicate is true.

### Does not prove

It does not prove:

- the strategic demand exists;
- the action will be selected;
- the command will complete;
- the requested object will exist afterward;
- a competing rule will not consume resources or builders first.

### Community pattern

A canonical production pattern is:

```
(defrule
    (unit-type-count-total knight-line < target)
    (can-train knight-line)
=>
    (train knight-line)
)
```

Community tutorials explicitly use count thresholds paired with `can-train`, and construction examples pair `can-build` with a count/pending guard. citeturn0search5

### Anti-pattern

Using `can-build` as the strategic trigger:

```
(defrule
    (can-build castle)
=>
    (build castle)
)
```

This confuses capability with demand and can create uncontrolled construction.

### Ownership

The domain owns the decision to request the action. Engine owns the meaning of `can-*`.

---

## 5. Construction facts and actions

### Core primitives

Typical construction predicates/actions include:

```
(build castle)
(build house)
(build farm)
(build town-center-foundation)
(build siege-workshop)
(build monastery)
```

Common witnesses/guards include:

```
(building-type-count-total castle)
(up-pending-objects c: castle ...)
```

Other building facts may be appropriate depending on whether the question is owned structures, total structures, foundations, or a particular object class.

### Semantic mapping

Construction demand:

`goal / strategic condition`

Capability:

`age + resources + prerequisites + builder availability + relevant construction state`

Feasibility:

`can-build X`

Action:

`build X`

Witness:

`building-type-count-total X > 0` or another appropriate completed-building fact

Pending protection:

`up-pending-objects c: X ...`

### Proves

A completed-building count can prove that the relevant building exists according to the count predicate.

A pending-object predicate can prove that a construction object is pending according to the selected filter.

### Does not prove

A build command does not prove completion.

A pending foundation does not prove the building is complete.

A capability predicate does not prove a builder has actually been assigned successfully.

### Community pattern

Community scripts commonly pair:

- `building-type-count-total`;
- `up-pending-objects`;
- `can-build`;
- `build`.

A public community example uses all four to prevent repeated building requests. citeturn0search0

### Anti-pattern

```
(defrule
    (building-type-count-total castle < 1)
    (can-build castle)
=>
    (build castle)
)
```

This may be enough for a deliberately simple one-shot example, but it teaches a dangerous incomplete lesson for persistent construction: the completed count is not necessarily enough to protect against pending construction, multiple rules, or same-pass/repeated requests.

### Engineering rule

For important construction, explicitly distinguish:

`absent → requested → pending/foundation → completed`.

Do not collapse those states into “not built.”

---

## 6. Pending-state primitives

### Primitive family

`up-pending-objects` is the important community-facing mechanism for detecting pending objects.

Typical pattern:

```
(up-pending-objects c: house < 2)
(can-build house)
=>
(build house)
```

### Semantic role

Pending state is an execution-state guard. It prevents a persistent demand from repeatedly issuing actions while the previous request is already represented in the engine.

### Proves

It can establish that the selected pending-object query currently satisfies its comparison.

### Does not prove

It does not prove:

- completion;
- successful builder assignment;
- eventual construction;
- strategic validity.

### Community evidence

Community scripting examples explicitly use `up-pending-objects` alongside `can-build` and count predicates to limit simultaneous building requests. citeturn0search0

### Anti-pattern

Treating “pending” as “complete.”

### Ownership

Construction owns pending-state interpretation for construction demands. Production owns analogous queue/production state.

---

## 7. Building and unit counts as witnesses

### Building counts

Typical forms:

```
(building-type-count-total castle)
(building-type-count-total town-center)
```

### Unit counts

Typical forms:

```
(unit-type-count-total villager)
(unit-type-count-total skirmisher-line)
(unit-type-count-total knight-line)
```

### Player/enemy counts

Common families include:

```
(players-building-type-count ...)
(players-unit-type-count ...)
```

These are particularly important for Information/Military because “my count” and “enemy count” are different semantic observations.

### Semantic role

Counts are world-state observations and often serve as completion witnesses.

### Proves

A count proves the observed quantity according to the command's scope and object definition.

AIRef's object tables distinguish unit lines, sets, classes, buildings, and related IDs. Unit-line counts can therefore intentionally cover upgraded members of a line rather than one exact unit. citeturn0search1

### Does not prove

A count does not prove why the objects exist or which rule produced them.

### Anti-pattern

Using a broad unit-line count when the strategic demand requires one exact unit type, or using a completed-building count when the question is about pending foundations.

### Engineering rule

State the exact scope of every witness:

- own vs enemy;
- exact object vs line/set/class;
- completed vs pending;
- total vs local/filtered observation.

---

## 8. Resource predicates

### Primitive family

Common resource observations include:

```
(food-amount)
(wood-amount)
(gold-amount)
(stone-amount)
(resource-found wood)
(resource-found gold)
(dropsite-min-distance wood ...)
```

Exact available predicates vary by question and engine version.

### Semantic role

Resource facts support:

- admissibility;
- capability;
- feasibility;
- economic observation;
- arbitration.

### Proves

A resource amount proves the observed resource quantity at evaluation time.

`resource-found` can establish resource availability in the relevant sense.

### Does not prove

A resource amount alone does not prove that the engine can execute a specific action. Other prerequisites, builders, queues, technology, age, or competing actions may still block it.

### Anti-pattern

Treating:

`wood >= 200`

as equivalent to:

`can-build siege-workshop`.

It is not.

### Community pattern

Community economy scripts commonly combine resource conditions, `can-build`, dropsite facts, pending guards, and building counts. citeturn0search4

---

## 9. Age and technology state

### Age facts

Typical primitive:

```
(current-age == dark-age)
(current-age >= castle-age)
```

### Technology feasibility

Typical primitive:

```
(can-research ri-loom)
(research ri-loom)
```

Technology state may also be queried through research/technology status commands where appropriate.

### Semantic mapping

Age demand:

`strategic age objective`

Capability:

`prerequisite buildings/resources/age-up requirements`

Feasibility:

`can-research / relevant engine predicate`

Action:

`research ...`

Witness:

`current-age`, technology/research completion state, or another direct world-state fact

Release:

goal/state transition after the witness.

### Proves

`current-age` proves the current age.

`can-research` proves current engine permission to research the specified technology.

A completed technology status proves that technology has actually completed if the selected status predicate has that meaning.

### Does not prove

Research command issuance is not technology completion.

Age-up intention is not current-age transition.

### Community pattern

Simple scripts commonly pair `can-research` with `research`. citeturn0search0

---

## 10. Strategic numbers

### Primitive family

Examples:

```
(strategic-number sn-food-gatherer-percentage > 0)
(set-strategic-number sn-food-gatherer-percentage 50)
```

Modification forms include `up-modify-sn` where appropriate.

### Semantic role

Strategic numbers are engine/control parameters and mutable numeric state. They are useful for configuring engine behavior and expressing tunable policy values.

### Proves

A strategic-number predicate proves the current configured value.

### Does not prove

It does not automatically prove:

- that the intended behavior occurred;
- that the engine has enough resources;
- that the strategic objective is complete.

### Anti-pattern

Using strategic numbers as a universal database because they are convenient integers.

### Ownership

The module responsible for the policy represented by the strategic number should own its semantic meaning. Engine owns the actual strategic-number mechanism.

### Community pattern

Community scripts use strategic numbers to configure gather percentages, attack levels, distances, and other engine behaviors. Public examples show both direct setting and modification. citeturn0search2

---

## 11. Timers

### Primitive family

Typical forms:

```
(enable-timer 1 60)
(timer-triggered 1)
(disable-timer 1)
```

### Semantic role

Timers provide temporal gating, cooldown, delayed reevaluation, and attack/behavior pacing.

### Proves

`timer-triggered` proves that the timer condition is currently triggered.

### Does not prove

It does not prove that the desired action succeeded.

### Anti-pattern

Using timers as persistent demand storage.

A timer answers “when may this rule run again?” It does not answer “do we still need this?”

### Community pattern

Community attack examples use timers to pace attack behavior, and tutorial scripts use timers to create recurring actions. citeturn0search2

### Learner rule

Persistent strategic intent belongs in goals/state. Timers are temporal mechanisms around that intent.

---

## 12. Action commands

### Construction

`build X`

### Production

`train X`

### Technology

`research X`

### Military control

`attack-now` and related commands where appropriate.

### State/configuration

`set-goal`, `set-strategic-number`, timer controls, and related state/configuration actions.

### Semantic rule

An action is an instruction to the engine.

The learner must always ask:

1. What condition authorized it?
2. What capability supported it?
3. What feasibility predicate was checked?
4. What world-state witness should follow?
5. What prevents duplicate/repeated issuance?
6. What releases the demand?

### Hard invariant

**Action is never witness.**

This is the single most important mapping in this document.

---

## 13. Production queues and unit-demand witnesses

A production demand commonly maps to:

```
unit-type-count-total X < target
can-train X
→ train X
```

### Capability

Production building, age, technology, resource, queue and other requirements.

### Feasibility

`can-train X`.

### Action

`train X`.

### Witness

`unit-type-count-total X >= target`, or a more specific production-state witness when the demand is queue-oriented rather than army-count-oriented.

### Release

The production demand is satisfied when the required count/state is reached, or it remains active if the strategic posture intentionally requires a standing minimum.

### Community pattern

This exact count-plus-`can-train` pattern is shown in community tutorials. citeturn0search5

### Anti-pattern

Issuing `train X` every pass solely because the count remains below target without considering queue/pending state or production capacity. A count deficit is demand, not proof that another immediate queue command is appropriate.

---

## 14. Housing and support infrastructure

Typical observations:

```
(housing-headroom < 4)
(population-headroom > 3)
(can-build house)
```

Typical action:

```
(build house)
```

### Semantic lesson

Housing is a useful example because:

- the demand may be derived from current population pressure;
- capability is a builder/resource condition;
- feasibility is `can-build house`;
- the action is `build house`;
- the witness is increased housing capacity/headroom or completed house state.

Community tutorials explicitly demonstrate `housing-headroom`, `population-headroom`, and `can-build house` as construction guards. citeturn0search5

---

## 15. Information and enemy observations

### Primitive families

Common observation families include:

```
(players-unit-type-count ...)
(players-building-type-count ...)
(player-number ...)
(focus-player ...)
```

Other scouting/search primitives can expose local or remote objects.

### Semantic role

These are Information inputs, not Strategy commands.

Information observes.

Strategy interprets and decides.

Military/Economy/Construction/Production execute domain responses.

### Proves

A player-count predicate proves the observed count in its specified scope.

### Does not prove

It does not prove the enemy's intention.

For example:

`enemy knight count > 0`

does not prove:

`enemy will attack my base with knights`.

### Anti-pattern

Directly turning every observation into an action without an interpretation layer.

---

## 16. Advanced `up-*` primitives

The `up-*` family provides more powerful engine-facing operations and fact manipulation. Examples include:

```
(up-get-fact ...)
(up-compare-goal ...)
(up-modify-goal ...)
(up-modify-sn ...)
(up-pending-objects ...)
(up-assign-builders ...)
(up-find-local ...)
(up-find-remote ...)
(up-target-objects ...)
(up-reset-filters ...)
(up-research-status ...)
```

These are powerful precisely because they expose lower-level engine behavior.

### Teaching rule

Do not introduce an `up-*` primitive merely because it is more sophisticated.

First teach the plain engine primitive. Introduce the `up-*` form only when the learner can explain exactly what additional engine fact or operation it supplies.

### Anti-pattern

Wrapping every primitive in an invented abstraction layer that hides what the engine is actually doing.

---

## 17. Builder assignment and execution state

Primitives such as `up-assign-builders` can control or inspect construction execution more directly.

### Semantic role

These belong to execution/capability handling, not strategic demand creation.

### Proves

An assignment operation indicates that the script requested a builder-management action.

### Does not prove

It does not by itself prove that construction completed.

### Engineering rule

When builder assignment matters to correctness, pair the request with a world-state witness rather than treating the assignment command as completion.

---

## 18. Attack actions and military witnesses

A military action such as:

```
(attack-now)
```

is an execution request.

It is not an attack-success witness.

### Possible witnesses

Depending on the behavior being taught:

- attack timer/state;
- military population/count;
- enemy unit/building observations;
- destruction counts or other observable state;
- later reassessment of the military objective.

### Teaching rule

Separate:

`ready to attack`

from:

`attack command issued`

from:

`attack actually changed the world`.

Community scripting examples demonstrate `attack-now` combined with military thresholds and timers. citeturn0search0turn0search2

---

## 19. Release primitives

There is no universal `release-demand` engine command.

Release is semantic and can be implemented through:

```
(set-goal GOAL 0)
```

or another goal/state transition, or simply by causing the rule that represents the demand to become false.

### Important distinction

A demand can be released because:

1. its completion witness became true;
2. strategy cancelled it;
3. it became obsolete;
4. a strategic transition replaced it;
5. a temporary mode ended.

### Anti-pattern

Clearing the demand immediately after issuing the action.

That converts:

`persistent demand`

into:

`one-shot request`

and destroys the feedback loop.

---

## 20. Canonical lifecycle: Castle

This is the canonical Construction example because it forces the learner to distinguish **availability, affordability, buildability, execution state, completion, and strategic release**. These are separate engine questions.

### Demand

Strategy establishes that Castle infrastructure is required.

Possible semantic representation:

\u0060\u0060\u0060
(goal GOAL-CASTLE 1)
\u0060\u0060\u0060

The goal means **the strategy still wants a Castle**. It does not mean that the Castle is available, affordable, buildable, under construction, or completed.

The demand should also have a target and an admissibility boundary, for example:

\u0060\u0060\u0060
required Castle count = 1
completed Castle count < required count
strategic Castle posture remains active
\u0060\u0060\u0060

### Admissibility

Strategy/domain conditions determine whether the demand still applies.

Examples:

- the intended strategic posture still calls for a Castle;
- the player is in the appropriate age/context;
- the demand has not been cancelled or superseded;
- the required Castle count has not already been satisfied.

Admissibility is **why we still care**. It is not an engine permission check.

### Capability: `building-available`

First distinguish whether the building is actually available to the civilization and current technology-tree state.

Conceptually:

\u0060\u0060\u0060
(building-available castle)
\u0060\u0060\u0060

This answers: **“Is Castle construction available in the current civ/tech-tree state?”**

It does not prove that the Castle can be placed, that its resources are available, that a builder can execute the request, or that the Castle is not already pending.

### Capability: `can-afford-building`

Resource affordability is a separate question.

Conceptually:

\u0060\u0060\u0060
(can-afford-building castle)
\u0060\u0060\u0060

This answers: **“Does the engine consider the normal Castle cost affordable right now?”**

It does not prove placement, builder execution, freedom from competing resource commitments, or eventual completion.

If the economy uses escrow/resource reservation, escrow represents **resource commitment/arbitration**, not Castle completion. A Castle can have resources protected without being built, and resources can exist in the bank while another demand has a legitimate claim on them.

### Capability: builder availability and assignment

Construction must distinguish:

1. villagers exist who are eligible to construct the building;
2. builders are actually available to be assigned;
3. the construction request has entered the appropriate builder/execution state.

Where explicit assignment is used, primitives such as:

\u0060\u0060\u0060
(up-assign-builders ...)
\u0060\u0060\u0060

are **execution/control operations**, not completion witnesses.

A builder assignment request proves that the script requested builder assignment. It does not prove that construction completed.

Do not turn “we have 10 villagers” into “Castle construction is feasible.” Worker availability is one input to construction execution, not the whole construction decision.

### Capability: placement constraints

Castle construction is spatial.

The learner must distinguish:

**“The Castle is affordable and available”**

from:

**“The engine can start a Castle at a legal/usable location now.”**

Placement/location constraints therefore belong to actual build feasibility. They must not be inferred merely from resource amounts or prerequisite buildings.

This is another reason `can-build castle` matters: it is the engine-facing feasibility test rather than a homemade claim that the prerequisites look good.

### Feasibility: `can-build`

The decisive engine-native construction test is:

\u0060\u0060\u0060
(can-build castle)
\u0060\u0060\u0060

Teach this as: **“The engine currently permits the Castle construction request under its buildability rules.”**

Keep it distinct from the diagnostic layers:

| Question | Primitive/concept |
|---|---|
| Is Castle available to this civ/tech state? | `building-available castle` |
| Can the normal cost be afforded? | `can-afford-building castle` |
| Are suitable builders/execution resources available? | builder/construction state |
| Can construction actually be started? | `can-build castle` |
| Is a Castle already completed? | `building-type-count castle` |
| Is a Castle completed or under construction? | `building-type-count-total castle` |
| Is a Castle construction object pending? | `up-pending-objects ... castle` |

Do not reduce all of these to one generic “Castle capability” flag.

`can-build castle` is also not a strategic decision. Construction asks whether the demand should be serviced; the engine answers whether the requested construction is feasible now.

### Escrow and resource arbitration

A persistent Castle demand can compete with farms, Town Centers, military production, upgrades, or other infrastructure.

The learner therefore needs this distinction:

\u0060\u0060\u0060
resource exists
    ≠
resource is available to this demand
    ≠
engine permits this build
\u0060\u0060\u0060

If the script uses escrow/resource reservation, escrow represents **resource commitment/arbitration**, not completion. It protects or commits resources for a purpose; it does not prove that a Castle exists.

Likewise, resource arbitration should not replace `can-build`. Economy decides whether the demand receives access to scarce resources; engine feasibility decides whether construction can actually proceed.

### Repeat prevention: completed versus pending

The critical construction-state distinction is:

\u0060\u0060\u0060
ABSENT
  ↓
DEMANDED
  ↓
BUILD REQUESTED
  ↓
PENDING / FOUNDATION
  ↓
COMPLETED
\u0060\u0060\u0060

The learner must not interpret “Castle count is zero” as “issue another Castle request.”

`building-type-count castle` is the important **completed/existing-building witness**.

By contrast, `building-type-count-total castle` answers a different question because it includes existing and under-construction buildings.

`up-pending-objects ... castle` can provide an explicit pending-construction guard when the script needs to know whether a Castle construction object is already pending or needs finer control over simultaneous requests.

For a one-Castle demand, a construction rule must prevent:

\u0060\u0060\u0060
Castle absent
→ build castle
→ Castle not completed yet
→ build castle again
→ duplicate construction requests
\u0060\u0060\u0060

A pending/total-state guard is therefore execution correctness, not an optional optimization.

A simple teaching rule may use `building-type-count-total` because it includes under-construction buildings:

\u0060\u0060\u0060
completed-or-under-construction Castle count < required count
+ can-build castle
→ build castle
\u0060\u0060\u0060

A more explicit construction system can separately inspect `up-pending-objects` when it needs to distinguish pending state or control simultaneous construction more precisely.

### Action

Once the demand remains admissible, the required capability exists, and the engine says construction is feasible:

\u0060\u0060\u0060
(build castle)
\u0060\u0060\u0060

This is an **action request**.

It is not a completion witness. It does not prove that a foundation was placed, builders were assigned, construction progressed, or the Castle completed.

### World-state transition

After the action, construction may progress through:

\u0060\u0060\u0060
REQUESTED
→ PENDING / FOUNDATION
→ UNDER CONSTRUCTION
→ COMPLETED
\u0060\u0060\u0060

The exact observable state available to the script depends on the engine primitive being used.

This transition is why action and witness must remain separate.

### Witness: `building-type-count`

The primary completion witness is:

\u0060\u0060\u0060
(building-type-count castle > 0)
\u0060\u0060\u0060

This is intentionally **not**:

\u0060\u0060\u0060
(building-type-count-total castle > 0)
\u0060\u0060\u0060

The distinction is critical:

- `building-type-count castle` teaches **completed/existing Castle**.
- `building-type-count-total castle` teaches **completed plus under-construction Castle**.

Therefore a positive total count can establish that the Castle lifecycle has entered construction state, but it must not automatically be used as proof that the Castle is completed.

For a target of N Castles:

\u0060\u0060\u0060
building-type-count castle >= required-count
\u0060\u0060\u0060

is the natural completion witness.

### Completion versus release

**Completion** and **release** are not the same event.

Completion means:

\u0060\u0060\u0060
world state proves required Castle count exists
\u0060\u0060\u0060

Release means:

\u0060\u0060\u0060
the strategic/domain demand no longer needs to remain active
\u0060\u0060\u0060

The normal successful path is:

\u0060\u0060\u0060
Castle demand active
→ Castle construction completed
→ completed-building witness true
→ Castle demand released or transitioned
\u0060\u0060\u0060

But release can also occur without completion when Strategy explicitly cancels or supersedes the demand.

Therefore distinguish:

- **COMPLETED:** expected world state exists;
- **CANCELLED/OBSOLETE:** Strategy no longer wants it;
- **BLOCKED:** Strategy still wants it, but execution is currently impossible;
- **ACTIVE:** Strategy still wants it and construction remains unresolved.

Never clear the demand merely because `build castle` fired.

### Blocked behavior

If `can-build castle` remains false while the Castle demand is still admissible, preserve the demand and diagnose the blocking layer:

1. Is `building-available castle` false?
2. Is the normal cost unaffordable?
3. Are resources committed to another demand/escrow?
4. Are eligible builders unavailable?
5. Is a Castle already pending?
6. Is the intended placement currently invalid?
7. Is another engine construction constraint blocking the action?
8. Is another rule consuming the resources or builders first?
9. Has Strategy actually cancelled or superseded the demand?

`can-build castle` is the immediate engine-level feasibility result. These other observations explain why it may be false or why the demand may remain blocked.

Do not solve a blocked persistent demand by accumulating permanent retry counters. Preserve intent, use transient cooldown/backoff where necessary, and reassess the actual blocking state.

### Canonical Castle trace

\u0060\u0060\u0060
DEMAND
  Strategy wants one Castle
        ↓
ADMISSIBILITY
  strategic Castle posture remains valid
        ↓
CAPABILITY
  building-available
  + resources/affordability
  + builders
  + prerequisites
  + construction state
        ↓
RESOURCE ARBITRATION
  required resources are available to this demand
        ↓
FEASIBILITY
  can-build castle
        ↓
ACTION
  build castle
        ↓
EXECUTION STATE
  pending/foundation/under construction
        ↓
WORLD-STATE WITNESS
  building-type-count castle >= required count
        ↓
COMPLETION
  required Castle actually exists
        ↓
RELEASE
  Castle demand clears/transitions
        ↓
REASSESS
  Strategy and domains react to the new infrastructure
\u0060\u0060\u0060

The hard invariants are:

- `building-available` is not `can-build`.
- `can-afford-building` is not `can-build`.
- builder availability is not completion.
- placement validity is not strategic demand.
- escrow is not completion.
- `build castle` is not completion.
- `building-type-count-total` is not the same witness as `building-type-count`.
- pending is not completed.
- completion is not automatically identical to release.
- cancellation/obsolescence is not successful completion.
- a persistent Castle demand survives temporary blockage unless Strategy explicitly removes it.

---

## 21. Canonical lifecycle: defensive Spearmen

### Demand

Information identifies a relevant cavalry threat. Military establishes a minimum defensive requirement.

### Capability

Relevant production building, age, technology and resources.

### Feasibility

```
(can-train spearman)
```

### Action

```
(train spearman)
```

### Witness

```
(unit-type-count-total spearman-line >= required-count)
```

### Release/reassess

The minimum requirement is satisfied, but the threat remains observable. Therefore the standing strategic condition may generate a new or continued demand later.

### Lesson

A production threshold is often a better teaching model than “train N units once.” It demonstrates persistent intent plus world-state completion.

---

## 22. Canonical lifecycle: Fletching

### Demand

A technology is justified by the current strategic/economic posture.

### Capability

Blacksmith and technology prerequisites exist.

### Feasibility

```
(can-research ri-fletching)
```

### Action

```
(research ri-fletching)
```

### Witness

Use the appropriate technology/research completion fact.

### Release

End the research demand only after actual completion or explicit cancellation.

### Lesson

A research command is not a technology witness.

---

## 23. Canonical lifecycle: farm construction

Farm production is a useful economic example because it demonstrates that resource pressure and infrastructure demand are distinct.

### Demand

Food infrastructure requires another farm under the economic policy.

### Capability

Mill/farm prerequisites, resources, builder availability and farm-specific engine conditions.

### Feasibility

```
(can-build farm)
```

### Action

```
(build farm)
```

### Witness

Farm count/state or the economic condition the farm demand was created to correct.

### Anti-pattern

“Food is low, therefore build farms forever.”

The economic demand must have an admissibility condition and an actual target/boundary.

Community examples use farm counts/goals and `can-build farm` as part of economic control. citeturn0search0

---

## 24. Capability versus feasibility

This distinction deserves its own section because it is where otherwise competent scripts become haunted.

### Capability

“Could we satisfy this demand in principle?”

Examples:

- Castle Age reached;
- Castle prerequisites exist;
- production building exists;
- technology is available;
- resources are being accumulated;
- a builder can potentially be assigned.

### Feasibility

“Does the engine permit this exact action now?”

Examples:

```
(can-build castle)
(can-train knight-line)
(can-research ri-fletching)
```

### Rule

Capability should normally feed feasibility. Capability should never be treated as proof that feasibility is true.

---

## 25. Pending versus completed

The learner must be able to draw this state ladder:

```
ABSENT
  ↓
DEMANDED
  ↓
ACTION REQUESTED
  ↓
PENDING / FOUNDATION / QUEUED
  ↓
COMPLETED
  ↓
WITNESSED
  ↓
RELEASED
```

The exact available predicates differ by action type.

### Hard rule

Do not collapse:

- requested;
- queued;
- pending;
- foundation;
- completed.

Those states are not interchangeable.

---

## 26. Goals, strategic numbers, and timers are not interchangeable

| Primitive | Best teaching role | Common misuse |
|---|---|---|
| Goal | Persistent semantic state, thresholds, modes | Universal database |
| Strategic number | Engine/control parameter | Universal state database |
| Timer | Temporal gating/cooldown | Persistent demand manager |
| World-state fact | Observation/witness | Strategic intent |
| `can-*` | Engine feasibility | Strategic decision |
| Action command | Request | Completion witness |

This distinction should remain visible throughout the learner curriculum.

---

## 27. Parser and engine caveats

The following are mandatory Engineering checks whenever these primitives become executable code:

### Syntax

- Balanced parentheses.
- Valid command/fact names.
- Valid identifiers and constants.
- Correct argument count.
- Correct argument types/ordering.

### Logical structure

- `and` receives the expected number of operands.
- `or` receives the expected number of operands.
- `not` receives the expected operand structure.
- Nested logical groups are inspected rather than trusted because the parentheses balance.

### Rule structure

- Check actual rule element limits.
- Avoid enormous condition/action lists.
- Split rules when the semantic chain becomes difficult to trace.

### Source order

- Definitions exist before use where required.
- Included files load in the intended order.
- Initialization occurs before consumption.
- First writer and first consumer are identified.

### State flow

For every important goal/number:

- initialization;
- first writer;
- all writers;
- all readers;
- transition values;
- release;
- cancellation;
- downstream consumer.

### Execution loops

For every action:

- Can the rule fire repeatedly?
- Is pending/queue state guarded?
- Is there a completion witness?
- Is there a release?
- Is there a legitimate reason to repeat?

### Runtime

Static validity does not prove engine behavior. Runtime verification remains empirical.

---

## 28. Anti-pattern catalogue

### Action-as-witness

```
(build castle)
(set-goal CASTLE-DONE 1)
```

The goal records that the rule ran, not that the Castle exists.

### Capability-as-demand

```
(can-build castle)
→ build castle
```

The engine's permission becomes the strategy.

### Count-without-pending

```
(building-type-count-total house < target)
(can-build house)
→ build house
```

Potentially repeats requests while earlier construction is already pending.

### Resource-as-feasibility

```
(wood-amount >= 200)
→ build siege-workshop
```

Resources alone do not establish engine feasibility.

### Timer-as-demand

```
(timer-triggered X)
→ train unit
```

The timer determines when, but not why the unit is still needed.

### Goal-as-proof

```
(goal CASTLE-DEMAND 1)
```

This proves intent, not Castle existence.

### Comment-as-contract

A comment saying “this builds the Castle” is not a witness, invariant, or engine fact.

### Generic-manager abstraction

A universal manager that hides goals, predicates, actions, and witnesses makes the learner less able to understand actual .per. The abstraction is working against the teaching goal.

---

## 29. Community-standard trace template

Every important learner behavior should be traceable with this worksheet:

| Stage | Question | .per evidence |
|---|---|---|
| Demand | What do we still want? | goal/state/strategic condition |
| Admissibility | Why is it still justified? | rule predicates |
| Capability | What means exist? | buildings, age, resources, prerequisites, pending state |
| Feasibility | Can the engine do it now? | `can-*` |
| Action | What did we request? | `build` / `train` / `research` / other action |
| World change | What should change? | observable engine state |
| Witness | What proves it? | count/state/technology/age/resource fact |
| Release | When does intent end/change? | goal/state transition or loss of admissibility |
| Reassess | What happens next? | later rules using current facts |

If any row has no clear answer, the behavior is not fully specified.

---

## 30. Verification checklist for future executable lessons

Before accepting a learner implementation:

- [ ] The strategic/domain owner is explicit.
- [ ] Persistent intent has a defined representation.
- [ ] Creation/admissibility conditions are explicit.
- [ ] Capability is distinguished from feasibility.
- [ ] An engine-native `can-*` predicate is used where applicable.
- [ ] Resource checks do not masquerade as full feasibility.
- [ ] Pending/queued/foundation state is guarded where repeated actions are possible.
- [ ] The action command is explicit.
- [ ] The expected world-state change is explicit.
- [ ] The witness is an observable engine/world fact.
- [ ] The action itself is not used as the witness.
- [ ] Release is explicit or demonstrably encoded by state/rule ineligibility.
- [ ] Cancellation/obsolescence is distinct from completion.
- [ ] Persistent intent survives temporary blockage.
- [ ] Timers are used for temporal control, not as demand storage.
- [ ] Strategic numbers retain engine/control meaning.
- [ ] Goal IDs have one semantic owner.
- [ ] All readers/writers of important state are traceable.
- [ ] Repeated-action behavior is understood.
- [ ] Rule order and same-pass interactions are understood.
- [ ] Parser arity and rule-size constraints are checked.
- [ ] Runtime verification is planned separately from static verification.

---

## 31. The learner's one-line mental model

When reading any serious .per behavior, translate it mentally as:

**“What do we want, why do we still want it, what means do we have, does the engine permit it now, what command do we issue, what fact proves it happened, and what causes us to stop caring?”**

That is the community-native bridge between strategic reasoning and the actual rule engine. Everything else is decoration until that chain is traceable.
