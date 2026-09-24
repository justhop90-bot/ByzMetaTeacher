# Basilisk Preemption + Telemetry Implementation Checklist

Acceptance target: temporary emergency ownership interruption must not reset, orphan, or resurrect a persistent capability lifecycle.

## 1. XS integration
Status: IMPLEMENTED
Cross-reference: UGC XS programmer guide; UGC beginner AI XS guide; aoe2-ai-parser diagnostics.
Sources: https://ugc.aoe2.rocks/general/xs/programmer/ | https://ugc.aoe2.rocks/general/xs/beginner/ | https://github.com/joerollman/aoe2-ai-parser/blob/main/docs/workflows/validator-diagnostic-codes.md
Requirements: .per includes the .xs file; xs-script-call invokes a zero-parameter function; validator rejects missing .xs extension and missing drain function.

## 2. Mutex semantics
Status: IMPLEMENTED
Cross-reference: community sn-resource-control pattern; Basilisk resource-control lifecycle.
Source: https://gist.github.com/Andygmb/1e3a6d9d444b2dfa8c40
Requirement: emergency receives its own claim. Emergency never bypasses or blindly clears sn-resource-control.

## 3. Preemption scope
Status: IMPLEMENTED
Cross-reference: current Basilisk owner scan; TC lifecycle; community resource-control convention.
Only bt-tc2-claim and bt-tc3-claim are preemptible, and only while the corresponding TC project is in the resource-claimed stage.
Protected: age claims, Castle/Imperial prerequisite claims, Castle claim, Monastery, Mill, University, Siege, Blacksmith, Market, Bombard University, and military siege-workshop claims.

## 4. Snapshot-before-displacement
Status: IMPLEMENTED
Required order: capture original owner and resource-mode -> activate preemption -> acquire emergency owner.
Validator rejects owner displacement without an earlier owner snapshot.

## 5. Watchdog independence
Status: IMPLEMENTED
Cross-reference: Basilisk TC watchdog lifecycle; timer-driven community economy pattern.
Sources: https://github.com/dekespo/aoe2_ai_scripts/blob/master/dekespo_ai/economy.per | Basilisk/Basilisk.per
Rule: preemption never disables, restarts, or replaces the TC watchdog.

## 6. World-state completion
Status: IMPLEMENTED
Completion is witnessed by actual TC count, not by current mutex ownership.
Completion while emergency ownership is active now terminates the emergency claim rather than restoring a stale claim.

## 7. Abandonment and restoration
Status: IMPLEMENTED
Resume only when the original TC project remains valid and engine feasibility still exists.
Abort returns a still-valid project to persistent demand; a vanished project is not resurrected.

## 8. Emergency defense
Status: IMPLEMENTED
At most one immediate counter is issued per preemption pulse: Spearman for cavalry threat or Skirmisher for ranged threat.
Both paths require engine-native can-train and queue/completed witnesses.

## 9. FIFO telemetry
Status: IMPLEMENTED
Four-slot FIFO uses explicit write-head, read-head, occupancy, sequence, overflow counter/state, per-slot event, owner, flags, timestamp, and sequence.
Empty is count 0. Full is count 4. Newest event is dropped on overflow; existing events are never overwritten.

## 10. No one-deep temporary event
Status: IMPLEMENTED
Events are written directly into the selected FIFO slot. There is no deferred global event register that can be overwritten before injection.

## 11. XS drain
Status: IMPLEMENTED
Drain is explicitly invoked by timer-triggered xs-script-call and processes at most four events per invocation.
XS is observational only. It never writes strategy, resource-mode, demand, commitment, ownership, or watchdog state.
Cross-reference: UGC programmer guide; parser diagnostics.

## 12. Goal namespace
Status: IMPLEMENTED
Historical collision fixed: bt-imperial-commitment-goal and bt-debug-last-strategy-goal previously shared GoalId 710.
Diagnostic strategy latch moved to GoalId 768. The former telemetry GoalIds 729-766 are now retired.
Validator rejects duplicate numeric GoalIds.

## 13. Timer-driven telemetry
Status: IMPLEMENTED
Cross-reference: dekespo economy timer pattern and Basilisk existing timers.
Source: https://github.com/dekespo/aoe2_ai_scripts/blob/master/dekespo_ai/economy.per
Strategic arbitration stays live. Only telemetry consumption is throttled.

## 14. Validator contracts
Status: IMPLEMENTED
Validator checks include syntax, .xs include integrity, duplicate GoalIds, protected claims, snapshot order, watchdog non-interference, completion/abort paths, FIFO occupancy and overflow, explicit XS drain, bounded XS loop, and XS chat-data signature.

## 15. Deterministic replay gate
Status: REQUIRED
Replay must prove: resume after interruption; completion while preempted; watchdog expiry while preempted; project disappearance while preempted; rapid begin/defense/end ordering; FIFO full and overflow; monotonic sequence; unchanged watchdog state.

## 16. Native runtime gate
Status: REQUIRED OUTSIDE REPOSITORY
Native AoE2DE testing must prove that the XS include loads, xs-script-call resolves, XS goal access works in AI context, TC ownership actually transfers, watchdog state survives the interruption, and rapid telemetry events are observable.
Cross-reference: UGC beginner guide explicitly recommends custom-scenario testing for AI XS integration.
Source: https://ugc.aoe2.rocks/general/xs/beginner/