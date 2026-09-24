# Basilisk Lifecycle Audit
## Full controller-state forensic review

Project: ByzMetaTeacher
Controller: Basilisk
Branch: main
Scope: every meaningful lifecycle in Basilisk, including strategic state, derived state, demands, capability projects, research cursors, resource claims, timers, retry/backoff, preemption, telemetry, DUC, Siege Tower transport, TC expansion, farming, scouting, diagnostics, and obscure one-off state.

## 1. Executive verdict

This audit does not justify an architecture rewrite.

Basilisk has a large state surface, but most of it is now organized into the correct categories:

- persistent strategic intent,
- derived current-world interpretation,
- persistent demand,
- local capability execution,
- local transaction state,
- bounded failure memory,
- observational diagnostics.

Current source inventory:

- 1,001 defrule forms after the repair.
- 559 defconst forms.
- 35 explicit demand latches, all with both assertion and release paths.
- 12 research-provider claim cursors.
- 47 named timers.
- Explicit local lifecycles for Town Centers, Mills, attacks, retreats, siege packages, Siege Tower transport, temporary preemption, telemetry FIFO, dropsite refresh, research failure backoff, opening selection, and resource arbitration.

One confirmed lifecycle defect was found and repaired:

BBC -> Trebuchet DUC had an armed-state latch with no target-loss release edge.

Original failure path:

~~~
Trebuchet exists
    ->
DUC armed
    ->
Trebuchet dies
    ->
BBC demand remains
    ->
DUC armed remains true
    ->
arm rule cannot fire again because armed != 0
~~~

That is a genuine stale-state defect.

The repair adds:

~~~
BBC demand = 1
+
DUC armed = 1
+
enemy Trebuchets < 1
    ->
disable target timer
    ->
armed = 0
    ->
stage = idle
~~~

The controller patch is commit:
fc29f3aac3bd746770979cd02fd80492909bf36f

The lifecycle validator patch is:
85eea8be4f9a915cf665845c891bd618f4a4de35

The regression self-test patch is:
50a64f6e2921604c91b3515d51b3fb93a02aba7d

One lower-severity coverage concern remains:

The housing demand can be asserted by population-headroom <= 0 while the first-house executor requires housing-headroom <= 5 and population-headroom > 0. This is not a proven runtime failure, but the trigger and consumer are not perfectly symmetric.

No runtime or replay certification was possible because the game machine is unavailable.

## 2. Audit contract

Every lifecycle was judged using:

~~~
OBSERVATION
    ->
INTERPRETATION
    ->
PERSISTENT INTENT
    ->
DEMAND
    ->
CAPABILITY
    ->
ENGINE FEASIBILITY
    ->
ACTION
    ->
WORLD-STATE WITNESS
    ->
COMPLETION / RELEASE
    ->
REASSESSMENT
~~~

For a lifecycle to pass:

1. The state has a semantic owner.
2. A consumer exists.
3. The action has a feasibility gate where the engine provides one.
4. Pending/queue state prevents duplicate requests where required.
5. Completion is proved by world state.
6. Temporary state releases on completion.
7. Failure does not erase valid strategic demand.
8. Strategic invalidation can terminate obsolete work.
9. Retry is bounded.
10. No unrelated subsystem can permanently inherit the state.

## 3. Strategic-state lifecycles

### Strategy

States: FLUSH, RUSH, BOOM, CASTLE-POWER.

Pattern:

~~~
opening / threats / battlefield
    ->
strategy selection
    ->
persistent posture
    ->
lower-layer consumers
    ->
battlefield change
    ->
explicit recovery or transition
~~~

Status: PASS.

The main risk is not lifecycle failure. It is writer precedence. Strategy has multiple legitimate writers, so source order is part of behavior and must remain validated.

### Unit-goal

Composition states include Spears, Skirmishers, Archers, Crossbows, Knights, Camels, and MIX.

Pattern:

~~~
strategy + threat
    ->
composition
    ->
standing role targets
    ->
production capacity
    ->
training
~~~

Status: PASS WITH WATCH.

Multiple writers are acceptable only if conditions are mutually exclusive or precedence is explicit.

### Opening

State surface includes map, threat, underlay, plan, and selection stage.

Pattern:

~~~
map + opening evidence
    ->
base plan
    ->
temporary anti-rush override
    ->
restore underlay
    ->
Castle / completed opening
~~~

Status: PASS WITH CAVEAT.

The opening stage reaching COMPLETE means initial selection is complete, not that the opening plan can never change again. That interpretation should remain documented.

## 4. Derived-state lifecycles

### Enemy threats

Cavalry, ranged, spear, and all-threat state are cleared and reconstructed from live enemy counts.

Status: PASS.

This is the correct heuristic-controller pattern.

### Counter levels

Same structure, with thresholds for 3/10/20 cavalry, 3/10/20 ranged, 4/8 spear, etc.

Status: PASS.

### Natural-food state

Stable, transition, and depleted states are derived from boar/deer/sheep-food conditions.

Status: PASS.

The farm layer consumes the derived state rather than directly owning the boar controller.

## 5. Housing

Demand is asserted on low housing headroom or emergency population headroom.

First-house path uses:

- no completed house,
- positive population headroom,
- low headroom,
- pending cap,
- can-build,
- two builders.

Later houses use:

- demand,
- completed house exists,
- pending cap,
- can-build.

Completion/release:

- first-house builder count resets to one,
- demand clears when headroom recovers and no house is pending.

Status: PASS WITH COVERAGE WATCH.

Potential edge:

population-headroom <= 0 plus housing-headroom > 5 plus zero completed houses.

Not proven reachable in normal game state, but worth keeping as a validator scenario.

## 6. Lumber / mining / dropsite lifecycle

Initialization:

- dropsite update deferral enabled,
- separation normal,
- adjacent dropsites disabled,
- camp placement radius initialized.

First camp:

~~~
resource/civilian condition
+
pending == 0
+
claim == 0
+
can-build
    ->
build camp
~~~

Adaptive placement:

~~~
resource too distant
    ->
camp radius +3
    ->
bounded at 40
~~~

Refresh:

~~~
temporary adjacent override
+
separation 4
+
claim
    ->
build camp
~~~

Release:

~~~
no pending lumber camp
+
no pending mining camp
    ->
adjacent override off
    ->
separation 8
    ->
claim release
~~~

Status: PASS.

Important distinction: Mill placement policy is separate and sticky. It sets its own placement zone and 10-tile separation. That should be treated as persistent engine policy, not generic temporary cleanup.

## 7. Mill lifecycle

State:

- target completed count,
- current project target,
- resource claim,
- placement anchor,
- watchdog,
- backoff.

Completion uses completed Mill count, not merely total queued construction.

Failure uses:

~~~
watchdog
+
no pending foundation
    ->
claim release
    ->
bounded backoff
~~~

Status: PASS.

No orphaned claim found.

## 8. Boar / natural-food lifecycle

The native hunt controller is configured through:

- one-lurer mode,
- active hunt-group mode,
- next-boar relure,
- normal hunting restoration.

The script does not manually micromanage villagers.

Status: PASS.

## 9. Economic technology lifecycles

Audited demand families:

- Double-Bit Axe
- Gold Mining
- Gold Shaft Mining
- Wheelbarrow
- Hand Cart
- Bow Saw
- Two-Man Saw
- Stone Mining
- Stone Shaft Mining
- Horse Collar
- Heavy Plow
- Crop Rotation

Common lifecycle:

~~~
persistent demand
    ->
provider capability
    ->
claim
    ->
can-research-with-escrow
    ->
research
    ->
research-complete
    ->
claim release
    ->
demand release
~~~

Failure:

~~~
research remains available
    ->
provider-local backoff
    ->
claim release
    ->
retry later
~~~

Status: PASS.

Crop Rotation is intentionally more direct because its mature-farm and Imperial gates already provide the strategic persistence.

## 10. Research-provider claim system

Providers:

1. Town Center
2. Mill
3. Lumber Camp
4. Mining Camp
5. Blacksmith
6. University
7. Castle
8. Barracks
9. Archery Range
10. Stable
11. Siege Workshop
12. Monastery

Each provider uses one capability-local claim cursor across multiple technologies.

Status: PASS.

The system correctly avoids creating one global scheduler per technology.

The claim is execution ownership.

The technology/package demand remains strategic.

## 11. Age transitions

Readiness stops normal villager production only when the age bank is genuinely feasible.

Execution:

~~~
resource control
+
can-research-with-escrow
    ->
research age
~~~

Completion:

current-age changes.

Failure:

age remains research-available, enters bounded cooldown.

Watchdog:

pending research keeps lifecycle alive.

Status: PASS.

## 12. Production and standing-army lifecycle

Standing army demand is derived from:

- standing floor deficit,
- role target deficit,
- strategic posture.

Consumers build:

- Barracks,
- Archery Ranges,
- Stables.

Training consumers use current and queued requirements.

Status: PASS.

This is demand-driven capacity rather than strategy directly issuing buildings.

## 13. Primary military upgrade lifecycles

Knight, Crossbow, Cavalier, Paladin, and Arbalest each follow the mature-package pattern:

~~~
unit-goal
    ->
actual mature mass
    ->
upgrade demand
    ->
provider claim
    ->
research
    ->
research-complete
    ->
upgrade demand release
~~~

Status: PASS.

## 14. Mangonel / Scorpion / Onager

### Mangonel
Castle response package, finite actual-unit target.

PASS.

### Scorpion
Four-unit response package against enemy infantry.

PASS.

### Ballistics
Only pursued after the actual Scorpion package exists.

PASS.

### Onager
Requires a real predecessor Mangonel mass. Research does not prematurely close the demand.

PASS.

## 15. BBC / Chemistry / University

BBC demand belongs to the Imperial siege package.

University is a distinct capability owner.

Chemistry is a downstream research demand, not generic Imperial research.

BBC package completion uses actual completed Cannons.

Status: PASS.

## 16. BBC -> Trebuchet DUC

This was the confirmed lifecycle defect.

Original valid edges:

- demand -> armed,
- armed -> Trebuchet probe,
- no Trebuchet -> building fallback,
- town attack -> disarm,
- demand loss -> disarm.

Missing edge:

~~~
armed
+
enemy Trebuchets < 1
    ->
disarm
~~~

Without this edge, future Trebuchet detection could never re-enter the arming rule.

Repair is now present in controller and validator.

Status: FIXED.

Regression test:
bbc-duc-target-loss-disarm-regression.

## 17. Siege Tower transport lifecycle

Stages:

1. idle
2. wall probe
3. tower pending
4. payload ready
5. garrisoning
6. loaded
7. approach
8. unload pending
9. assault
10. retry wait
11. cycle complete/reset

Failure types distinguish:

- no wall,
- tower timeout,
- garrison timeout,
- approach exhaustion,
- unload exhaustion.

Retry count is capped.

All timers and garrison strategic numbers are cleared on terminal reset.

Attack-cycle cleanup performs final teardown.

Status: PASS.

This is the most legitimate local finite-state machine in Basilisk because the engine operation itself is multi-stage and asynchronous.

## 18. Imperial siege package

Entry requires:

- Imperial,
- valid target,
- sufficient standing army,
- sufficient reserve,
- acceptable relative force,
- no veto,
- no retreat,
- no Imperial bank preparation.

Children include:

- Trebuchets,
- Rams,
- BBC,
- Onager,
- research packages,
- Castle recovery.

Army collapse below the abort floor clears package-owned child demand.

Status: PASS.

## 19. Siege Workshop capability

Any active siege demand may create Workshop demand.

Lifecycle:

~~~
siege demand
    ->
Workshop missing
    ->
claim
    ->
can-build
    ->
build
    ->
pending foundation
    ->
watchdog
    ->
completed Workshop
    ->
claim release
~~~

Failure becomes bounded cooldown only.

Status: PASS.

## 20. University capability

Demand exists when live research packages require University.

Lifecycle is complete:

demand -> claim -> build -> completion -> release

or:

watchdog -> backoff -> retry.

Status: PASS.

## 21. Monastery capability

Monk demand creates Monastery capability demand.

Lifecycle:

monk need -> Monastery -> claim -> build -> completion -> monk training.

Status: PASS.

## 22. TC2 / TC3 Boom lifecycle

Stages:

~~~
idle
→ demanded
→ resource claimed
→ placement pending
→ foundation active
→ complete
~~~

Failure paths return to demand without destroying the strategic reason.

Strategic cancellation is allowed before a foundation exists.

Live foundations are allowed to finish.

Status: PASS.

## 23. TC preemption

Only TC2/TC3 discretionary claims may be preempted.

Lifecycle:

~~~
TC claim
    ->
town emergency
    ->
snapshot owner
    ->
emergency claim
    ->
defensive pulse
    ->
resume / complete / abort
~~~

Validator explicitly rejects preemption of protected claims.

Status: PASS.

Critical source-order finding:

Preemption opener is before TC execution rules and requires stage resource-claimed. It therefore cannot newly preempt after the TC has already advanced to placement-pending/foundation-active during the same pass.

The apparent deadlock was investigated and rejected.

## 24. Telemetry FIFO

Four slots:

- write head,
- read head,
- occupancy,
- sequence,
- overflow,
- event payloads.

Append is bounded to four slots.

Overflow is a pulse plus a lifetime count.

XS drains up to four events per call.

The XS consumer is observational only.

Status: PASS.

## 25. Attack lifecycle

Start requires:

- valid strategy,
- valid enemy target,
- standing demand satisfied,
- attack reserve,
- relative force,
- no counter veto,
- no retreat,
- no town attack.

Then:

~~~
attack-goal = 1
    ->
attack-now
    ->
gather watchdog
    ->
attack-soldier-count >= 10
    ->
measurement timer
    ->
reset attack
    ->
damage/force result
    ->
next cadence
~~~

Status: PASS.

Attack result is based on world-state damage and force rather than command execution alone.

## 26. Retreat lifecycle

Retreat triggers on:

- town attack,
- negative attack reserve,
- severe relative-force failure.

It:

- resets attack-now,
- calls retreat,
- raises standing-army demand,
- closes attack,
- starts retreat cooldown.

Cooldown releases retreat and restores later attack cadence.

Status: PASS.

## 27. Ram lifecycle

Castle:

~~~
attack package
→ two Rams
→ completion
→ release
~~~

Imperial:

~~~
Imperial siege package
→ four-Ram target
→ Capped Ram
→ Siege Ram
→ completion
→ release
~~~

Status: PASS.

## 28. Trebuchet lifecycle

Trebuchet target is derived from defended enemy structures.

Production uses queue-aware target gating and engine feasibility.

Completion requires actual completed Trebuchets.

Demand clears if the target player disappears, Imperial state is lost, Castle capability is lost, or package context disappears.

Status: PASS.

## 29. Cataphract / Varangian lifecycle

Both are premium packages.

They are driven by battlefield demand, mature targets, and explicit opportunity-cost gates.

Varangian includes later Logistica and Elite continuation.

Status: PASS.

The system does not treat either premium line as a default civilization-wide objective.

## 30. Resource-mode lifecycle

Resource mode is reset every pass.

Priority sequence:

1. food crisis,
2. gold crisis,
3. wood crisis,
4. age banks,
5. Imperial prerequisite funding,
6. stone/premium modes,
7. military/premium modes,
8. strategy-based fallback.

Most writers require mode = 0.

Imperial prerequisite funding is deliberately allowed to override normal mode ownership and has explicit P0 exclusions.

Status: PASS.

Resource mode is derived allocation state, not persistent strategy.

## 31. Failure-backoff lifecycle

Research failures do not erase strategy.

Pattern:

~~~
attempt
→ failure
→ provider-local cooldown
→ claim released
→ package remains
→ retry
~~~

All 47 named timers have enable and trigger paths.

Only the scouting timer has no disable path, and it is intentionally recurring.

Status: PASS.

## 32. Diagnostic-state lifecycles

Debug last-state goals act as edge detectors.

They do not own:

- strategy,
- resources,
- production,
- execution claims.

Status: PASS.

They should remain outside strategic lifecycle reasoning.

## 33. Global resource-control review

Global resource-control is used for:

- age transitions,
- TCs,
- prerequisites,
- Mill,
- Monastery,
- University,
- Siege Workshop,
- research-provider claims,
- emergency preemption.

This is acceptable because claims are separated by subsystem.

The critical invariant is:

> a subsystem may release its own claim; unrelated cleanup must not blindly clear another subsystem's claim.

Status: PASS.

## 34. Complete demand-latch inventory result

Static source inventory found all 35 explicit demand latches have both set-to-1 and set-to-0 paths.

No binary demand was found to be write-only.

This does not prove that every release predicate is strategically optimal. It proves there are no obvious dead-end binary demand variables at the lifecycle-closure level.

## 35. Timer inventory result

47 timers were scanned.

Results:

- recurring timers without explicit trigger handling: none.
- trigger-bearing timers without any disable path: one, the intentionally recurring scouting timer.
- all other watchdog/backoff/cadence timers have disable paths.

Status: PASS.

## 36. State-machine quality finding

Basilisk contains a genuine local finite-state machine: Siege Tower.

It also contains smaller local staged lifecycles:

- TC projects,
- opening selection,
- preemption,
- DUC,
- attack results,
- research provider claims.

That is acceptable.

The audit does not find evidence that the whole AI has collapsed into a global FSM.

The correct architecture remains:

~~~
heuristic controller
+
persistent intent
+
derived state
+
local transactions
~~~

## 37. Remaining watch list

### Housing trigger symmetry
The emergency population-headroom writer and first-house executor do not share exactly the same conditions.

### Strategy precedence
Multiple strategy writers remain. Source order is part of their behavior.

### Unit-goal precedence
Multiple composition writers remain. Their mutual exclusion/priority must remain validated.

### Sticky placement policy
Mill placement parameters are persistent policy, unlike the temporary camp adjacent-dropsite override.

### Research package multiplexing
Many technologies share provider claim cursors. This is the right architecture, but it increases the need for claim lifecycle regression.

None of these is a current confirmed deadlock.

## 38. Required validator standard after this audit

Lifecycle validation should continue to check:

- assertion edge,
- completion edge,
- invalidation edge,
- failure edge,
- retry edge,
- capability-loss edge,
- resource-claim release,
- timer release,
- pending-object guard,
- queued/current production witness,
- world-state completion witness.

The BBC DUC defect demonstrates why the invalidation edge deserves equal status with completion.

## 39. Final verdict

Basilisk does not need a lifecycle rewrite.

It needs disciplined lifecycle closure.

The central rule is:

> Every meaningful state must have an edge for every meaningful reason that state should stop being true.

That is the difference between a stateful controller that remains adaptive and one that becomes a fossil.

The BBC DUC defect was a fossil edge.

It has now been removed.

No other confirmed orphaned lifecycle was found in the present source audit.

Runtime/replay remains the final witness and is still required before treating the implementation as gameplay-certified.
