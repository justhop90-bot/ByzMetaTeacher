# Byzantine Scenario Matrix - Phase 0 Baseline

This is the frozen behavioral test surface for the current Byzantine.per artifact. It is an acceptance contract, not a promise that every scenario already passes.

| Scenario | Stimulus | Expected strategic decision | Required execution/witness | Primary subsystem evidence | First failure to record |
|---|---|---|---|---|---|
| Standard land opening | Arabia/open land, standard opponent | Reach Feudal on stable economy, maintain first defensive package | Feudal transition witnessed by current-age; economy remains productive | age transition, opening economy | age timing, villager idle, first military |
| Feudal mounted pressure | enemy stable/scout or early knight signal | Pre-position spears before contact | counter package issued and trained; enemy composition observation persists | scout phases + counter packages | reaction latency and resource starvation |
| Feudal ranged pressure | enemy archery-range/skirmisher signal | Shift to skirmisher/ranged counter | counter production begins before full attack | scout + ranged counter | late counter, wrong composition |
| Castle commitment | successful Feudal -> Castle path | Commit resources only after admissibility and infrastructure conditions | Castle research/build completion is witnessed separately from issuance | castle commitment lifecycle | bank starvation, failed issuance, stale demand |
| Castle two-TC | mature Castle economy | Add TC2 when opportunity is viable, not merely because resources exist | building-type-count witness; persistent TC2 completion state | lines around 7877 onward | overboom, delayed army, failed recovery |
| Imperial conversion | mature Castle economy + university | Age to Imperial when military/economic maturity supports it | current-age witness releases demand | lines around 7751 onward | premature age-up or excessive bank |
| Enemy composition shift | enemy transitions from one unit family to another | Change composition rather than preserve obsolete counter | posture changes and new demand issued | Imperial posture lines around 7700 | stale counter lock |
| Fortified enemy base | castles/towers/walls around target | Stop wasting ordinary army; scale siege | fortification threat witness changes siege scale | fortification probe + siege scale | suicide attack, idle army |
| Open-ground attack | enemy army exposed and attack package complete | Attack with appropriate package | attack readiness -> attack execution -> reassessment | attack controller | premature attack, no follow-up |
| Army loss | meaningful army package destroyed | Rebuild/reassess rather than repeat same attack | reinforcement demand and changed attack posture | recovery rules | perpetual re-feed |
| Enemy exposed wood/gold | scout finds lumber/mining camp | Convert scout information into raid waypoint | scout stores position and a combat package can exploit it | scout missions around lines 2261-2335; raid hooks | intel never becomes action |
| Relic opportunity | monastery + monk and reachable relic | Acquire or contest valuable relics | target established and monk command issued; later ownership/witness checked | lines 633-656 | targeting first object only, no completion/recovery |
| Defensive base response | enemy forward pressure | Fortify threatened approach without destroying economy flow | fortification threat state and construction demand | fortification probe | wall/tower overreaction |
| Late-game wood surplus | wood > 5k in Imperial | Convert surplus into active strategic spend, not permanent bank | demand raised, production/build/research/market consumes wood | surplus spend + late burn | wood remains extreme |
| Late-game gold surplus | gold > 4.5k in Imperial | Convert gold into active military/tech/siege spend | demand raised and bank declines | surplus spend + military upgrade/research | gold remains extreme |
| Late-game food surplus | food > 5k in Imperial | Convert food into production/economy/market use | demand raised and bank declines | surplus spend + farm/market | food remains extreme |
| Resource shortage under surplus elsewhere | one resource low, another high | Retask gatherers with hysteresis | SN/gatherer change persists for cadence, then releases | bounded gatherer delta controller | oscillation |
| Starvation/recovery | food production interrupted or food bank collapses | Restore food acquisition while preserving higher-priority obligations | food recovery demand and witness | current bot has no explicit starvation-labeled rule; must audit food-low behavior | stall or economic death |
| Water opening | Islands/Archipelago-type opening | Establish fishing/naval/transport economy appropriate to map | dock/fishing/naval state and resource continuity | water section around 505 onward | land doctrine leaks into water |
| Transport invasion | disconnected land masses | Protect transport and send useful military/villager payload | transport action followed by landing/world witness | transport section | empty/unsafe transport |
| Transport loss | transport destroyed | Rebuild transport capability and resume objective | loss observation -> rebuild -> new crossing | transport recovery | permanent isolation |
| Naval pressure | enemy naval commitment | Increase appropriate warship composition | naval production and enemy-water response | water/naval subsystem | navy exists without strategic effect |
| Relic denial | enemy has monks/relic intent | Contest relic access when value warrants it | enemy monk observation and target action | relic-denial rule around line 646 | no denial or late response |
| Trade/late economy | long Imperial game with safe trade option | Use trade/resources to sustain final army when appropriate | trade economic state remains compatible with army spending | market/trade audit | bank while army starves |
| Recovery after base damage | major home-base disruption | Rebuild economy/infrastructure and reassess attack | destroyed resource/production witness triggers recovery | recovery subsystem | attack loop continues despite economic damage |

## Phase-0 audit findings

The current source has strong implementation coverage for age transitions, scouting, counters, siege, fortification, market behavior, water/transport, recovery, and late-game spending.

The following areas require special scrutiny before tuning:

1. Scouting already locates enemy lumber and mining camps and stores points, but the baseline must demonstrate that this information actually changes a combat decision. The presence of DUC movement is not sufficient proof of strategic exploitation.
2. Relic handling is only two small DUC rules. The acquisition rule repeats the monk-count fact and immediately targets search-remote object index zero. Completion, relic ownership, denial recovery, and value arbitration require deeper audit.
3. Raid references are sparse relative to the 16k-line artifact. The current source can store enemy resource points, but the matrix must prove those points become meaningful raid execution.
4. There is no literal starvation-labelled subsystem. Food-low behavior therefore needs scenario testing rather than assuming "farm boom" equals starvation recovery.
5. Late-game surplus handling is extensive, but the observed 8k/8k/4-5k bank proves coverage alone is not enough. The test must measure bank decay after an existing composition floor has been met.
6. Water and transport have extensive source coverage. The matrix must distinguish "the rules exist" from "a transport actually lands a strategically useful package and recovers after loss."
7. Army attack readiness currently depends on fixed composition thresholds. The matrix must test whether those floors are sufficient under changing enemy composition and fortified positions.

## Measurement protocol

For each scenario capture:
- exact bot Git SHA and Byzantine.per blob SHA
- map, civ matchup, difficulty, population, and starting resources
- game-time checkpoints
- food/wood/gold/stone
- villager count and idle villagers
- military counts by major family
- production-building counts and pending objects
- active strategic goals relevant to the scenario
- current-age and key research completion
- first unexpected decision
- immediate world-state witness
- whether recovery changed the next decision

Record the first causal failure, not merely the eventual game result.

Phase 0 is complete when this matrix is paired with reproducible game traces. Strategic thresholds must not be tuned solely from code inspection.
