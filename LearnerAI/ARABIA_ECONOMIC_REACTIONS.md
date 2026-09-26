# Arabia Worker, Production, Construction, and Resource Reactions

This document converts `ARABIA_TIMING_WINDOWS.md` and the Arabia threshold documents into concrete economic and execution reactions.

The design uses **temporary worker packets**, not fixed opening splits.

A packet is a short-lived allocation adjustment opened by an observed strategic demand. When the demand is witnessed, the packet is released and the economy returns toward its current strategic target.

This keeps timing from becoming a hidden build order.

## 1. Base Arabia economic mode

### B0: normal open-land Feudal economy

When there is no active override:

| Resource | Default allocation band |
|---|---:|
| Food | 50-55% |
| Wood | 25-30% |
| Gold | 15-20% |
| Stone | 0% unless a Castle demand is active |

The exact worker count varies with current population, food source, farm state, and whether the Castle trajectory is active.

B0 protects:

1. continuous villagers;
2. houses;
3. current age/transition resources;
4. Castle trajectory once it becomes active;
5. only then optional military or infrastructure.

### Worker-packet convention

One packet = the smallest temporary allocation change that closes the current shortage.

The packet is evaluated against:

- current worker count;
- current stock;
- resource price/opportunity cost;
- active production queue;
- active strategic demand;
- construction feasibility.

Do not create a second packet while the first packet is already closing the shortage unless current production or world-state evidence proves it is insufficient.

Current official AI behavior also changes farm and tree-gathering behavior when wood becomes unusually expensive, so worker packets must yield to resource-price/crisis arbitration rather than force a fixed percentage.

## 2. Reaction ladder

| Demand | Temporary worker reaction | Production reaction | Construction reaction | Release |
|---|---|---|---|---|
| 2 Spears | +1 food, +1 wood | 2 Spears from existing Barracks | none unless resource is exposed | spear target witnessed |
| 4 Spears | +1 food, +2 wood | 4 Spears; second Barracks only if queue capacity is insufficient | local wall if resource remains exposed | mounted threat falls below D3 |
| 2 Skirms | +1 food, +2 wood | 2 Skirms; one Range if absent | short funnel if ranged units can enter economy | ranged target witnessed |
| 4 Skirms | +1 food, +2-3 wood | 4 Skirms; second Range only with sustained 8+ ranged pressure | local wall if pressure reaches resource | ranged threshold falls |
| 3 Archers vs MAA | +1 food, +2 wood | 1 Range + 3 Archers | short resource wall | MAA threshold clears |
| 4-6 Archers vs MAA | +1 food, +3 wood | 4-6 Archers; second Range only at sustained higher pressure | local wall/gate | MAA threshold clears |
| Tower defense | +2 wood, +2 stone; reduce optional gold | use existing counters; add only required counter package | 2-4 builders for emergency tower/defensive response | tower threat removed/neutralized |
| Own Castle bank | +2 food, +2 gold; +5-8 stone once Castle demand is active | close optional Feudal production | 5-8 builders for first Castle when serviceable | Castle foundation/completion witness |
| Opponent early Castle, low pressure | +2 food, +2 gold, -2 wood | close optional Feudal queues | no new static defense | own Castle starts/pressure changes |
| Opponent Castle + active pressure | +1 food, +1 wood, maintain +2 gold; stone only if own Castle remains feasible | minimum counters + relevant Castle response | tower/wall only when resource is actually threatened | pressure stabilizes |
| Water/transport override | packet defined by actual dock/transport demand | naval/transport queue only when justified | Dock/landing infrastructure | water objective ends |

The numbers are **allocation deltas**, not promises that exactly those workers must exist at every moment.

## 3. Scout / cavalry timing reactions

### 08:30-10:30: early scout signal

With actual cavalry evidence:

**Worker**
- +1 food;
- +1 wood;
- keep Castle gold floor intact;
- do not start stone collection merely because cavalry is suspected.

**Production**
- 2 Spears for S1.
- Existing Barracks is sufficient.
- Do not build a second Barracks for only two Spears.

**Construction**
- Short wall/funnel becomes admissible if the threatened food/gold/wood is exposed.
- Use 2 wall builders for a small closure.
- Do not start a tower merely because the Scout window is early.

**Resource mode**

    B0
      -> CAV-S1

Maintain enough gold to avoid destroying the Castle trajectory.

Release the packet immediately after the 2-Spear target is met and no higher mounted threshold is active.

### 10:30-12:30: expected scout pressure

With 2+ active mounted units:

- maintain CAV-S1;
- escalate to CAV-S2 at 3-4 mounted;
- add +1 wood only when the next Spear production requires it;
- keep at least the normal Castle gold floor.

At 4+ mounted:

- +1 food;
- +2 wood;
- stop optional Feudal military that does not answer cavalry.

Second Barracks becomes admissible only when one Barracks cannot sustain the current standing target.

### 12:30-14:00: late scout pressure

Do not carry an old early-game worker packet forward automatically.

Require current mounted units or active Stable production.

With actual 3+ mounted pressure:

- retain the +1 food/+2 wood packet;
- preserve local walling;
- delay optional Castle expenditure only while the pressure remains active.

### >14:00: stale timing

Timing contributes no worker reallocation.

Current mounted counts alone can reopen CAV-S1/S2/S3.

This is a hard release rule against permanent Spear taxation.

## 4. Archer timing reactions

### 09:30-11:30: early Archer signal

With only a discovered Range:

**Worker**
- +1 wood;
- +1 food;
- maintain Castle gold floor.

This buys enough flexibility to establish one Range or short walling.

With 2+ actual Archers:

- add a second wood worker packet;
- open 2-Skirmisher production.

**Production**
- one Range;
- 2 Skirms;
- no second Range.

**Construction**
- short funnel only if Archers have a path to the economy.

### 11:30-13:30: expected Archer pressure

At 2-3 Archers:

- +1 food;
- +2 wood;
- 2 Skirms.

At 4-7 Archers:

- +1 food;
- +2-3 wood;
- 4 Skirms.

At 8+ or two active Ranges:

- +2 food;
- +3-4 wood;
- 6 Skirms;
- second Range becomes admissible.

**Resource rule:** do not reduce Castle gold below its protected minimum merely to overproduce Skirms.

### 13:30-15:00: late ranged transition

Require current ranged army evidence.

If current 4+ Archers remain active:

- preserve +2 wood;
- preserve +1 food;
- maintain 4 Skirms.

If the enemy is visibly moving Castleward:

- stop adding Skirms above the current threshold;
- protect the own Castle resource trajectory.

### >15:00

No timing-derived Skirmisher allocation.

Current ranged army and active production determine it.

## 5. Men-at-Arms timing reactions

### 06:30-08:30: commitment detection

This window changes information handling, not production by itself.

With only suspicion:

- maintain B0;
- preserve enough wood for the first Archery Range;
- keep a safe Range placement available;
- do not start Archer production from the clock.

With actual forward Militia/MAA evidence:

- make the first Archery Range a protected P1 capability;
- +1 food;
- +1-2 wood until the Range is placed and the first Archer queue is serviceable;
- preserve the Castle gold floor.

The strategic purpose is readiness, not a prebuilt Archer mass. Current community discussion specifically emphasizes getting the Range up early enough that the first Archer can meet fast MAA pressure, while small resource walls buy the required time. citeturn358751reddit22turn358751reddit25

### 08:30-10:00: early MAA

With 2 MAA:

- +1 food;
- +2 wood;
- one Range;
- 3 Archers.

With 3-4 MAA:

- +1 food;
- +3 wood;
- 4 Archers.

Construction:

- 2-3 builders for a short wall/funnel;
- do not spend stone on a tower unless the MAA are actually denying a critical resource.

### 10:00-11:30: expected MAA

At 2 MAA:

    3 Archers

At 3-4:

    4 Archers

At 5-7:

    6 Archers

Worker packet:

- +1 food;
- +3 wood while the Archer target is being assembled;
- preserve the Castle gold floor;
- return excess wood workers toward Castle/farm needs once the standing Archer target is serviceable.

One Range is the default provider for the first Archer package.

A second Range becomes admissible only when the current MAA pressure persists and one Range cannot restore the required Archer standing target within the active threat/reassessment window. Merely seeing 5-7 MAA does not authorize permanent double-Range production.

### 11:30-12:30: late MAA

Require active MAA evidence.

If active:

- +2 wood;
- +1 food;
- preserve 4-6 Archers.

If MAA production stops:

- stop the extra wood packet;
- reassess whether the opponent is transitioning into Archers or Castle.

### >12:30

Timing no longer writes an MAA worker packet.

## 6. Tower-rush timing reactions

Tower pressure is fundamentally different because the structure changes the resource map.

### 07:30-09:30: high-risk tower

On a relevant forward foundation:

**Worker**
- +2 wood;
- +2 stone;
- optional gold workers are temporarily the first source to reassign;
- suspend optional Castle stone if the enemy tower itself is the immediate survival problem.

**Construction**
- 2-4 builders for defensive response;
- use the minimum builders that make the defensive structure arrive before the enemy completes the threat;
- short wall/funnel first when that can safely deny builder access.

**Production**
- preserve the current counter package;
- add no generic Spear/Skirmisher mass without actual enemy military.

### 09:30-10:30: expected tower pressure

If 2+ enemy builders or military protection is present:

- maintain +2 wood/+2 stone;
- 3-4 defensive builders;
- defensive tower admissible;
- short wall/gate admissible.

If the tower is completed over gold/wood:

- the affected resource becomes P0;
- relocate workers if necessary rather than feeding them into a losing position.

### 10:30-11:30: late tower pressure

Treat as a positional structure.

Worker packet becomes only:

- +1-2 wood;
- +1-2 stone

while the structure threatens the economy.

If the tower is irrelevant to current resource access:

- release the packet.

### >11:30

No timing-based tower economy.

A tower still receives a response if its actual location, builders, or military escort threaten the economy.

## 7. Early opponent Castle reactions

### 13:30-15:30: Castle suspicion

This window should barely touch worker allocation.

When Castle evidence is partial:

- keep B0;
- optionally move **one** worker from wood to gold if the own Castle trajectory is already active;
- do not open a new stone packet solely from suspicion;
- stop voluntary Feudal military expansion.

Production:

- no new military queue unless current defense requires it.

Construction:

- no tower/wall expansion without actual threat.

### 15:30-17:00: confirmed early Castle, low Feudal pressure

This is the strongest Castle-acceleration reaction.

**Worker mode: FC-ACCEL**

- +2 food;
- +2 gold;
- -2 wood;
- stone only if the own Castle demand is already strategically active.

The wood reduction comes from:

- closing optional production buildings;
- pausing unnecessary wall expansion;
- avoiding extra farms before current food demand requires them.

**Production**

- close optional Feudal military;
- maintain only the current defensive floor;
- do not add second production for a dead Feudal demand.

**Construction**

- no new tower unless an exposed resource actually requires it;
- no wall expansion unless active pressure exists;
- prioritize the prerequisite/infrastructure needed for own Castle conversion.

### 17:00-18:15: expected Castle conversion

Maintain FC-ACCEL when:

- enemy Castle is confirmed;
- own defense is D2 or lower;
- own food production is stable.

If enemy Castle units appear:

    FC-ACCEL
       ->
    FC-DEFENSE

FC-DEFENSE:

- +1 food;
- +1 wood;
- retain +2 gold;
- restore only the minimum counter production required.

### 18:15-19:15: normal/late Castle

Do not use timing alone to maintain FC-ACCEL.

Current enemy units, TCs, Monastery, Siege Workshop, Castle location, and economic expansion determine the response.

### >19:15

Timing packet is released completely.

The opponent's current strategic state owns the response.

## 8. Worker allocation modes

The Strategy/Economy interface should expose named **modes**, not raw individual villager orders.

| Mode | Food | Wood | Gold | Stone | Purpose |
|---|---:|---:|---:|---:|---|
| B0-NORMAL | baseline | baseline | baseline | 0 unless Castle | normal Arabia |
| CAV-DEFENSE | +1 | +1-2 | protect floor | 0 | Spears |
| RNG-DEFENSE | +1 | +2-3 | protect floor | 0 | Skirms |
| MAA-ARCHER | +1 | +2-3 | protect floor | 0 | Archers |
| TOWER-EMERGENCY | +1 | +2 | reduce optional gold | +2 | defensive structure |
| FC-ACCEL | +2 | -2 | +2 | strategic | own Castle acceleration |
| FC-DEFENSE | +1 | +1 | +2 | only if Castle remains active | Castle + defense |
| CASTLE-CONSTRUCTION | protect food | enough wood for farms/builders | protect Castle tech/military | +5-8 | first Castle |
| RECOVERY | +2 | +2 | current need | 0 | replace damaged resource income |

These modes are **relative modes**.

They must not be implemented as universal percentages that ignore worker count, farms, dead villagers, fishing, map geometry, or current resource stock.

A mode is a target tendency, not a hard assignment. The current stock/resource price and active demand may override it.

## 9. Production capacity rules

### Feudal defensive unit capacity

One existing Barracks:

- enough for 2 Spears;
- enough for the first 4-Spear defensive package if the threat is not immediate.

Second Barracks:

- admissible for 4+ sustained Spears;
- required only when queue completion would otherwise lag behind the standing target.

One Range:

- required for 2-4 Skirms or 3-6 Archers.

Second Range:

- only when:
  - 8+ Archers are present;
  - 2 enemy Ranges are active;
  - MAA pressure persists and Archer replacement cannot keep up;
  - or an explicit offensive ranged demand exists.

### Production closure

When the observed threat drops below the current threshold:

1. stop creating new units;
2. finish useful queued units unless an explicit cancellation mechanism exists;
3. release the worker packet;
4. preserve existing army as the new standing floor;
5. restore Castle/economic allocation.

This is important because a queue is an obligation in the immediate production state. The strategic demand can close without pretending a queued unit never existed.

## 10. Wall reactions

### Short wall

Use:

- 2 builders;
- 1 temporary wood packet if necessary;
- 60-80 wood normal budget.

### Reinforced local wall

Use:

- 3-4 builders;
- up to 120 total new wall wood under active pressure.

### Large enclosure

Only when the threshold document authorizes it.

Use:

- 4-6 builders;
- explicit Castle-opportunity-cost check;
- no concurrent optional Feudal production unless the defense requires it.

### Wall release

When the threat clears:

- stop new wall orders;
- keep existing useful walls;
- return wall builders to economic work immediately.

## 11. Tower reactions

### First defensive tower

Use:

- 3 builders normally;
- 4 if the resource will be denied before completion otherwise.

Worker mode:

    +1-2 stone
    +1 wood
    -1 optional gold

### Second defensive tower

Require D2+ or independent critical-resource exposure.

Use:

- 3-4 builders;
- second stone packet only after the first tower's strategic purpose is established.

### Tower upgrade

Do not shift a large stone packet into an upgrade merely because the upgrade becomes available.

Require:

- continuing threat;
- valuable position;
- actual survivability/denial improvement.

## 12. Resource arbitration rules

### Food crisis

Food crisis overrides:

- optional walls;
- optional tower upgrades;
- redundant Feudal production;
- optional Blacksmith research.

Food crisis does not automatically cancel the Castle strategy. It suspends lower-value spending until food stabilizes.

### Wood crisis

Wood crisis overrides:

- extra walls;
- second production;
- redundant houses only when not needed;
- optional Dock/fishing.

Wood crisis does not override required transport or emergency defensive construction.

### Gold crisis

Gold crisis can temporarily release:

- optional military upgrades;
- optional Castle-unit investment;
- market trades that do not improve the active objective.

Do not cut the Castle-age gold floor when the Castle transition is the active P1 target unless P0 survival requires it.

### Stone crisis

Stone remains at 0 until a Castle/tower demand is live.

Once a Castle demand is active:

- protect 5-8 stone miners;
- temporary P0 pressure can reduce them;
- restore them as soon as the threat clears.

This prevents the bot from mining stone forever because a Castle might someday be emotionally meaningful.

## 13. Timing-window reaction matrix

| Timing window | Worker reaction | Production reaction | Wall reaction | Tower reaction | Resource mode |
|---|---|---|---|---|---|
| Scout early | +1F/+1W on evidence | 2 Spears | short funnel if exposed | none by timing alone | CAV-DEFENSE |
| Scout expected | +1F/+1-2W at 2+ mounted | 2 -> 4 Spears | local reinforcement at 4+ | tower only for exposed resource | CAV-DEFENSE |
| Scout late | evidence-only packet | current mounted threshold | positional | positional | return B0 when stale |
| Archer early | +1F/+1-2W | 1 Range + 2 Skirms on evidence | short funnel | no timing-only tower | RNG-DEFENSE |
| Archer expected | +1F/+2-3W | 2 -> 4 Skirms | local wall if army reaches eco | tower if critical resource is denied | RNG-DEFENSE |
| Archer late | evidence-only | maintain only current threshold | positional | positional | B0/FC mode |
| MAA early | +1F/+2W | 1 Range + 3 Archers | 2-3 builders | only if resource denial | MAA-ARCHER |
| MAA expected | +1F/+3W | 3 -> 6 Archers | 2-4 builders | conditional | MAA-ARCHER |
| MAA late | +1F/+2W with evidence | maintain 4-6 | positional | positional | B0/FC mode |
| Tower early | +2W/+2S | current counters only | 2-4 builders | defensive tower admissible | TOWER-EMERGENCY |
| Tower expected | +2W/+2S | only required counters | 3-4 builders | first/second tower as threshold permits | TOWER-EMERGENCY |
| Tower late | +1-2W/+1-2S only if threat remains | current threat only | positional | positional | release when neutralized |
| Castle suspicion | +1G at most | close unnecessary production | no new walling | no timing-only tower | B0 -> Castle focus |
| Early Castle confirmed | +2F/+2G/-2W | close optional Feudal queues | none unless threatened | none unless threatened | FC-ACCEL |
| Castle + pressure | +1F/+1W/+2G | minimum counters + response package | only threatened resource | tower if justified | FC-DEFENSE |
| Castle late/stale | current-state only | current-state only | current-state only | current-state only | normal strategy |

## 14. Hard invariants

1. Timing never directly trains a unit.
2. Timing never directly builds a wall.
3. Timing never directly builds a tower.
4. Timing only changes interpretation confidence and therefore the minimum evidence required to open a demand.
5. Worker packets must have release conditions.
6. A second worker packet requires evidence that the first packet cannot satisfy the active demand.
7. A second production building requires queue/capacity evidence.
8. Tower pressure suspends Castle stone only while the actual defensive problem remains.
9. Opponent Fast Castle with weak Feudal army accelerates the own Castle trajectory; it does not create a larger Feudal standing army.
10. Existing queued units are not magically erased when a demand closes.
11. Existing useful walls/towers remain useful after a demand releases.
12. Stone stays at zero unless a live Castle/tower demand exists.
13. Castle stone becomes protected only after a strategic Castle purpose exists.
14. A worker allocation mode is subordinate to P0 crisis arbitration.
15. Map profile and timing window never override direct world-state evidence.
16. A stale timing window cannot reopen a closed demand.

## 15. Implementation ownership

Information provides:

- current game time;
- enemy military counts;
- production structure evidence;
- enemy Age;
- forward structures;
- resource exposure;
- water/transport context.

Strategy chooses:

- active timing interpretation;
- Arabia pressure mode;
- Castle acceleration;
- release/invalidation.

Economy owns:

- worker packets;
- resource allocation;
- crisis arbitration;
- capital protection.

Production owns:

- queue targets;
- production-building capacity;
- current + queued counts;
- closure of standing production demand.

Construction owns:

- wall builders;
- tower builders;
- production infrastructure;
- Castle builders.

State stores only persistent execution facts that cannot be safely derived from current world state.

The lifecycle remains:

    TIMING + OBSERVATION
        ->
    INTERPRETATION
        ->
    STRATEGIC MODE
        ->
    RESOURCE / PRODUCTION / CONSTRUCTION DEMANDS
        ->
    FEASIBILITY
        ->
    ACTION
        ->
    WORLD-STATE WITNESS
        ->
    RELEASE / INVALIDATE
        ->
    REASSESS

## 16. Current-game reference

The current September 22, 2026 update includes AI/pathfinding changes, more open competitive Arabian Desert terrain, funnel-wall behavior, and fixes around AI building failures and escrow edge cases. These are consistent with keeping worker allocation, construction, and production as separate responses to the same strategic interpretation rather than binding all reactions to a clock.

Reference:

- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- `LearnerAI/ARABIA_THRESHOLDS.md`
- `LearnerAI/ARABIA_OVERRIDE_THRESHOLDS.md`
- `LearnerAI/ARABIA_TIMING_WINDOWS.md`
