# Concrete Semantic Schemas

AoE2DE does not provide typed runtime structs. These schemas are semantic contracts mapped onto goals, facts, actions, strategic numbers, timers, and rule conditions.

## Demand

A demand states what should become true and why it remains relevant.

DEMAND includes:

- owner;
- subject;
- purpose;
- lifecycle state;
- priority when meaningful;
- quantity when meaningful;
- prerequisites;
- conflict class;
- creation condition;
- cancellation or invalidation condition;
- completion witness.

A demand is not an action.

Examples:

Castle demand.

Minimum anti-cavalry army demand.

Second Town Center demand.

Farm-capacity demand.

Siege capability demand.

## Capability

A capability is the means required to satisfy a demand.

CAPABILITY includes:

- owner;
- subject;
- provider;
- prerequisites;
- resource requirements;
- quantity;
- availability;
- pending state when relevant;
- feasibility test.

Capability never substitutes for strategic demand.

Example: a Stable is a capability provider for a mounted-unit demand. The Stable itself is not a strategic reason.

## Action

An action is a request sent to the engine.

ACTION includes:

- owner;
- subject;
- target;
- prerequisites;
- capability;
- feasibility predicate;
- execution command;
- expected witness;
- repeat policy.

Action issuance is never success evidence.

## Witness

A witness is an observable world-state fact that proves the expected result.

WITNESS includes:

- owner;
- subject;
- expected state;
- observation;
- validity condition;
- completion condition;
- failure condition.

Examples:

Castle exists.

Research is completed.

Current age is Castle.

Unit count reaches the target.

A queued or pending total is not automatically a completion witness.

## Release / invalidation

A demand may:

- complete;
- transition to another objective;
- become obsolete;
- be cancelled by Strategy;
- lose its capability;
- remain valid while temporarily blocked.

Execution state must be cleaned up when its owning demand ends.

## Interruption rule

Temporary execution failure must normally preserve valid strategic demand.

This is a central product requirement, not an optional compiler exercise.

## Resource conflict

A demand may compete for resources.

Economy arbitrates the temporary allocation, but Strategy retains ownership of the strategic reason.

sn-resource-control or equivalent global mechanisms are exceptional. They require a real contention problem and a documented release path.

## Hard rules

Action is never the witness.

Capability is never the demand.

can-* is feasibility, not completion.

Pending is not completed.

A strategy phase is not a task queue.

A timer is not strategic truth.

State must buy real control capability or it should probably not exist.
