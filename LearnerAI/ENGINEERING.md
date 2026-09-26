# Engineering and Verification Standard

Engineering prevents plausible-looking .per code from being mistaken for a competent player.

## Proof layers

There are four different proof questions.

1. Semantic proof: did we specify a coherent lifecycle?
2. Native proof: is the generated .per legal according to the native parser/linter?
3. Static control proof: are ownership, source order, dependencies, and release paths coherent?
4. Runtime proof: did AoE2DE actually behave as intended?

No layer substitutes for the next.

## Static checks

Every implementation phase should examine:

- parser syntax;
- logical operator arity;
- native identifiers and command forms;
- rule element limits;
- source/load order;
- first writer versus first consumer;
- all readers and writers of important state;
- dead-end, unfed, blocked, functionally-disconnected, unfinished, duplicate/conflicting, and open-loop state;
- repeated actions without release;
- missing pending guards;
- missing feasibility;
- impossible witnesses;
- resource claims without release;
- stale demands after strategic invalidation.

## Runtime verification

For important behaviors record:

    observation
      -> interpretation
      -> strategy
      -> demand
      -> capability
      -> feasibility
      -> action
      -> world-state change
      -> witness
      -> release
      -> reassessment

Runtime testing must include failure and interruption cases.

## Product acceptance

The first real acceptance target is the Dark -> Feudal -> Castle Byzantine vertical slice.

A green parser is not acceptance.

A clean compiler report is not acceptance.

A valid generated .per is not acceptance.

The player must actually preserve a coherent economy and military position while reaching Castle and recovering from ordinary disruption.

## Native backend

Native .per validation remains delegated to the pinned aoe2-ai-parser backend.

LearnerAI verifies the backend identity and protocol. It does not copy its implementation.

The current compiler suite contains 48 tests according to the latest checked-in verification record. That number is compiler evidence only; it says nothing about gameplay quality.

## Recovery discipline

Persistent strategic intent normally survives temporary execution failure.

Use transient backoff and explicit cancellation/obsolescence instead of accumulating retry counters.

Global resource control is exceptional.

Timers are execution tools, not strategy.

## Source of truth

Use LearnerAI/SOURCE_MAP.md whenever an implementation question does not have an obvious authoritative source.
