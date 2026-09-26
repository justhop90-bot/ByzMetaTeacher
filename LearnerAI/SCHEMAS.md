# Concrete Semantic Schemas

These are semantic schemas for .per design. AoE2DE does not provide general-purpose structs, so implementation should use goals, constants, facts, actions, strategic numbers, timers, and rule conditions rather than pretending the engine is a typed application framework.

## Demand

DEMAND { owner, subject, purpose, state, priority, quantity, prerequisites, conflict-class, creation-condition, cancellation-condition, completion-witness }

Required concepts: owner, subject, purpose, lifecycle state, creation, cancellation, and completion witness. Quantity and priority apply when relevant.

Typical states: inactive, active, preparing, executing, complete, cancelled.

## Capability

CAPABILITY { owner, subject, provider, prerequisites, resource-requirements, quantity, availability, pending-state, feasibility-test }

Capability answers what means exist. Feasibility answers whether the engine permits the action now. They are not the same thing.

## Action

ACTION { owner, subject, target, prerequisites, capability, feasibility, execution, expected-witness, repeat-policy }

An action is an engine request, not a success record. Every important action should have an expected witness and an explicit repeat policy.

## Witness

WITNESS { owner, subject, expected-state, observation, validity-condition, completion-condition, failure-condition }

Witnesses may prove existence, count, state transition, technology completion, economic transition, or military outcome.

## Release

RELEASE { owner, demand, trigger, witness, cleanup, next-state }

A demand can release because it completed, became obsolete, was cancelled by strategy, or otherwise no longer applies. Release must clean up associated commitments where applicable.

## Domain examples

Construction demand → construction capability → build action → building-exists witness → release.

Military unit demand → production capability → train action → unit-count witness → release or escalation reassessment.

Age demand → age capability/feasibility → research action → current-age witness → transition/release.

Economic demand → resource allocation capability → allocation action → observed economic state → release/reassess.

## Hard rule

Action is never the witness. Capability is never the demand. Existence of a capability is never proof of successful execution.
