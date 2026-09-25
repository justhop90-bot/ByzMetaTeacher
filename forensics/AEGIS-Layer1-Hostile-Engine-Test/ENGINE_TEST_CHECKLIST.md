# AEGIS Layer 1 / Hostile Engine Emulator Test Checklist

## Purpose

This folder preserves the complete evidence checklist required to execute the hostile Age of Empires II DE engine-emulator test against the reverse-engineering Layer 1 machinery from the historical AEGIS / AiByz work.

This is a forensic test, not a Basilisk gameplay change. The target is to determine whether a concrete AEGIS Layer 1 implementation survives adversarial engine semantics involving resource-control contention, escrow latency, persistent timers, preemption, blind builder assignment, asynchronous foundation destruction, and telemetry packing.

The current repository baseline used for this documentation is `86c0f2166f55d7423787678cbe9b1087fa500ceb` on `main`. No gameplay code is part of this test fixture.

## 1. Target code that MUST be present before execution

Retrieve the actual AEGIS Layer 1 source and identify the exact writers, readers, and consumers for:

- Castle demand signal and Castle FSM.
- Fletching demand signal and Fletching FSM.
- `sn-resource-control`: every writer, reader, release path, and restoration path.
- Castle watchdog timer: declaration/initialization, start/reset, `timer-triggered` checks, cancellation, expiry handling, and ownership.
- `town-under-attack` detection and all preemption rules that can suspend, replace, or restore Castle work.
- Castle builder assignment, including every `up-assign-builders` call and all builder-count predicates.
- Foundation detection and completion witnesses for the Castle.
- Any rule that reacts to Castle foundation loss/destruction.
- Telemetry ring-buffer writer, index update, field packing, and decoder/unpacker if present.
- Any Fletching action that can claim the same resource-control channel.
- Any global or subsystem scheduler rule that can execute between these FSM stages.

Do not infer missing logic from comments or names. Use the executable `.per` rules, goals, strategic numbers, timers, facts, and engine-native conditions/actions.

## 2. Scheduler / control-flow evidence

Prove from the target source:

- Rule load order.
- Rule evaluation order within a pass.
- Whether a triggered rule is evaluated immediately or only on a later pass.
- `disable-self` behavior.
- Positive and negative `up-jump-rule` behavior.
- Whether jumps skip the next N rules or re-enter earlier rules.
- Exact ordering between state mutation and later rule evaluation in the same pass.
- Exact conditions under which one subsystem can release and another can immediately claim `sn-resource-control`.
- Whether any apparent preemption is only control-flow skipping rather than an actual ownership transfer.
- Whether restored rules resume from saved state or simply re-evaluate their ordinary predicates.

Known Layer 1 finding: direct goal/SN mutation is strongly supported as shared controller state visible to later rule logic in the same pass. Same-pass visibility is not evidence of atomic commitment ownership transfer.

Required model:

`controller clock = RULE -> GOAL/SN/FLAG mutation -> later controller evaluation`

`world clock = COMMAND -> engine processing -> queue/pending -> world-state change -> later observation`

Do not collapse these into one clock.

## 3. Resource-control / escrow evidence

For every writer and consumer of `sn-resource-control`, record:

- Rule/file.
- Exact write value.
- Entry condition.
- Exit/release condition.
- Whether the value means ownership, commitment, phase, or merely admission.
- Whether a release is performed before the engine action.
- Whether the successor can see the release in the same pass.
- Whether the action queues or completes immediately.
- Whether escrow is included, deducted, or merely requested at each predicate/action.

Required semantic distinctions:

`requested cost != escrowed cost != physically spent resource`

Historical AEGIS/stock evidence establishes escrow-aware command families and procedural resource control, but exact engine-side escrow deduction timing is not proven by source. This hostile test deliberately supplies that engine behavior.

Historical idioms to recognize:

- `up-can-research ... escrow-state ...`
- `up-can-train ... escrow-state ...`
- `up-can-build ... escrow-state ...`
- `up-release-escrow`
- `up-modify-escrow`
- `release-escrow` before a physical command.
- `sn-resource-control` as a persistent admission/commitment channel.
- `escrow-purpose-goal` as an explicit purpose record in historical scripts.

Important historical observation: rule order matters because an earlier action can consume resources and leave later rules unable to spend them. There is no proven universal fairness scheduler.

## 4. Timer / watchdog evidence

For the Castle watchdog identify:

- Timer ID.
- Initialization point.
- Starting value.
- Trigger condition.
- Reset/start condition.
- Cancellation/clear condition.
- Whether timer status is evaluated while the Castle FSM is preempted.
- Whether a triggered timer remains triggered until explicitly consumed or cleared.
- Whether preemption pauses timer progression.
- What happens if the timer expires while another subsystem owns `sn-resource-control`.
- Whether the original Castle state records the failure or can return to an earlier waiting state.

Hostile engine axiom:

> `timer-triggered` does NOT pause during preemption. If the watchdog reaches expiry while emergency defense owns `sn-resource-control`, the timer becomes triggered and remains triggered until the target implementation explicitly clears/resets/consumes it.

Therefore a correct implementation must distinguish "FSM not currently evaluating" from "time did not pass."

## 5. Builder / foundation evidence

For every Castle builder action record:

- Foundation type passed to `up-assign-builders`.
- Requested builder count.
- Whether the command targets all incomplete foundations of that type.
- Whether multiple simultaneous foundations can exist.
- Whether DUC data is used to select one foundation.
- What happens when an assigned builder dies.
- What happens when the foundation persists but the builder pool drops below the requested count.
- Whether a later reassignment can recover the project.
- Whether the controller detects a missing builder separately from a missing foundation.

Hostile engine axiom:

> `up-assign-builders` is blind. It targets all incomplete foundations of the specified structure type. Without DUC, there is no per-foundation discrimination.

Also treat this as an asynchronous system. The foundation can remain in the world while the capability/FSM is preempted or no longer evaluating its own repair rule.

## 6. Foundation destruction evidence

Prove the exact witness used for Castle presence/completion:

- `building-type-count-total`.
- `building-type-count`.
- `up-pending-objects`.
- Any remote-object/foundation lookup if used.
- Any explicit foundation-destruction rule.
- Any restoration or restart condition after foundation loss.

Important engine distinction from current official behavior: current DE builds have had fixes around unreachable foundations and builder-path failures. The hostile emulator's timeline is authoritative for this test, even where it intentionally diverges from current engine behavior.

Hostile axiom:

> A foundation may be asynchronously destroyed while its FSM is preempted. The later Castle logic must observe the world-state change rather than assuming the old foundation still exists.

## 7. Preemption evidence

Trace the complete transition on attack:

1. Castle state immediately before attack.
2. Rule that detects `town-under-attack`.
3. Exact state mutation.
4. Exact `sn-resource-control` mutation.
5. Telemetry event written for the transition.
6. Rules skipped by jump/preemption.
7. Emergency defense ownership while active.
8. Any Castle timer progression during the skipped interval.
9. Exit condition when the attack ends.
10. Exact restoration rule and resulting Castle state.

Do not call something a "preemption" merely because a jump skips Castle rules. It must be demonstrated as skipped state plus surviving/replaced state plus later re-entry or replacement behavior.

## 8. Telemetry evidence

Before running the test, identify:

- Telemetry ring length.
- Ring index variable.
- Wrap condition.
- Event type field width.
- Sequence field width.
- Owner field width.
- Flags field width.
- Time/tick field width.
- Any reserved bits.
- Packing order from low bit to high bit.
- Signed vs unsigned interpretation.
- The exact integer written on each event.
- The exact decoder/unpacker.

Do NOT invent the bit layout. The target code must provide it.

For every telemetry write, capture:

`tick | event | owner | flags | state | resource-control | watchdog | packed-integer`

## 9. Two-clock audit

Every test observation must be tagged as either:

- Controller-state event: rules, goals, strategic numbers, flags, jumps, timer predicates.
- World-state event: resource deduction, command acceptance, queue creation, pending object, foundation progress, destruction, unit death.

Same-pass visibility only proves controller-state propagation unless the engine action itself is also proven to have completed.

## 10. Exact hostile timeline

The emulator supplies these states/events:

| Tick | Engine state / event |
|---|---|
| 1 | `650 Stone`, `800 Food`, `200 Gold`; `bt-castle-demand = 1`; `bt-fletching-demand = 1` |
| 2 | Trace acquisition of `sn-resource-control`; determine whether Fletching is starved by Castle despite using different resource types |
| 30 | Villager places Castle foundation at `1%`; `building-type-count-total = 1`; trace Castle FSM and resource mutex |
| 35 | `town-under-attack = true`; preemption triggers; trace ownership transition and packed telemetry integer |
| 40 | Active Castle builder is killed; foundation remains at `1%` |
| 120 | Castle watchdog reaches `120 s`; attack/preemption remains active; emergency defense owns resource control |
| 150 | Attack becomes false; preemption ends; trace restoration |
| 151 | Trap tick: original Castle claim is restored. Determine whether the FSM recognizes watchdog expiry from tick 120, masks it, resets it, reassigns builders, or loops on the dead-builder condition |

The emulator owns the timing semantics. Do not silently replace them with real-game assumptions.

## 11. Output contract

Produce one rigid trace row per relevant tick and preserve every state mutation:

`TICK | RULE / EVENT | CASTLE FSM | FLETCHING FSM | sn-resource-control | ESCROW | WATCHDOG | FOUNDATION | BUILDERS | TELEMETRY | WORLD RESULT`

At minimum, the final trace must cover ticks:

`1, 2, 30, 35, 40, 120, 150, 151`

If intervening ticks contain timer, ownership, or state changes, include them rather than hiding them.

For each row, distinguish:

- pre-rule state,
- rule(s) executed,
- state writes,
- engine command,
- end-of-pass engine effect,
- post-rule/controller state,
- newly observable world state.

## 12. Required pass/fail questions

Answer these explicitly from the concrete target code and emulator trace:

1. At tick 2, can Castle's claim starve Fletching even when their physical resource costs differ?
2. At tick 35, exactly who owns `sn-resource-control`?
3. If Castle releases resource control in the same pass that it starts an action, can a lower rule claim the bank before end-of-pass escrow deduction?
4. At tick 40, does the Castle FSM still assume a live builder?
5. At tick 120, is the watchdog triggered even though Castle logic is preempted?
6. At tick 150, is the triggered watchdog still triggered when Castle becomes eligible again?
7. At tick 151, does Castle reassign builders, detect foundation loss, detect builder loss, or return to an already-invalid state?
8. Does Fletching ever obtain resource control after the Castle release but before engine escrow deduction?
9. Is telemetry lossless across ring wrap for the tested events?
10. Is the packed telemetry integer decoded exactly, with no invented field ordering?

## 13. Terminal failure classification

The test must finish with exactly one terminal classification if a critical failure occurs:

- `Escrow Double-Spend`: two controller claims/actions can spend against the same pre-deduction resource bank in one hostile pass.
- `Masked Timer`: watchdog expiry occurs during preemption but is lost, reset, or ignored when the Castle FSM resumes.
- `Dead-Builder Deadlock`: Castle restoration remains dependent on a builder that died, without a reachable reassignment/recovery path.

If none of these occur, report `SURVIVED` and state the exact recovery path demonstrated by the trace.

## 14. Evidence standards

Do not accept:

- comments as proof of behavior;
- rule names as proof of ownership;
- syntax/parse success as proof of execution;
- same-pass state visibility as proof of world completion;
- a jump as automatic preemption;
- a builder assignment command as proof that the builder actually reaches the foundation;
- a timer declaration as proof that the timer survives preemption;
- a telemetry write as proof that the packed value can be decoded without inspecting the bit layout.

The game/hostile emulator behavior is the final validator.

## 15. Known evidence already established

Layer 1 reverse-engineering history already establishes:

- Direct goal/SN mutation is strongly supported as shared controller state visible to later logic in the same pass.
- Same-pass state visibility is distinct from atomic ownership transfer.
- Historical `sn-resource-control` is a persistent control/commitment channel.
- Historical escrow usage is explicit and procedural.
- Historical scripts rely heavily on rule order for economic arbitration.
- No universal global fairness scheduler is proven.
- `up-assign-builders` exists and can assign multiple builders to a structure class.
- `up-pending-objects` and foundation-count APIs exist.
- `timer-triggered` and timer-status checks exist.
- Positive and negative jump semantics are documented.
- Current DE engine versions have had asynchronous foundation/build-path fixes, so emulator assumptions must be kept separate from current game-engine observations.

Historical Layer 1 pass references of special interest:

- PASS 85, `fe79d83c546f0c5b80ab6cc3e135eeb3a90d66d9`: same-pass visibility / handoff boundary.
- Pass 55, `599e1f2a...`: resource-control / escrow / affordability provenance.
- Pass 56, `d96cf55...`: historical economic arbitration / starvation / rule-order archaeology.
- System 04 jump/preemption forensic artifact: `SYSTEM_04_JUMP_PREEMPTION_FORENSICS_v0.1.md`, donor SHA-256 `c6431af3f16597b3de223e65e7b60db6c0b22266c0684915ed435bbb054f55b4`.

## 16. Primary external references

Use these as engine-contract references, not as substitutes for target-code evidence:

- AIRef / UserPatch reference: https://userpatch.aiscripters.net/reference.html
- AoE2 DE scripting discussion covering multi-builder assignment and `sn-enable-new-building-system`: https://steamcommunity.com/workshop/discussions/-1/2217311444333302935/?appid=221380
- Microsoft/Age of Empires II DE update notes, including AI scripting and builder/foundation behavior: https://www.ageofempires.com/games/age-of-empires-ii/updates/

## 17. Execution discipline

Before the test starts, freeze the target source revision and record:

- repository,
- commit SHA,
- every imported `.per`/source file,
- every emulator axiom,
- every telemetry-field definition,
- every numeric constant used by the test.

During execution, do not repair the implementation. The point is to expose whether the existing design survives the hostile semantics. Patch only after the trace and terminal classification are complete.
