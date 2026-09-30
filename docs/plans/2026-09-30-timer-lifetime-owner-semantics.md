# Timer Lifetime / Owner Semantics

Date: 2026-09-30
Base main: 7ee770fc8d2fec56d6e0c1d4e920e370c73ea6f7
Implementation branch: timer-owner-release-control

## Audited gap

The compiler already models declared timers as persistent execution memory and has a separate persistent-state lifetime analysis. The missing seam was the typed relationship between a compiler-owned timer, its demand owner, the demand's explicit release contract, and a provable post-release cleanup operation.

## Community cross-reference

Community `.per` practice uses timers primarily for cadence, throttling, delay, rearm, and recurring control. The common idiom is to enable a timer, test `timer-triggered`, disable it, and re-enable it for another cycle. This reinforces the boundary that timer state is control/cadence state, not completion or strategic truth.

The implementation therefore does not simulate timer expiry or infer runtime ownership. It applies owner-release cleanup policy only to compiler-declared timer state in the semantic demand model.

## Implemented policy

- `TimerState.owner` is a read-only projection of `TimerState.request.request_id.owner`.
- `PersistentControlRef.owner` is copied from that semantic owner; native TimerId is not semantic identity.
- Declared compiler timers use lifetime `UNTIL_OWNER_RELEASE` as compiler policy.
- `disable-timer` is explicit cleanup.
- constant-negative `up-set-timer` is explicit cleanup.
- `timer-triggered` is never cleanup.
- initialization `disable-timer` is not owner-release cleanup.
- dynamic timer writes remain `UNKNOWN`.
- owner release is located structurally from the existing release contract and lifecycle state transition; emitted comments are not parsed.
- same-rule cleanup must occur after the release state write.
- later cleanup must be reachable through the existing `RuleReachabilityReport`.
- unresolved control flow or unresolved timer lifetime yields `UNKNOWN`, not a proof.

## Semantic outputs

`PersistentControlCleanupObligation` reports:

- `SATISFIED`: cleanup is explicitly present and statically reachable after owner release.
- `REQUIRED`: the timer lifetime was activated but no acceptable post-release cleanup was proven.
- `UNKNOWN`: release/cleanup reachability or timer lifetime cannot be statically closed.
- `NOT_APPLICABLE`: no timer lifetime activation is visible in the analyzed effective rules.

Persistent-control diagnostics are bridged into the existing rule-diagnostic taxonomy and artifact annotation path rather than creating a parallel compiler diagnostic channel.

`PSTATE-007` remains the generic timer lifetime analysis. The owner/release pass adds stronger compiler-owned demand lifecycle context.

## Invariants

The implementation does not claim:

- DE timer countdown/pass granularity;
- runtime expiry timing;
- automatic disable or automatic rearm;
- TimerId reuse semantics;
- engine-level timer owner identity;
- exact cross-pass cadence behavior;
- that timer-triggered or timer status proves completion, release, target liveness, resources, or strategic truth.

## Focused regression coverage

`test_persistent_control.py` covers projection, owner mismatch, same-release cleanup, later reachable cleanup, pre-release cleanup, unreachable cleanup, dynamic lifetime, timer-triggered non-cleanup, initialization cleanup distinction, negative `up-set-timer` cleanup, multiple timers, and determinism.

`test_timer_allocation.py` covers semantic owner projection alongside existing binding determinism.

`test_semantic_program.py` covers persistent-control assembly and owner validation.

`test_rule_diagnostics.py` covers bridging persistent-control diagnostics into the existing rule taxonomy.

## Acceptance gate

- [ ] Focused timer/persistent-control tests pass.
- [ ] Full compiler regression passes.
- [ ] Native zero-findings acceptance passes.
- [ ] 9/9 native-support determinism passes.
- [ ] Snapshot comparison passes.
- [ ] Compiler verification gate passes.

These boxes are intentionally unchecked until CI verifies the current implementation head.

## Evidence still requiring runtime probes

Runtime experiments remain required for timer countdown/pass granularity, trigger timing, automatic expiry/disable behavior, cross-pass cadence semantics, reuse behavior, and any claim that a native timer has an engine-defined semantic owner.
