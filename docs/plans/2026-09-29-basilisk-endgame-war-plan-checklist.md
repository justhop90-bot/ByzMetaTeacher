# Basilisk Endgame / War-Plan Compiler Checklist — 2026-09-29

## Purpose

This checklist converts community AoE2 AI attack practice into an implementable Basilisk endgame/war-control layer.

The target is not a generic RTS simulator, tactical combat simulator, or universal scheduler. The target is a persistent strategic control loop that can express:

OBSERVE → INTERPRET → WAR OBJECTIVE → CAPABILITY → PREPARE → ASSEMBLE → ATTACK → PRESS/REASSESS → REINFORCE/RETREAT → RETARGET → OBJECTIVE COMPLETE

Runtime DE execution remains user-owned. This checklist covers research, typed semantics, deterministic compilation, native artifact acceptance, diagnostics, and strategy integration only.

## Evidence basis

- Established native attack mechanisms: attack-now, attack-groups, and town-size attack. See the AoE2 community attack analysis:
  https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476
- The community analysis distinguishes attack-now, attack-groups, and town-size attack and documents materially different behavior, including attack-group scale, land-vs-naval applicability, exploration dependence, and attack-window control.
- The Duke repository provides a concrete multi-state attack controller with READY, PREPARING, PULLING-TROOPS, ATTACKING, and STOP states, military-parity gates, siege requirements, attack timers, regrouping, attack prolongation, attack cancellation, and town-size reset:
  https://github.com/tim-kos/the_duke_ai
- The Naga database records Naga as originating from Promi DE AI and being handed over to Naga development in 2021. It also records continued development and a broad strategy/settings feature surface while explicitly noting that Naga remains exploitable. This makes Naga useful as a source of strategic breadth and known failure modes, not as proof of perfect endgame logic:
  https://aoeaidatabase.pythonanywhere.com/ai?name=Naga
- Forgotten Empires describes Promi as a balanced AI and the broader AI family as containing distinct strategic personalities, including aggressive rushers and boom-oriented AIs:
  https://www.forgottenempires.net/ai
- Current community testing tracks Naga and other actively maintained AI scripts across updates and map/settings support:
  https://steamcommunity.com/sharedfiles/filedetails/?id=3491589853

## Architectural decision

### The generic compiler DOES need additional substrate

The compiler must gain enough semantic support to represent a complete attack/controller lifecycle.

Required generic/compiler work:

- typed attack lifecycle state;
- attack issue/admission separation;
- attack preparation state;
- attack-group / town-size / attack-now execution modes as distinct native mechanisms;
- target provenance and target validity boundaries;
- regroup / retreat / re-entry state;
- attack timer/reassessment state;
- military capability and reinforcement capability observations;
- target-class / objective metadata where it can be represented without inventing native semantics;
- attack-related Strategic Number bindings;
- DUC target/search support needed by attack controllers;
- capability-loss/recovery integration;
- deterministic lowering and native acceptance for every newly executable native surface.

### The generic compiler must NOT contain the war planner

These remain Basilisk/client strategy policy:

- choosing the current war objective;
- deciding whether to attack production, economy, fortification, military, trade, or another target class;
- selecting Byzantine strategic posture;
- deciding opportunity cost between economy and military pressure;
- deciding when an achieved objective should cause a strategic transition;
- civilization-specific military composition policy.

Those policies consume the generic compiler's typed capabilities and observations.

## Phase 1 — Native attack mechanism inventory

- [ ] Produce authoritative contracts for attack-now.
- [ ] Produce authoritative contracts for attack-group control.
- [ ] Produce authoritative contracts for town-size attack.
- [ ] Identify all attack-related Strategic Numbers used by DE/UP.
- [ ] Identify native reset/disable/re-entry controls.
- [ ] Identify attack-group size controls and documented cardinality.
- [ ] Identify native exploration dependency for attack target visibility.
- [ ] Separate naval attack behavior from land attack behavior.
- [ ] Record version/patch scope for every attack control.
- [ ] Mark all controller causality that remains evidence-only.

Acceptance:
- Every attack primitive has a source-backed contract or is explicitly OPEN.
- No community idiom is promoted to engine fact without independent native evidence.

## Phase 2 — Attack lifecycle semantic IR

- [ ] Extend the current issue-only attack IR to model a persistent lifecycle.
- [ ] Define states: READY, PREPARING, ASSEMBLING, ATTACKING, PRESSING, RETREATING, REASSESSING, COMPLETE, CANCELLED.
- [ ] Define legal transitions.
- [ ] Require explicit admission evidence before transition into ATTACKING where the native contract supports it.
- [ ] Keep ISSUE separate from SUCCESS.
- [ ] Keep ATTACKING separate from OBJECTIVE_COMPLETE.
- [ ] Represent attack mode as typed native execution intent: ATTACK_NOW, ATTACK_GROUPS, TOWN_SIZE_ATTACK, DUC_TARGETED.
- [ ] Represent attack owner / strategic-demand identity.
- [ ] Prevent conflicting attack controllers from silently overwriting one another.
- [ ] Add deterministic lifecycle fingerprints.

Acceptance:
- Static tests reject impossible transitions and conflicting lifecycle ownership.
- The compiler never treats attack-now issuance as proof that an attack succeeded.

## Phase 3 — War objective model

Add this in the Basilisk strategy layer, not as generic AoE2 engine semantics.

- [ ] Define typed war objectives: BREAK_MILITARY, BREAK_PRODUCTION, BREAK_ECONOMY, BREAK_FORTIFICATION, RAID, POSITIONAL_PRESSURE, EMERGENCY_DEFENSE.
- [ ] Define objective identity and persistence.
- [ ] Define objective prerequisites.
- [ ] Define objective completion witnesses.
- [ ] Define objective invalidation.
- [ ] Define objective reassessment triggers.
- [ ] Define objective capability requirements.
- [ ] Keep objective policy separate from attack execution mode.

Acceptance:
- A war objective can remain active while individual attack attempts are issued, stopped, retried, or retargeted.
- Attack failure never silently deletes the strategic objective.

## Phase 4 — Kill-capability / break-capability graph

Before committing an attack, Basilisk should be able to represent missing capabilities.

- [ ] ARMY_CAPABILITY
- [ ] COUNTER_CAPABILITY
- [ ] SIEGE_CAPABILITY
- [ ] TARGET_ACCESS
- [ ] REINFORCEMENT_CAPABILITY
- [ ] POSITIONAL_ACCESS
- [ ] ECONOMIC_SUPPORT

For each capability:

- [ ] provider;
- [ ] feasibility;
- [ ] supporting production;
- [ ] required resources;
- [ ] completion witness;
- [ ] loss condition;
- [ ] recovery path;
- [ ] strategic-demand preservation.

Acceptance:
- If a capability is unavailable, the strategic objective remains alive and the compiler produces a blocked/preparation path rather than an unconditional attack.

## Phase 5 — Target model

- [ ] Define a typed strategic target identity separate from raw native object IDs.
- [ ] Track target source: DUC search; native target; world-state fact; strategic inference.
- [ ] Track target lifetime/proof status.
- [ ] Track target class.
- [ ] Track target invalidation.
- [ ] Track target replacement/reassessment.
- [ ] Connect DUC SearchSession/TargetSession to attack objectives.
- [ ] Add fail-closed handling for stale DUC targets.
- [ ] Prevent target identity from being confused with GoalSpan search-state output.

Target classes should remain strategic policy, not hard-coded engine semantics.

## Phase 6 — Preparation / assembly

Model the community pattern seen in mature bots.

- [ ] Wait for attack readiness.
- [ ] Verify military capability.
- [ ] Verify required upgrades.
- [ ] Verify siege capability where applicable.
- [ ] Verify reinforcement capacity.
- [ ] Preserve required defensive force.
- [ ] Pull/regroup forces when the native mechanism supports it.
- [ ] Start an attack window only after preparation succeeds.
- [ ] Preserve the strategic objective while preparation is incomplete.

Acceptance:
- PREPARING and ASSEMBLING are explicit states, not hidden timing assumptions.

## Phase 7 — Attack execution

- [ ] Emit the selected native attack mechanism deterministically.
- [ ] Bind required Strategic Numbers.
- [ ] Preserve within-rule action ordering.
- [ ] Validate attack controls against their native parameter domains.
- [ ] Reject unsupported controller combinations.
- [ ] Separate land and naval attack contracts.
- [ ] Keep attack issue emission separate from completion witnessing.
- [ ] Add native zero-findings fixture for each promoted attack execution form.

Acceptance:
- Source → IR → binding → .per → native parser is deterministic for each promoted attack mechanism.

## Phase 8 — Pressure / reinforcement / sustainment

This is the most important missing endgame layer after attack issue.

- [ ] Model PRESSING as distinct from ATTACKING.
- [ ] Define reinforcement demand.
- [ ] Connect production capacity to reinforcement capability.
- [ ] Preserve resource support for military replacement.
- [ ] Detect strategic capability loss statically where possible.
- [ ] Preserve war objective across temporary military loss.
- [ ] Allow repeated attack attempts without creating duplicate strategic demands.
- [ ] Define re-entry state after a stopped attack.
- [ ] Prevent repeated unconditional attack-now loops.

Acceptance:
- Multiple attack executions can belong to one persistent war objective.
- A failed attack does not create an uncontrolled retry storm.

## Phase 9 — Retreat / stop / recovery

Use the mature community pattern of explicit attack stopping and re-entry.

- [ ] Define retreat condition contract.
- [ ] Define stop condition contract.
- [ ] Define regroup condition.
- [ ] Define cooldown/re-entry condition.
- [ ] Preserve strategic objective through retreat.
- [ ] Restore defensive town-size/attack controls where appropriate.
- [ ] Reopen the same war objective after capability recovery.
- [ ] Distinguish temporary tactical failure from strategic invalidation.

Acceptance:
- RETREAT does not become CANCEL.
- Capability loss does not release the strategic objective.
- Recovery returns the same objective to an executable state when its prerequisites are restored.

## Phase 10 — Objective completion

Do not use attack issuance or army size as completion.

- [ ] Define military-break witnesses.
- [ ] Define production-break witnesses.
- [ ] Define economic-break witnesses.
- [ ] Define fortification-break witnesses.
- [ ] Define raid completion witnesses where statically meaningful.
- [ ] Define explicit invalidation where objective conditions disappear.
- [ ] Require world-state evidence for completion wherever the engine exposes it.
- [ ] Keep strategic interpretation separate from raw native facts.

Acceptance:
- Every executable war objective has either a typed completion witness or an explicit OPEN completion boundary.

## Phase 11 — Reassessment

The strategic loop must select what comes next.

- [ ] Reassess after attack stop.
- [ ] Reassess after target invalidation.
- [ ] Reassess after capability loss.
- [ ] Reassess after objective completion.
- [ ] Reassess after major enemy-state changes represented by available native facts.
- [ ] Preserve unaffected strategic demands.
- [ ] Avoid restarting already completed prerequisites.
- [ ] Prevent oscillation between incompatible war objectives.

Acceptance:
- Reassessment changes strategic objective only through an explicit typed policy transition.

## Phase 12 — Basilisk endgame policy

Initial policy surface:

### Military break
Use when enemy field resistance can be reduced sufficiently to open the base.

### Production break
Use when enemy military replacement is the dominant blocker.

### Fortification break
Use when castles/walls/defensive infrastructure prevent direct pressure and siege capability is required.

### Economic break
Use when enemy military can be bypassed or when resource denial is the more direct path.

### Raid
Use mobile forces against exposed economic/production targets rather than forcing frontal engagements.

### Positional pressure
Use when repeated direct attacks are inefficient but forward control can improve future attack capability.

- [ ] Define policy transition conditions.
- [ ] Define capability requirements for each policy.
- [ ] Define target classes used by each policy.
- [ ] Define native execution methods allowed by each policy.
- [ ] Define recovery/re-entry semantics.
- [ ] Define terminal objective semantics.
- [ ] Keep policy entirely inside clients/basilisk.

## Phase 13 — Community cross-check

MUSE must produce a dedicated endgame/war-controller research report covering:

- [ ] Naga / Promi strategic attack architecture and documented limitations.
- [ ] Duke attack-state implementation and attack-window patterns.
- [ ] attack mechanism differences.
- [ ] retreat/re-entry and regroup patterns.
- [ ] siege and military-parity gates.
- [ ] DUC target selection and target invalidation.
- [ ] production/reinforcement coupling.
- [ ] enemy production/economy/fortification targeting.
- [ ] adaptation to enemy strategy.
- [ ] documented failure modes and anti-patterns.
- [ ] source provenance and native-vs-community confidence for every finding.
- [ ] assign every finding a compiler status and implementation owner.

## Phase 14 — Compiler integration

- [ ] Add attack lifecycle contracts to the native semantic registry.
- [ ] Extend typed attack IR beyond issue-only execution.
- [ ] Add target/war-objective storage requests where required.
- [ ] Add attack-state diagnostics.
- [ ] Add conflicting attack-controller diagnostics.
- [ ] Add stale-target attack diagnostics.
- [ ] Add attack objective lifecycle diagnostics.
- [ ] Extend DUC semantic diagnostics for attack consumers.
- [ ] Extend production semantic diagnostics for reinforcement consumers.
- [ ] Add deterministic source-to-.per attack lifecycle fixtures.
- [ ] Add native zero-findings gates for every newly promoted native execution seam.
- [ ] Update compiler coverage baseline.
- [ ] Update implementation map.
- [ ] Update native semantic gap map.
- [ ] Update MUSE checklist from the same implementation commit.

## Explicit non-goals

- No tactical combat simulator.
- No generic RTS planner in the compiler core.
- No universal attack scheduler.
- No invented combat-success Boolean.
- No inference that attack-now means success.
- No inference that army size alone proves attack readiness.
- No strategy policy embedded in native primitive definitions.
- No community idiom promoted to engine truth without evidence.
- No runtime claim before DE execution.

## Definition of done

The war-control/compiler tranche is complete when:

1. Native attack mechanisms have typed semantic contracts.
2. Attack lifecycle is represented independently from strategic objective lifecycle.
3. Strategic objectives can persist through failed attacks.
4. Capabilities can block or reopen an objective.
5. Targets have explicit provenance/invalidation boundaries.
6. Attack, stop, retreat, regroup, and re-entry can be expressed deterministically.
7. DUC, production, SN, timer, and attack semantics connect through typed contracts.
8. Basilisk client owns war-policy selection.
9. Every promoted emitted attack capability has deterministic artifact and native zero-findings coverage.
10. Genuine runtime questions remain explicitly OPEN rather than being encoded as compiler assumptions.
