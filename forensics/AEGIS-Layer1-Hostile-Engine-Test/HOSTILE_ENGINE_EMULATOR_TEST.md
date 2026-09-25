# Hostile Age of Empires II DE Engine Emulator Test

## Test ID

`AEGIS-L1-HOSTILE-EMU-001`

## Scope

This is a hostile reverse-engineering test for the AEGIS Layer 1 control machinery historically developed in `justhop90-bot/AiByz`. It is preserved in `justhop90-bot/ByzMetaTeacher` as a reusable forensic fixture.

The test is intentionally adversarial. Human scripts routinely behave as though commands happen exactly where their lines appear, timers politely wait while a subsystem is skipped, and dead villagers remain useful because apparently software can survive on vibes. This test removes those assumptions.

## Target

Test the concrete target implementation supplied by the operator. Required machine-specific evidence is listed in `ENGINE_TEST_CHECKLIST.md`.

Do not substitute Basilisk code unless the test is explicitly being ported. Do not infer AEGIS state IDs, telemetry fields, or control values that are absent from the target source.

## Hostile engine axioms

### Axiom A: Escrow latency

Escrow is deducted by the engine strictly at the end of the AI pass.

The deduction is NOT tied to the exact `(research)`, `(build)`, or equivalent command line.

Therefore:

1. A subsystem can release `sn-resource-control`.
2. The same pass can continue into lower-priority rules.
3. A lower rule can claim the released control channel.
4. The engine has not yet deducted the original escrow.
5. Both controller paths may appear affordable against the same pre-deduction resource bank.

This is the intended trap.

### Axiom B: Persistent timers

`timer-triggered` does not pause during preemption.

If the Castle watchdog reaches expiry while Castle logic is skipped because emergency defense owns resource control, the timer becomes triggered and remains triggered until the target implementation explicitly clears/resets/consumes it.

Preemption therefore hides evaluation, not elapsed time.

### Axiom C: Blind builder assignment

`up-assign-builders` targets all incomplete foundations of the specified structure type.

Without DUC targeting, the controller cannot discriminate between multiple foundations of the same type.

### Axiom D: Asynchronous destruction

A building foundation may be destroyed while the capability/FSM that owns it is preempted and not evaluating its own recovery path.

The controller must eventually reconcile with the changed world state instead of assuming its prior foundation witness is still true.

## Initial world state

### Tick 1

Resources:

- Stone: `650`
- Food: `800`
- Gold: `200`

Controller demands:

- `bt-castle-demand = 1`
- `bt-fletching-demand = 1`

No other initial state is implied. Record every additional state value read from the target source or required by the emulator.

## Test timeline

### Tick 1 -> initialization

Record:

- Castle FSM state before first evaluation.
- Fletching FSM state before first evaluation.
- `sn-resource-control`.
- escrow state for Castle.
- escrow state for Fletching.
- Castle watchdog state.
- pending objects / foundations.
- builder assignment.
- telemetry index and current packed value.

### Tick 2 -> contention test

Both Castle and Fletching demands are active.

Trace every rule touching `sn-resource-control`.

Determine:

- Which subsystem acquires the channel first.
- What exact integer is written.
- What escrow is marked/accumulated.
- Whether the other subsystem is blocked.
- Whether resource-type separation matters to controller admission.
- Whether same-pass release creates a second claimant before end-of-pass deduction.

Explicit question:

`Can Fletching be starved by Castle even though their underlying resource costs differ?`

Do not answer from the resource types alone. Trace the actual mutex/channel semantics.

### Tick 30 -> foundation placement

World event:

- A villager places a Castle foundation at `1%` completion.
- `building-type-count-total = 1`.

Trace:

- Castle demand -> claim -> placement state transitions.
- `sn-resource-control`.
- builder assignment.
- foundation witness.
- watchdog start/reset.
- telemetry event(s).

Capture both controller state and world state separately.

### Tick 35 -> attack preemption

World event:

- `town-under-attack = true`.

Trace:

1. attack predicate;
2. preemption rule;
3. Castle state before mutation;
4. Castle state after mutation;
5. `sn-resource-control` before mutation;
6. `sn-resource-control` after mutation;
7. emergency-defense state;
8. rules skipped;
9. watchdog state;
10. telemetry event and exact packed integer.

The packed integer must be decoded from the target's real field definitions. No invented bit schema is permitted.

### Tick 40 -> builder death

World event:

- Active Castle builder dies.
- Castle foundation remains at `1%`.

Trace:

- builder count / assignment visibility;
- Castle FSM state;
- whether Castle recovery logic is currently preempted;
- watchdog status;
- foundation witness;
- `sn-resource-control`;
- telemetry event, if any.

The expected forensic pressure is that the world has lost the builder while the controller may still contain a valid-looking project state.

### Tick 120 -> watchdog expiry under preemption

World event:

- Castle watchdog reaches `120 seconds`.
- Emergency defense still owns resource control.
- Attack remains active.

Apply Axiom B exactly.

Trace:

- timer transition to triggered;
- Castle FSM state remains what it was while preempted;
- `sn-resource-control`;
- emergency-defense owner;
- foundation;
- builder availability;
- telemetry event, if the target records timer changes.

Critical question:

`Does the timer expiry become persistent controller state even though Castle logic is not evaluating?`

### Tick 150 -> attack clears

World event:

- `town-under-attack = false`.
- Preemption ends.

Trace:

- emergency owner release;
- Castle claim restoration;
- Fletching eligibility;
- watchdog status;
- foundation status;
- builder status;
- any restoration jump or state handoff;
- telemetry.

Do not assume the restored claim automatically means the Castle FSM resumes at the correct state.

### Tick 151 -> trap

The original Castle claim is restored.

This is the decisive tick.

Determine whether the Castle FSM:

1. sees the watchdog already triggered;
2. sees the builder already dead;
3. sees the foundation still present at `1%`;
4. reassigns builders;
5. restarts placement;
6. marks a failure/retry state;
7. incorrectly returns to a waiting/placement state that assumes the old builder is alive;
8. ignores the expired watchdog;
9. loops without a reachable state transition.

Also determine whether Fletching obtains resource control on this pass.

## Required trace format

Use one row per relevant event/pass:

`TICK | RULE/EVENT | CASTLE FSM | FLETCHING FSM | sn-resource-control | ESCROW | WATCHDOG | FOUNDATION | BUILDERS | TELEMETRY | WORLD RESULT`

Minimum mandatory tick rows:

- 1
- 2
- 30
- 35
- 40
- 120
- 150
- 151

Insert additional rows whenever state changes between the mandatory points.

Each row must distinguish:

- pre-rule state;
- rule(s) that execute;
- controller-state mutations;
- engine command issued;
- end-of-pass engine effect;
- post-pass controller state;
- later world observation.

## Telemetry requirement

For every telemetry write capture:

- ring index before;
- event type;
- sequence;
- owner;
- flags;
- timestamp/tick;
- packed integer in decimal;
- packed integer in hexadecimal;
- decoded field values;
- ring index after;
- wrap status.

If the target source does not expose the packing format, mark telemetry decoding as `UNKNOWN` rather than fabricating it.

## Terminal classifications

The test must conclude with exactly one of the following when applicable.

### `Escrow Double-Spend`

Use this classification if the trace proves that two controller paths can successfully claim/spend against the same pre-deduction bank because escrow is not deducted until the end of the pass.

Required evidence:

- first claim/release;
- second claim;
- pre-deduction resource state;
- commands issued;
- end-of-pass deduction result.

### `Masked Timer`

Use this classification if the Castle watchdog expires during preemption but the resumed Castle FSM fails to recognize the already-triggered condition, clears it incorrectly, or routes around the failure witness.

Required evidence:

- timer start/reset;
- tick 120 trigger;
- preemption state;
- tick 150 release;
- tick 151 evaluation;
- exact branch that hides or mishandles the trigger.

### `Dead-Builder Deadlock`

Use this classification if the resumed Castle path depends on the builder that died at tick 40 and no reachable rule reassigns or replaces the builder.

Required evidence:

- builder assignment before tick 40;
- death at tick 40;
- surviving foundation;
- restoration at tick 150;
- tick 151 failure to recover.

### `SURVIVED`

Use this only if the implementation demonstrably handles:

- end-of-pass escrow latency;
- timer persistence under preemption;
- dead-builder recovery;
- foundation state reconciliation;
- resource-control restoration;
- and exact telemetry packing/decoding.

A surviving result requires the trace, not merely source inspection.

## Verdict discipline

Do not report "probably survived," "looks safe," or "architecture seems sound."

Report the exact observed transition chain.

The decisive question is not whether the code looks reasonable. It is whether the controller remains consistent when controller time, engine time, resource deduction, and world-state changes stop happening at the convenient moments imagined by the script author.

## Known historical evidence baseline

The following prior forensic results are part of the test context:

- PASS 85 (`fe79d83c546f0c5b80ab6cc3e135eeb3a90d66d9`) strongly supports direct same-pass goal/SN state visibility and explicitly separates controller clock from world clock.
- Pass 55 (`599e1f2a...`) documents `sn-resource-control`, escrow-aware feasibility, and the distinction between requested, escrowed, and physically spent resources.
- Pass 56 (`d96cf55...`) documents historical rule-order economic arbitration and the absence of a proven global fairness mechanism.
- `SYSTEM_04_JUMP_PREEMPTION_FORENSICS_v0.1.md` records static jump control-flow evidence and warns that a jump is not automatically a commitment preemption.
- Historical AEGIS persistent construction work used explicit lifecycle states for demand, resource claim, placement, foundation-active, stall, block, failure, retry, and builder reassignment. Treat that as a source pattern, not proof of native atomicity.

## External engine references

- AIRef / UserPatch reference: https://userpatch.aiscripters.net/reference.html
- AoE2 DE AI scripting discussion: https://steamcommunity.com/workshop/discussions/-1/2217311444333302935/?appid=221380
- Official AoE2 DE update notes: https://www.ageofempires.com/games/age-of-empires-ii/updates/

## Execution rule

Do not modify the target implementation during the hostile run.

Run the existing machine first. Capture the failure. Classify it. Only then design the smallest repair that closes the demonstrated hole.
