# Timer Lifetime / Owner Semantics Checklist

Date: 2026-09-30
Base main: 1dfd7185968deafb1d8c58034270c662bbcfc741
Branch: timer-lifetime-owner-semantics

## Audited gap

The compiler already models timers as explicit persistent engine state and preserves
source/rule order, but the persistent-state pass did not distinguish a timer that is
explicitly cleaned up from one that may remain armed after its controlling lifecycle
moves on.

Authoritative cross-references:

- `LearnerAI/Compiler/COMMUNITY_ENGINE_SEMANTICS_CHECKLIST_2026-09-26.md`
  - unchecked timer lifetime/owner analysis
  - unchecked diagnostic for timers left running after controlling demand release
  - unchecked distinction between timing/cooldown state and durable strategic state
- `05-SN-TIMER.md`
  - timer namespace/allocation is implemented
  - timer runtime states are compiler policy, not engine proof
  - owner/rearm/cleanup across passes remain UNKNOWN
- `LearnerAI/Compiler/ir/recurrent.py`
  - `TimerRequest` / `TimerState`
  - DISABLED/RUNNING/TRIGGERED generation model
- `LearnerAI/Compiler/semantic/persistent_state.py`
  - existing timer Goal/SN/Timer access ordering and reachability analysis
- `LearnerAI/Compiler/tests/test_timer_persistent_state.py`
  - existing timer read/write extraction contracts
- `LearnerAI/Compiler/tests/test_persistent_state.py`
  - lifetime regression boundary for the new warning

## Implemented compiler policy

- `enable-timer` is a statically definite timer START.
- `disable-timer` is a statically definite timer CLEANUP.
- `up-set-timer` with constant interval >= 0 is START.
- `up-set-timer` with constant interval < 0 is CLEANUP.
- `up-set-timer` using Goal/SN-derived interval values remains UNKNOWN and does not
  trigger a lifetime-direction warning.
- A START with no later reachable CLEANUP produces warning `PSTATE-007`.
- The diagnostic identifies the START rule as the static owner candidate. This is
  rule/source ownership evidence only, not a claim that the compiler has proven a
  semantic demand owner or runtime lifecycle release.
- Timer state remains a distinct `PersistentStateKind.TIMER`; the analyzer does not
  reinterpret timer cadence as strategic state or world-state truth.

## Invariants

- No countdown/pass-granularity claim is introduced.
- No timer-triggered state is treated as completion truth.
- No automatic disable/rearm action is emitted.
- No timer-ID reuse semantics are promoted.
- Runtime DE behavior remains outside this repair.
- Existing Goal/SN persistent-state diagnostics remain unchanged.

## Tests

Focused regression coverage:

- open timer without cleanup -> `PSTATE-007` warning
- explicit `disable-timer` cleanup -> no `PSTATE-007`
- dynamic `up-set-timer` interval -> no inferred START/CLEANUP direction

## Verification gate

- [ ] Focused persistent-state tests pass.
- [ ] Full compiler regression passes.
- [ ] Native zero-findings acceptance passes.
- [ ] 9/9 native-support determinism passes.
- [ ] Snapshot comparison passes.
- [ ] Compiler verification gate passes.

## Explicitly open

- actual DE countdown/pass granularity
- runtime expiry timing
- semantic demand ownership of native timers
- runtime release behavior
- timer reuse/lifetime across independently authored source packages
