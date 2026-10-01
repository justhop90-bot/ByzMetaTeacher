# Byzantine Threat Arbitration Checklist

Date: 2026-10-01
Scope: 1v1 standard-land Byzantine controller.

## Threat-class cross-reference

- [x] Mounted pressure has a typed Feudal trigger and Castle escalation path.
- [x] Ranged pressure has a typed Feudal trigger and Skirmisher demand.
- [x] Infantry pressure has a typed Castle trigger and premium response.
- [x] Siege pressure has a typed Castle trigger and mobile response.
- [x] Mixed threats preserve orthogonal counter roles instead of collapsing to one package.
- [x] Same-class overlapping packages resolve deterministically by package priority.
- [x] Suppressed same-class packages are recorded explicitly in runtime state.

## Compiler contract

- [x] CounterPackage remains strategy data, not an execution scheduler.
- [x] Package triggers bind through existing native StrategicObservation references.
- [x] Package activation feeds the existing StrategicDemand lifecycle.
- [x] Capability, feasibility, escrow, witness, release, and recovery remain downstream.
- [x] Counter arbitration participates in runtime fingerprints.
- [x] Counter-package changes remain explicit reassessment signals.

## Acceptance coverage

- [x] Five Byzantine package identities are registered.
- [x] Siege package activates only from the native mangonel-line observation.
- [x] Mixed mounted+ranged pressure produces `MIXED` arbitration.
- [x] Same-class lower-priority package is suppressed.
- [x] Unknown threat evidence does not create an executable counter demand.
- [x] Known threat with unknown production feasibility becomes `STRATEGIC_ACTIVE_BLOCKED`.
- [x] Counter arbitration is deterministic across repeated evaluation.
- [ ] Add ranged+siege and mounted+siege integration fixtures.
- [ ] Add explicit composition-quality arbitration for upgrades, army-role coverage, and replacement rate.

## Evidence boundary

Threat thresholds are compiler policy over verified native observations. Community counter-unit patterns are precedent, not engine proof. Current Byzantine roster changes are sourced from Update 185872 and the repository's pinned game-data layer.

## Next layer

The next substantive gap is not another individual unit rule. It is composition quality: determining whether the selected counter package has the required role coverage, upgrade state, replacement capacity, and economic admissibility before attack arbitration consumes it.