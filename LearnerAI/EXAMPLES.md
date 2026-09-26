# Worked Examples: Specification Only

This file reserves canonical teaching examples. No executable code belongs here yet.

## Example A — Castle

Strategic intent: establish Castle-age infrastructure.

Demand owner: Strategy.

Domain requirement: Construction requires one Castle.

Capability: Castle Age, sufficient stone/resources, eligible builder, required engine capability.

Feasibility: engine-native can-build condition is true.

Action: Construction requests Castle construction.

Witness: Castle exists in world state.

Release: construction demand and associated temporary commitments are released; Castle infrastructure demand may transition to the next objective.

Blocked case: preserve legitimate strategic intent while diagnosing resource, prerequisite, builder, pending, or competing-demand blockage.

## Example B — defensive Spearmen

Observation: Information identifies a cavalry threat.

Interpretation: Strategy/Military establishes a defensive requirement.

Demand: maintain the required minimum Spearman count.

Capability: appropriate production building, technology/age prerequisites, and resources.

Feasibility: engine-native can-train condition.

Action: Production queues the unit.

Witness: unit count reaches the requested threshold.

Release: minimum-defense production demand is satisfied, while continued threat observation may create a new demand later.

## Example C — Fletching

Demand: technology is strategically/economically admissible.

Capability: Blacksmith and prerequisites.

Feasibility: engine permits research.

Action: research request.

Witness: technology is actually researched.

Release: research demand ends and downstream capabilities may change.

## Example D — adaptive military production

Observation → interpretation → military demand → production capability → feasible action → unit witness → threat reassessment.

The important lesson is not the specific unit count. The lesson is the lifecycle and ownership boundary.

## Rule for future examples

Every example must document owner, demand, capability, feasibility, action, witness, release, conflicts, and blocked/recovery behavior before executable code is written.
