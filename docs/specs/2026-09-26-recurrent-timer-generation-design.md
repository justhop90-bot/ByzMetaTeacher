# Recurrent Timer Generation Semantics Design

**Date:** 2026-09-26

## Scope

This design adds the minimum timer-generation and pass-scheduler semantics required for a generic AoE2 .per compiler to represent recurrent timer idioms faithfully. It is compiler-core work only.

## Evidence and cross-reference

The checked-in AIRef schema defines enable-timer, disable-timer, timer-triggered, and up-timer-status, including timer states disabled, triggered, and running. AIRef also defines RuleDelta for native rule jumps.

Public AoE2 community scripting uses a stable recurrent pattern: arm a timer, test timer-triggered, explicitly disable it, perform timer-driven work, and re-enable it for the next interval. Examples also use disable-self after one-shot timer initialization and use up-jump-rule for same-pass skips and loops.

The Naga database identifies Naga as a long-lived community .per AI with broad strategy and feature coverage. This tranche does not reproduce Naga strategy; it targets the recurrent native execution substrate that Naga-class scripts depend on.

## Revised checklist

- [x] Timer identity is persistent and generation-based.
- [x] Every activation receives a new generation.
- [x] Disable/reset invalidates the previous generation.
- [x] Pending expiries carry timer identity and generation.
- [x] Stale pending expiries are discarded instead of mutating a newer activation.
- [x] Current-generation trigger reads are level-triggered and non-consuming.
- [x] Explicit timer mutations are same-pass visible.
- [x] Elapsed-time expiry is committed across a pass boundary and first visible to the next pass.
- [x] disable-self affects later rule eligibility without aborting the current action sequence.
- [x] Jumps do not advance timer time.
- [x] Native up-jump-rule relative semantics are preserved: zero-based target = current index + delta + 1.
- [x] The scheduler advances to the next pass only after the reachable rule scan exhausts.
- [x] The compiler distinguishes timer evidence from world-state completion evidence.
- [x] Standard enable-timer, disable-timer, timer-triggered, and up-timer-status are represented in persistent-state analysis.
- [x] UserPatch up-set-timer is treated as an interval setter/disable operation.
- [x] Exact intra-pass wall-clock scheduling is left engine-defined; the compiler scheduler uses explicit pass-boundary elapsed time.

## Runtime model

A timer is initialized by compiler/runtime binding as an existing native slot in DISABLED state. No source-language initialization command is invented.

Each timer maintains timer identifier, current generation, status, deadline when RUNNING, and trigger generation when TRIGGERED.

enable-timer creates a new generation, clears any old trigger, and starts RUNNING.

disable-timer invalidates the current generation and returns the timer to DISABLED.

IR-level reset is equivalent to disable for generation invalidation.

Expiry is represented by a pending record carrying timer identifier, generation, and deadline. At the pass boundary, a pending expiry may transition the matching RUNNING generation to TRIGGERED. If the generation no longer matches, or the timer is no longer RUNNING, the pending expiry is stale and is discarded.

A trigger read is true only when status is TRIGGERED and trigger_generation equals the current generation. Reading a trigger never consumes it.

## Pass scheduler

At pass start, pending expiries are committed before rule predicates are evaluated.

The scanner walks effective rule order. Disabled rules are skipped. An enabled rule evaluates facts against current persistent state. If true, actions execute in source order.

Timer mutations and rule-control mutations are immediately visible to later rules in the same pass. disable-self disables the current rule for subsequent scans but does not abort the current action list.

A jump changes the next rule address in the same pass. Native up-jump-rule addressing is represented explicitly so the compiler cannot silently reinterpret RuleDelta.

A pass ends only when the scan reaches beyond the effective rule set without another control transfer. Only then does the scheduler advance logical elapsed time and stage new pending timer expiries for the following pass.

## Non-goals

This tranche does not implement full arbitrary .per fact/action semantics, DUC/search state, world-state simulation, or strategy state machines. Unknown native actions remain outside the scheduler rather than receiving invented semantics.

## Verification target

Focused tests cover initial disabled state, generation creation, disable/reset invalidation, re-enable from TRIGGERED, stale expiry rejection, current-generation trigger reads, same-pass writes, next-pass trigger visibility, self-disable, jump/timer interaction, native jump relative semantics, pass-boundary staging, native timer access extraction, zero-second timers, repeated re-enable, out-of-range jumps, and deterministic repeated traces.
