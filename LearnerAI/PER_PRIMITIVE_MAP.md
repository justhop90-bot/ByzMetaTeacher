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

This is the canonical Production/Military example. It teaches that a defensive unit requirement is not “train N units once.” The real lifecycle is threat interpretation → persistent requirement → unit availability → production feasibility → queued/trained state → force-state witness → reassessment.

### Demand

Information identifies a relevant cavalry threat. Military translates that observation into a minimum defensive requirement.

Conceptually:

```
cavalry threat observed
→ defensive requirement = required Spearman-line count
```

The requirement is strategic intent, not a train command.

For example:

```
required Spearman-line count = 4
current Spearman-line count < required count
cavalry-defense posture remains active
```

The exact threshold is strategy-dependent. The important lesson is that the threat creates a persistent demand, while Production owns the mechanics of satisfying it.

### Admissibility

The demand remains admissible while the underlying military reason exists. Examples include relevant enemy cavalry remaining observed, the defensive posture not being cancelled, and the minimum defensive requirement not already being satisfied.

Do not confuse “enemy cavalry exists” with “train Spearman immediately.” Information supplies evidence; Military/Strategy determines the requirement.

### Capability: unit availability

First establish that the requested unit or unit line is available to the civilization and its current tech-tree state.

```
(unit-available spearman-line)
```

This is a capability/prerequisite question. It does not prove that a Barracks exists, that the unit can be trained now, that resources are available to this demand, or that the unit is already trained.

For a learner script:

```
unit-available
    ≠
can-train
```

### Production infrastructure

The Production domain must also have an appropriate production building and usable production capacity. For Spearmen this normally means a Barracks capable of training the requested unit line.

Distinguish:
- the unit is available to the civ;
- the required production building exists;
- the production building can train the unit;
- relevant production capacity is usable;
- the economy can support the training.

Do not collapse “we have a Barracks” into “we can train a Spearman.”

### Resource arbitration and escrow

Training competes with villagers, upgrades, buildings, farms, and other military units.

```
resource exists
    ≠
resource is available to this demand
    ≠
training can start
```

If escrow is used, the resource reservation belongs to Economy/resource arbitration. It does not prove that a Spearman was trained.

AIRef exposes both can-train and can-train-with-escrow forms. The distinction mirrors the Castle lesson: ordinary feasibility and escrow-aware feasibility are separate engine questions. citeturn0search0

### Feasibility: can-train

The engine-native production feasibility test is:

```
(can-train spearman-line)
```

AIRef defines can-train as checking whether training of the requested unit can start. citeturn0search0

Keep these questions separate:

| Question | Primitive/concept |
|---|---|
| Is the unit available to the civ/tech state? | `unit-available spearman-line` |
| Can training start under normal resources? | `can-train spearman-line` |
| Can training start using escrow-aware resources? | `can-train-with-escrow spearman-line` |
| Has the unit actually trained? | `unit-type-count spearman-line` |
| Has the unit trained or entered the queue? | `unit-type-count-total spearman-line` |

### Repeat prevention: queued versus trained

This is the production equivalent of Castle pending construction.

The important state distinction is:

```
REQUIRED
  ↓
TRAIN REQUESTED
  ↓
QUEUED / TRAINING
  ↓
TRAINED
```

unit-type-count counts trained units. unit-type-count-total includes trained and queued units. AIRef documents this distinction, and UserPatch notes confirm that total/pending counting includes queued training. citeturn0search0turn0search3

Therefore a production threshold should normally use the total count when its purpose is: “Do not queue more units once the required force is already trained or queued.”

Example:

```
(unit-type-count-total spearman-line < required-count)
(can-train spearman-line)
=>
(train spearman-line)
```

This prevents the classic loop:

```
4 Spearmen required
→ 0 trained
→ train
→ still 0 trained because the unit is queued
→ train again
→ duplicate queueing
```

AIRef community examples use the same pattern: a total unit-count threshold is paired with can-train before issuing train. citeturn0search1

### Action

Once the demand remains admissible and training is feasible:

```
(train spearman-line)
```

This is an action request. It is not proof that the unit immediately exists on the map. The action can result in queued/training state before the trained-unit witness changes.

### World-state witness

There are two legitimate witnesses, depending on what the domain is trying to prove.

For production progress / force reservation:

```
(unit-type-count-total spearman-line >= required-count)
```

This proves that the required number is either trained or queued.

For actual fielded military strength:

```
(unit-type-count spearman-line >= required-count)
```

This proves that the required number of units actually exists as trained units.

That distinction is critical. Production can use unit-type-count-total to prevent over-queueing, while Military readiness should use unit-type-count when it needs actual fielded strength.

### Completion versus release

Completion of the current production target is not necessarily release of the defensive posture.

```
COMPLETION OF CURRENT PRODUCTION TARGET
    ≠
RELEASE OF DEFENSIVE POSTURE
```

The threat may still exist after the initial requirement is trained. The correct loop is:

```
threat observed
→ defensive requirement established
→ production target satisfied
→ military remains vigilant
→ threat changes
→ requirement reassessed
→ new production demand may be created
```

Release belongs to the demand, not automatically to the production action. A later threat increase can raise the target; a threat disappearance can make the requirement obsolete.

### Reassessment

Military should reassess the world state after production changes: enemy cavalry count can increase, friendly Spearman-line count can fall because units die, the opponent can transition away from cavalry, or another counter can become preferable.

This is why the example must not become a one-shot “train four Spearmen and forget about it” script. The persistent strategic demand is stable; the numerical production target is the current execution requirement.

### Canonical defensive Spearman trace

```
OBSERVE
  relevant cavalry threat exists
        ↓
INTERPRET
  cavalry threat is strategically relevant
        ↓
DEMAND
  minimum Spearman-line requirement established
        ↓
ADMISSIBILITY
  defensive posture remains active
        ↓
CAPABILITY
  unit available
  + production infrastructure
  + economic support
        ↓
RESOURCE ARBITRATION
  resources are available to this demand
        ↓
FEASIBILITY
  can-train spearman-line
        ↓
ACTION
  train spearman-line
        ↓
EXECUTION STATE
  queued / training
        ↓
WORLD-STATE WITNESS
  unit-type-count-total reaches target
        ↓
CURRENT PRODUCTION TARGET SATISFIED
        ↓
MILITARY REASSESSMENT
  actual trained force and enemy threat are observed
        ↓
RELEASE / CONTINUE / ESCALATE
  demand may clear, persist, or increase
```

### Hard invariants

- unit-available is not can-train.
- can-train is not train.
- train is not proof of a trained unit.
- resources in the bank are not automatically resources available to this demand.
- escrow is resource arbitration, not a military witness.
- unit-type-count is not unit-type-count-total.
- queued units are not fielded units.
- satisfying a production target is not necessarily release of the defensive posture.
- a persistent threat can generate a new demand after the previous production target was satisfied.
- Military readiness should use actual world state when fielded strength matters.
- Production should use queued-aware thresholds when the objective is to prevent over-queueing.
- Production executes the current requirement; Strategy/Military owns why that requirement exists.

---
## 22. Canonical lifecycle: Fletching

This is the canonical Research example. It teaches that a technology has its own lifecycle: **strategic demand → tech availability/prerequisites → affordability → research feasibility → queued/researching state → completed research witness → release/reassessment**. A research command is an action, not proof that the technology already exists.

### Demand

Strategy or the relevant domain establishes that Fletching is currently useful or required.

Conceptually:

```
ranged-combat posture active
→ Fletching is an admissible technology demand
```

The demand is persistent intent. It is not the same thing as issuing `(research ri-fletching)`.

### Admissibility

The research demand remains valid while the strategic reason remains valid.

Examples:
- ranged units are part of the current military/economic plan;
- the technology has not already been completed;
- Strategy has not cancelled or superseded the upgrade;
- the technology remains relevant to the current posture.

Do not let the existence of a Blacksmith turn every available technology into an automatic research demand. Availability is not strategic justification.

### Capability: technology availability and prerequisites

First establish that Fletching is actually available to the civilization and current tech-tree state.

Conceptually:

```
(research-available ri-fletching)
```

The exact research-availability primitive should be verified against the target engine build/reference set before being used as executable `.per`; the learner must not invent a predicate merely because the semantic concept exists.

At the capability level, distinguish:
- technology is available to the civ/age/tech tree;
- required Blacksmith/infrastructure exists;
- prerequisite technologies/buildings are satisfied;
- technology has not already completed;
- the technology is not already in research/pending state.

Capability means **the technology could be researched under the relevant prerequisites**. It does not mean research can start this instant.

### Affordability

Resource affordability is a separate question.

Conceptually:

```
(can-afford-research ri-fletching)
```

If the target engine exposes a dedicated affordability predicate, use that engine-native predicate. If it does not, do not fabricate one: resource predicates and the actual `can-research` predicate must be treated according to the supported command set.

The semantic distinction remains:

```
technology is available
    ≠
technology is affordable
    ≠
technology is feasible now
```

Fletching can be available in the tech tree while its food/gold cost is unavailable to the current economic posture.

### Resource arbitration and escrow

Research competes with villagers, buildings, units, farms, and other technologies.

```
resource exists
    ≠
resource is available to Fletching
    ≠
research can start
```

If escrow/resource reservation is used, it belongs to Economy/resource arbitration. It does not prove that Fletching completed.

Where an escrow-aware research feasibility primitive exists, distinguish it explicitly from ordinary research feasibility. Do not silently equate “resources are reserved” with “technology is researched.”

### Feasibility: `can-research`

The engine-native feasibility stage is:

```
(can-research ri-fletching)
```

Teach this as the engine's current answer to **“Can the research action start now?”**

Keep the stages separate:

| Question | Primitive/concept |
|---|---|
| Is Fletching available in the current tech-tree state? | research availability / tech-tree state |
| Are its normal resources affordable? | research affordability / resource state |
| Can the engine start the research now? | `can-research ri-fletching` |
| Has research been requested or entered pending state? | research action / pending research state |
| Has Fletching actually completed? | research-completion state |

Do not replace `can-research` with a hand-built test of food, gold, age, and Blacksmith count. Those facts explain prerequisites and economic state; `can-research` is the engine-native feasibility test.

### Research state and repeat prevention

Research has a state transition just like construction and production:

```
DEMANDED
  ↓
RESEARCH REQUESTED
  ↓
PENDING / RESEARCHING
  ↓
COMPLETED
```

The learner must distinguish **not completed** from **not started**.

If the completion witness remains false while Fletching is already pending, a naive rule can repeatedly issue the research action. The research rule therefore needs an explicit research-state guard or an engine-supported research-status predicate where available.

Where the engine exposes a research-status primitive, use it to distinguish pending/researching from completed. AIRef's UserPatch documentation includes `up-research-status`, which can be used for this kind of state inspection. citeturn0search3

Do not use a retry counter as a substitute for knowing whether research is already pending.

### Action

Once the demand remains admissible and research is feasible:

```
(research ri-fletching)
```

This is an **action request**.

It does not prove that:
- Fletching started;
- resources were successfully committed;
- the research is currently progressing;
- Fletching completed.

The next observable state must come from the engine's research state, not from the fact that the rule fired.

### Completion witness

The completion witness must prove **technology completion**, not merely affordability, availability, action issuance, or pending research.

Conceptually:

```
research-status == COMPLETED
```

or the engine-native completed-technology fact supported by the target build/reference set.

Do not teach a generic “research command succeeded” boolean. The witness must come from world/engine state showing that Fletching is actually researched.

If a research-status primitive distinguishes pending from completed, then:

```
PENDING / RESEARCHING
    ≠
COMPLETED
```

is the key teaching point.

### Completion versus release

Research completion and demand release are related but distinct.

```
Fletching completion
    ≠
automatic strategic release
```

Normally:

```
Fletching demand active
→ research completes
→ completion witness becomes true
→ Fletching demand releases or transitions
→ Strategy reassesses the new technology state
```

However, release can also occur before completion if Strategy explicitly cancels or supersedes the demand.

Therefore distinguish:
- **COMPLETED:** Fletching is actually researched;
- **CANCELLED/OBSOLETE:** Strategy no longer wants it;
- **BLOCKED:** Strategy still wants it but research cannot currently proceed;
- **ACTIVE/PENDING:** Strategy still wants it and research is unresolved or in progress.

Never clear the demand merely because `(research ri-fletching)` fired.

### Blocked behavior

If `can-research ri-fletching` remains false while the demand remains admissible, preserve the demand and diagnose the blocking layer:

1. Is the technology actually available to the current civ/age/tech tree?
2. Are the required Blacksmith and prerequisites satisfied?
3. Is the research already pending?
4. Are the required resources unavailable or reserved for another demand?
5. Is another research or engine state preventing the action?
6. Has Strategy actually cancelled or superseded the demand?

`can-research` is the immediate engine feasibility result. The other facts explain the strategic, prerequisite, resource, or pending state around that result.

Do not turn a persistent technology demand into a permanent retry counter. Preserve intent, use transient cooldown/backoff where appropriate, and reassess the actual blocking state.

### Canonical Fletching trace

```
DEMAND
  Strategy wants Fletching
        ↓
ADMISSIBILITY
  ranged-combat posture remains active
        ↓
CAPABILITY
  technology available
  + Blacksmith/prerequisites
        ↓
AFFORDABILITY / RESOURCE ARBITRATION
  required resources are available to this demand
        ↓
FEASIBILITY
  can-research ri-fletching
        ↓
ACTION
  research ri-fletching
        ↓
RESEARCH STATE
  pending / researching
        ↓
WORLD-STATE WITNESS
  completed research state is true
        ↓
COMPLETION
  Fletching actually researched
        ↓
RELEASE
  Fletching demand clears/transitions
        ↓
REASSESS
  Strategy and Military react to the new technology state
```

### Hard invariants

- technology availability is not affordability.
- affordability is not feasibility.
- `can-research` is not `research`.
- `research` is not proof of completion.
- pending/researching is not completed.
- resource escrow is arbitration, not a technology witness.
- a Blacksmith existing is not proof that Fletching can start now.
- a technology completion witness must come from actual research state.
- completion is not automatically identical to strategic release.
- cancellation/obsolescence is not successful completion.
- a persistent Fletching demand survives temporary blockage unless Strategy explicitly removes it.
- do not invent an engine predicate simply because a semantic concept would be convenient; verify the exact command/status primitive against AIRef and the target engine build.

---
## 23. Canonical lifecycle: economic upgrade

Use an economic technology such as Wheelbarrow as the canonical upgrade example. This teaches the same lifecycle as Fletching, but the strategic reason is economic: **economic demand → research availability → affordability → research feasibility → pending state → completion witness → release/reassessment**.

Do not teach an economic upgrade as “we have food and gold, so research it.” The engine has separate facts for availability, affordability, feasibility, and completion. Human beings apparently require several nouns to prevent one technology button from becoming a theology.

### Demand

Economy/Strategy establishes that the upgrade is currently justified by the economic posture.

Conceptually:

```
economic posture requires improved villager efficiency
→ Wheelbarrow demand is active
```

A demand can be represented semantically by a goal or equivalent domain state. The representation is project-specific; the important fact is that the demand persists independently of the research action.

### Admissibility

The economic upgrade remains admissible while its strategic/economic reason remains valid.

Examples:
- the economy still benefits from the upgrade;
- the upgrade has not already completed;
- Strategy has not cancelled or superseded the economic plan;
- the current age/posture still makes the upgrade appropriate.

Availability of the technology is not admissibility. A technology can be available while Strategy deliberately postpones it because food, gold, builders, military production, or another economic priority has precedence.

### Capability: `research-available`

First establish whether the technology is actually available to the civilization and current game state.

```
(research-available ri-wheelbarrow)
```

AIRef defines `research-available` as checking that the research is available to the civilization and available at the current time. citeturn0search1

This is the **availability/prerequisite** question. It does not prove that the upgrade is affordable, that research can start immediately, or that the upgrade has completed.

Keep the semantic layers distinct:

```
research-available
    ≠
can-afford-research
    ≠
can-research
    ≠
research-completed
```

### Capability: prerequisites and infrastructure

Availability is the engine-level answer to the technology's current tech-tree eligibility. The learner may still need to understand the world-state prerequisites that explain the result, such as age, required building, or prerequisite research.

Do not replace `research-available` with a homemade list of prerequisites and assume the list is equivalent to engine behavior. Use documented engine facts as the authority and use prerequisite facts for diagnosis or strategic reasoning.

Likewise, the existence of a Mill, Market, or other economic building is not itself proof that Wheelbarrow can be researched.

### Affordability: `can-afford-research`

Resource affordability is a separate engine question.

```
(can-afford-research ri-wheelbarrow)
```

AIRef documents `can-afford-research` as checking whether the computer player has enough resources to perform the given research. citeturn0search1

This answers **“Can the normal research cost be paid?”**

It does not prove:
- the technology is available;
- the research can start under the current engine state;
- resources will remain available until the action is evaluated;
- the research will complete.

The distinction is therefore:

```
technology available
    ≠
technology affordable
    ≠
technology feasible now
```

### Resource arbitration and escrow

Economic upgrades compete directly with other economic demands. Food and gold can be needed simultaneously for villagers, age advancement, military, buildings, and additional technologies.

Therefore:

```
resource exists
    ≠
resource is available to the upgrade
    ≠
research can start
```

If the AI uses escrow, escrow represents resource commitment/arbitration. It is not an upgrade-completion witness.

AIRef also documents `can-research-with-escrow`, which checks whether research can start when escrowed resources are included. citeturn0search1

Use the distinction deliberately:

- `can-research` = ordinary current-resource feasibility;
- `can-research-with-escrow` = feasibility when the relevant escrowed resources are included.

Do not silently substitute one for the other. The economic policy must decide whether escrowed resources are legitimately available to this demand.

### Feasibility: `can-research`

The decisive engine-native feasibility test is:

```
(can-research ri-wheelbarrow)
```

AIRef defines `can-research` as checking whether the given research can start. citeturn0search1

Teach this as the boundary between **economic intent** and **engine execution**.

Do not write a homemade predicate such as:

```
food >= cost
gold >= cost
age = feudal
has required building
→ therefore research is possible
```

Those conditions may describe pieces of capability or explain a blockage, but `can-research` is the engine-native feasibility answer.

### Pending state and repeat prevention

Research has an execution state:

```
DEMANDED
  ↓
RESEARCH REQUESTED
  ↓
PENDING / RESEARCHING
  ↓
COMPLETED
```

The learner must distinguish **not completed** from **not started**.

`up-research-status` provides an explicit research-state inspection mechanism. UserPatch defines research states including `research-unavailable`, `research-available`, `research-pending`, and `research-complete`. citeturn0search0

Conceptually:

```
(up-research-status c:>= ri-wheelbarrow research-pending)
```

Use the exact comparison syntax appropriate to the target engine/reference set. The important semantic rule is that a pending upgrade must block another identical research request.

Without a pending guard, this failure is possible:

```
Wheelbarrow incomplete
→ research wheelbarrow
→ research still pending
→ completion witness still false
→ research wheelbarrow again
→ duplicate research requests
```

Repeat prevention is therefore a state problem, not a retry-counter problem.

### Action

Once the demand is admissible, the technology is available, resources are legitimately available, and the engine says research can start:

```
(research ri-wheelbarrow)
```

This is an **action request**.

It does not prove that:
- the research entered the queue;
- resources were successfully committed;
- the upgrade is progressing;
- Wheelbarrow completed.

The action must be followed by an engine/world-state witness.

### Completion witness: `research-completed`

The canonical completion witness is:

```
(research-completed ri-wheelbarrow)
```

AIRef defines `research-completed` as checking that the given research is completed. citeturn0search1

This is materially stronger than `research-available`, `can-afford-research`, or the fact that the `research` action fired.

The learner should therefore keep this invariant:

```
research action
    ≠
pending research
    ≠
completed research
```

`up-research-status` can also expose the completed state when the script needs a more general research-state interface. Use one authoritative completion witness rather than maintaining a second homemade completion flag.

### Completion versus release

Completion and release are related but distinct.

```
Wheelbarrow completed
    ≠
automatic release of every economic-upgrade demand
```

The normal successful path is:

```
economic upgrade demand active
→ research completes
→ research-completed witness is true
→ current upgrade demand releases/transitions
→ Economy/Strategy reassesses
```

Release may also occur before completion if Strategy explicitly cancels or supersedes the demand.

Distinguish:
- **COMPLETED:** the upgrade is actually researched;
- **CANCELLED/OBSOLETE:** Strategy no longer wants it;
- **BLOCKED:** Strategy still wants it but research cannot currently proceed;
- **ACTIVE/PENDING:** Strategy still wants it and research is unresolved or in progress.

Never clear the economic demand merely because `(research ri-wheelbarrow)` fired.

### Reassessment

After completion, Economy/Strategy must reassess the new economic state.

Examples:
- the upgrade improves the current gathering plan;
- another economic upgrade becomes admissible;
- military demand now has different resource requirements;
- the economic posture changes because the game state changed;
- the upgrade becomes strategically irrelevant before completion.

The upgrade demand is therefore a lifecycle, not a one-shot button press.

### Blocked behavior

If `can-research ri-wheelbarrow` remains false while the demand is still admissible, retain the demand and diagnose the layer that is actually blocking progress:

1. Is `research-available` false?
2. Is the upgrade already pending?
3. Is it already completed?
4. Is `can-afford-research` false?
5. Are the required resources reserved for another legitimate demand?
6. Is escrow-aware feasibility intentionally different from ordinary feasibility?
7. Is another research or engine state preventing the action?
8. Has Strategy cancelled or superseded the economic demand?

`can-research` is the immediate engine feasibility result. The surrounding facts explain availability, affordability, arbitration, pending state, or strategic cancellation.

Do not convert a persistent economic demand into an infinite retry counter. Preserve the demand, use transient cooldown/backoff where appropriate, and reassess the real blocking state.

### Canonical economic-upgrade trace

```
DEMAND
  Strategy/Economy wants Wheelbarrow
        ↓
ADMISSIBILITY
  economic posture still justifies the upgrade
        ↓
CAPABILITY
  research-available
  + required tech-tree prerequisites
        ↓
AFFORDABILITY
  can-afford-research
        ↓
RESOURCE ARBITRATION
  resources are legitimately available to this demand
        ↓
FEASIBILITY
  can-research ri-wheelbarrow
        ↓
ACTION
  research ri-wheelbarrow
        ↓
RESEARCH STATE
  pending / researching
        ↓
WORLD-STATE WITNESS
  research-completed ri-wheelbarrow
        ↓
COMPLETION
  Wheelbarrow actually researched
        ↓
RELEASE
  current upgrade demand clears/transitions
        ↓
REASSESS
  Economy/Strategy react to the new technology state
```

### Hard invariants

- `research-available` is not `can-afford-research`.
- `can-afford-research` is not `can-research`.
- `can-research` is not `research`.
- `research` is not proof of completion.
- pending/researching is not completed.
- escrow is resource arbitration, not a completion witness.
- `can-research-with-escrow` is not interchangeable with ordinary `can-research`.
- a prerequisite/building fact is not a substitute for the engine's research-availability or feasibility facts.
- `research-completed` is the completion witness, not the research action.
- repeat prevention must account for pending research.
- completion is not automatically identical to strategic release.
- cancellation/obsolescence is not successful completion.
- a persistent economic-upgrade demand survives temporary blockage unless Strategy explicitly removes it.
- do not invent engine predicates where a documented availability, affordability, feasibility, status, or completion primitive already exists.

---
## 24. Canonical lifecycle: military production

Use a Knight-line production demand as the canonical Military/Production example. It makes the capability-versus-feasibility distinction concrete while also teaching **availability, affordability, production capacity, queue state, repeat prevention, completion witnesses, and strategic release**.

AIRef defines `unit-available` as checking unit availability and tech-tree prerequisites, `can-afford-unit` as resource affordability, `can-train` as whether training can start, and `unit-type-count-total` as including queued units. citeturn0search0

### Demand

Military/Strategy establishes that a cavalry force is currently required.

```
enemy composition or strategic posture justifies Knights
→ required Knight-line count = target
```

The target is persistent military intent. It is not a command to train a fixed number once.

For example:

```
required Knight-line count = 4
current Knight-line count < required count
cavalry production posture remains active
```

The target may later increase, decrease, or disappear as the battlefield changes.

### Admissibility

The production demand remains admissible while the military reason exists.

Examples:
- the current strategy still calls for the Knight line;
- the opponent or strategic posture still justifies cavalry;
- the required force has not been made obsolete;
- the target has not already been satisfied;
- Strategy has not cancelled or superseded the cavalry plan.

Do not let `unit-available` become the strategy. A Knight can be available while Military deliberately chooses not to produce one.

### Capability: `unit-available`

First establish whether the requested unit is available to the civilization and current tech-tree state.

```
(unit-available knight-line)
```

AIRef defines `unit-available` as checking that the unit is available to the civ and that its tech-tree prerequisites for training are met. citeturn0search0

This answers:

**“Could this civilization train this unit under the current technology-tree state?”**

It does not prove that the unit is affordable, that the production building has usable capacity, that training can start now, or that the unit is already trained.

Keep the distinction explicit:

```
unit-available
    ≠
can-afford-unit
    ≠
can-train
```

### Production infrastructure and capacity

Capability also includes the production infrastructure required to execute the demand.

For a Knight line this normally means the appropriate stable production infrastructure exists and is usable.

Distinguish:
- the unit is available to the civ;
- the production building exists;
- the building is capable of training the requested unit line;
- the production queue/capacity permits another training action;
- the economic policy is willing to spend the required resources.

A Stable existing is not proof that a Knight can train immediately. Production infrastructure is capability; `can-train` is engine-level feasibility.

### Affordability: `can-afford-unit`

Resource affordability is a separate question.

```
(can-afford-unit knight-line)
```

AIRef defines `can-afford-unit` as checking whether the computer player has enough resources to train the given unit. citeturn0search0

This answers:

**“Can the normal Knight-line cost be paid?”**

It does not prove that the unit is available, that a production slot is usable, that the engine will accept the training request now, or that the unit will complete.

Therefore:

```
unit available
    ≠
unit affordable
    ≠
unit trainable right now
```

### Resource arbitration and escrow

Military production competes with villagers, buildings, upgrades, farms, age advancement, and other military units.

```
resource exists
    ≠
resource is available to Knights
    ≠
Knight training can start
```

If escrow is used, it is resource arbitration, not a military completion witness.

AIRef documents `can-train-with-escrow` as the escrow-aware counterpart to `can-train`. citeturn0search0turn0search1

Keep the two meanings separate:

- `can-train` = ordinary current-resource feasibility;
- `can-train-with-escrow` = feasibility when escrowed resources are included.

Do not use escrow as evidence that a Knight exists. Escrow proves only that resources are being treated as committed/available under the chosen arbitration model.

### Feasibility: `can-train`

The decisive engine-native production test is:

```
(can-train knight-line)
```

AIRef defines `can-train` as checking that training of the given unit can start. citeturn0search0

This is the boundary between the Military demand and engine execution.

Do not replace it with a homemade conjunction of resource amounts and building counts:

```
food >= cost
gold >= cost
stable exists
→ therefore train Knight
```

Those facts can explain capability and resource state. `can-train` is the engine-native feasibility result.

### Pending state and repeat prevention

Military production has a state transition:

```
DEMANDED
  ↓
TRAIN REQUESTED
  ↓
QUEUED / TRAINING
  ↓
TRAINED
```

`unit-type-count` counts trained units. `unit-type-count-total` includes queued units. AIRef documents that the total form includes queued training, and UserPatch notes explicitly describe total/pending unit counting behavior. citeturn0search0turn0search1

`up-pending-objects` can provide an explicit pending-object check when the script needs finer control over pending production. It should not be confused with the completed-unit witness.

For a force target, the normal anti-repeat pattern is:

```
(unit-type-count-total knight-line < required-count)
(can-train knight-line)
=>
(train knight-line)
```

This prevents the classic failure:

```
target = 4
trained = 0
→ train Knight
→ Knight remains queued
→ trained = 0
→ naive rule fires again
→ queue fills before the strategy notices
```

Repeat prevention is therefore a world-state/queue-state problem, not a retry-counter problem.

UserPatch also documents configurable training queues and notes that queue behavior affects `can-train` and `train`. citeturn0search1

### Action

Once the demand is admissible, the unit is available, resources are legitimately available, and `can-train` is true:

```
(train knight-line)
```

This is an **action request**.

It does not prove that the Knight exists on the map. It does not prove that training completed, and it should not be used as the completion witness.

### Completion witnesses

There are two different useful witnesses.

For **production-target accounting / anti-repeat control**:

```
(unit-type-count-total knight-line >= required-count)
```

This proves that the target number is either trained or queued.

For **actual military strength**:

```
(unit-type-count knight-line >= required-count)
```

This proves that the target number of units is actually trained.

Therefore:

```
queued Knight
    ≠
fielded Knight
```

Production may use the total count to avoid over-queueing. Military readiness, attack composition, or a commitment requiring actual units should use the trained-unit witness.

### Completion versus release

Satisfying the current production target is not automatically release of the military posture.

```
production target satisfied
    ≠
cavalry strategy released
```

The correct successful lifecycle is:

```
Knight demand active
→ required target reached
→ completion/target witness true
→ current production demand may release
→ Military reassesses the battlefield
```

Release can also occur before the target is reached if Strategy explicitly cancels or supersedes the demand.

Distinguish:
- **COMPLETED:** the current production target is actually satisfied;
- **CANCELLED/OBSOLETE:** Strategy no longer wants the cavalry target;
- **BLOCKED:** Strategy still wants it but training cannot currently proceed;
- **ACTIVE/PENDING:** Strategy still wants it and the production requirement remains unresolved.

A cavalry posture can therefore remain active after four Knights exist, because four may only have been the current minimum target.

### Reassessment

Military must reassess after production changes.

Examples:
- enemy composition changes;
- Knights die and actual trained count falls;
- the target is increased because more cavalry is required;
- another counter becomes preferable;
- the opponent reaches defenses that make further Knights strategically unnecessary;
- the economy can no longer sustain the current target without violating higher-priority demands.

The production rule executes the current target. It does not own the strategic reason for that target.

### Blocked behavior

If `can-train knight-line` remains false while the demand is still admissible, preserve the demand and diagnose the actual layer:

1. Is `unit-available knight-line` false?
2. Is the production infrastructure missing?
3. Is the production capacity/queue occupied?
4. Is `can-afford-unit knight-line` false?
5. Are resources reserved for another legitimate demand?
6. Is escrow-aware feasibility intentionally different?
7. Is the unit already pending and therefore protected by the repeat guard?
8. Is another production rule consuming the available capacity or resources?
9. Has Strategy cancelled or superseded the demand?

`can-train` is the immediate engine feasibility result. The surrounding facts explain capability, affordability, arbitration, pending state, or strategic cancellation.

Do not solve a blocked military demand by incrementing a permanent retry counter. Preserve the demand, use transient cooldown/backoff when needed, and reassess the actual blocker.

### Canonical military-production trace

```
OBSERVE / INTERPRET
  battlefield and strategic posture justify cavalry
        ↓
DEMAND
  required Knight-line target established
        ↓
ADMISSIBILITY
  cavalry posture remains active
        ↓
CAPABILITY
  unit-available
  + production infrastructure
        ↓
AFFORDABILITY
  can-afford-unit
        ↓
RESOURCE ARBITRATION
  resources legitimately available to the demand
        ↓
FEASIBILITY
  can-train knight-line
        ↓
ACTION
  train knight-line
        ↓
EXECUTION STATE
  queued / training
        ↓
COMPLETION / TARGET WITNESS
  unit-type-count-total reaches target
        ↓
MILITARY READINESS WITNESS
  unit-type-count reaches required fielded strength
        ↓
RELEASE / CONTINUE / ESCALATE
  production demand clears, persists, or target increases
        ↓
REASSESS
  Military/Strategy react to the new battlefield state
```

### Hard invariants

- `unit-available` is not `can-afford-unit`.
- `can-afford-unit` is not `can-train`.
- `can-train` is not `train`.
- `train` is not proof of a trained unit.
- production infrastructure is capability, not feasibility.
- resource escrow is arbitration, not a military witness.
- `can-train-with-escrow` is not interchangeable with ordinary `can-train`.
- `unit-type-count` is not `unit-type-count-total`.
- queued units are not fielded units.
- pending production must be accounted for when preventing repeated training requests.
- satisfying a production target is not necessarily release of the military posture.
- cancellation/obsolescence is not successful completion.
- a persistent military demand survives temporary blockage unless Strategy explicitly removes it.
- Production executes the current target; Military/Strategy owns why the target exists.
- documented engine facts should be preferred over homemade approximations of availability, affordability, or feasibility.

---
## 25. Pending versus completed

Pending state is one of the most important distinctions in practical `.per` scripting because an engine action can succeed as a request without the requested world-state object existing yet.

Use the following as a semantic teaching ladder, not as a claim that `.per` contains one universal state machine:

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
WORLD-STATE WITNESS
  ↓
RELEASE / REASSESS
```

Different action classes expose different engine facts for these states. Construction, training, and research must therefore be taught with their actual primitives rather than a fabricated universal `pending` or `completed` predicate.

### 25.1 Demand is not pending state

A persistent demand means Strategy or a domain still wants something.

```
Castle target remains wanted
    ≠
Castle foundation exists

Knight target remains wanted
    ≠
Knight is queued

Wheelbarrow remains wanted
    ≠
Wheelbarrow research is pending
```

Demand can survive a temporary inability to act. Pending state means the engine has already accepted some form of execution and the world is now in an intermediate state.

Do not store a demand merely because an action is pending. The demand is strategic intent; pending state is execution state.

### 25.2 Action requested is not pending

An action command is a request to the engine.

Examples:

```
(train knight)
(build castle)
(research ri-wheelbarrow)
```

The action firing does not itself prove that the requested object is queued, under construction, researching, or complete.

This is the critical rule:

```
ACTION
  ≠
EXECUTION STATE
  ≠
COMPLETION
```

The script must use an actual engine/world-state fact when the distinction matters.

### 25.3 Construction: foundation versus completed building

Construction is the clearest example.

A build request can lead to a foundation or under-construction object before the building is complete.

For repeat prevention, the script may need a total-count or pending-object witness so that another identical build request is not issued while the first one is already underway.

For completion, use a completed-building witness appropriate to the primitive being taught. Do not treat a total object count as equivalent to a completed building.

Conceptually:

```
(build castle)
    ↓
foundation / construction pending
    ↓
castle completed
    ↓
completed Castle witness
```

The important distinction is:

```
building-type-count-total
    ≠
completed building count
```

The total form is useful for accounting for an object that is already underway. A completion witness must prove the state the strategy actually cares about.

### 25.4 Training: queued versus trained

Military production has the same problem in a different form.

```
(train knight)
    ↓
queued / training
    ↓
trained Knight
```

`unit-type-count-total` can be used for target accounting because queued units count toward the production target. `unit-type-count` represents trained units.

Therefore:

```
unit-type-count-total
    ≠
unit-type-count
```

Use the total form when preventing over-queueing. Use the trained count when the strategy requires actual fielded strength.

A queue is not an army. Humanity has somehow managed to need this sentence written down.

### 25.5 Research: pending versus completed

Research has the same lifecycle.

```
(research ri-wheelbarrow)
    ↓
research pending / researching
    ↓
research completed
```

AIRef exposes explicit research-state information through `up-research-status`, with distinct states for unavailable, available, pending, and complete. AIRef also exposes `research-completed` as a completion fact.

That makes research an especially useful teaching example because it demonstrates that:

```
research available
    ≠
research can start
    ≠
research pending
    ≠
research completed
```

The exact comparison syntax should follow the target engine/reference set. Do not invent a generic research-state abstraction when the engine already provides the state information.

### 25.6 Pending state is primarily repeat protection and execution awareness

Pending state has two practical jobs.

First, it prevents duplicate requests:

```
target not satisfied
+
already pending
→
do not request another copy
```

Second, it lets the script distinguish "the engine is already working on this" from "nothing has happened yet."

This is why pending state is usually more useful than a retry counter. A retry counter remembers that the script tried something. Pending state observes whether the engine is actually carrying out the requested work.

Do not create permanent counters merely to represent state that the engine already exposes.

### 25.7 Pending does not guarantee completion

A pending object can remain pending because of construction time, production time, queue position, or other engine behavior. A script must not clear a strategic demand merely because an action entered an intermediate state.

The safe sequence is:

```
DEMAND
→ ACTION
→ PENDING
→ COMPLETION WITNESS
→ RELEASE / REASSESS
```

If the demand remains strategically valid while the object is pending, the demand remains alive.

### 25.8 Completion witness must match the claim

A witness proves a particular world-state claim.

Examples:

```
"Knight is queued"
    → unit-type-count-total

"Knight is actually trained"
    → unit-type-count

"Castle exists as a completed building"
    → completed-building witness

"Wheelbarrow is researched"
    → research-completed
```

Do not substitute a weaker state for a stronger claim.

```
action fired
    ≠
pending
    ≠
completed
```

Likewise, do not use "available" as proof of completion. A technology can be available before it is researched. A unit can be available before it is trained. A building type can be available before one exists.

### 25.9 Release conditions

Completion and release are related but not identical.

A demand may release because:

- its actual completion condition is satisfied;
- Strategy cancelled it;
- Strategy replaced it with another target;
- the strategic reason became obsolete.

A pending state is not a release condition by itself.

Likewise, completion of one object does not necessarily release an entire strategic posture.

```
current target complete
    ≠
strategic posture obsolete
```

For example, four Knights can satisfy the current production target while the cavalry posture remains active and later raises the target to eight.

### 25.10 Blocked versus pending

These states must also remain separate.

```
PENDING:
engine has accepted work and it is underway

BLOCKED:
demand remains valid but the action cannot currently proceed
```

A blocked demand should normally persist until the strategic reason disappears or the blocker is resolved.

Do not convert blockage into fake pending state merely because the script attempted the action.

### 25.11 Canonical state traces

Construction:

```
DEMAND
→ can-build / placement / resource feasibility
→ build
→ FOUNDATION / CONSTRUCTION
→ COMPLETED BUILDING WITNESS
→ RELEASE / REASSESS
```

Training:

```
DEMAND
→ can-train
→ train
→ QUEUED / TRAINING
→ TRAINED UNIT WITNESS
→ RELEASE / REASSESS
```

Research:

```
DEMAND
→ can-research
→ research
→ PENDING / RESEARCHING
→ research-completed
→ RELEASE / REASSESS
```

The common teaching pattern is therefore:

```
persistent intent
→ engine feasibility
→ action
→ engine/world execution state
→ actual completion witness
→ semantic release
→ reassessment
```

The implementation does **not** require a universal state registry, scheduler, retry manager, or object-oriented state machine.

### 25.12 Hard invariants

- Demand is not pending state.
- Action request is not proof of execution.
- Pending is not completion.
- Foundation is not completed construction.
- Queued is not trained.
- Available is not completed.
- A pending witness is not a completion witness.
- A completion witness must prove the specific world-state claim being made.
- Pending state is useful for repeat prevention and execution awareness.
- Prefer engine-provided pending/queue/state facts over homemade retry counters.
- Blocked is not pending.
- Completion of a current target is not automatically release of the strategic posture.
- Cancellation/obsolescence is not successful completion.
- Different action classes require different engine-native state/completion predicates.
- The lifecycle is a teaching model for reasoning about `.per`; it is not a literal universal runtime object model.

---
## 26. Goals, strategic numbers, and timers: real community patterns

The learner should not treat every mutable `.per` value as the same kind of state. Community scripts use goals, strategic numbers, and timers for different jobs. The useful lesson is not to invent a cleaner software architecture around them. It is to recognize the engine primitive being used, understand what it controls, and keep its ownership narrow.

The practical teaching sequence is:

```
COMMUNITY PATTERN
→ ENGINE PRIMITIVES
→ MINIMAL VALID PATTERN
→ WHY IT WORKS
→ COMMON FAILURE
→ BASILISK-SCALE VARIANT
```

This section teaches the primitives through recognizable scripting jobs rather than through a generic state-management abstraction.

### 26.1 Goal: persistent semantic state or threshold

#### Community pattern

Community scripts commonly use goals as mutable state or thresholds that other rules consume. A typical economy pattern classifies the current resource situation, stores that interpretation in a goal, and then uses the goal to select engine behavior. Goals are also used for strategy modes, desired quantities, and other persistent choices.

The important point is that the goal is not the entire subsystem. It stores the piece of semantic state that needs to persist between rule evaluations.

#### Engine primitives

The basic forms are:

```
(set-goal goal-id value)
(goal goal-id value)
```

Related goal comparison or modification primitives may also be available depending on the target DE/AIRef reference set.

A goal answers:

**“What persistent integer state or threshold should other rules currently see?”**

It does not answer:

- whether an action is feasible;
- whether a requested object exists;
- whether an action succeeded;
- whether the strategic reason for the goal still exists.

#### Minimal valid pattern

```
(defrule
    (food-amount < 300)
=>
    (set-goal food-state 1)
)

(defrule
    (goal food-state 1)
=>
    (set-strategic-number sn-food-gatherer-percentage 50)
)
```

The first rule observes current state and stores an interpretation. The second rule consumes that persistent state.

The goal survives after the first rule fires. That is what makes it different from a one-shot action or a timer trigger.

#### Why it works

The goal separates repeated interpretation from repeated consumption.

Without a goal, several consumers may each duplicate the same threshold logic:

```
food-amount < 300
→ rule A

food-amount < 300
→ rule B

food-amount < 300
→ rule C
```

With a goal:

```
food-amount < 300
→ food-state = low
→ consumers react to food-state
```

That is useful when the interpreted state genuinely has multiple consumers or must persist independently of the rule that first derived it.

A goal is therefore a reasonable representation of persistent semantic intent or a mutable target. It is not automatically necessary just because a value needs to exist.

#### Common failure

The classic failure is turning goals into a universal database:

```
goal 1 = strategy
goal 2 = target
goal 3 = pending
goal 4 = timer
goal 5 = resource reservation
goal 6 = whether the last action succeeded
...
```

That creates a fake object model out of integers.

Another failure is treating a goal as a completion witness:

```
(set-goal castle-done 1)
```

does not prove that a Castle exists.

Likewise:

```
(goal knight-target 4)
```

does not prove that four Knights exist.

Goals represent stored or derived semantic state. World-state facts prove world state.

#### Basilisk-scale variant

Basilisk should use a goal when persistent semantic state genuinely needs to be shared or retained.

For example:

```
Strategy:
    desired Knight target = 4

Military:
    owns why Knights are currently wanted

Production:
    consumes the target

Production:
    unit-type-count-total knight-line < target
    can-train knight-line
    → train knight-line

Witness:
    actual Knight count
```

The goal can bridge strategic intent and execution. It does not replace `can-train`, pending state, resource arbitration, or the trained-unit witness.

### 26.2 Strategic number: engine-defined control

#### Community pattern

Community scripts commonly use strategic numbers to configure behavior already owned by the AI engine. Economy scripts use them for gatherer percentages, drop distances, camp distances, and similar controls. Other scripts use engine-defined strategic numbers for military or exploration behavior.

The critical distinction is that the strategic number already has an engine-defined meaning.

#### Engine primitives

The basic forms are:

```
(set-strategic-number sn-example value)
(strategic-number sn-example > value)
(strategic-number sn-example == value)
```

The exact valid strategic numbers and their effects come from the target engine/reference documentation.

A strategic number answers:

**“What engine control parameter should have this value?”**

It is not a general-purpose semantic database.

#### Minimal valid pattern

```
(defrule
    (goal food-state 1)
=>
    (set-strategic-number sn-food-gatherer-percentage 50)
)
```

The goal represents interpreted state.

The strategic number configures engine behavior.

That separation is the useful pattern.

#### Why it works

The script is using an existing engine control rather than attempting to recreate that control with custom state.

The flow is:

```
interpret state
→ configure engine
→ engine applies behavior
```

The script remains small because it lets the engine own the behavior it already knows how to perform.

This is one of the strongest community-native lessons for a learner: do not replace an engine parameter with a homemade manager merely because a manager feels more architectural.

#### Common failure

The failure is using strategic numbers as arbitrary storage:

```
sn-my-castle-demand = 1
sn-knight-target = 4
sn-last-build-result = 1
```

If a strategic number does not represent an engine-defined control, it is probably the wrong primitive for the job.

Another failure is assuming that setting a strategic number proves the resulting behavior occurred:

```
(set-strategic-number ...)
≠
world-state change
```

The script still needs to observe the actual resulting state.

#### Basilisk-scale variant

Basilisk should use strategic numbers only when the engine itself exposes the desired behavior through that control.

For example:

```
Strategy / Economy:
    determine that wood priority should increase

Economy:
    set the appropriate engine gatherer control

Engine:
    applies the control

State / Information:
    observe resulting resource state

Strategy:
    reassess
```

Strategy remains semantic. The strategic number remains an engine control.

### 26.3 Timer: temporal trigger or cooldown

#### Community pattern

Community scripts use timers to make periodic work happen without requiring the same action rule to fire continuously. Attack checks, scouting, economic rebalance, delayed transitions, and cooldowns are common uses.

The basic pattern is:

```
time passes
→ timer triggers
→ current state is evaluated
→ action or control change
→ timer is reset or scheduled again
```

The timer determines when a check occurs. It does not supply the strategic reason for the check.

#### Engine primitives

Typical timer primitives include:

```
(enable-timer timer-id duration)
(disable-timer timer-id)
(timer-triggered timer-id)
```

Exact argument conventions and behavior must be checked against the target DE/AIRef reference set before executable use.

#### Minimal valid pattern

A minimal temporal pattern is conceptually:

```
(defrule
    (timer-triggered military-check)
    (military-population >= 10)
=>
    (attack-now)
)
```

A separate initialization or reset rule enables the timer according to the desired interval.

The important point is that the timer is only one condition. Current military state still determines whether the action rule can fire.

#### Why it works

A timer prevents periodic work from becoming an every-evaluation action loop.

It is useful when the correct behavior is:

```
check periodically
→ evaluate current facts
→ act only if current conditions justify action
```

It is especially appropriate for scouting intervals, attack-group checks, economic rebalance, cooldowns, and delayed reassessment.

The important distinction is:

```
TIMER + CURRENT STATE
→ DECISION
```

not:

```
TIMER
→ PERMANENT DEMAND
```

#### Common failure

The classic failure is treating a timer as the demand itself:

```
timer expires
→ build Castle
```

Elapsed time does not prove that the Castle is still strategically wanted, that the economy is ready, or that the engine can build it.

Another failure is using timers as retry counters:

```
try
→ wait
→ try
→ wait
→ try
```

when the actual issue is a blocked feasibility condition or an obsolete demand.

The timer answers **when to look again**. It does not answer **why the action remains valid**.

#### Basilisk-scale variant

Basilisk should use timers for transient temporal control:

```
persistent strategic demand
        +
transient timer / cooldown
        ↓
current feasibility check
        ↓
engine action
        ↓
world-state witness
        ↓
release or reassessment
```

A military posture can persist because Strategy still wants pressure while a timer prevents attack-group reassessment from firing continuously.

If the timer expires after the strategic demand has disappeared, the action should not occur merely because the timer fired.

The ownership boundary is:

```
Strategy owns WHY.
Timer owns WHEN TO RECHECK.
Engine facts own WHAT IS POSSIBLE.
Action commands request WHAT TO DO.
World state proves WHAT HAPPENED.
```

### 26.4 Combined community pattern

The strongest lesson comes from combining the three primitives without pretending that they are interchangeable.

A representative community economy pattern can be understood as:

```
world resource state
        ↓
set-goal interpreted state
        ↓
timer-triggered reassessment
        ↓
set-strategic-number engine control
        ↓
engine changes behavior
        ↓
world state changes
        ↓
next reassessment
```

The three primitives have separate jobs:

| Primitive | Practical job |
|---|---|
| Goal | Preserve interpreted state or a mutable target |
| Strategic number | Configure an engine-defined behavior |
| Timer | Trigger evaluation after time has passed |
| World-state fact | Observe actual game state |
| `can-*` | Ask the engine whether an action is feasible |
| Action command | Request a state change |
| Completion witness | Prove that the requested result exists |

This is the important community standard: **small primitives with narrow jobs connected by ordinary rules**.

### 26.5 Basilisk-scale combined variant

At Basilisk scale, the same pattern maps onto the larger lifecycle:

```
OBSERVE
    current resource / threat / production state
        ↓
INTERPRET
    derive the strategic or domain meaning
        ↓
PERSISTENT DEMAND / TARGET
    retain intent when it genuinely needs persistence
        ↓
TRANSIENT CONTROL
    use timers for time
    use strategic numbers for engine controls
        ↓
CAPABILITY / FEASIBILITY
    evaluate current engine facts and can-* predicates
        ↓
ACTION
    build / train / research / other engine action
        ↓
WORLD-STATE WITNESS
    observe actual building / unit / technology / resource state
        ↓
RELEASE / REASSESS
```

This is not a requirement to create nine managers.

It is a set of ownership rules for ordinary `.per` primitives.

A simple community pattern should remain simple when the problem is simple:

```
(defrule
    (unit-type-count-total knight-line < target)
    (can-train knight-line)
=>
    (train knight-line)
)
```

If a persistent target is shared across several rules, a goal may be appropriate. If the engine exposes the desired behavior through a strategic number, use that strategic number. If evaluation genuinely needs to happen periodically, use a timer.

Do not add an abstraction merely because the semantic model contains a word for it.

### 26.6 Common architecture-theater failures

The learner should recognize these warning signs:

- A goal exists solely to remember something the world state already exposes.
- A strategic number is being used as arbitrary storage rather than an engine control.
- A timer is being used to preserve strategic intent.
- A timer is being used as a retry counter for a condition that should instead remain persistent.
- A custom state variable duplicates a `can-*` feasibility predicate.
- A completion flag duplicates an observable world-state witness.
- Every action receives a bespoke manager even though the engine already provides the required primitive.
- Several layers of indirection are required to express what could be a two- or three-condition community-standard rule.

The test is simple:

**What concrete engine behavior or scripting problem does this extra state solve?**

If there is no concrete answer, it is probably decoration.

### 26.7 Hard invariants

- A goal is persistent mutable semantic state or a threshold, not a universal database.
- A goal does not prove world-state completion.
- A strategic number is an engine/control parameter, not arbitrary storage.
- Changing a strategic number does not prove that the resulting behavior occurred.
- A timer is a temporal trigger or cooldown, not persistent strategic intent.
- Timer expiration does not make a demand valid.
- World-state facts observe reality; goals represent interpreted or stored semantic state.
- `can-*` predicates provide engine feasibility; they do not decide strategy.
- Action commands request changes; they are not completion witnesses.
- Multiple primitives may participate in one lifecycle while retaining separate jobs.
- The smallest valid community pattern is preferred when it already solves the problem.
- Basilisk-scale complexity should come from real strategic interactions, resource arbitration, pending state, and reassessment, not from wrapping simple `.per` operations in unnecessary abstractions.
- The semantic lifecycle remains a teaching model mapped onto ordinary engine primitives, not a literal runtime object architecture.

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

## 27. Real community production and economy patterns

The learner should now see how ordinary community scripts connect persistent targets, engine feasibility, production, construction, and economic control without inventing a second scripting language.

The recurring community pattern is:

    WORLD STATE → TARGET / DEMAND → ENGINE PREREQUISITES → can-* FEASIBILITY → ACTION → WORLD-STATE WITNESS → RELEASE / REASSESS

The important lesson is not that every rule must contain every stage. Simple behaviors can legitimately be simple. The engineering requirement is that the omitted stages are either irrelevant or represented elsewhere and still traceable.

### 27.1 Villager production

#### Community pattern

A basic villager-production rule is intentionally small:

    (defrule
        (unit-type-count-total villager < target)
        (can-train villager)
    =>
        (train villager)
    )

This is a normal community pattern because the production building, age, and other engine prerequisites are largely represented by the engine's can-train predicate.

The count expresses the strategic production target. can-train expresses current engine feasibility. train villager is the action.

#### Why it works

The target prevents unlimited production. can-train prevents the rule from blindly requesting an impossible transaction. The resulting loop is current villager count → target still unmet → can-train → train → villager count changes → reassess.

A learner should not add a custom villager-production manager merely to wrap those predicates.

#### Common failure

The dangerous version is simply can-train villager → train villager. That converts engine capability into an unlimited production policy.

The opposite mistake is building a large state machine for a simple fixed target when the engine already exposes the required production feasibility.

### 27.2 Military production

#### Community pattern

Military production follows the same shape: desired unit composition + current unit count + can-train / can-train-with-escrow → train.

A minimal example is:

    (defrule
        (unit-type-count-total skirmisher-line < target)
        (can-train skirmisher-line)
    =>
        (train skirmisher-line)
    )

For more contested economies, can-train-with-escrow may be appropriate when the script deliberately reserves or arbitrates resources for the transaction.

The strategic layer determines the target. Production owns the production request. The engine owns the feasibility predicate.

#### Pending and queue state

A production rule must distinguish not enough units exist from nothing is currently queued. A target of 10 does not necessarily mean the script should issue ten commands in rapid succession. If the production system or engine exposes queue/pending state appropriate to the transaction, that state must participate in repeat protection.

The conceptual distinction is: TARGET 10 ≠ TRAIN 10 NOW. It means keep production moving until the observed target is satisfied while respecting queue capacity and current resource arbitration.

#### Common failure

Do not use the action count as the completion count. train skirmisher-line is not evidence that the target population increased. The world state must eventually show the resulting unit population.

### 27.3 Infrastructure production and construction

#### Community pattern

Community economy scripts frequently construct required infrastructure using a small combination of count, pending-state, and feasibility predicates:

    building absent / below target
    + no appropriate pending construction
    + can-build
    → build

A representative pattern is:

    (defrule
        (building-type-count-total lumber-camp < target)
        (up-pending-objects c: lumber-camp < pending-limit)
        (can-build lumber-camp)
    =>
        (build lumber-camp)
    )

The exact pending-object filter and arguments must be verified against the target DE/AIRef reference before executable use. The teaching point is ownership of each predicate, not memorizing one filter spelling.

#### Why it works

building-type-count-total answers the world-state question. up-pending-objects answers the execution-state question. can-build answers the engine-feasibility question. build requests the construction.

This is why a completed count alone can be insufficient for a persistent rule. A construction foundation may exist before the completed-building count changes.

#### Common failure

The classic construction spam loop is count < target + can-build → build with no pending protection. If the rule remains eligible while the first building is under construction, it may issue another request before the completion witness changes.

The fix is not a generic scheduler. The fix is to model the actual construction state that matters.

### 27.4 Economy balancing

#### Community pattern

Community economy scripts often separate resource observation from engine gatherer controls. The recurring pattern is resource state → interpreted economic state → goal / threshold → strategic-number control → engine changes gatherer behavior → resource state changes → reassess.

A simplified teaching example is:

    (defrule
        (food-amount < food-threshold)
    =>
        (set-goal economy-food-critical 1)
    )

followed by a control rule that changes an engine-defined gatherer setting:

    (defrule
        (goal economy-food-critical 1)
    =>
        (set-strategic-number sn-food-gatherer-percentage food-priority)
    )

The exact strategic-number and value must be selected from the target engine's documented semantics. Do not treat arbitrary strategic numbers as a general-purpose variable store.

#### Why it works

The resource amount is observation. The goal is interpreted/persistent economic state. The strategic number is the engine-facing control. The engine changes gatherer behavior. Later resource observations provide feedback.

#### Common failure

Do not write resource shortage → set-strategic-number → assume the crisis is solved. The command only requests a control change. The learner must still observe the resulting economic state.

Do not make every economic decision a timer-driven retry loop. A persistent economic condition should remain represented while it is true; a timer can control when reassessment occurs.

### 27.5 Production and economy are coupled, but not the same module

Real community scripts naturally couple economy and production:

    economy determines resource pressure
        ↓
    production demand competes for resources
        ↓
    resource arbitration affects feasibility
        ↓
    production action
        ↓
    world state changes
        ↓
    economy reassesses

That does not mean Economy owns military production or Production owns resource policy.

A useful ownership boundary is:

    Economy: what resource posture is required?
    Strategy: what production target matters?
    Production: what transaction should be requested?
    Engine: can the transaction happen now?
    World state: did the transaction actually produce the expected result?

### 27.6 Basilisk-scale production loop

At Basilisk scale, the simple community pattern becomes:

    STRATEGY → persistent production demand
        ↓
    PRODUCTION → target / composition / infrastructure requirement
        ↓
    ECONOMY → resource posture and arbitration
        ↓
    CAPABILITY → building / age / technology / queue state
        ↓
    FEASIBILITY → can-train / can-build / can-research
        ↓
    ACTION → train / build / research
        ↓
    WORLD-STATE WITNESS → actual unit / building / technology state
        ↓
    RELEASE OR REASSESS

The production target should survive temporary resource blockage unless Strategy has made the demand obsolete. A blocked can-train condition is therefore not automatically a reason to clear the demand.

Likewise, a successful action is not automatically a reason to clear the demand if the target remains unmet.

The practical distinction is:

    DEMAND = what remains wanted
    PENDING = what is already in execution
    COMPLETION = what the world proves
    RELEASE = why we stop pursuing it

Those are different facts.

### 27.7 Hard invariants

- A production target is not an action count.
- can-train and can-build are feasibility predicates, not strategic demands.
- A queued or pending action is not the same as a completed world-state result.
- A completed count is not the same as a pending count.
- Resource availability alone does not establish full engine feasibility.
- Persistent production demand should survive temporary resource blockage when the strategic objective remains valid.
- Queue/pending protection must prevent repeated requests when the same demand is already represented in execution state.
- Economy controls resource posture; Production controls production transactions.
- Strategy determines why a target matters; domain modules determine how to pursue it.
- The simplest community pattern that correctly represents the required state is preferable to an abstraction that hides ordinary .per behavior.
## 28. Research and technology: community patterns

Research rules should stay close to the engine primitives that already represent research availability, feasibility, pending state, and completion. Community scripts commonly use `can-research` or `can-research-with-escrow` followed by `research`, while larger upgrade systems add goals, technology categories, escrow release, and research-status checks. The strategic complexity belongs around the transaction, not inside a replacement research engine.

### 28.1 Civilization-specific research: unique technologies and conditional availability

#### Community pattern

Civilization-specific technologies should be treated as ordinary research transactions with civilization-specific admissibility.

The useful distinction is:

```
civilization-specific eligibility
+
strategic demand
+
generic research feasibility
→ research
```

A unique technology being available does not make it automatically desirable. Civilization identity determines what is possible. Strategy determines what is wanted.

Community-style research systems therefore benefit from keeping special technology selection separate from the generic execution rule. A civilization-specific rule can identify when a unique technology enters the admissible set, while the ordinary research machinery handles availability, feasibility, pending state, action, and completion.

#### Engine primitives

The generic research layer uses:

```
(research-available technology)
(can-afford-research technology)
(can-research technology)
(can-research-with-escrow technology)
(research technology)
(research-completed technology)
(up-research-status ...)
```

Civilization-specific conditions should sit around those primitives rather than replacing them.

Conceptually:

```
civilization-specific condition
+
strategic condition
+
research availability
+
research feasibility
→ research
```

If the engine already exposes the civilization or technology restriction through its research predicates, the script should use that engine fact rather than reconstructing the restriction manually.

#### Minimal valid pattern

The generic executor can remain simple:

```
(defrule
    (can-research ri-example-tech)
=>
    (research ri-example-tech)
)
```

A civilization-specific rule can supply the additional admissibility:

```
(defrule
    (goal civ-techs 1)
    (research-available ri-example-tech)
    (can-research ri-example-tech)
=>
    (research ri-example-tech)
)
```

The important point is that `civ-techs` expresses strategic or civilization-specific admissibility. It does not replace `can-research`.

#### Why it works

This keeps generic research logic reusable.

The generic research layer answers:

**Can this technology be researched now?**

The civilization-specific layer answers:

**Is this technology part of this civilization's available and strategically relevant technology set?**

The resulting chain is:

```
civilization knowledge
→ strategic admissibility
→ generic research feasibility
→ research action
→ completion witness
```

That separation makes failures easier to diagnose. If a unique technology is never researched, the learner can inspect independently whether it was available, whether the civilization-specific rule made it admissible, whether the strategic demand existed, whether `can-research` became true, whether `research` fired, and whether completion was witnessed.

#### Common failure

Do not put every civilization exception into the generic research executor:

```
generic conditions
+
Byzantine exception
+
another civilization exception
+
another technology exception
→ research
```

That eventually turns generic research into a collection of civilization-specific exceptions.

Do not manually duplicate engine availability when the engine already provides it. For example, adding every possible age, building, prerequisite, and civilization test around a `can-research` predicate can create a second, potentially inconsistent feasibility system.

Do not confuse unique with desirable. A unique technology can be available without being the current strategic priority.

Do not use `research-available` as the completion witness. Availability is not completion.

#### Basilisk-scale variant

Basilisk should keep civilization-specific research in a thin admissibility layer above generic research execution:

```
CIVILIZATION KNOWLEDGE
    identify unique or conditional technologies
            ↓
STRATEGIC ADMISSIBILITY
    decide whether the technology is wanted now
            ↓
GENERIC RESEARCH EXECUTION
    availability
    pending state
    resource arbitration
    can-research / can-research-with-escrow
            ↓
ACTION
    research technology
            ↓
WORLD-STATE WITNESS
    research-completed / verified research status
            ↓
RELEASE / REASSESS
```

For Basilisk, Byzantine-specific technology rules should identify special demand, timing, or admissibility conditions. They should not duplicate generic research feasibility, escrow semantics, pending-state handling, completion witnesses, or release semantics.

The ownership boundary is:

```
Civilization layer: WHAT IS SPECIAL?
Strategy: WHY NOW?
Economy: CAN RESOURCES BE COMMITTED?
Research: HOW IS THE TRANSACTION REQUESTED?
Engine: CAN IT HAPPEN?
World state: DID IT HAPPEN?
```

The hard invariant is:

**Civilization identity changes what can be relevant or available. It does not change what a research action, feasibility predicate, pending state, or completion witness means.**

---

## 29. Anti-pattern catalogue

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

## 30. Community-standard trace template

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

## 31. Verification checklist for future executable lessons

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

## 32. The learner's one-line mental model

When reading any serious .per behavior, translate it mentally as:

**“What do we want, why do we still want it, what means do we have, does the engine permit it now, what command do we issue, what fact proves it happened, and what causes us to stop caring?”**

That is the community-native bridge between strategic reasoning and the actual rule engine. Everything else is decoration until that chain is traceable.
