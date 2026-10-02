**7/7 PROMPTS**

# Byzantine Core v1 — Age-First Bot Roadmap

**Artifact:** Byzantine Core v1
**Branch:** `bot/byzantine-core-v1`
**Method:** community-derived behavior expressed through the existing Byzantine StrategyProfile and existing compiler/native vocabulary.
**Style rule:** every addition must read like the existing `LearnerAI/Compiler/bots/byzantine.py`: small pure helpers, `StrategicDemandSpec` construction, `replace(...)` for execution guards, explicit native fact strings, existing `StrategyPosture`/`StrategicPriority` values, deterministic tuple ordering, focused unit tests, no second scheduler, no new bot-side language.

## **1/7 — Prompt 1: Dark Age Foundation — IMPLEMENTED**

### Objective

Turn Dark Age from a villager-count checkpoint into a real economic opening while preserving the existing bot architecture.

### Implemented in this prompt

- Dark Age villager baseline raised from 18 to 22.
- Counter-opening branch extends the Dark target to 24.
- Arena Fast Castle branch extends the Dark target to 26.
- Water branches extend the Dark target to 24.
- Loom is now an explicit Dark Age research demand using the same `StrategicDemandSpec` construction style as the existing age-transition demand.
- Loom protects its factual 50-gold cost through the existing opportunity-cost mechanism.
- Existing Feudal/Castle/Imperial villager stages remain intact.
- No generic compiler changes.
- No replacement economy scheduler.
- Tests lock the new identities and emitted Loom action.

### Deferred execution dependency closed in the final completeness tranche

At Prompt 1 time, resource-building construction for lumber camp, mill, mining camp and farm was deliberately deferred because the bot did not yet expose those providers through its executable policy path. The final completeness tranche now uses the existing native BuildingId catalog and construction lifecycle directly. Dock remains owned by the existing Islands/water policy.

The bot now emits real Lumber Camp, Mining Camp, Mill and Farm demands, uses the supported `dropsite-min-distance` observation together with existing villager/provider facts, and applies existing Strategic Number placement controls. This closes the old Prompt 1 execution dependency without changing generic compiler semantics.

### Acceptance

- profile contains the four Dark villager branches;
- profile contains `dark-loom`;
- compiled artifact contains `(research loom)`;
- deterministic compilation remains identical;
- no existing Castle/Imperial behavior is removed;
- native lint remains zero.

---

## **2/7 — Prompt 2: Feudal Economic and Military Engine — IMPLEMENTED / CI PENDING**

### Objective

Make Feudal the Byzantine information-to-action age.

### Implemented in this prompt

- Added a persistent Feudal Barracks provider demand using the existing one-sided building-demand pattern.
- Bound Feudal Spearman and Skirmisher responses to their actual Feudal production providers.
- Kept the cheap-counter floors at four units and preserved the existing typed counter-package arbitration.
- Shifted the existing COUNTER_FEUDAL economy controller allocation to 42 food / 40 wood / 18 gold / 8 builders.
- Sequenced Double-Bit Axe and Horse Collar behind Wheelbarrow.
- Made Fletching conditional on the actual Feudal Archery Range and observed ranged pressure.
- Made the Castle transition wait for at least 24 villagers and clearance of the existing five-militia pressure observation.
- No generic compiler semantics or new bot-side scheduler were introduced.


### Bot policy

- Construct the Feudal barracks path needed by Spearman demands.
- Preserve the existing Archery Range conditional style.
- Add explicit Feudal production packages for:
  - mounted pressure → Spearman;
  - ranged pressure → Skirmisher;
  - mixed pressure → bounded cheap-counter package;
  - no pressure → eco/Castle conversion.
- Add Feudal blacksmith research sequencing around the active package.
- Make 30 villagers a soft production target rather than the only Feudal economic definition.
- Keep Castle gold reserve alive while funding active Feudal defense.
- Use existing `opening-plan` values and current threat observations rather than creating another selector.

### Resource doctrine

Food funds villagers and cheap counter units.
Wood funds farms, houses, barracks/range and production continuity.
Gold funds the Castle trajectory and selected ranged/technology packages.
Stone remains zero unless a specific defensive or Castle objective calls for it.

### Acceptance

Every Feudal military demand must have a verified provider, a counter-condition, a release witness, and a recoverable economic path.

Prompt 2 also requires focused tests for the Barracks provider, counter-package continuity, Feudal economy allocation, research sequencing, and the Castle-pressure gate.

---

## **3/7 — Prompt 3: Castle Conversion Engine — IMPLEMENTED / CI PENDING**

### Objective

Replace the current blunt Castle package with explicit Byzantine conversion branches.

### Implemented in this prompt

- Restricted the existing second Town Center demand to the Arena Fast Castle branch: Arena map, opening plan 3, at least 35 villagers, and no active five-militia pressure.
- Made the default non-Arena Castle path effectively 1TC by withholding the second-TC demand rather than inventing a separate scheduler.
- Added a bot-local Logistica research demand using the existing StrategicDemandSpec/research lifecycle style and the verified native `ri-logistica` alias.
- Made the Cataphract floor depend on either the Arena Fast Castle branch or verified infantry pressure, and require completed Logistica before Castle Cataphract production.
- Made the Monk floor conditional on an actual Monastery and the Arena Fast Castle branch.
- Expanded Castle siege capability to activate for verified enemy siege or sustained ranged pressure, while retaining the existing bounded Mangonel production floor.
- Sequenced Castle economy research with native research-status guards: Wheelbarrow -> Hand Cart, Double-Bit Axe -> Bow Saw, Gold Mining -> Gold Shaft Mining, Horse Collar -> Heavy Plow, and Fletching -> Bodkin Arrow with an Archery Range present.
- Shifted Castle conversion economy to 45 food / 30 wood / 25 gold / 7 builders.
- Raised the Imperial conversion readiness gate to at least 40 villagers while preserving the existing persistent Imperial demand.
- No generic compiler changes and no new Castle scheduler.


### Branches

- Open-map defensive Castle.
- Arena 2TC boom.
- 1TC Knight/Camel pressure.
- Monk/relic control.
- Siege pressure.
- Cataphract conversion only when Castle economics support it.
- Fast Imperial preparation when the opponent permits it.

### Required repairs

- Make second TC conditional on map, pressure and economic state.
- Remove universal simultaneous Knight + Cataphract floors where they compete for the same gold.
- Preserve cheap Spear/Skirmisher counter production.
- Add Castle economic upgrades in the existing research-demand style.
- Introduce package-aware Cataphract production so Castle Cataphracts are not confused with the Imperial Logistica power spike.

### Acceptance

The compiled bot must exhibit one coherent Castle macro posture at a time rather than paying for every possible Castle option simultaneously.

---

## **4/7 — Prompt 4: Imperial Win-Condition Engine — IMPLEMENTED / CI PENDING**

### Objective

Give Byzantines an actual endgame plan.

### Implemented in this prompt

- Added Imperial Halberdier, Elite Skirmisher, Heavy Camel, Hand Cannoneer, and Elite Cataphract production branches using the existing staged-training demand pattern.
- Halberdier, Elite Skirmisher, and Heavy Camel are triggered by verified sustained mounted/ranged pressure rather than standing mass production.
- Hand Cannoneer is triggered by sustained infantry pressure and requires Chemistry completion.
- Elite Cataphract conversion requires both Logistica and Elite Cataphract research, with Arena or infantry pressure as the strategic trigger.
- Added targeted Imperial research demands for Halberdier, Elite Skirmisher, Heavy Camel, and Elite Cataphract.
- Reused the existing stock Chemistry and Conscription demands, adding bot-local execution guards instead of duplicate research identities.
- Preserved the existing Imperial economy allocation at 40 food / 25 wood / 35 gold / 7 builders.
- The Castle Logistica demand is correctly Imperial-gated; Castle Cataphract production remains available before Logistica, while the Imperial upgrade branch is gated on both technologies.
- No new scheduler, compiler primitive, or parallel package controller was introduced.


### Primary conversion packages

**Trash War**
- Halberdier
- Elite Skirmisher
- Heavy Camel where appropriate
- sustained food/wood production
- reduced dependence on gold

**Cataphract/Trash**
- Elite Cataphract
- Logistica
- Halberdier/Elite Skirmisher support
- gold protected until the conversion is established

**Gunpowder/Siege**
- Hand Cannoneer
- Bombard Cannon
- Chemistry
- Siege support
- defensive buildings as anchors

**Water**
- Fire Ship/Galleon/advanced naval conversion where map state warrants it

### Acceptance

Imperial entry must select a resource and production direction instead of merely unlocking more unit types.

Prompt 4 also requires focused tests for trash conversion, gunpowder conversion, Elite Cataphract conversion, research gating, and generated artifact actions.

---

## **5/7 — Prompt 5: Resource Demand Controller — IMPLEMENTED / CI PENDING**

### Objective

Turn the existing static economy percentages into demand-responsive allocation without inventing a scheduler.

### Implemented in this prompt

- Locked the seven existing economy postures to explicit Byzantine resource priorities:
  - BASE 50/30/20/5;
  - COUNTER_FEUDAL 42/40/18/8;
  - FAST_CASTLE 55/15/30/3;
  - WATER_ECONOMY 40/40/20/5;
  - WATER_CONTROL 38/42/20/8;
  - CASTLE_CONVERSION 45/30/25/7;
  - IMPERIAL_CONVERSION 40/25/35/7.
- Kept the existing economy controller as the only worker-allocation controller. No second economic scheduler was introduced.
- Made discretionary economic research explicitly subordinate to economic readiness:
  - Hand Cart requires 30 villagers;
  - Bow Saw requires 35 villagers;
  - Two-Man Saw requires 50 villagers and Imperial Age;
  - Conscription requires 45 villagers;
  - Chemistry remains threat-triggered by sustained infantry pressure.
- Preserved the existing age-transition, Town Center, and premium conversion resource-protection contracts.
- Kept training demands on the existing production arbitration channel so resource pressure does not create a second production ownership model.
- Imperial research demands with unresolved checked-in research costs no longer invent a price. They use native escrow feasibility and remain open on unverified cost data.
- No generic compiler semantics were changed.


### Rule

Age percentages remain the baseline. Explicit strategic demand can temporarily dominate them.

### Demand priorities

1. age-up;
2. villagers;
3. houses;
4. active production buildings;
5. active military package;
6. farms/economic infrastructure;
7. second TC/Castle/University/Monastery;
8. upgrade package;
9. late-game conversion.

### Resource rules

**Food:** villagers, farms, age-ups, cheap trash.
**Wood:** houses, farms, production, blacksmith/range/barracks, water.
**Gold:** Castle/Imperial, technology, premium military.
**Stone:** event resource for Castle/fortification commitments, otherwise near-zero.

### Acceptance

The same bot demand must not simultaneously claim mutually incompatible resource priorities without explicit arbitration.

Prompt 5 also requires focused tests for all seven economy modes, research priority gating, deterministic compilation, and preservation of existing production arbitration.

---

## **6/7 — Prompt 6: Water, Transport, and Positional Completion — IMPLEMENTED / CI PENDING**

### Objective

Finish the water branch without pretending that ship production alone is a water strategy.

### Implemented in this prompt

- Added the missing Byzantine first-Dock capability demand for Islands maps.
- Reused the existing typed water execution plan for fishing, transport, naval defense, naval control, and transport-loss recovery.
- Kept the stock water continuity demand bounded at two ships and added the separate Dark-Age Islands opening tranche to reach four Fishing Ships after the first Dock.
- Kept transport at one reusable ship and allowed the existing capability-loss path to return it to the execution phase after loss.
- Kept defensive Fire Galley production bounded to observed enemy naval pressure.
- Kept Castle Galley control bounded to observed enemy naval pressure and Castle availability.
- Did not add a second Dock demand.
- Did not modify the generic water compiler or create a second water scheduler.
- Added bot-focused artifact coverage for Dock, Fishing Ship, Transport Ship, Fire Galley, and Galley actions.


### Required behavior

- dock construction where the verified native surface permits it;
- fishing economy continuity;
- transport production;
- transport load/destination/landing lifecycle where already supported;
- escort/defense response;
- naval production packages;
- recovery after transport/naval loss.

The existing water and transport compiler machinery is reused. No parallel water scheduler is permitted.

Prompt 6 also requires focused tests for first-Dock admission, fishing continuity, transport recovery, naval-defense pressure, and deterministic water artifact emission.

---

## **7/7 — Prompt 7: Game-Proof, Tuning, and Release — ACTIVE**

### Objective

Convert the strategic profile into a measured playable bot.

### Implemented in this prompt

- Added a dedicated Byzantine Core v1 game-proof and release matrix covering:
  - standard open land;
  - mounted, ranged, infantry, and siege pressure;
  - Arena conversion;
  - 1TC open Castle defense;
  - Fast Imperial;
  - Imperial trash war;
  - gunpowder;
  - Cataphract conversion;
  - Islands water;
  - transport loss/recovery;
  - resource starvation;
  - prolonged late game.
- Defined artifact-level acceptance signals for each behavior rather than treating mere unit availability as proof of a working strategy.
- Made the existing deterministic build manifest the release identity surface.
- Kept native parser zero-findings, cross-platform determinism, full compiler regression, and focused Byzantine tests as the hard release gate.
- Recorded unresolved runtime questions explicitly instead of pretending the static compiler is an RTS simulator.


### Required proof set

- standard open land;
- early scout/cavalry pressure;
- archer pressure;
- infantry pressure;
- fast Castle opponent;
- Arena;
- water/islands;
- Castle siege pressure;
- Imperial trash war;
- Cataphract conversion;
- gunpowder/siege;
- transport loss/recovery;
- resource starvation;
- prolonged late game.

### Acceptance gate

- deterministic artifact;
- native zero findings;
- full compiler test suite;
- bot-focused tests;
- artifact hash recorded;
- DE gameplay matrix recorded;
- no unsupported native primitive silently introduced;
- no change justified only by “it looks like a bot.”

The release matrix is recorded in `docs/release/2026-10-02-byzantine-core-v1-gameproof-matrix.md`.

---

# Cross-prompt style contract

Every prompt must preserve these existing conventions:

- extend `_bot_demands()` or adjacent bot-local helpers before introducing new architecture;
- use `_aged_building_demand`, `_staged_building`, `_staged_training`, `_research_demand`, or the existing strategy helpers where applicable;
- use literal native `.per` fact/action strings exactly as the current bot does;
- attach conditions through `execution.requirements`, not ad-hoc runtime logic;
- use existing `StrategyPosture` and `StrategicPriority`;
- use existing observations and opening state before adding new observations;
- keep evidence/reason labels explicit and human-readable;
- return immutable tuples;
- compile twice in tests and compare artifacts;
- test the behavior, not just object existence;
- do not alter generic compiler semantics to make an individual Byzantine policy easier;
- do not build a second compiler inside the bot profile.

The goal is a Byzantine bot that looks like it was written by the same author as the current bot, because it effectively was. Human beings have enough trouble maintaining software when every function decides to develop a personality.
