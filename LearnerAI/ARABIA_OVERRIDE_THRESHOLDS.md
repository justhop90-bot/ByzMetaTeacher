# Arabia Threshold Overrides

This document defines exception thresholds that override the normal Arabia thresholds in `LearnerAI/ARABIA_THRESHOLDS.md`.

These are **specific pressure recognizers**, not additional build orders.

The normal Arabia rules remain authoritative unless one of these exception states is active.

## 1. Override rule

An override must satisfy three conditions:

1. the underlying pressure is actually observed;
2. the exception changes the correct capability package;
3. the response remains bounded.

An override can raise a unit/wall/tower target temporarily.

It cannot create an unlimited production loop.

When the observed condition disappears, the normal Arabia thresholds resume.

## 2. Scout / cavalry override

### Important distinction

The starting enemy Scout is not an attack signal.

A lone Scout moving around the map is Information.

A growing mounted count entering the economic area is Military pressure.

### Scout thresholds

| Observed state | Override | Response |
|---|---|---|
| 0-1 enemy Scouts, no Stable evidence | none | D0 |
| 2 Scouts active near home OR confirmed Stable with one produced mounted unit | S1 | 2 Spearmen |
| 3-4 mounted units OR repeated mounted entry into the economy | S2 | 4 Spearmen |
| 5-6 mounted units OR 2 active Stables producing mounted units | S3 | 6 Spearmen; no additional Feudal counter unless another threat exists |
| 7+ mounted units OR sustained all-in scout/light-cavalry pressure | S4 | 6 Spearmen + local wall/tower package; suspend optional Castle spending until the economy is safe |

Because Byzantines receive a 25% discount on the Spearman line, a small anti-cavalry package is particularly compatible with the civilization's defensive identity.

### Scout release

Return from S3/S4 when:

- enemy mounted count falls below the active threshold;
- no replacement production is observed;
- mounted units stop reaching the home economy;
- and the existing Spear count can preserve the resource.

Do not delete or instantly disband excess Spears.

Stop creating additional Spears and resume the normal Arabia/Castle resource allocation.

### Scout + archer combination

If mounted and ranged thresholds are simultaneously active:

    mounted threshold
        -> Spear demand

    ranged threshold
        -> Skirmisher demand

Do not increase one response merely because the other threat exists.

This preserves the principle that each counter package pays for the threat actually observed.

## 3. Archer override

### Archer thresholds

| Observed state | Override | Response |
|---|---|---|
| 0-1 enemy Archer | none | no mandatory Skirmisher production |
| 2-3 enemy Archers | A1 | 2 Skirmishers |
| 4-7 enemy Archers | A2 | 4 Skirmishers |
| 8+ enemy Archers OR 2 active Ranges producing | A3 | 6 Skirmishers |
| 8+ Archers + forward position/ram/tower | A4 | 6 Skirmishers + local wall/tower; Castle bank can be suspended |

The A3/A4 exception is deliberately above the normal D3/D4 Arabia threshold because a genuine two-Range Feudal army can arrive faster than four Skirmishers can stabilize an exposed economy. The exception ends as soon as the pressure no longer warrants six.

### Archer approach rule

Do not use total enemy Archery Range count as the sole trigger.

Require one of:

- visible produced Archers;
- repeated Archer movement toward the home economy;
- an active forward Archer position.

A Range in the enemy base is Information, not damage.

### Archer release

Drop the Skirmisher creation target back to the lower threshold when:

- visible ranged count falls below the active band;
- no active forward ranged production remains;
- the enemy begins a Castle transition and ranged production visibly stops;
- the home economy is no longer being exposed to ranged pressure.

## 4. Men-at-Arms override

### Core rule

**Men-at-Arms do not count as the ranged or cavalry threat.**

Do not answer Men-at-Arms with the normal Spear/Skirmisher package.

The correct Feudal response is an Archer capability, supported by walls, TC positioning, or a defensive tower when necessary.

The official game guidance describes Archer-line units as effective against infantry and Spearman-line units as the cavalry counter, which is why the MAA override must be a separate branch.

### MAA thresholds

| Observed state | Override | Response |
|---|---|---|
| 1 enemy MAA outside economy | M0 | no automatic mass response; protect villagers with positioning |
| 2 enemy MAA approaching economy | M1 | 3 Archers + short wall/funnel if available |
| 3-4 enemy MAA | M2 | 4 Archers; preserve TC/resource shelter |
| 5-7 enemy MAA OR active forward Barracks/MAA production | M3 | 6 Archers + local wall/gate |
| 8+ MAA OR MAA + ranged support | M4 | 6-8 Archers + 2 Skirmishers if ranged support is present; additional tower escalation is allowed only if the general tower/resource test is also satisfied |
| MAA are actively idling multiple critical resources | M5 | suspend optional Feudal spending and protect the endangered economy first |

The MAA package is intentionally Archer-heavy rather than Skirmisher-heavy.

### MAA + archer override

When both MAA and Archers are present:

    MAA count
        -> Archer floor

    Archer count
        -> Skirmisher floor

Do not let the Archer branch satisfy both roles.

A composition such as 4 MAA + 6 Archers therefore produces:

    6 Archers
    + 4 Skirmishers

only when the separate ranged threshold is also reached.

### MAA release

Drop the Archer target when:

- MAA production stops;
- MAA count falls below the active threshold;
- the enemy has transitioned toward Castle **and** the surviving MAA no longer satisfy the active pressure threshold;
- or the enemy's surviving MAA can no longer reach the economy.

Do not keep manufacturing Archers simply because the enemy once had MAA.

## 5. Tower-rush override

Tower pressure is a structural threat. It therefore overrides ordinary Feudal unit-count thresholds.

### Tower-state bands

| Observed state | Override | Response |
|---|---|---|
| Foundation exists but does not materially threaten a critical resource | T0 | monitor; no automatic tower |
| Foundation is spatially close enough to threaten a critical resource | T1 | short emergency wall/funnel; mobilize available units |
| Threatening foundation + 2+ builders or military escort | T2 | emergency defensive tower admissible + relevant counter units |
| Completed tower controls a critical resource or route | T3 | defensive tower or safe relocation path; suspend optional Castle spending |
| 2+ forward towers or foundations threaten the same economic zone | T4 | defensive tower + wall/gate + relevant counter units; Castle bank suspended |
| Tower + MAA/Archers at the same forward position | T5 | treat as full Feudal pressure; protect economy first |

The spatial test is deliberately qualitative at the strategy layer. Do not hard-code a universal "12 tiles" rule into the compiler. Map the threat to engine-native distance/targeting facts and tune the actual distance band from runtime evidence.

### Tower builder rule

A single incomplete tower with one builder is not automatically a rush emergency.

Escalate immediately when:

- 2+ builders are committed;
- the construction site is close enough to deny a critical resource;
- a second forward foundation appears;
- or military units are protecting the construction.

### Tower completion rule

A completed enemy tower is a stronger signal than a foundation.

When a completed tower controls:

- gold;
- primary woodline;
- primary food source;
- forward production area;
- or the only practical route around a resource,

the affected resource becomes a P0 protection problem.

### Tower release

Release the tower override when:

- the construction is cancelled/destroyed;
- the tower no longer threatens a critical resource;
- the economy has safely relocated;
- or the enemy forward position is permanently neutralized.

## 6. Early Castle-pressure override

There are two different situations.

They must not share one demand.

### A. Opponent fast-Castle

Treat the opponent as fast-Castle pressure when:

1. enemy Castle Age is confirmed;
2. enemy Feudal military count is below 5;
3. no major Feudal all-in is currently threatening the economy;
4. the opponent has invested in an identifiable Castle follow-up such as Knights/Cataphracts/Monks/siege/TC.

This is not an emergency.

It is a **conversion warning**.

### Opponent fast-Castle response

When the FC condition is true:

- close unnecessary Feudal unit production;
- retain only the minimum defense required by current observed units;
- protect the Castle bank;
- accelerate the own Castle trajectory;
- avoid unnecessary towers and walls;
- prepare the cheapest appropriate Castle response.

In other words:

    enemy Castle + weak Feudal army
        -> stop feeding the Feudal war
        -> protect own Castle

A player who sees the opponent click Castle and answers by manufacturing twenty Spearmen has discovered a remarkable new way to lose both ages.

### B. Opponent Castle + immediate pressure

Escalate from FC-warning to FC-threat when:

- enemy reaches Castle;
- and 1+ Knights/heavy mounted units, siege, or Castle-unit pressure reaches the home economy;
- or a forward Castle/production position threatens a critical resource.

Response:

- 2-4 Spears for mounted pressure;
- 2-4 Skirmishers for ranged support;
- defensive tower if a critical resource is exposed;
- suspend optional Castle-bank spending only until the immediate pressure is stabilized.

### C. Opponent Castle + forward siege/Castle

Treat as severe pressure when:

- enemy Castle is forward enough to directly constrain the economy;
- a Siege Workshop/Siege unit is operating from the forward position;
- or a forward Castle threatens the primary economy.

Response:

- Castle trajectory is temporarily subordinate to survival;
- Siege capability becomes P2/P1 depending on immediate threat;
- wall/tower resources can become P0;
- military production expands only to the smallest force that can prevent collapse.

This is the point where "I was saving for Castle" stops being a useful sentence.

## 7. Early Castle acceleration override

The Arabia Castle bank should receive an **acceleration** override when:

- the opponent has reached Castle;
- enemy Feudal military remains below 5;
- own defense is at or below D2;
- own villager production is continuous;
- no P0 food/wood crisis exists.

Then:

1. close optional Feudal unit production;
2. close optional wall/tower investment;
3. protect food/gold required for Castle;
4. protect required Castle prerequisites;
5. use Market only when it materially reduces the Castle delay;
6. reassess immediately after Castle completion.

### Castle acceleration block

The acceleration override is blocked by:

- D3/D4 sustained military pressure;
- active tower rush;
- multiple enemy military groups reaching the economy;
- food collapse;
- villager production interruption;
- loss of the main resource base.

When blocked, return to the normal Arabia trajectory rather than creating a special "emergency Castle" state.

## 8. Priority override table

| Pressure | Normal Arabia response | Override |
|---|---|---|
| 1 enemy Scout | none | none |
| 2+ active enemy Scouts / 1 mounted unit | 2 Spears | S1 |
| 3-4 mounted | 2-4 Spears | S2 |
| 5-6 mounted / 2 active Stables | 4 Spears | S3 = 6 Spears |
| 2-3 Archers | 2 Skirms | A1 |
| 4-7 Archers | 4 Skirms | A2 |
| 8+ Archers / 2 active Ranges | 4 Skirms | A3 = 6 Skirms |
| 2 MAA | general defense | M1 = 3 Archers |
| 3-4 MAA | 2-4 counters | M2 = 4 Archers |
| 5-7 MAA | normal D4 | M3 = 6 Archers |
| 8+ MAA + support | D4 | M4 = Archer + Skirmisher package |
| 1 nearby tower foundation | monitor | T1 |
| 1 tower + 2+ builders | local defense | T2 |
| Completed tower over resource | local defense | T3 |
| 2+ forward towers | normal defense | T4 |
| Enemy Castle, <5 Feudal units | Castle trajectory | FC acceleration |
| Enemy Castle + units at home | Castle trajectory | FC threat |
| Enemy forward Castle/siege | normal defense | survival-first override |

## 9. Override interaction rules

### Scouts + Archers

Do not add Spears because Archer count increased.

Use:

    mounted pressure -> Spears
    ranged pressure -> Skirms

### MAA + Scouts

MAA triggers Archers.

Scouts trigger Spears.

Minimum mixed package is therefore:

    3-4 Archers
    + 2 Spears

unless the actual counts justify escalation.

### MAA + Archers

Use:

    Archer floor for MAA
    + Skirmisher floor for enemy Archers

This is preferable to blindly raising one counter.

### Tower + MAA

Tower pressure wins the resource-protection decision.

Do not merely make Archers while the tower cuts off gold or wood.

First protect the resource.

### Fast Castle + low Feudal army

Fast Castle accelerates the own Castle trajectory.

It should **reduce**, not increase, unnecessary Feudal military.

### Fast Castle + real army pressure

Immediate defense first.

The Castle bank resumes as soon as the pressure returns below the relevant threshold.

## 10. Hard ceilings

These ceilings are there specifically to prevent runaway reactive production.

Normal Arabia:

- Spears: 4
- Skirmishers: 4
- Archers: 0 unless a specific MAA/pressure package opens them
- Defensive towers: 1
- Local wall investment: 60-80 wood

Override ceilings:

- Spears: 6 for genuine all-in mounted pressure
- Skirmishers: 6 for genuine two-Range ranged pressure
- Archers: 6 for sustained MAA
- Archers: 8 only for MAA + continuing pressure or Castle-transition conversion
- Defensive towers: 2 before Castle under sustained rush pressure

Exceeding these values requires a separate strategic pressure demand.

The numbers are **standing defensive targets**, not guaranteed final battlefield populations.

## 11. Implementation contract

Information provides:

- visible mounted count;
- visible Archer count;
- visible MAA count;
- enemy Stable/Range/Barracks activity;
- tower foundations and completed towers;
- builder count;
- spatial relation to critical resources;
- enemy Age;
- forward military/siege/Castle state.

Strategy selects the active override.

Military owns the counter demand and production target.

Construction owns walls/towers.

Economy protects or suspends the Castle bank.

State stores only persistent override conditions that cannot be derived directly from current engine state.

The lifecycle remains:

    OBSERVE
      -> INTERPRET
      -> OVERRIDE
      -> DEMAND
      -> CAPABILITY
      -> FEASIBILITY
      -> ACTION
      -> WORLD-STATE WITNESS
      -> RELEASE / INVALIDATE
      -> REASSESS

Do not implement these as unrelated hard-coded "rush scripts."

## 12. Why these exceptions exist

Community Arabia discussion consistently treats Men-at-Arms, Scouts, Archers, and tower pressure as distinct opening problems rather than one generic "rush" category. Typical community descriptions place MAA earlier than Scouts and straight Archers, while noting that Scout pressure commonly produces Spears and Archer pressure produces Skirmishers. Community discussion also explicitly treats tower pressure as a positional problem that may justify changing the defensive structure of the response.

The official game guidance likewise describes Archer-line units as an infantry counter and Spearman-line units as a cavalry counter, supporting the separate MAA branch instead of treating every Feudal threat as a Spear/Skirmisher problem.

## 13. Reference sources

- https://aoeaidatabase.pythonanywhere.com/ai?name=Naga
- https://forums.ageofempires.com/t/whats-the-time-that-each-opening-hits/214870
- https://forums.ageofempires.com/t/scouts-are-kill-on-arabia/220726
- https://forums.ageofempires.com/t/any-tips-for-hardest-ai-difficulty/238151
- https://www.ageofempires.com/learn-to-play/military-and-economy-aoe2/
