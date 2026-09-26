# Universal Lifecycle

The same control grammar applies to economy, construction, production, military, research, and age transitions.

    DEMAND
      -> ADMISSIBILITY
      -> CAPABILITY
      -> FEASIBILITY
      -> ACTION
      -> WORLD-STATE CHANGE
      -> WITNESS
      -> RELEASE / INVALIDATE
      -> REASSESS

## Demand

A persistent statement that something should become true.

It survives a rule pass when the strategic reason remains valid.

## Admissibility

The reason for the demand still exists.

Examples:

- enemy cavalry still threatens us;
- Castle remains strategically justified;
- production is still below the required standing target;
- a Town Center remains economically admissible.

If the reason disappears, the demand may become obsolete.

## Capability

The responsible domain identifies what must exist to satisfy the demand.

Example:

Castle demand -> Castle-capable construction path.

Military unit demand -> production building and queue capability.

Research demand -> provider building plus research capability.

## Feasibility

Engine-native predicates decide whether the action can happen now.

can-build, can-train, can-research, resource/pending prerequisites, and similar facts belong here.

## Action

One owning domain issues the action.

The action is a request.

## World-state change

The engine may asynchronously construct, train, research, move, or otherwise update the game.

## Witness

A world-state fact proves the expected result.

The witness must not be something that merely repeats the action's feasibility.

## Release / invalidation

Completion releases the finished demand or advances it.

Strategic invalidation cancels an obsolete demand.

Capability loss may release local execution state while preserving the strategic demand if the capability can return.

## Blocked lifecycle

If the demand remains valid but feasibility is false:

- preserve the demand;
- diagnose the blocking condition;
- use transient backoff only where useful;
- allow other legitimate work to proceed;
- retry when conditions change.

Do not accumulate retry counters as a substitute for reasoning.

## Interruption

The desired player behavior is:

    preferred plan
      -> interruption
      -> temporary response
      -> strategic intent survives
      -> recovery
      -> preferred plan resumes or is deliberately replaced

That is the core resilience requirement of the Byzantine player.

## Reassessment

Information and current world state feed Strategy and domains again.

The controller is a feedback loop, not a build-order replay.
