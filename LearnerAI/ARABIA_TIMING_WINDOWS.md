# Arabia Timing Windows

This document defines **timing windows**, not timed build-order commands, for the Arabia/open-land profile.

A window answers:

> When should the Strategy/Information layers treat this pressure as plausible, urgent, late, or suspicious?

It does **not** answer:

> Build this unit at 08:37.

The observed state always outranks the clock.

Recent community timing references place generic MAA pressure around the 10:00-11:30 arrival band, Scouts around 11:05-12:30, and two-range Archers around 13:00 with a developed ranged package. Contemporary 2026 discussion also describes earlier Feudal timing and substantial Arabia pressure, so these windows are deliberately ranges rather than exact timestamps.

## 1. Timing semantics

Each pressure family has four timing bands.

| Band | Meaning |
|---|---|
| Early | A pressure signal in this window deserves immediate investigation because the opponent is investing heavily or using a civ-specific fast line |
| Expected | Normal arrival/pressure timing for a competent standard opening |
| Late | Still possible, but the opponent should have a visible explanation or transition |
| Stale | Timing alone must no longer create a standing demand; current evidence is required |

The timer never creates a unit demand by itself.

The timer changes the **confidence threshold for interpreting incomplete scouting**.

## 2. Arabia master timing table

| Pressure | Early | Expected | Late | Stale |
|---|---|---|---|---|
| Scout/cavalry | 08:30-10:30 | 10:30-12:30 | 12:30-14:00 | >14:00 |
| Archers | 09:30-11:30 | 11:30-13:30 | 13:30-15:00 | >15:00 |
| Men-at-Arms | 08:30-10:00 | 10:00-11:30 | 11:30-12:30 | >12:30 without current evidence |
| Tower rush | 07:30-09:30 | 09:30-10:30 | 10:30-11:30 | >11:30 unless paired with other forward pressure |
| Opponent Fast Castle | 15:30-17:00 | 17:00-18:15 | 18:15-19:15 | >19:15 as an “early Castle” signal |

These are **arrival/pressure interpretation windows**, not build-start timestamps.

The current game also includes a September 2026 update with AI/pathfinding rework and a more open competitive Arabian Desert variant, so exact movement and map geometry can materially shift practical arrival times.

## 3. Scout / cavalry timing windows

### 08:30-10:30: early scout signal

A mounted signal in this window is unusually important.

Examples:

- multiple enemy Scouts visible;
- enemy Stable confirmed unusually early;
- first mounted unit already approaching the home side.

Response:

- raise scout/cavalry confidence;
- inspect enemy Stable and food/gold allocation;
- prepare the 2-Spear threshold if current military evidence supports it;
- prepare short walling around the most exposed resource.

Do not automatically create Spears solely because the clock entered 08:30.

### 10:30-12:30: expected scout pressure

This is the primary Arabia Scout interaction window.

If two or more Scouts/mounted units are active:

    2 Spears -> expected defensive floor

If four or more mounted units are active:

    4 Spears -> normal escalation

If the enemy remains visibly committed to mounted production:

    continue the current defense band
    do not produce additional Spears without increased observed count

### 12:30-14:00: late Scout pressure

A mounted attack is still credible, but the AI should demand evidence.

At this point:

- visible mounted units;
- active Stable production;
- repeated home-economy contact;
- or a clear scout-to-knight/cavalry transition

should be required to maintain the mounted-defense demand.

A clock-only trigger is no longer sufficient.

### After 14:00

Do not create a fresh Arabia Scout-defense demand from timing alone.

Use current military facts.

This prevents a late, harmless surviving Scout from keeping a Spear production loop alive while the opponent is actually going Castle.

## 4. Archer timing windows

### 09:30-11:30: early Archer signal

This usually indicates:

- fast Range;
- aggressive 1-range play;
- civ/economic acceleration;
- or a very early Feudal commitment.

Require visible Archers or clear forward Range activity before opening the full ranged-defense package.

A lone Range discovered in this window is an information clue, not six Skirmishers.

### 11:30-13:30: expected Archer pressure

This is the main straight-Archer window.

At:

- 2-3 visible Archers -> 2 Skirmishers;
- 4-7 -> 4 Skirmishers;
- 8+ or two active Ranges -> 6 Skirmishers.

The current timing reference places a developed two-range Archer arrival around 13:00 with approximately six Archers and Fletching, while straight one-range pressure can appear earlier.

### 13:30-15:00: late ranged transition

A large ranged force in this window is still dangerous, but should usually have an identifiable reason:

- two Ranges;
- MAA -> Archer follow-up;
- Scouts -> Archer follow-up;
- defensive range producing while the opponent goes Castle;
- forward range.

Require current unit counts to maintain the higher Skirmisher target.

### After 15:00

Do not infer early-Feudal Archer pressure from timing alone.

Current visible ranged production and army composition are authoritative.

## 5. Men-at-Arms timing windows

MAA deserves a tighter early-warning system because the useful defensive response must begin before the first MAA reaches the economy.

### 06:30-08:30: commitment detection

This is not usually the main attack-arrival window.

It is the **scouting and inference window**.

Raise MAA suspicion when:

- opponent has Barracks activity;
- several enemy villagers are committed to gold;
- Dark Age military units are visible;
- Feudal timing and resource distribution imply a fast infantry upgrade;
- Militia are already moving forward.

Do not create the full Archer package from one clue.

### 08:30-10:00: early MAA

MAA arriving this early should be treated as aggressive pressure.

Response:

- safe Archery Range placement;
- 3-4 Archers depending current MAA count;
- short walls/funnels around critical resources;
- preserve the Castle trajectory unless the attack is actually damaging it.

### 10:00-11:30: expected MAA window

This is the main MAA arrival band.

At 2 MAA:

    3 Archers

At 3-4:

    4 Archers

At 5-7:

    6 Archers

The community timing reference places generic MAA arrival around 10:00-11:30, with the first defensive MAA-related unit appearing earlier.

### 11:30-12:30: late MAA

Require stronger evidence:

- surviving MAA count;
- forward Barracks;
- active upgrade/production;
- continuing economic pressure.

A late MAA sighting can represent a delayed opening or an MAA -> Archer transition.

### After 12:30

The clock no longer opens the MAA response.

Use the visible composition.

This prevents the bot from making Archers for an enemy MAA opening that ended twenty minutes ago in practical terms.

## 6. Tower-rush timing windows

Tower pressure must be interpreted earlier than unit pressure because the structure itself can create a permanent economic denial.

### 07:30-09:30: high-risk tower window

A forward foundation near a critical resource in this period is an immediate strategic signal.

If:

- foundation is close;
- builders are committed;
- resource is important;

then activate the tower-rush override immediately.

Do not wait for completion.

### 09:30-10:30: expected tower window

Still a fully credible tower rush.

Require:

- forward foundation;
- two or more builders;
- military protection;
- or direct resource denial

before escalating to the full T2/T3 response.

### 10:30-11:30: late tower pressure

A new tower is still relevant, but the AI should ask whether this is:

- residual Feudal aggression;
- MAA + towers;
- Archer + towers;
- a forward siege/production plan;
- or simple defensive investment.

The clock alone cannot justify a new tower response.

### After 11:30

Treat a newly founded enemy tower as a **positional event**, not as a generic “tower rush” state.

Its distance from and control over a critical resource matters more than its age.

## 7. Early Castle-pressure timing windows

This window concerns the **opponent's Castle transition** and the decision to accelerate or suspend the Byzantine Castle trajectory.

### 13:30-15:30: Castle suspicion

This is the reconnaissance phase.

Do not assume Fast Castle from low military count alone.

Look for:

- unusually weak Feudal military investment;
- sustained gold income;
- Market activity;
- missing Feudal production;
- resource banking behavior;
- reduced pressure on the Byzantine economy.

The AI should increase Castle suspicion, not yet redirect the entire economy.

### 15:30-17:00: early Castle confirmation

If the opponent actually reaches Castle in this interval with:

- fewer than roughly five Feudal military units;
- no major active Feudal all-in;
- visible Castle follow-up potential;

then activate **Castle acceleration**:

    close optional Feudal unit creation
    preserve minimum defense
    protect food/gold
    protect own Castle resources
    avoid unnecessary towers/walls

This is the primary early-Castle pressure window.

### 17:00-18:15: expected Castle conversion

Castle Age here is still early enough to materially alter the Byzantine decision.

If the opponent has:

- Knights;
- Monks;
- siege;
- Castle units;
- extra TC pressure;

then keep the own Castle trajectory protected and begin the appropriate capability response.

If the opponent reaches Castle without a real follow-up, treat the timing as information rather than an automatic military emergency.

### 18:15-19:15: normal/late Castle transition

At this point the opponent's Castle is no longer surprising.

The AI should stop using timing as the main reason for acceleration.

Current enemy production, unit composition and economic expansion determine the response.

### After 19:15

Do not call this **early Castle pressure**.

The opponent may still be ahead in age or economy, but that is a current-state problem, not an opening timing classification.

## 8. Timing windows for interaction

Timing must modify confidence, not bypass observation.

### Early window + evidence

Highest confidence.

    early timing
    + relevant building/unit evidence
    -> immediate demand admission

Example:

    08:45
    + forward Barracks
    + Militia moving
    -> MAA suspicion rises sharply

### Expected window + partial evidence

Normal confidence.

    expected timing
    + one relevant clue
    -> investigate
    + actual unit
    -> open demand

Example:

    11:10
    + enemy Range observed
    + 2 Archers visible
    -> 2 Skirms

### Late window + weak evidence

Low confidence.

    late timing
    + generic building only
    -> no escalation

Example:

    14:20
    + enemy Stable
    + no visible mounted units
    -> do not create new Spear demand

### Stale window

Current world state only.

    timing expires
    -> timing no longer writes demand

This is the critical anti-loop rule.

## 9. Timing + threshold interaction

Timing never replaces the concrete thresholds from:

- `LearnerAI/ARABIA_THRESHOLDS.md`
- `LearnerAI/ARABIA_OVERRIDE_THRESHOLDS.md`

Instead:

    TIMING WINDOW
        changes confidence

    OBSERVED UNIT / STRUCTURE
        establishes actual pressure

    THRESHOLD
        establishes required response size

Example:

    09:10 + 1 Scout
        -> high scout suspicion
        -> no automatic 2-Spear demand

    11:10 + 2 Scouts
        -> expected Scout window
        -> 2 Spears

    13:40 + no Scouts
        -> stale Scout timing
        -> no new Spears

## 10. Byzantine-specific timing guard

Byzantines should exploit their cheap counter capability without turning every expected timing window into unit production.

A timing window therefore changes the **minimum evidence required to open the counter**.

It does not change the hard ceiling.

Example:

    10:00-11:30
        enemy mounted count >= 2
        -> 2 Spears

    10:00-11:30
        enemy mounted count = 0
        -> 0 Spears

Likewise:

    11:30-13:30
        enemy Archers >= 2
        -> 2 Skirms

    11:30-13:30
        enemy Archers = 0
        -> 0 Skirms

The clock is an information prior, not a production order.

## 11. Timing overrides for missing information

When scouting is incomplete:

### 08:30-10:00

Assume **watchful**, not **armed**.

One missing scout/MAA clue can justify repositioning and scouting.

### 10:00-12:30

Assume **prepared** if the opponent's economy strongly suggests aggression.

This may justify:

- barracks;
- range;
- short walls;
- one counter pair

before the army is fully visible.

### 12:30-15:00

Require actual military evidence for continued Feudal production.

### 15:00+

Require actual enemy age or production evidence for age-response changes.

This gives the AI a bounded anticipation mechanism without creating speculative production loops.

## 12. Timing-based release rules

Release a timing-derived suspicion when:

- the window expires;
- the relevant military building disappears or becomes inactive;
- the expected army does not materialize;
- the enemy enters Castle and stops the Feudal line;
- the opponent's economy clearly transitions to another strategy.

Timing suspicion is temporary.

World-state evidence is persistent.

## 13. Compact timing rules

    08:30-10:30
        scout/cavalry = investigate aggressively

    10:30-12:30
        scout/cavalry = expected contact window

    09:30-11:30
        archers = early ranged signal

    11:30-13:30
        archers = expected ranged pressure

    06:30-08:30
        MAA = commitment/inference window

    08:30-10:00
        MAA = early arrival

    10:00-11:30
        MAA = expected arrival

    07:30-09:30
        tower = high-risk early tower

    09:30-10:30
        tower = expected tower pressure

    15:30-17:00
        opponent Castle = early-Castle acceleration

    17:00-18:15
        opponent Castle = expected Castle conversion

    18:15+
        opponent Castle = current-state response, not timing response

## 14. Implementation contract

Information owns:

- current game time;
- visible military counts;
- enemy production structures;
- enemy Age;
- forward structures;
- resource allocation clues;
- observation freshness.

Strategy owns:

- timing confidence;
- opening-pressure interpretation;
- Castle acceleration;
- pressure suspicion;
- release of timing-derived suspicion.

Military owns:

- actual counter targets.

Construction owns:

- walls;
- towers;
- production infrastructure.

Economy owns:

- protected Castle resource trajectory;
- crisis arbitration.

The compiler should validate that timing predicates are **writers of interpretation**, not direct action writers.

Preferred lifecycle:

    TIME + OBSERVATION
        ->
    INTERPRETATION
        ->
    DEMAND
        ->
    CAPABILITY
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

There should be no:

    TIME
      -> TRAIN SPEAR

direct path.

## 15. Sources

- Current official AoE2DE Update 185872, September 22, 2026:
  https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- AoE2 community timing discussion for MAA, Scouts and Archers:
  https://forums.ageofempires.com/t/whats-the-time-that-each-opening-hits/214870
- Current 2026 Arabia discussion on earlier Feudal timing:
  https://www.reddit.com/r/aoe2/comments/1w6ryjc/why_is_everyone_going_up_to_feudal_so_fast_on/
- Current 2026 MAA/Arabia discussion:
  https://www.reddit.com/r/aoe2/comments/1w2ysg8/arabia_every_opening_is_maa/
- Current 2026 Arabia walling/FC discussion:
  https://www.reddit.com/r/aoe2/comments/1tgp9le/arabia_in_2026/
