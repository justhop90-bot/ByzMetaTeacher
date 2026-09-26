# Canonical Behavior Traces

These examples define the kinds of complete behaviors the stock-style Byzantine player must eventually implement.

They are specifications until executable code exists.

## Example A — Castle conversion

Observation: economy is stable enough for a Castle trajectory and threat does not require uncontrolled Feudal mass.

Interpretation: Castle conversion remains strategically valuable.

Demand: Strategy owns persistent Castle demand.

Capability: Castle prerequisites, resources, builder path, and construction capability.

Feasibility: engine says construction can start.

Action: Construction issues build.

Pending: action enters construction lifecycle and duplicate construction is blocked.

Witness: Castle exists.

Release: construction state releases. Strategy reassesses the now-Castle position and opens downstream economic, production, military, siege, Monk/relic, and technology demands as justified.

Interruption: enemy pressure may temporarily raise military demand. Castle intent survives if still strategically valid.

## Example B — Dock and fishing

Observation: the map has meaningful fish/water and the fish economy is strategically valuable.

Interpretation: water economy is admissible.

Demand: Strategy opens a dock/fishing demand.

Capability: dock placement, builders, fishing-ship production, fish access.

Feasibility: engine permits the current build/train actions.

Action: build dock, then produce fishing ships.

Witness: dock exists; fishing fleet reaches the useful target.

Reassessment: enemy naval pressure or fish depletion may change the water posture.

Release/invalidation: if water loses strategic value, naval expansion is stopped and land economy resumes.

## Example C — Transport

Observation: a required resource base or military target is separated by water and ordinary land access is insufficient.

Interpretation: transport capability is strategically required.

Demand: transport capability.

Capability: dock + transport ship + protected embarkation/landing path.

Action: produce and use transport.

Witness: transport operation reaches the intended world-state outcome.

Failure: preserve strategic intent while changing landing/escort or abandoning the operation when it becomes obsolete.

## Example D — Defensive Spearmen

Observation: current enemy composition contains meaningful cavalry threat.

Interpretation: maintain minimum anti-cavalry floor.

Demand: Military owns a finite standing-defense requirement.

Capability: Barracks and production resources.

Feasibility: can-train and queue/pending guards.

Action: Production trains.

Witness: actual unit count reaches the target.

Release: the finite production deficit clears. Continued cavalry threat can recreate the demand later.

## Example E — Siege

Observation: enemy ranged mass, fortified position, buildings, or composition makes siege materially useful.

Interpretation: siege capability is admissible.

Demand: Siege Workshop and relevant siege-unit demand.

Capability: Workshop, resources, required research/age, protected production.

Action: build workshop, then produce siege.

Witness: workshop and actual siege count.

Release/reassess: production scales or stops when the tactical problem changes.

## Example F — Monks and relics

Observation: a relic is available and the route is safe enough relative to expected value, or Monks are strategically useful for healing/conversion.

Interpretation: Monk/relic demand is admissible.

Demand: monastery and Monk/relic objective.

Capability: monastery, Monk production, escort, map access.

Action: build monastery, train Monk, contest/collect relic.

Witness: monastery exists; Monk count and relic state change.

Release/reassess: stop Monk investment when relic opportunity closes, Monks are lost, or military/economic opportunity cost becomes excessive.

## Example G — Fortification

Observation: exposed economy, chokepoint, sustained enemy pressure, or late positional defense creates a defensive requirement.

Interpretation: fortification is worth the resource cost.

Demand: wall/gate/tower/fortification capability.

Capability: builders, placement, age, stone/wood, feasible action.

Action: construct the chosen defensive structure.

Witness: structure reaches the required world state.

Release/reassess: defensive demand changes as the enemy or map position changes.

## Required evidence

Every future example must document:

owner;
observation;
interpretation;
demand;
capability;
feasibility;
action;
witness;
release/invalidation;
resource interaction;
interruption;
recovery;
reassessment.
