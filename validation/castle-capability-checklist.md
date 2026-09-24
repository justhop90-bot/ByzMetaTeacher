# Basilisk Castle Capability Checklist

Scope: Castle-age transition, immediate-Castle/Castle-drop intent, Castle stone funding, Castle construction ownership, and the two Imperial missing-Castle writers.

## Castle capability lifecycle

- [x] Castle age ownership remains a separate state: `bt-castle-commitment-goal` owns the Feudal -> Castle age-up, not Castle construction.
- [x] The 28-villager Castle boundary remains the hard age-up ownership boundary.
- [x] Castle research still requires the existing `castle-age` escrow feasibility check.
- [x] Castle-age completion releases the age-up bank before Castle-age consumers arbitrate.
- [x] Existing Castle capability demand remains `bt-castle-cataphract-demand-goal`.
- [x] Existing Castle construction ownership remains `bt-castle-cataphract-claim`.
- [x] Existing Castle build executor remains engine-native `can-build-with-escrow castle` -> `build castle`.
- [x] Completed Castle remains the demand completion witness.
- [x] Pending Castle foundations remain protected from strategic withdrawal.
- [x] Castle stone mode already has a terminal release at 650 stone, Castle completion, or demand disappearance.

## Immediate-Castle / Castle-drop intent

- [x] The live upstream condition is `bt-opening-plan-goal == bt-opening-plan-arena-fast-castle`.
- [x] The opening plan is preferred over raw `map-type arena`: Arena alone does not require an immediate Castle.
- [x] The live opening plan is preferred over the underlay: anti-rush can temporarily replace the live plan.
- [x] Generic Arabia Fast Castle is not used as an immediate-Castle trigger.
- [x] Castle-Power is not used as the trigger: it is a Castle-age downstream strategy state.
- [x] Pre-Castle stone now reuses the existing Castle-bank resource owner instead of adding a Castle-stone demand state.
- [x] While the live Arena Fast Castle plan owns the Castle bank and stone < 650, gather allocation is 50F/15W/20G/15S.
- [x] Once stone reaches 650, or the Arena Fast Castle plan disappears, the normal Castle-bank allocation returns to 55F/15W/30G/0S.
- [x] P0 Food/Gold/Wood crisis arbitration remains above the Castle bank and therefore above the stone diversion.
- [x] On reaching Castle Age, the existing Castle capability demand is activated for the live Arena Fast Castle plan.
- [x] The resulting demand feeds the existing Castle-stone/build lifecycle without a new goal or mutex.
- [x] Arena Fast Castle is converted to Arena Boom only after Castle Age is real, so the live plan is still available to the Castle-demand writer at the transition boundary.

## Castle demand writers / clearers

- [x] Normal Castle-demand writer: Castle Age + infantry pressure.
- [x] Normal Castle-demand writer: Castle Age + mature BOOM/Castle-Power economy.
- [x] Arena Fast Castle now joins that same demand writer as an immediate-Castle project.
- [x] Strategic withdrawal clearer remains guarded by the project commitment bit and no pending foundation.
- [x] Construction completion clearer releases demand, mature commitment, backoff, and the resource mutex.
- [x] Secondary completion clearer closes a demand that discovers an already-completed Castle outside the normal claim owner.
- [x] Castle-loss watchdog still converts a failed foundation into a capability-local backoff rather than silently deleting the project.

## Imperial missing-Castle audit

- [x] Imperial writer A: `bt-imperial-siege-package-goal == 1` + Imperial + no Castle/pending foundation + target building + 650 stone + force/reserve floors -> Castle demand.
- [x] Writer A exists early enough to feed the Castle executor in the same pass when 650 stone is already available.
- [x] Imperial writer B: same Imperial missing-Castle package without the 650-stone prerequisite -> Castle demand.
- [x] Writer B occurs later in source order, allowing the existing Castle-stone resource mode to accumulate the missing stone on the next pass.
- [x] Writer A and Writer B are therefore not functionally duplicate: A is the stone-ready same-pass path; B is the stone-accumulation path.
- [ ] Runtime retest both Imperial paths in-game: stone-ready immediate placement and stone-shortage recovery.
- [ ] Revisit the two writers only if runtime proves the late writer creates an unintended source-order delay or stale demand.

## Static validation

- [x] Controller source remains parenthesis-balanced after the change.
- [x] Normal Castle-bank wood/gold split was preserved at 55F/15W/30G/0S.
- [x] The stale Castle diagnostic saying "30 villagers" was corrected to the canonical 28-villager boundary.
- [ ] Runtime validation remains outstanding because the Windows/game host is not available in the current environment.
- [ ] The existing `validation/basilisk-validator.js` remains a separate issue: its known undefined validator calls must be repaired before its overall PASS/FAIL result is trusted.
