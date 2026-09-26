# Interfaces and Ownership Contracts

The module map says where code belongs. These contracts define who decides, who writes, what crosses the boundary, and what constitutes completion.

## Engine

Owns engine configuration, engine-native facts/actions, strategic-number interfaces, timers as engine mechanisms, and engine-specific primitives.

Provides facts, capabilities, feasibility predicates, and actions. It does not decide strategic purpose.

Contract: engine permission to execute is not proof that the requested world-state change occurred.

## State

Owns persistent representation of strategy, demands, transitions, temporary modes, and controlled timers.

Every persistent state variable has one semantic owner, legal values, initialization, transition rules, readers, and release behavior.

State represents decisions; it does not invent them.

## Information

Owns observations and interpretations of external game state: scouting, enemy/map information, threat facts, and freshness/re-observation.

Contract: observation informs interpretation; Information does not directly spam strategic responses.

## Strategy

Owns strategic purpose: strategy selection, posture, age objectives, economic/military posture, adaptation, and creation/cancellation of strategic demands.

Contract: Strategy decides why; domain modules determine how.

## Economy

Owns worker/resource allocation, farms, economic technologies, resource pressure, recovery, and transient arbitration between legitimate demands.

Contract: Economy owns resource allocation, not the strategic objectives competing for those resources.

## Construction

Owns the building lifecycle: demand, prerequisite checking, existing/pending checks, builder requirements, build request, construction state, completion, and release.

Contract: a build request is not completion. Completion requires a world-state witness.

## Production

Owns production capability and queues for villagers, military units, production buildings, and upgrades.

Contract: Production converts legitimate demands into feasible production actions; it does not independently invent strategic need.

## Military

Owns military demands below strategic intent and military execution: defense, composition, readiness, attack, siege, reinforcement, retreat, and military recovery.

Contract: Military may translate strategy and information into military demands, but does not silently rewrite global strategy.

## Engineering

Owns validation and verification discipline: parser/engine legality checks, lifecycle witnesses, failure detection, diagnostics, and recovery analysis.

Contract: Engineering verifies and diagnoses; it does not become a second Strategy or generic manager.

## Universal contract

Strategy owns why. Domain modules own how. Engine owns engine-native feasibility and execution. World state proves what actually happened. Engineering verifies the chain.
