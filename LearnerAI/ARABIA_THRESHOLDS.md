# Arabia Thresholds: Byzantine Stock-AI

This document makes the Arabia/open-land profile numerically concrete.

The thresholds are deliberately based on **observed pressure and economic consequence**, not elapsed-game timers.

The goal is a competent stock-style Byzantine player:

- no Feudal army merely because Feudal Age exists;
- minimum defensive counters against a confirmed opening;
- small escalation steps;
- short, local walling rather than automatic full walling;
- towers only for exposed strategic resources or direct forward pressure;
- no Arabia Dock unless water has real value;
- Castle investment protected early enough to produce a real Castle, but not so early that every stone deposit becomes a religion.

## 1. State vocabulary

### Defense levels

| Level | Standing Feudal defense | Meaning |
|---|---|---|
| D0 | 0 | No confirmed military problem |
| D1-CAV | 2 Spearmen | Confirmed cavalry/scout threat |
| D1-RNG | 2 Skirmishers | Confirmed ranged threat |
| D2-MIXED | 2 Spearmen + 2 Skirmishers | Both threat classes are confirmed |
| D3-CAV | 4 Spearmen | Cavalry threat is materially larger than the initial counter floor |
| D3-RNG | 4 Skirmishers | Ranged threat is materially larger than the initial counter floor |
| D4-MIXED | 4 Spearmen + 4 Skirmishers | Sustained mixed pressure; normal maximum Feudal defensive package |

D4 is a **normal defensive ceiling**, not a standing target.

Going beyond D4 requires a separate strategic reason, such as sustained direct attack, a lost defensive position, or an explicit Feudal pressure plan.

## 2. Feudal military entry rules

### No military

Remain at D0 when all of the following are true:

- no enemy Stable is producing visible mounted units;
- no enemy Range is producing meaningful ranged pressure;
- no enemy military has reached the home-side economy;
- no forward military production or tower pressure is detected.

The normal Arabia plan is therefore allowed to bank toward Castle with no standing Feudal army.

### Two Spearmen

Open D1-CAV when any one of these is true:

1. enemy Stable is confirmed and at least 1 enemy mounted unit is observed;
2. 2 or more enemy Scouts/Light Cavalry are simultaneously active against the home economy;
3. enemy cavalry has entered the home-side economy or forced villagers off a resource;
4. a confirmed cavalry opening exists and a key food/gold/wood resource is exposed enough that one successful raid would materially damage the Castle trajectory.

Do **not** make 2 Spears merely because the enemy owns a Stable with no demonstrated cavalry pressure.

### Two Skirmishers

Open D1-RNG when any one of these is true:

1. enemy Range is confirmed and at least 2 enemy Archers are observed;
2. one enemy Archer has already reached the home-side economy and the Range remains active;
3. two or more enemy Archers are moving through the main approach to the exposed economy.

One enemy Range with no produced archers is an observation, not an automatic four-unit response.

### Mixed 2 + 2

Open D2-MIXED when both the cavalry and ranged entry conditions are true at the same time.

Do not add a second pair merely because the opponent has two production buildings. The second pair requires actual battlefield pressure or a clearly committed composition.

## 3. Feudal escalation rules

### Spears: 2 -> 4

Increase from 2 to 4 Spears when either:

- 3 or more enemy mounted units are observed;
- 2 or more enemy mounted units reach the economic area simultaneously;
- the initial two Spears cannot prevent repeated mounted access and the cavalry threat remains active at the next strategic reassessment;
- a second enemy Stable is confirmed **and** cavalry is actually being produced.

Do not scale from 2 to 4 solely because the enemy has two Stables.

### Skirmishers: 2 -> 4

Increase from 2 to 4 Skirmishers when either:

- 4 or more enemy ranged units are observed;
- 2 or more enemy Ranges are actively producing;
- the first two Skirmishers cannot keep ranged units away from the exposed economy and the ranged threat remains active at reassessment.

### Mixed escalation

Use 4 Spears + 4 Skirmishers only when both sides of the threat remain at D3 strength.

Normal Arabia Feudal standing defense should not exceed 8 units without an explicit higher-level demand.

### Escalation stop rule

When the enemy no longer satisfies the current defense threshold:

- stop adding units immediately;
- preserve existing counters;
- redirect new food/wood/gold toward the protected strategic trajectory.

Do not use a retry counter to decide whether escalation worked. The world state decides.

## 4. Feudal military resource gate

The standing-defense package cannot repeatedly consume the Castle bank.

When the current standing defense has reached D2 or higher:

- new counter production is allowed while the observed threat still satisfies its threshold;
- unnecessary upgrades and extra production are deferred;
- attack-only military production does not inherit the defensive demand automatically.

Once the threat falls back below D1:

**defensive production closes and Castle investment regains full resource authority.**

This is the concrete guard against producing roughly twenty Feudal Spears and twenty Feudal Skirmishers simply because the military rules keep asking for units.

## 5. Arabia wall thresholds

### No wall

Stay unwalled when:

- no confirmed Feudal military threat exists;
- the core economy is reasonably covered by TC/terrain;
- there is no direct enemy tower or forward-building problem.

Open Arabia does not justify a full perimeter by itself.

### Short resource wall

Build a **short palisade/gate funnel** when all of these are true:

1. D1 or higher military pressure is active;
2. at least one critical resource cluster is exposed;
3. the enemy has a viable land route into that resource without passing through TC protection;
4. a short wall can meaningfully delay, redirect, or narrow the attack.

The target is the exposed resource, not the entire base.

### Wall reinforcement

Add a second local wall/gate when any one is true:

- 4 or more enemy military units are committed;
- a previous raid has reached the exposed resource;
- enemy production is forward and the route is still open;
- the first wall creates a useful funnel that leaves another critical resource exposed.

### Full/large Arabia enclosure

Do **not** make a full perimeter a default Feudal demand.

Permit a larger enclosure only when at least two of these are true:

- 4+ enemy military units are actively pressuring;
- multiple independent approaches reach the economy;
- enemy forward military production is confirmed;
- the economy has multiple exposed resource clusters;
- the wall can be completed without materially delaying Castle investment.

### Wall wood cap

Before Castle Age:

- normal wall budget: **60-80 wood**;
- active rush defense: **up to 120 wood**;
- above 120 wood requires a separate persistent defensive reason.

The cap applies to **new walling investment**, not existing houses or already useful structures.

This keeps walling from quietly becoming the Feudal military equivalent of a hobby.

## 6. Arabia tower thresholds

### Outpost / first tower

Open a tower demand when:

1. a critical gold, wood, or food cluster is outside safe TC coverage;
2. D1 or stronger enemy pressure is active **or** an enemy forward tower/building threat is confirmed;
3. defending the resource with mobile units alone would require at least two standing counters or repeated villager idle time.

One tower is then preferred to another four defensive units if the tower provides durable positional coverage.

### Second tower

A second defensive tower requires:

- a separate critical economic point is exposed;
- the first tower does not cover it;
- threat remains at D2 or higher, or an independent enemy forward pressure exists.

### Tower ceiling

Before Castle:

- normal Arabia ceiling: **1 defensive tower**;
- sustained pressure ceiling: **2 defensive towers**;
- >2 requires direct tower/ram pressure or an explicit defensive posture.

### Tower upgrade

Do not automatically upgrade an Outpost just because Feudal Age starts.

Upgrade to a stronger tower only when:

- enemy ranged/mounted pressure remains active;
- the position is strategically valuable;
- the upgrade materially changes survivability or denies the attack route.

## 7. Arabia Dock thresholds

A Dock remains closed by default.

Open a Dock demand on Arabia when at least one of these is true:

### Fishing admission

- **5 or more usable fish** are available in the local water area;
- the fishing area is sufficiently safe to sustain boats;
- the land economy is not in an active P0 crisis.

Fewer than 5 usable fish is normally not enough to justify a dedicated Arabia fishing investment.

### Transport admission

Open regardless of fish count when:

- a required resource/expansion area is separated by water;
- transport is necessary to establish or preserve the intended position.

This is a transport-critical override.

### Naval admission

Open regardless of fish count when:

- the enemy has meaningful naval investment in the same water;
- water control materially protects access, trade, or expansion.

### Dock scaling

Do not build a second Dock merely because water exists.

Require:

- the first Dock has sustained production activity;
- the water objective remains active;
- one production queue is insufficient to service the current naval/fishing demand.

### Dock release

Stop new Dock/fishing investment when:

- fewer than 2 usable fishing opportunities remain and transport/naval value is absent;
- fish production has become materially less valuable than land food;
- enemy naval pressure has ended and water no longer controls access;
- transport objectives are complete.

Existing useful docks are infrastructure. Release means stop feeding them new obligations, not bulldoze them.

## 8. Castle-age trajectory threshold

### Open Castle trajectory

Enter the Castle trajectory when:

- Feudal Age is complete;
- the current standing defense is no higher than D2 unless the threat is genuinely unavoidable;
- villager production is continuous;
- there is no active P0 food/wood crisis;
- the economy can pursue the Castle-age resource requirement without abandoning the current defensive floor.

The normal target is the Castle-age cost, not an arbitrary elapsed-time checkpoint.

### Protected Castle bank

Once the Castle resource trajectory is active:

- unnecessary Feudal military expansion closes;
- optional walls/towers are deferred;
- Market spending is allowed only when it materially improves the Castle timing or solves a crisis;
- extra production is opened only when current military demand justifies it.

### Castle trajectory suspension

Suspend the Castle bank when:

- D3/D4 pressure is active and the economy cannot survive without stronger defense;
- repeated raids materially reduce villager production;
- the enemy has created a forward position that must be removed before Castle is safe;
- a transport/water objective becomes strategically necessary.

Suspension is not cancellation.

### Castle trajectory restoration

Restore the Castle bank when:

- standing defense returns to D2 or below;
- villager production is stable;
- the immediate threat is no longer growing;
- resource income is again sufficient to meet the Castle objective.

## 9. First Castle investment threshold

Castle Age and Castle construction are separate decisions.

Do **not** begin Arabia stone investment merely because Castle Age was reached.

Open first-Castle stone investment only when all are true:

1. Castle Age is real;
2. a concrete Castle purpose exists;
3. the economy has no unresolved P0 crisis;
4. standing Feudal/Castle military is not consuming the entire available resource surplus;
5. the intended Castle will provide a durable strategic capability.

Concrete Castle purposes include:

- protected base anchor against sustained pressure;
- forward control of a high-value choke or resource area;
- active Cataphract/Varangian Guard or other Castle-unit package;
- Trebuchet/late siege platform;
- durable positional defense that replaces repeated Feudal spending.

### Stone threshold

Once the first-Castle demand is active:

- below **450 stone**: stone investment is an active project, but other P0/P1 needs can temporarily preempt it;
- **450-649 stone**: Castle stone becomes a protected conversion resource unless a P0 crisis exists;
- **650 stone**: Castle construction becomes immediately serviceable;
- above **650 stone**: stop treating first-Castle stone as a generic economic sink unless a second strategic Castle is explicitly demanded.

### Castle cancellation

Cancel the first-Castle demand only when:

- its strategic purpose disappears;
- another conversion demonstrably replaces it;
- the resource opportunity cost becomes structurally unacceptable;
- or the position has changed enough that the Castle would no longer solve the problem it was opened to solve.

A temporary shortage of stone is not cancellation.

## 10. Priority ordering when thresholds collide

Use this order:

### P0

1. Villagers.
2. Food continuity.
3. Population capacity.
4. Immediate exposed-economy survival.
5. D1-D4 defensive package according to actual threat.

### P1

6. Castle-age resource trajectory.
7. Farms/economic throughput required to sustain it.
8. Core production needed to maintain the minimum defense.

### P2

9. Short walls.
10. First tower.
11. Dock when a real admission test passes.
12. Additional military beyond the minimum defense floor.
13. Siege/Monastery/other situational capability.

### P3

14. First Castle construction after a genuine Castle purpose is established.
15. Extra TCs.
16. Additional production.
17. Larger siege/naval/Monk investment.

This ordering is not a global scheduler. It describes what the Arabia strategy must protect when no higher-order threat overrides it.

## 11. One-line decision rules

These are the compact rules the Strategy layer should eventually be able to emit.

    enemy cavalry >= 1 + Stable confirmed
        -> 2 Spearmen

    enemy archers >= 2 + Range confirmed
        -> 2 Skirmishers

    both thresholds true
        -> 2 Spears + 2 Skirms

    enemy cavalry >= 3
        -> 4 Spears

    enemy ranged >= 4
        -> 4 Skirms

    both escalations active
        -> 4 Spears + 4 Skirms
        -> normal Feudal defense ceiling reached

    D1+ threat + exposed critical resource + meaningful funnel
        -> short wall/gate

    D2+ threat + separate exposed critical resource
        -> second local wall/gate or tower

    exposed critical resource + D1+ threat + mobile defense inefficient
        -> first tower

    second independent exposed resource + continuing D2+ threat
        -> second tower

    usable fish >= 5
        -> Dock admissible

    transport required
        -> Dock/Transport admissible regardless of fish count

    enemy naval control matters
        -> Dock/naval response admissible

    Feudal + no P0 crisis + defense <= D2
        -> Castle trajectory protected

    Castle Age + real Castle purpose + stone project
        -> stone investment active

    Castle stone >= 450
        -> protect Castle stone from optional spending

    Castle stone >= 650
        -> Castle action immediately serviceable

    no live Castle purpose
        -> do not gather stone merely because 650 is possible

## 12. Implementation rule

These thresholds are semantic gates, not instructions to invent new state variables.

Information should expose:

- enemy Stable/Range;
- visible mounted/ranged counts;
- whether enemy units reached the home economy;
- exposed resource status;
- meaningful water/fish count;
- transport necessity;
- forward production/tower pressure;
- current resource and production crises.

Strategy converts those observations into the defense level and capability demand.

Military owns the standing-unit execution.

Construction owns walls, towers, docks, and Castle construction.

Economy owns resource allocation and protects the active Castle bank.

Every demand still follows:

    DEMAND
      -> ADMISSIBILITY
      -> CAPABILITY
      -> FEASIBILITY
      -> ACTION
      -> WORLD-STATE WITNESS
      -> RELEASE / INVALIDATE
      -> REASSESS

No timer-based "build X at minute Y" rule is required.

## 13. Why these thresholds are deliberately conservative

The current official AI direction emphasizes compressed development, selective funnel walls, economic expansion, and map-conditioned transport rather than indiscriminate static investment. The latest September 2026 update also describes Arabia as highly open with scarce shelter and notes continued AI/pathfinding work. Community discussion likewise treats open-Arabia walling as situational rather than mandatory, while noting that excessive stone/walling competes with Castle/TC investments.

References:

- https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- https://forums.ageofempires.com/t/feedback-on-ais-new-feature-walling/202468
- https://forums.ageofempires.com/t/whats-the-current-status-of-stone-walls/271370
- https://aoeaidatabase.pythonanywhere.com/ai?name=Naga
