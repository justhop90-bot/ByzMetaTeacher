# Basilisk Removable-State Audit
## North-Star compliance pass

Project: ByzMetaTeacher
Controller: Basilisk
Branch: main
Scope: identify state that can be deleted or simplified because it does not purchase real control capability.

## 1. Governing rule

Basilisk defaults to repeated condition/action rules.
State must earn its existence.

Before keeping or adding a goal, claim, timer, retry latch, stage, or mutex, ask:
1. Can current engine facts already answer this?
2. Can an existing demand express the need?
3. Can can-build, can-train, or can-research express the execution boundary?
4. Can current + queued or pending-object state prevent duplicate work?
5. Can deliberate rule order supply the required precedence?
6. Is there a genuine multi-pass engine operation?
7. Is there real resource/capability contention requiring ownership?

If the first five answers are enough, the state should normally be deleted.

## 2. Executive result

The audit found a meaningful amount of removable machinery.
The controller is not broken because of this state, but several subsystems have accumulated memory that does not control gameplay.

Highest-confidence removals:
- 5 dead goal variables.
- the runtime debug narration state: 21 debug goals and 86 chat/narration rules.
- the preemption metadata that records reason/result solely for reporting.
- the telemetry FIFO and XS bridge, if runtime telemetry is not itself a gameplay requirement.

Strong simplification candidate:
- collapse TC emergency preemption from a stateful transaction into direct interruption/retry rules using town-under-attack, existing TC claim, pending state, and rule order.

Second-order simplification candidates:
- ordinary building capability transactions such as Mill, University, Monastery, and Military Siege Workshop.
- some derived arithmetic goals such as standing-army deficit and attack reserve.

These second-order candidates need a narrower behavior audit before deletion because they currently participate in many consumers.

## 3. Dead state: remove

### 3.1 bt-debug-last-age-event-goal
Controller occurrences are only the defconst and initialization. It is never read by the controller.
Classification: DEAD.
Action: delete goal and initialization write when removing the debug narration layer.

### 3.2 bt-debug-last-tc-project-goal
Controller occurrences are only definition and initialization.
Classification: DEAD.
Action: delete.

### 3.3 bt-preempt-reason-goal
It is written when preemption begins, but never read anywhere in the controller.
The telemetry path does not consume it.
Classification: DEAD.
Action: delete.

### 3.4 bt-preempt-result-goal
It records resume, complete, and abort outcomes, but no controller rule reads those outcomes.
The telemetry path already records explicit event types.
Classification: DEAD.
Action: delete the goal, result constants, initialization, and result writes.

### 3.5 bt-telemetry-event-sequence-goal
It is initialized to zero and never participates in the telemetry FIFO.
The actual sequence counter is bt-telemetry-sequence-goal.
Classification: DEAD.
Action: delete.

## 4. Diagnostic state: remove from the runtime controller

Current diagnostic state includes 21 debug goals and 86 chat-local-to-self rules.
None of this state decides strategy, resources, production, research, construction, attack, or retreat.
It exists to narrate what the controller is already doing.

Classification: REMOVABLE SCAFFOLDING.

Preferred treatment:
move human-readable narration out of the authoritative controller. Keep temporary debugging instrumentation in a development-only file or branch if needed.

The practical gain is significant: removing 86 narration rules also removes a large amount of same-pass source-order noise.

## 5. Telemetry FIFO: strong removal candidate

Runtime telemetry currently uses write/read heads, occupancy, sequence, overflow state, event payloads, four slots, one timer, and an XS consumer.
It observes preemption but does not decide or execute gameplay.

It therefore fails the primary North-Star test: does the state purchase real control capability?
Answer: no.

Classification: REMOVABLE FROM THE AUTHORITATIVE CONTROLLER.

Preferred replacement: keep debugging outside Basilisk.per.

Removing telemetry also makes bt-preempt-original-mode-goal unnecessary, because its only remaining use is encoding telemetry flags.

## 6. TC preemption: simplify, do not expand

The current mechanism has active state, original owner, original resource mode, reason, result, defense-issued state, emergency resource-control ownership, 13 rules, and telemetry.

The actual gameplay problem is smaller:
A discretionary TC resource claim must not block emergency defense while the town is under attack.

A simpler expression is:
1. TC claim acquisition refuses while town-under-attack.
2. If an existing TC resource claim becomes active and town-under-attack begins, release that TC claim and return the TC project to demand.
3. Normal military demand/production rules then see resource-control = 0.
4. When the attack ends, the ordinary TC demand can reclaim resources.

The current source order is favorable to this simplification because a direct interrupt rule can run before the military production block.

Classification: STRONG SIMPLIFICATION CANDIDATE.

Do not delete the current preemption system blindly. First verify that ordinary threat/standing-army demand produces the needed emergency response when the standing floor is already satisfied.

The likely end-state is two direct rules plus normal demand, not another smaller FSM.

## 7. Preemption defense-issued state is also suspect

bt-preempt-defense-issued-goal exists to prevent the emergency counter action from firing more than once.
That is probably redundant if emergency production uses existing counter targets, current+queued count, pending-object guards, and can-train.

Classification: REMOVE AFTER DIRECT-EMERGENCY-PRODUCTION TEST.
Do not replace it with another latch.

## 8. Ordinary building lifecycles: likely over-modeled

Several capability builders currently use:
demand -> failure-history -> backoff -> global claim -> watchdog -> build -> completion release.

For ordinary buildings, the community-native shape is often simply:
demand -> pending == 0 -> can-build-with-escrow -> build -> world state changes -> reassess.

The strongest audit targets are:
- Mill
- University
- Monastery
- Military Siege Workshop.

Why they are suspicious:
- pending-object state already proves a live construction request exists;
- can-build-with-escrow proves current affordability/engine feasibility;
- repeated passes already provide retry;
- completed building count already provides completion.

Classification: REDUCTION CANDIDATE, NOT A BLIND DELETE.

## 9. Mill is the clearest first target

The Mill lifecycle currently uses target, project, claim, backoff, watchdog, and placement policy state.
The placement policy may be useful. The transaction state is questionable.

A simpler executor can potentially be:
Mill demand active + target not reached + pending Mill = 0 + strategic vetoes absent + can-build-with-escrow mill -> build mill.

The engine and next pass already provide retry.

Classification: FIRST CONTROLLED REDUCTION EXPERIMENT.

## 10. University is also highly suspicious

University demand already has direct capability facts: university count, pending university, research package demand, and can-build-with-escrow.

The current lifecycle adds backoff, a global claim, a watchdog, and builder reassignment.

Classification: STRONG CANDIDATE.

## 11. Monastery is the same pattern

Monk demand plus Castle age plus monastery count plus pending monastery plus can-build-with-escrow can likely express the capability directly.
The failure-history/backoff/watchdog stack is heavier than the underlying decision.

Classification: STRONG CANDIDATE.

## 12. Military Siege Workshop is the next capability candidate

Any active siege demand can justify a Workshop.
The current capability lifecycle uses a claim, watchdog, and backoff.

A direct provider may be sufficient:
active siege demand + Workshop absent + pending Workshop = 0 + resource-control free + can-build-with-escrow -> build Workshop.

Classification: STRONG CANDIDATE.

## 13. Derived arithmetic state: keep for now, review later

These are not dead:
- bt-standing-army-deficit-goal
- bt-attack-reserve-goal
- bt-standing-army-infra-goal
- bt-varangian-fielded-goal.

They summarize arithmetic that is otherwise awkward to repeat and are consumed by many rules.

Classification: KEEP FOR NOW.

Do not create additional scratch goals of this kind.

## 14. Resource mode: keep

bt-resource-mode-goal centralizes economic priority between crises, age banks, prerequisite funding, stone, premium gold, military modes, and strategy fallback.
Removing it would push the same precedence logic into many consumers.

Classification: KEEP.

## 15. Counter levels and veto state: keep

The counter-level goals and bt-counter-veto-goal are shared strategic interpretations consumed downstream.
They are not simple engine mirrors.

Classification: KEEP.
Keep them derived, not historical.

## 16. Research provider claims: keep for now

Provider claims answer which technology currently owns a provider capability across an asynchronous research operation.
Current research status can prove individual technology state, but removing provider claims would force each provider family to reconstruct active technology ownership across many research statuses.

Classification: KEEP FOR NOW.
Do not add more claim families unless a real new provider contention exists.

## 17. Siege Tower stage: keep

Siege Tower is a genuine multi-pass engine operation: wall probe -> target point -> tower -> payload -> garrison -> loaded -> approach -> unload -> assault.

Classification: KEEP.
It is the kind of local FSM the North Star permits.

## 18. TC stage: review second

TC stage is more questionable than Siege Tower. Some of it may be expressible through project target, resource-control claim, pending placement, and completed TC count.
Foundation support still has real execution semantics, so this should be a controlled simplification experiment rather than immediate deletion.

Classification: REVIEW SECOND.
Do not add another stage.

## 19. Housing and dropsite state: keep

Housing demand is persistent demand with a simple pending cap.
Dropsite placement claim temporarily owns global placement policy while a camp request is live.

Classification: KEEP.

## 20. Farm transition reserves: keep

Farm transition reserve state encodes a real policy decision about idle/depleted farm capacity and is shared by multiple farm rules.

Classification: KEEP.

## 21. Removal order

Do not attack the controller wholesale.

Recommended order:
1. Dead goal variables.
2. Runtime narration/debug latches.
3. Telemetry FIFO and XS bridge.
4. Preemption metadata.
5. Collapse TC preemption into direct interrupt/reclaim rules.
6. Simplify one ordinary building capability at a time: Mill first, then University/Monastery, then Siege Workshop.
7. Only later review derived arithmetic scratch goals.

Do not touch in the first reduction pass:
- Siege Tower FSM.
- research provider claims.
- resource mode.
- counter-level interpretations.
- standing army targets.
- housing demand.

## 22. What not to do

Do not replace removed state with a different latch, a generic state manager, a new claims manager, more timers, or another lifecycle framework.

If deleting state creates a problem, first try current engine facts and rule order.

## 23. Expected direction

The desired controller after state reduction should be closer to:
current facts -> direct heuristic rule -> can-* -> action -> world-state change -> next pass.

Persistent strategy and genuine demand remain.
Local transactions remain only where the engine makes them necessary.
Everything else is allowed to disappear.

## 24. Final verdict

The controller is not suffering from a lack of lifecycle sophistication.
It is carrying a surplus of lifecycle sophistication in places where ordinary .per rules are already sufficient.

The safest high-value cleanup is subtractive.

Improve the controller by making the engine do more of the work.


## September 24, 2026 implementation follow-through

The subtractive audit was applied with one deliberate exception: the `chat-local-to-self` diagnostic layer stays. The chat rules do not participate in gameplay arbitration and are not large enough to justify turning replay diagnostics into an external instrumentation project.

Removed from runtime:

- The `BasiliskTelemetry.xs` include.
- The four-slot telemetry FIFO and XS drain timer.
- All 32 telemetry GoalIds.
- Preemption metadata whose only consumer was telemetry: `bt-preempt-original-mode-goal`, `bt-preempt-reason-goal`, and `bt-preempt-result-goal`, plus their reason/result constants.
- The two XS source copies.

Kept intentionally:

- All 86 `BASILISK | ...` chat rules.
- Actual preemption control state.
- Strategic and tactical state with gameplay consumers.

Two additional gameplay-state reductions were made because the duplication was mechanical rather than architectural:

- `bt-monastery-failure-history-goal` was removed. Its only lifecycle was set together with `bt-monastery-backoff-goal`, read together with it, and cleared together with it. The backoff timer already provided the full execution delay.
- `bt-blacksmith-repair-failure-history-goal` was removed for the same reason. Its manual reset participation was replaced by the existing blacksmith repair backoff state.

The next audit target is not "find more state." It is "prove a state variable is redundant." In particular, persistent intent such as Castle maturity, farm transition reserves, housing demand, research-provider claims, attack measurement, and the Siege Tower execution path currently demonstrate independent control value and remain in place pending stronger evidence.


## Second-pass gameplay-state tightening

Two additional state reductions were verified against the live controller and then removed.

### Opening stage shadow state

`bt-opening-stage-goal` was only a one-bit mirror of `bt-opening-plan-goal`:

- it started in `selecting`;
- every selection rule required `selecting`;
- every selection rule wrote a nonzero opening plan and then `committed`;
- the opening plan was never reset to zero after initialization;
- the only later `committed` reader merely permitted the anti-rush override;
- the later `complete` value had no gameplay consumer.

The equivalent control surface is simply `bt-opening-plan-goal == 0` for selection and `bt-opening-plan-goal != 0` for post-selection behavior. The stage goal and all three stage constants were therefore pure shadow state.

### Opening map mirror

`bt-opening-map-goal` was an immutable mirror of the engine's `map-type` fact. It was written once during classification and then used only to restate `arabia`, `arena`, or generic-map status. Since map type is directly available to every rule and does not change during a normal match, the persistent mirror purchased no control capability.

Opening selection now consumes `map-type` directly. `bt-opening-underlay-goal` remains because it is not a mirror: it preserves the base opening while Anti-Rush temporarily overrides `bt-opening-plan-goal`.

### Current high-confidence state verdict

The subtractive pass has now removed:
- dead diagnostic/telemetry machinery;
- two duplicate failure-history latches;
- one opening-stage shadow;
- one immutable map mirror.

The remaining small-reader states have been reviewed individually. Castle mature commitment, Feudal eco hold, farm wood hold, housing demand, research backoff, Monk/Trebuchet targets, attack measurement, and Siege Tower cycle state each preserve information that current engine facts do not independently retain across passes. Preemption state remains the next risky area for controlled simplification, but `bt-preempt-active-goal` and `bt-preempt-defense-issued-goal` should not be deleted blindly because they currently bound an actual emergency-control path.

## Final subtractive pass in this cycle

Two more gameplay shadows were removed after the first cleanup pass.

### Feudal eco hold

`bt-feudal-eco-hold-goal` was a same-pass scratch latch. It was reset to zero every evaluation pass, written by three rules, and consumed by exactly one Fast-Castle bank rule. Its writers simply encoded current Horse Collar/Double-Bit Axe feasibility and demand. The bank rule now tests those same current facts directly, so no persistence or lifecycle memory is required.

### Spear counter level

`bt-spear-counter-level-goal` was a three-level derived state, but its only consumer asked whether the value was at least one. The existing `bt-cavalry-threat-goal` already represents the same threshold: three or more enemy cavalry-class units. The three spear-counter writers and the unused intermediate state were removed; the standing-archer target rule now consumes the existing cavalry threat witness directly.

### Preemption active latch

`bt-preempt-active-goal` was also shadow state. Once preemption starts, `sn-resource-control == bt-preempt-emergency-claim` is the actual engine-facing ownership witness. The begin rules already acquire that emergency claim only from the TC2/TC3 claims, and every defense/resume/abort/completion rule already requires the emergency claim. The active latch therefore added no independent control capability and was removed. `bt-preempt-original-owner-goal` remains because it remembers whether the interrupted project was TC2 or TC3, and `bt-preempt-defense-issued-goal` remains because it intentionally bounds emergency production to a single pulse.

The controller has now been statically rechecked at this HEAD: balanced parentheses, zero logical-arity violations, zero duplicate numeric GoalIds, 987 rules, 505 constants, and all 86 diagnostic chat rules retained.

The remaining low-reader gameplay states are not being deleted merely because they have few readers. They each preserve either cross-pass intent, an explicit target, a real cooldown, an asynchronous engine lifecycle, a measurement snapshot, or a multi-step execution witness.