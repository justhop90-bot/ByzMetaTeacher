# Path-Sensitive Recurrent Execution Semantics — 2026-09-27

## Objective

Close the highest-leverage remaining generic compiler hole: the gap between
source-order/persistent-state diagnostics and a path-sensitive model of
recurrent .per execution.

The implementation is a bounded abstract interpreter, not a game simulator.
It models exact persistent Goal/SN/Timer state where the compiler can prove the
value, rule enablement, and native control transfers. Unknown world facts branch
conservatively and never become compiler certainty.

## Implementation checklist

- [x] Define a public recurrent execution analysis contract.
- [x] Model recurrent versus one-shot rule lifetime through existing
      RulePassBehavior and disable-self state.
- [x] Model same-pass persistent Goal writes and later-pass persistence.
- [x] Model exact Strategic Number writes where set-strategic-number supplies
      a literal.
- [x] Model exact Timer enable/disable/status state without treating timer
      expiry as immediate truth.
- [x] Model up-jump-rule using the native current-index + RuleDelta + 1 target
      convention already used by PassScheduler.
- [x] Branch conservatively on unknown guards.
- [x] Detect guaranteed recurrent forward-jump preemption.
- [x] Detect persistent-state starvation when a guaranteed recurrent writer
      repeatedly establishes the exact value contradicting a consumer guard.
- [x] Preserve a bounded-state failure mode so state-space exhaustion becomes
      RUNTIME_DEPENDENT rather than a false NEVER_RUNNABLE proof.
- [x] Add deterministic recurrent diagnostics REX-001 through REX-004.
- [x] Map recurrent diagnostics into the existing RuleDiagnostic surface.
- [x] Wire recurrent analysis into compile-time rule diagnostics for source,
      package, and staged-file compilation paths.
- [x] Add focused regression tests for starvation, successful state transfer,
      disable-self persistence, recurrent preemption, and one-shot recovery.
- [x] Add rule-diagnostic integration coverage.
- [x] Preserve existing native parser ownership and avoid introducing a second
      scheduler/manager language.
- [ ] Verify the full GitHub compiler matrix and native zero-findings gate on
      the completed implementation commit.
- [ ] Merge the verified tranche into main.

## Explicit non-goals

- No AoE2 runtime simulator.
- No inference of arbitrary world facts.
- No automatic strategy selection.
- No generic scheduler abstraction.
- No DUC/search-state implementation.
- No replacement of the native parser or AIRef command authority.
