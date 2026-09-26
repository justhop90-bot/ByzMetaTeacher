# Authoritative Goal

## Definition

The Learner AI is a teaching/reference workspace for learning how to write competent AoE2DE AI scripts using patterns that experienced community scripters can recognize, trace, validate, and maintain.

It is not intended to be a competitive tournament bot, optimized opening package, research simulator, or generalized software architecture exercise.

## What good means here

A good learner script demonstrates:

1. Real AoE2DE engine knowledge rather than invented abstractions.
2. Clear ownership of facts, state, decisions, actions, and completion.
3. Persistent strategic intent rather than disconnected trigger spam.
4. Engine-native feasibility checks before actions.
5. World-state witnesses after actions.
6. Explicit release and cancellation conditions.
7. Resource and production conflicts that can be traced.
8. Adaptive behavior driven by observations.
9. Community-familiar modular organization.
10. Conservative, readable rules that teach the engine instead of hiding it.

## Non-goals

Do not optimize every opening. Do not maximize APM. Do not create a scheduler, universal manager, abstraction-heavy framework, or opaque priority system merely to make the design look sophisticated.

The standard is understandable, traceable, engine-native community AI practice.

## Teaching principle

Every important behavior should let a learner answer:

- Who owns the decision?
- What is the persistent intent?
- What observation justifies it?
- What capability is required?
- What does the engine permit now?
- What action is requested?
- What world-state fact proves success?
- What releases or cancels the demand?
- What happens if it remains blocked?

If those answers cannot be traced, the behavior is not sufficiently specified.
