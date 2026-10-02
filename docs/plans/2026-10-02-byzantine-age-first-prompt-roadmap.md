# Byzantine Core v1 — Age-First Bot Roadmap

**Artifact:** Byzantine Core v1
**Branch:** `bot/byzantine-core-v1`
**Method:** community-derived behavior expressed through the existing Byzantine StrategyProfile and existing compiler/native vocabulary.
**Style rule:** every addition must read like the existing `LearnerAI/Compiler/bots/byzantine.py`: small pure helpers, `StrategicDemandSpec` construction, `replace(...)` for execution guards, explicit native fact strings, existing `StrategyPosture`/`StrategicPriority` values, deterministic tuple ordering, focused unit tests, no second scheduler, no new bot-side language.

## **1/7 — Prompt 1: Dark Age Foundation — ACTIVE**

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

### What remains deliberately outside Prompt 1

Resource-building construction for lumber camp, mill, mining camp, farm and dock remains constrained by the current verified native BuildingId surface. Do not smuggle a compiler/catalog repair into the bot prompt. The policy can be added once the already-existing native vocabulary is usable; the bot roadmap records that as an execution dependency rather than falsifying support.

### Acceptance

- profile contains the four Dark villager branches;
- profile contains `dark-loom`;
- compiled artifact contains `(research loom)`;
- deterministic compilation remains identical;
- no existing Castle/Imperial behavior is removed;
- native lint remains zero.

---

## **2/7 — Prompt 2: Feudal Economic and Military Engine — QUEUED**

### Objective

Make Feudal the Byzantine information-to-action age.

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

---

## **3/7 — Prompt 3: Castle Conversion Engine — QUEUED**

### Objective

Replace the current blunt Castle package with explicit Byzantine conversion branches.

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

## **4/7 — Prompt 4: Imperial Win-Condition Engine — QUEUED**

### Objective

Give Byzantines an actual endgame plan.

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

---

## **5/7 — Prompt 5: Resource Demand Controller — QUEUED**

### Objective

Turn the existing static economy percentages into demand-responsive allocation without inventing a scheduler.

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

---

## **6/7 — Prompt 6: Water, Transport, and Positional Completion — QUEUED**

### Objective

Finish the water branch without pretending that ship production alone is a water strategy.

### Required behavior

- dock construction where the verified native surface permits it;
- fishing economy continuity;
- transport production;
- transport load/destination/landing lifecycle where already supported;
- escort/defense response;
- naval production packages;
- recovery after transport/naval loss.

The existing water and transport compiler machinery is reused. No parallel water scheduler is permitted.

---

## **7/7 — Prompt 7: Game-Proof, Tuning, and Release — QUEUED**

### Objective

Convert the strategic profile into a measured playable bot.

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
