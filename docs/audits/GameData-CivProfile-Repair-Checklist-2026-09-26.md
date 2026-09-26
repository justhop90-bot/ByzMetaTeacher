# Basilisk GameData / CivProfile Repair Checklist

Audit baseline: `1335ce273d4674cc5cee962ea97afbef84e8cd14`  
Current repair head: `581dc272c2eb5da5210ee1a8c7de5ea2eccdd252`

## Acceptance boundary

The GameData layer is allowed to expose a verified factual subset. It is not allowed to turn omitted data into a false civilization-unavailable conclusion, and it is not allowed to infer executable upgrade capability from an unresearched unit edge.

Current snapshot status:

```
scope    = CIVILIZATION / Byzantines
coverage = FACTUAL_SUBSET
runtime  = final feasibility authority
```

## P0 repair status

### Factual graph

- [x] Typed `PrerequisiteKind`.
- [x] Typed `TechEffectKind`.
- [x] Explicit `UpgradeRelation(previous,current,research)`.
- [x] Upgrade relations cross-validated against unit links and research definitions.
- [x] Bidirectional production-provider validation.
- [x] Bidirectional research-provider validation.
- [x] Snapshot fingerprint includes upgrade graph.
- [x] Rational values normalized before fingerprinting.

### Byzantine modifiers

- [x] Spearman/Pikeman/Halberdier -25%.
- [x] Skirmisher/Elite Skirmisher -25%.
- [x] Camel/Heavy Camel -25%.
- [x] Imperial Age 667F/536G override.
- [x] Building HP scaling.
- [x] Free Town Watch / Town Patrol.
- [x] Fire Ship/Dromon current attack-speed modifier.
- [x] Team Monk healing modifier.
- [x] Current Cataphract 13/18 infantry bonus.
- [x] Current Logistica Cataphract + Varangian target scope.

### Age advancement

- [x] Feudal -> Castle -> Imperial predecessor chain.
- [x] Native age-advance IDs.
- [x] Feudal two-of-five Dark Age building prerequisite.
- [x] Castle two-of-four Feudal building prerequisite.
- [x] Imperial Castle-or-two-Castle-Age-building exception.
- [x] Removed unsupported fixed age-up research duration from factual strategy data.

### Varangian Guard

- [x] Varangian / Elite Varangian IDs represented.
- [x] Shock Infantry engine class.
- [x] Gold generation while fighting represented as a typed factual effect.
- [x] Gambesons interaction represented.
- [x] Logistica target expansion represented.
- [x] Controller evidence downgraded to compatibility cross-check.

### Coverage and StrategyProfile safety

- [x] Explicit `FactualCoverage`.
- [x] Explicit `GameDataScope`.
- [x] Effective snapshot exposes scope and coverage.
- [x] StrategyProfile capability intents require factual coverage.
- [x] Partial snapshots no longer imply omitted entities are unavailable.
- [x] Generic AIRef technology IDs are not automatically promoted into Byzantine availability.

## P1 repair status

- [x] Typed unit effects introduced.
- [x] Engine-unit classes separated from generic strategy tags.
- [x] Snapshot scope is validated against the owning civilization.
- [x] Patch IDs use semantic numeric ordering.
- [x] PatchChange has target-patch and previous-fingerprint verification hooks.
- [x] Entity-level provenance fallback is present for the current subset.

## Still open, deliberately

- [ ] Extract a universal GameData baseline independent of any civilization.
- [ ] Implement civ availability as a real overlay over universal GameData.
- [ ] Complete the current Byzantine 57-unit / 75-technology / 29-building factual graph.
- [ ] Populate verified research costs, research times, train times, and effect payloads instead of unresolved values.
- [ ] Add explicit known-unavailable entities to the universal snapshot.
- [ ] Implement replayable typed patch overlays; current 185872 remains a resolved snapshot, not baseline-plus-overlay reconstruction.
- [ ] Populate real previous/replacement fingerprints and enforce CAS during overlay application.
- [ ] Complete field-level provenance for every materially consumed factual property.
- [ ] Add cross-civilization factual fixtures before treating the layer as a general strategy authority.

## Red-team cases now covered

- [x] Castle Age + Barracks no longer implies Pikeman is researched.
- [x] Castle Age + Range no longer implies Elite Skirmisher is researched.
- [x] Imperial Age + Castle no longer implies Elite Cataphract is researched.
- [x] Resources + Town Center no longer imply an executable age transition without the building prerequisite graph.
- [x] Generic Bloodlines, Parthian Tactics, and Heavy Scorpion entries are not promoted into the Byzantine provider graph.
- [x] Missing Skirmisher discount cannot silently survive the factual-cost regression suite.
- [x] A strategy capability referencing an uncovered entity fails closed as insufficient factual coverage rather than being interpreted as civilization-unavailable.

## Community / engine cross-reference

The checked-in community bot sources use native feasibility such as `can-research-with-escrow` before issuing research, and common AI repositories keep the actual .per rules separate from launcher .ai files. Tech-tree data tooling likewise models universal entities and civilization-specific availability as different concerns.

Primary current references used for this repair:

- Official DE age-advancement requirements: https://www.ageofempires.com/learn-to-play/advancing-aoe2/
- Official DE Update 185872: https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- Current Byzantine technology tree: https://www.aoe2insights.com/civ/byzantines/techtree/
- Current Byzantine bonus reference: https://aoe2.ai/civ/byzantines/
- Community AI scripts: https://github.com/niektb/AI
- Community builder-upgrade patterns: https://github.com/JackkelDragon/AoE2DE_AIBuilder/blob/master/AI%20Libraries/builder%20upgrades.per

## Definition of done for StrategyProfile-wide authority

The compiler may consume this layer as a verified subset now.

It may not call the layer authoritative for the whole civilization until:

```
universal GameData
+
civ availability overlay
+
complete current coverage
+
verified costs/times/effects
+
real patch replay
+
field-level provenance
```

are all present.

The engine-native `can-*` boundary remains the final feasibility witness. Static GameData establishes what the compiler knows to be legal and how entities relate; it does not replace runtime truth.
