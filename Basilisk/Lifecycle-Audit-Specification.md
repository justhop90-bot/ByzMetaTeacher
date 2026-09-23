# Basilisk Lifecycle Audit Specification

Status: Project-standard specification  
Scope: Basilisk/Basilisk.per and its supporting .per modules  
Baseline reviewed: main at 17ccb30651482e318cd82841f5d392a668ae673e  
Purpose: define the minimum semantic contract for auditing Basilisk lifecycles before code is accepted as complete.

## 1. Why this specification exists

A Basilisk rule is not correct because it parses, looks clean, or eventually executes an engine command. A lifecycle is correct only when strategic intent survives long enough to reach the engine, execution failure does not accidentally erase that intent, the requested world-state change is independently observed, and the system returns control to reassessment.

The canonical lifecycle is:

~~~text
OBSERVATION
    ->
INTERPRETATION
    ->
STATE
    ->
DEMAND
    ->
PACKAGE
    ->
CAPABILITY
    ->
CLAIM
    ->
FEASIBILITY
    ->
ACTION
    ->
WORLD-STATE CHANGE
    ->
COMPLETION or INVALIDATION
    ->
REASSESSMENT
~~~

Not every action requires a package, a claim, or a dedicated goal. Those are semantic roles, not mandatory data structures. What is mandatory is that the audit can explain the same edge with concrete writers, readers, predicates, engine actions, completion evidence, ownership, and recovery behavior.

The project standard is deliberately community-native. We use the language the AoE2 AI engine actually exposes: goals, strategic numbers, facts, can-* predicates, unit-type-count-total, building-type-count, up-pending-objects, timers, escrow, research status, and engine actions. We do not add an abstract scheduler merely to make the diagram prettier. Humans have already done that to enough codebases.

## 2. Evidence standard

Three evidence classes are used together.

### 2.1 AIRef / engine-reference evidence

AIRef is the primary reference for command names, parameters, strategic numbers, object and technology vocabulary, and the documented AI scripting surface. It is a language reference, not a runtime proof system.

Reference: https://airef.github.io/

### 2.2 Community-script evidence

Community scripts and scripting discussions are behavioral evidence for patterns that have survived actual engine use. They establish practical idioms such as goal-backed targets, can-train or can-build feasibility gates before actions, queue-aware unit-type-count-total production caps, timer-driven attack cycles, and explicit engine reset/re-entry patterns.

Useful references:

- AoE2 AI Scripting Encyclopedia: https://airef.github.io/
- Age of Empires Forum, creating simple AI scripts: https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881
- Age of Empires Forum, attack/timer scripting: https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476
- Niek's public AI collection: https://github.com/niektb/AI
- Eruner's AoE2 AI scripting collection: https://github.com/Eruner/Age-Of-Empires-AI-Scripts

The community standard is not "copy the oldest script." Old scripts are evidence of solved engine problems. The audit must determine which problem the pattern solves and whether Basilisk has the same problem.

### 2.3 Runtime evidence

Replay/game behavior is the final judge. Static code can prove structure and intended connectivity. It cannot prove that the engine actually builds the foundation, trains the unit, researches the technology, releases the claim, forms the attack group, or returns to the intended state under real timing pressure.

Therefore:

~~~text
PARSER CLEAN != LIFECYCLE CLOSED
LIFECYCLE CLOSED != STRATEGICALLY CORRECT
STRATEGICALLY CORRECT != RUNTIME PROVEN
~~~

A runtime observation that contradicts a static interpretation wins the argument and triggers source tracing.

## 3. Roles that must remain separate

The following roles are semantic responsibilities. A single defrule may participate in more than one physical role, but ownership must remain explicit.

### Demand

Demand is persistent strategic intent.

It answers:

> What does Basilisk currently require to make its chosen policy viable?

Demand is written by strategic/meta logic and consumed by package, capability, production, research, or execution logic.

Demand must:

- have a real upstream cause;
- be initialized to a known neutral value;
- have an identified semantic owner;
- survive temporary execution failure;
- be cleared only when its strategic purpose disappears or its finite package is truly complete;
- have at least one live downstream consumer.

Temporary shortage, a failed can-* predicate, a missing builder, a construction delay, or a retry cooldown are not automatically valid reasons to erase demand.

Failure statuses:
DEAD-END, UNFED, FUNCTIONALLY-DISCONNECTED.

### Package

A package is an ordered strategic execution path when one technology, prerequisite, or unit follows another.

Examples include:

~~~text
Crossbow demand
    ->
Crossbow package
    ->
University / Archery Range prerequisites
    ->
Crossbow research
    ->
Crossbow mass
~~~

and:

~~~text
Ram pressure demand
    ->
Capped Ram
    ->
Siege Ram
~~~

Package state must be downstream of strategic intent. A package may select the next necessary step, but package/reliability logic must not invent a replacement strategy merely because the current action failed.

Every package stage must have:

1. an entry condition;
2. exactly one intended successor or a documented terminal state;
3. a completion witness;
4. a strategic invalidation path.

A package is not complete because an action rule fired. It is complete because the world satisfies the package's completion predicate.

### Capability

Capability establishes what must exist before execution is possible.

Typical capability edges are:

~~~text
standing unit demand -> Barracks / Range / Stable
siege demand -> Siege Workshop
university research -> University
Castle technology -> Castle
research package -> required prerequisite technology
~~~

Capability must distinguish:

- required;
- completed;
- pending/foundation;
- unavailable.

can-build, can-train, and can-research are feasibility predicates. They are not completion witnesses.

For construction, the audit normally distinguishes:

~~~text
completed provider count
+
pending foundation/object guard
~~~

so repeated rules do not spam duplicate foundations.

For training, current and queued production are different facts. unit-type-count-total is appropriate when queued production must satisfy the target cap; unit-type-count is appropriate when the audit needs completed units as the witness.

### Claim

A claim is transient execution ownership.

It answers:

> Which subsystem currently owns the right to spend the shared execution/resource lane on this action?

A claim must have:

- one semantic owner;
- acquisition conditions;
- an identifiable release path;
- a completion release;
- a failure release;
- provider-loss cleanup where the provider is destroyed or absent.

Basilisk currently uses sn-resource-control as a shared execution mutex in several lifecycles. A new claim must not silently introduce a competing ownership model.

A claim is not demand. Keeping a claim latched because demand remains live is a stale-state defect.

### Feasibility

Feasibility is the final gate before an engine action.

Separate, where applicable:

1. strategic feasibility: should we still do this?
2. capability feasibility: does the required provider/prerequisite exist or have a valid path?
3. resource feasibility: can the intended spend occur without violating higher-priority reservations?
4. engine feasibility: does the appropriate can-* predicate currently permit the action?

The last gate before an engine command should be engine-native when such a predicate exists.

### Action

An action is the actual engine instruction:

~~~text
build
train
research
attack-now
up-reset-attack-now
~~~

Every action must have an identifiable upstream cause, a valid capability, applicable ownership, final feasibility, and a separate completion/recovery story.

An engine action firing is not proof of success.

### Completion

Completion is a world-state witness.

Examples:

- research: up-research-status ... == research-complete;
- building capability: completed building-type-count or equivalent actual provider witness;
- military package: completed unit-type-count;
- queued-production cap: unit-type-count-total;
- attack assembly: attack-soldier-count or another explicit package witness;
- age transition: current-age >= ....

Completion must release the claim it owns, advance or clear the package as appropriate, and clear demand only when the semantic contract says the strategic requirement is finished.

Do not use intention, stockpile, can-*, queued objects, or an action counter as a substitute for a world-state completion witness.

### Invalidation

Invalidation means the strategic owner no longer wants the action.

Examples:

- enemy threat disappears;
- strategy changes;
- finite response package has completed;
- attack state ends and the associated pressure is no longer valid;
- the required strategic purpose has explicitly been superseded.

Invalidation is not ordinary execution failure.

These normally belong to retry/feasibility, not demand invalidation:

- temporary resource shortage;
- temporary global resource mutex contention;
- builders unavailable;
- a provider is still under construction;
- a transient can-* failure;
- a prior attempt failed and requires a fairness cooldown.

### Retry

Retry is execution reliability, not strategic policy.

The Basilisk doctrine is:

~~~text
persistent demand
    +
bounded local cooldown
    ->
re-open feasibility
    ->
retry
~~~

A retry mechanism must:

- leave persistent demand intact during temporary failure;
- release the claim on failure;
- avoid selecting a replacement technology or strategy;
- use bounded cooldown/backoff;
- remain local to the failed capability/action;
- reopen the same action when the cooldown expires;
- reset local retry state only on the correct strategic reset.

Do not use a finite terminal retry budget for an inherently persistent strategic demand unless the package itself has a semantically finite terminal condition.

A cooldown is not a retry budget.

~~~text
COOLDOWN = delay before another attempt
RETRY HISTORY = evidence about repeated execution failure
TERMINAL EXHAUSTION = only valid when the semantic package actually has a terminal failure state
~~~

The project has intentionally moved away from terminal retry ladders for persistent construction and research demand. Any reintroduction requires explicit justification and a finite semantic package.

## 4. Ownership matrix

The default ownership contract is:

| Role | Owner | Must not do |
|---|---|---|
| Observation | Scout / observation state | Select final action directly without policy |
| Interpretation | Strategic/meta layer | Hide raw engine failure state |
| Demand | META | Act as a transient claim |
| Package | META | Choose a replacement strategy because execution failed |
| Capability | Capability subsystem | Invent strategic policy |
| Claim / watchdog / cooldown | RELIABILITY | Clear strategic demand merely because an attempt failed |
| Engine action | EXECUTION | Invent new strategic state |
| Completion | Completion logic | Pretend action success without world evidence |
| Invalidation | Strategic owner | Be used as generic failure cleanup |
| Reassessment | META | Depend on stale claims or stale providers |

The key prohibited shortcuts are:

~~~text
reliability -> replacement strategy
capability -> strategic policy
action -> implied completion
failure -> strategic invalidation
completion -> invented demand
~~~

Cleanup may clear state owned by the same lifecycle only when that cleanup is part of the documented contract. One subsystem must not silently clear another subsystem's semantic state.

## 5. Audit record

Every audited lifecycle is recorded using the following fields.

~~~text
Signal / Goal:
Semantic Owner:
Initialization Writer:
Activation Writers:
Activation Conditions:
Package State:
Package Owner:
Required Capability:
Capability Writers:
Capability Completion Witness:
Claim:
Claim Owner:
Claim Acquisition Conditions:
Feasibility Predicate:
Engine Action:
Action Owner:
World-State Completion Witness:
Completion Writer:
Strategic Invalidation Conditions:
Execution Failure Conditions:
Retry State:
Retry Timer / Cooldown:
Retry Exhaustion Policy:
Capability-Loss Behavior:
Readers:
Downstream Consumers:
Source-Order Dependencies:
Queue / Pending Semantics:
Escrow / Reservation Semantics:
Reassessment Edge:
Final Status:
~~~

Every field does not need a bespoke variable. The point is to make the contract explicit enough that the auditor can trace it without guessing.

## 6. Status vocabulary

Use exactly these status meanings.

- VALID: complete lifecycle; all required edges and witnesses are present and coherent.
- CONNECTED: structural edge exists and is semantically live, but the lifecycle may still need deeper review.
- DEAD-END: state is written but has no live downstream effect.
- UNFED: consumer expects a state that no active writer can establish.
- BLOCKED: valid downstream path exists but a condition or missing capability prevents entry.
- FUNCTIONALLY-DISCONNECTED: syntax connects the symbols, but the predicates make the consumer effectively unreachable under intended play.
- OPEN-LOOP: action or execution path has no reliable completion/recovery return.
- UNFINISHED: package or lifecycle stops before a terminal/completion state.
- DUPLICATE-CONFLICTING: multiple semantic writers can fight without an explicit priority contract.
- STALE: state survives after its owning world-state or transaction has ended.
- WRONG-WITNESS: completion uses evidence that does not prove the requested behavior actually occurred.
- OWNERSHIP-VIOLATION: the wrong subsystem creates, mutates, or clears semantic state.
- FALSE-TIMING: lifecycle assumes same-pass visibility when the required world-state change is necessarily observed on a later pass.
- RESOURCE-UNSAFE: action can cannibalize a higher-priority reservation, bank, or protected spend.

## 7. Source-order audit

AoE2 rules are evaluated in source order within the engine's pass semantics. Source order is therefore part of the program whenever multiple writers touch the same mutable state.

Classify each state:

### SAFE-PERSISTENT

The value is established and remains until an explicit owner changes it. Source order does not alter policy.

### SAFE-DERIVED

The value is recomputed from current world facts in a way that is order-independent or deliberately rebuilt before consumers.

### ONE-PASS-LATENCY

A writer changes state that a consumer will observe on a later pass. This is acceptable only when the latency is intended and harmless.

### ORDER-SENSITIVE

The final value depends on rule ordering. This is allowed only when the ordering is the policy and is documented.

### UNSAFE-FORWARD-DEPENDENCY

A consumer assumes a writer has already run in the same pass or assumes a value has already been cleared/initialized when source order does not guarantee that. This is a defect.

A common legal pattern is the priority writer chain:

~~~lisp
(defrule
    (goal resource-mode-goal 0)
    (<highest-priority predicate>)
=>
    (set-goal resource-mode-goal <high>)
)

(defrule
    (goal resource-mode-goal 0)
    (<next-priority predicate>)
=>
    (set-goal resource-mode-goal <next>)
)
~~~

This is a source-order priority table, not an abstract multi-writer state machine.

For such chains the audit requires:

1. neutral initialization;
2. highest priority first;
3. each later writer guarded on the neutral value;
4. exactly one selected terminal value per pass;
5. no unrelated cleanup reopening the neutral value mid-chain;
6. consumers placed after the writers when same-pass consumption is required.

Do not "clean up" a deliberate priority chain into several unconstrained writers. That would remove policy while making the file look more sophisticated. Humanity has enough elegant regressions already.

## 8. Queue and pending semantics

The audit must identify whether each target means:

~~~text
actual completed objects
queued + completed objects
pending construction foundation
~~~

Use the witness appropriate to the question.

For production targets:

~~~text
desired - actual - queued
~~~

is the normal production-capacity concept when queued objects satisfy the strategic target.

For construction:

~~~text
required - completed - pending
~~~

is the normal duplicate-prevention concept.

For finite completion:

~~~text
actual completed >= terminal target
~~~

must be used when the package is not complete until the objects actually exist.

Do not substitute unit-type-count-total for a completion witness when the queued unit has not yet become part of the fighting army.

## 9. Resource and escrow semantics

Three resource concepts must remain separate.

### Strategic reservation

A protected bank required by the chosen policy.

Examples include age-up commitments, protected military reserves, or explicit high-priority technology banks.

### Engine escrow

The engine mechanism used to reserve/spend resources as part of a specific action.

### Current stockpile

What the player currently has in raw resources.

The audit must verify:

~~~text
spendable = stockpile - protected commitment
~~~

where the project actually uses commitment accounting.

A can-* predicate is the final engine feasibility gate, not proof that the action is strategically affordable after higher-priority reservations.

Any bank-safe exception must have a concrete cost/commitment witness. "It seemed safe" is not a resource policy.

On failure:

- release the execution claim;
- preserve strategic demand unless strategically invalid;
- preserve the strategic bank unless the policy explicitly cancels it;
- begin the local cooldown/backoff if required.

## 10. Capability-loss cleanup

When a provider disappears, stale downstream state must not survive.

Examples:

- Barracks loss must not leave live Barracks research claims;
- Range loss must not leave ranged research package state that assumes the provider exists;
- Stable loss must not leave Stable claims;
- Siege Workshop loss must clear Workshop-owned siege capability state;
- University loss must clear University research claims/package state;
- Castle loss must clear Castle-dependent claims/package state;
- TC or camp loss must clear provider-specific research claims.

Capability-loss cleanup clears execution state owned by the missing capability. It must not silently rewrite strategic policy into a different strategy.

This distinction is critical:

~~~text
provider loss -> invalidate the capability edge
provider loss !-> invent a new strategic demand
~~~

## 11. Research lifecycle contract

The minimum research lifecycle is:

~~~text
strategic demand
    ->
package selection
    ->
provider capability
    ->
research claim
    ->
can-research-with-escrow
    ->
research
    ->
research-complete
    ->
claim release
    ->
package advance/clear
    ->
demand clear only if strategic purpose is complete
    ->
reassessment
~~~

Research failure must return to the same strategic owner. Reliability code may set a backoff/failure-history state, but it must not choose the next technology.

This keeps the division:

~~~text
META selects technology/package.
RELIABILITY determines when the same attempt may be retried.
COMPLETION proves the technology exists.
~~~

For ordered chains such as Chemistry -> Onager or Capped Ram -> Siege Ram, the package owns the successor relation. A failed Chemistry attempt does not get to rewrite the strategy into "perhaps we should research Thumb Ring instead." That would be a very creative bug.

## 12. Construction lifecycle contract

The minimum construction lifecycle is:

~~~text
persistent capability demand
    ->
provider requirement
    ->
claim
    ->
pending-foundation check
    ->
can-build-with-escrow
    ->
build
    ->
completed provider witness
    ->
claim release
    ->
watchdog/backoff reset
    ->
downstream consumer becomes feasible
~~~

The watchdog has two legitimate outcomes.

### Foundation exists

Keep ownership alive, renew/assign builders as required, and wait for the actual provider completion witness.

### No foundation exists

Treat this as an execution failure:

- release the claim;
- do not erase persistent demand;
- record bounded backoff/failure state;
- retry later.

A terminal retry ladder is not the default for persistent capability demand.

## 13. Military production contract

Military production is audited as two separate problems.

### Standing force

Persistent role floors such as Spear/Pike, Skirmisher/Elite Skirmisher, Archer, Knight, Camel, or later heavy branches.

### Attack package

A temporary subset of the standing army assembled for a specific engagement.

Therefore:

~~~text
standing target != attack group
~~~

and:

~~~text
production target = strategic need - actual - queued - applicable pending state
~~~

The current Basilisk architecture intentionally separates unit-goal composition from standing role targets. The audit must preserve that distinction unless code evidence proves the split is functionally wrong.

Attack readiness must use a package witness appropriate to the attack system. Basilisk currently uses attack-soldier-count >= 10 as the minimum assembly witness. That witness proves an attack package exists. It does not, by itself, prove strategic victory, favorable combat quality, or safe engagement.

## 14. Attack / retreat lifecycle

The minimum attack cycle is:

~~~text
attack demand / attack timer
    ->
strategic eligibility
    ->
army readiness
    ->
attack-goal active
    ->
attack-now
    ->
attack package witness
    ->
engine control/reset
    ->
attack cycle ends
    ->
reassessment
~~~

If the minimum package does not assemble before the watchdog expires, the cycle must recover without permanently latching attack state.

Retreat is a strategic interruption:

~~~text
bad battlefield state
    ->
set retreat state
    ->
reset attack engine state
    ->
recall / retreat
    ->
release attack cycle
    ->
reassess
~~~

The system must not continue issuing attack-now commands while retreat ownership is active.

## 15. Audit procedure

For each lifecycle, audit in this order.

### Pass A: upstream tracing

Start from the action or consumer and walk backward:

~~~text
ACTION
<- FEASIBILITY
<- CLAIM
<- CAPABILITY
<- PACKAGE
<- DEMAND
<- STATE
<- OBSERVATION
~~~

At every edge ask:

- Who writes this state?
- Under exactly what conditions?
- Is the state initialized?
- Can another writer overwrite it?
- Can it become impossible to reach?
- Does it persist long enough to be consumed?

### Pass B: downstream tracing

Start at the demand/state and walk forward:

~~~text
DEMAND
-> PACKAGE
-> CAPABILITY
-> CLAIM
-> FEASIBILITY
-> ACTION
-> COMPLETION
-> REASSESSMENT
~~~

Ask:

- Is every downstream consumer live?
- Does can-* lead to an actual action?
- Does the action have a world-state witness?
- Does completion release the correct state?
- Does failure return without erasing the strategic intent?
- Does provider loss clean up stale execution state?

### Pass C: source-order review

For every mutable state with multiple writers:

- locate all writers;
- classify each writer as priority, initialization, activation, cleanup, completion, or invalidation;
- determine whether source order is policy or accidental;
- test for same-pass forward dependencies;
- check whether a later writer can reopen a state the earlier writer intentionally closed.

### Pass D: resource review

For every action involving resources:

- identify protected commitments;
- identify engine escrow;
- identify current stockpile;
- prove that the action cannot silently consume a higher-priority bank;
- prove claim release on failure and completion.

### Pass E: runtime review

Confirm the static contract with the game:

- does the action happen?
- does the world-state witness change?
- does the next consumer become eligible?
- does the state clear or advance?
- does the lifecycle repeat correctly?
- does temporary failure leave demand alive?
- does the same policy recover after cooldown?
- does a strategic change actually invalidate the old package?

## 16. Minimum acceptance test

A lifecycle is not accepted until an auditor can answer all of these without guessing.

1. What observation or strategic condition creates the demand?
2. Who owns the demand?
3. What initializes it?
4. What package consumes it, if any?
5. What capability must exist?
6. Who establishes that capability?
7. What proves the capability completed?
8. Who owns the execution claim?
9. What is the exact claim acquisition condition?
10. What is the final engine feasibility predicate?
11. What engine action is issued?
12. What world-state witness proves success?
13. What clears/releases the claim?
14. What constitutes temporary execution failure?
15. Does temporary failure preserve demand?
16. What timer/backoff allows a retry?
17. What conditions genuinely invalidate the strategy?
18. What happens if the provider disappears?
19. Which rules write the same state, and is source order intentional?
20. What exact reassessment edge returns control to the strategic layer?

If the answer to any item is "another rule probably handles it," the lifecycle remains open.

## 17. Parser, lifecycle, and runtime division of labor

The project deliberately separates three audit layers.

### Parser / static language layer

Responsible for:

- syntax;
- parentheses;
- rule structure;
- command arity;
- identifier/constant validity;
- command vocabulary;
- logical-operator arity;
- package/load/include structure;
- source-level line-length and other repository hygiene checks.

### Lifecycle layer

Responsible for:

- writer/reader connectivity;
- ownership;
- persistence;
- demand/package/capability/claim closure;
- action-to-completion closure;
- invalidation semantics;
- retry semantics;
- source-order interactions;
- queue/pending interpretation;
- resource reservation correctness.

### Runtime layer

Responsible for:

- actual engine execution;
- world-state changes;
- timing;
- race/order effects;
- builder assignment;
- queue behavior;
- attack-group formation;
- strategic quality;
- whether the resulting behavior resembles the intended competitive policy.

The parser must never be treated as the lifecycle auditor, and the lifecycle auditor must never pretend it has executed the game.

## 18. Basilisk-specific implementation rules

These are project rules derived from the current controller and its established style.

1. Prefer engine-native primitives over custom abstractions when the primitive already solves the problem.
2. Keep strategic demand persistent and let execution reliability handle temporary failure.
3. Keep claims transient and capability-local.
4. Use actual world-state completion witnesses.
5. Use queue-aware counts for production caps where queued work is valid progress.
6. Use completed counts for finite package completion.
7. Treat pending construction as distinct from completed capability.
8. Keep standing army floors distinct from temporary attack packages.
9. Keep unit-goal composition policy distinct from standing role-floor policy unless a concrete source audit proves the separation wrong.
10. Keep resource commitment logic separate from ordinary stockpile checks.
11. Do not let reliability code choose replacement strategy or technology.
12. Do not clear persistent demand merely because a can-* predicate failed once.
13. Do not introduce a terminal retry counter for a persistent policy merely because repeated failures look ugly in a debugger.
14. Do not add an additional global execution mutex when an existing ownership mechanism already covers the contention.
15. Treat deliberate source-order priority chains as policy and document them rather than refactoring them into uncontrolled writers.
16. Prefer small, engine-native rules over elegant indirection.
17. Every new lifecycle change must be auditable backward and forward before it is considered complete.
18. Replay/game behavior overrides comments and static optimism.

## 19. Change-review gate

Before publishing a lifecycle repair to main, the change must pass:

~~~text
ENGINE REFERENCE CHECK
    +
COMMUNITY PATTERN CHECK
    +
STATIC HYGIENE CHECK
    +
UPSTREAM / DOWNSTREAM TRACE
    +
OWNERSHIP CHECK
    +
SOURCE-ORDER CHECK
    +
RESOURCE / ESCROW CHECK
    +
COMPLETION-WITNESS CHECK
    +
RUNTIME / REPLAY VALIDATION
~~~

No single layer can substitute for the others.

A change that passes parser checks but creates a dead demand is rejected.

A change that closes the lifecycle but changes the intended strategy is rejected unless the strategy change is deliberate.

A change that is strategically correct but consumes a protected bank is rejected.

A change that works once but cannot recover from temporary execution failure is rejected.

A change that looks clever but cannot be explained using normal AoE2 engine primitives is treated with suspicion until the complexity proves necessary.

## 20. Canonical rule

The final standard is:

> See the position. Decide what it means. Preserve the intent. Build what the intent requires. Spend with purpose. Execute only when the engine permits it. Believe the world, not the command. Recover without forgetting. Reassess without panicking.

That is the Basilisk lifecycle standard.

It is intentionally strict because .per bots fail in boring ways: stale claims, dead goals, unreachable branches, duplicated builders, queue blindness, fake completion, source-order accidents, and resource reservations that look reasonable until the army never gets built. The audit exists to catch those failures before the replay does.

---

## Appendix A: compact audit template

Use this block verbatim in future lifecycle audits.

~~~text
[Lifecycle]
Signal / Goal:
Owner:
Initialization:
Activation writers:
Activation conditions:
Package:
Package owner:
Capability:
Capability writer:
Capability completion witness:
Claim:
Claim owner:
Claim acquisition:
Feasibility:
Engine action:
Action owner:
Completion witness:
Completion release:
Strategic invalidation:
Execution failure:
Retry state:
Retry timer:
Retry exhaustion:
Capability-loss cleanup:
Readers:
Consumers:
Source-order dependency:
Queue semantics:
Pending semantics:
Escrow / reservation:
Reassessment:
Status:

[Verdict]
PARSER:
LIFECYCLE:
RUNTIME:
STRATEGY:
~~~

## Appendix B: audit shorthand

~~~text
D   = Demand
P   = Package
C   = Capability
CL  = Claim
F   = Feasibility
A   = Action
W   = World-state completion witness
I   = Invalidation
R   = Retry
O   = Ownership
SO  = Source order
RQ  = Queue / pending semantics
E   = Escrow / reservation
RE  = Reassessment
~~~

A lifecycle is closed only when the meaningful edges can be traced:

~~~text
D -> P? -> C -> CL? -> F -> A -> W -> RE
 \-> I
      \-> R -> F
C loss -> execution cleanup without policy invention
~~~

The question is never merely "does this rule fire?"

The question is:

> Can Basilisk explain why it wanted the action, what had to exist first, who owned the attempt, why the engine allowed it, what proves the world actually changed, what happens when it fails, and how the system returns to policy?

If not, the lifecycle is not finished.
