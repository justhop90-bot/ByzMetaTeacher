# Basilisk BOOM Patch Checklist — September 2026

Scope: Castle BOOM as the primary economic strategy. This checklist is the paper/runtime contract for the BOOM repair pass. Runtime execution is deliberately deferred to the project owner.

## Strategic identity

- [x] BOOM remains one of the four existing strategy states.
- [x] No fifth BOOM sub-strategy or new macro architecture is introduced.
- [x] BOOM is treated as economic expansion first, with only a small defensive floor.
- [x] Castle-Power retains its pressure-oriented military floor rather than inheriting BOOM's economic floor.
- [x] The Castle BOOM gatherer baseline remains 50 food / 35 wood / 15 gold / 0 stone. It is not being used to compensate for bad consumer ownership.

## Standing military

- [x] Castle BOOM TC1 floor = 4.
- [x] Castle BOOM TC2 floor = 6.
- [x] Castle BOOM TC3+ floor = 8.
- [x] Old Castle pressure floors 12 / 16 / 20 remain available to Castle-Power only.
- [x] Role targets remain downstream of the standing-floor writer.
- [x] No infrastructure -> army positive feedback loop remains as the BOOM floor authority.
- [x] Shared standing-unit production retains the Castle-bank veto during BOOM.
- [x] FLUSH may override the Castle bank for emergency standing production.

## Town Center capital project

- [x] TC2 remains persistent demand at the existing 32-villager / 350-food / 300-wood maturity threshold.
- [x] TC3 remains persistent demand at the existing 45-villager / 500-food / 300-wood maturity threshold.
- [x] Existing TC2/TC3 staged lifecycle remains authoritative: demand -> resource claim -> placement -> foundation -> completion.
- [x] Active BOOM TC2/TC3 projects suppress discretionary standing demand during demanded, resource-claimed, and placement-pending stages.
- [x] Foundation-active does not keep pre-foundation military suppression alive; the capital resource has already been spent.
- [x] TC completion resets the project and allows normal BOOM reassessment.
- [x] TC project cancellation remains pre-foundation only when BOOM is no longer the strategy.
- [x] No default TC4 demand is added.

## Town Center stone economics

- [x] Existing TC2/TC3 stone resource-mode handoffs remain in place.
- [x] TC2 and TC3 persistent project state owns the stone-mode decision.
- [x] Stone mode remains an economic execution mode and does not recreate TC demand.
- [x] Existing resource mutex protects the TC claim during resource-claimed and placement-pending stages.

## Primary Castle military

- [x] Generic BOOM Knight selection requires a completed second TC.
- [x] Existing Archer investment can still justify Crossbow continuation without forcing the generic Knight gate.
- [x] Knight demand yields while a BOOM TC2/TC3 project is active.
- [x] Crossbow demand yields while a BOOM TC2/TC3 project is active while preserving Castle-Power ownership.
- [x] Knight/Crossbow engine train rules retain the same active-TC veto at the final action boundary.
- [x] No generic Castle BOOM primary army is created merely because food/gold are temporarily available.

## Capability ownership

- [x] Standing military production-capability rules respect the Castle bank.
- [x] FLUSH emergency ownership can bypass the normal bank gate.
- [x] Stable capability also yields during an active BOOM TC project.
- [x] The existing capability/action separation is preserved: capability rules build buildings; production rules train units.

## Farms and economic throughput

- [x] Existing 2-TC farm reserve scaling remains present.
- [x] Existing 3-TC farm reserve scaling remains present.
- [x] Farm scaling executes after the age/population reserve model and before farm execution.
- [x] Feudal BOOM farm-budget safeguards remain intact.
- [x] No new farm simulation or prediction layer is introduced.

## Economic technologies

- [x] Wheelbarrow remains a persistent direct research lifecycle with engine feasibility.
- [x] Hand Cart remains tied to a mature BOOM economy.
- [x] Bow Saw remains tied to the existing Castle BOOM maturity witnesses.
- [x] Gold Shaft Mining remains a Castle BOOM opportunity after existing maturity gates.
- [x] Heavy Plow remains tied to the existing farm lifecycle.
- [x] Existing Imperial-bank opportunity-cost witnesses remain intact.
- [x] No duplicate economic-research architecture is introduced.
- [x] Resource mutex remains the final research arbitration mechanism.

## Paper replay cases

- [x] Castle BOOM at 1 TC derives floor 4.
- [x] TC2 demand arms persistent capital state and suppresses discretionary standing demand.
- [x] TC2 resource-claimed retains capital priority.
- [x] TC2 placement-pending retains capital priority.
- [x] TC2 foundation-active releases the pre-foundation military suppression.
- [x] TC2 completion raises BOOM floor to 6 and reopens normal standing-demand evaluation.
- [x] TC3 demand suppresses discretionary military demand while pending.
- [x] TC3 completion raises BOOM floor to 8.
- [x] Generic Knight posture cannot qualify at 1 TC.
- [x] Generic Knight posture can qualify after TC2 when its existing unit-goal writer is active.
- [x] Castle commitment suppresses normal BOOM standing production.
- [x] FLUSH can override the Castle commitment for defensive production.
- [x] Active TC projects use the existing resource/capability boundaries instead of a second reservation architecture.
- [x] 2-TC and 3-TC farm scaling witnesses remain present.
- [x] TC2/TC3 stone-mode handoffs remain present.

## Exit and preemption safety

- [x] Existing BOOM -> FLUSH threat preemption remains intact.
- [x] Existing RUSH objective-loss and repeated-stall release behavior remains intact.
- [x] Existing Castle-Power expiry remains intact.
- [x] TC resource claims can be preempted and resumed through the existing preemption owner protocol.
- [x] No BOOM patch clears active foundations or resurrects stale TC demand.

## Validation hardening

- [x] BOOM floor invariants are checked by the main validator.
- [x] TC capital arbitration is checked by the main validator.
- [x] Knight/Crossbow maturity gates are checked by the main validator.
- [x] Castle-bank emergency override is checked by the main validator.
- [x] Standing capability-family ownership is checked by the main validator.
- [x] Deterministic BOOM paper replay is executed as part of validator invocation.
- [x] BOOM mutations are included in the critical self-test inventory.
- [x] Critical mutation inventory has no missing names.
- [x] Controller strategy inventory remains exactly FLUSH=200, RUSH=201, BOOM=202, Castle-Power=203.
- [x] No runtime certification is claimed here.

## Explicit non-goals

- [x] No TC4 default BOOM strategy.
- [x] No new strategy state.
- [x] No simulation/predictive economy layer.
- [x] No replacement of the existing TC lifecycle.
- [x] No rewrite of the resource-mode architecture.
- [x] No replacement of the existing eco-tech lifecycle.
- [x] No runtime/game result is inferred from source replay.

## Runtime handoff

Runtime validation remains outside this patch pass. The owner should eventually execute the controlled 1-TC, 2-TC, 3-TC, Castle-bank/FLUSH, Knight, Crossbow, and TC-project interruption scenarios against the live AoE2DE game and treat those observations as the final behavioral witness.
