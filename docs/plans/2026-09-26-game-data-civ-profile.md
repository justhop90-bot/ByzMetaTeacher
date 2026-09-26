# GameData and CivProfile Implementation Record

**Status:** Implemented foundation on main; full contemporary data ingestion remains separate.

## Completed checklist

- [x] Typed patch identity and evidence provenance.
- [x] Typed costs, selectors, prerequisites, providers, units, buildings, technologies, and unit lines.
- [x] GameData structural validation.
- [x] Civilization modifiers and interactions.
- [x] Deterministic EffectiveCivData resolution and fingerprinting.
- [x] Byzantine Update 185872 factual subset.
- [x] Native metadata boundary and explicit local-alias semantics.
- [x] CI verification: 173 compiler tests, native generated fixture clean.

## Intentionally incomplete

- [ ] Full 145-node Byzantine manifest ingestion.
- [ ] Complete verified research cost/time/effect ingestion.
- [ ] Independent verification of current Varangian Guard unit numeric IDs.
- [ ] Full AIRef native command/parameter metadata ingestion.
- [ ] Historical multi-patch replay fixtures.

## Community cross-reference

AIRef establishes the native parameter/type boundary and finite native storage namespaces.

The Duke and Niek/Atilla provide community-native evidence for explicit age, resource, provider, production, and research relationships.

AgeScript and AgeOfPython provide typed compiler/lowering precedent without requiring Basilisk to become a general-purpose language.

## Architectural conclusion

The compiler now has a credible factual boundary:

    Native metadata -> GameData + CivProfile -> EffectiveCivData -> StrategyProfile -> SemanticDemand

The next layer should therefore be strategy-domain semantics, not another generic execution primitive.

## Forensic repair tranche (2026-09-26)

The original implementation record treated the GameData/CivProfile layer as structurally finished too early. Cross-reference against the checked-in AIRef inventory, the repository Byzantine manifest, current Byzantine technology-tree references, current 185872 patch notes, and community .per practice found that the layer was semantically under-specified.

### Verified corrections

- [x] Byzantine Skirmisher/Elite Skirmisher -25% cost is now represented as a separate `skirmisher-line` civilization modifier.
- [x] Unit upgrade edges now carry their native research trigger as `UpgradeRelation(previous,current,research)`.
- [x] Upgrade relations are validated against both unit bidirectional links and the research technology's `upgrades` set.
- [x] Production and research provider graphs are validated in both directions.
- [x] `Prerequisite.kind` and `TechEffect.kind` are typed enums rather than free-form strings.
- [x] `N_OF` prerequisite semantics were added for age advancement.
- [x] Feudal advancement requires two Dark Age buildings from the documented set.
- [x] Castle advancement requires two Feudal buildings from the documented set.
- [x] Imperial advancement models the documented Castle-or-two-Castle-Age-buildings exception.
- [x] Unsupported fixed age-up research durations were removed from the factual snapshot.
- [x] Varangian Guard and Elite Varangian Guard now carry typed Shock Infantry/passive-effect facts in the factual subset.
- [x] Civilization-scoped GameData is explicitly marked as such; the current Byzantine snapshot can no longer silently present itself as universal GameData.
- [x] Factual coverage is explicit and currently `FACTUAL_SUBSET`.
- [x] StrategyProfile capability intents are gated against verified factual coverage rather than interpreting omission from a partial snapshot as civilization unavailability.
- [x] Snapshot fingerprints now include coverage, scope, and upgrade relations.
- [x] Rational values are canonicalized before fingerprinting.
- [x] Patch IDs use semantic numeric ordering for update/build components.
- [x] PatchChange now exposes target-patch and previous-fingerprint verification hooks.
- [x] Controller evidence for current Varangian IDs is explicitly marked `cross-check`, not primary engine authority.
- [x] Generic tech IDs that the current Byzantine tree marks unavailable were removed from the Byzantine provider graph: Bloodlines (435), Parthian Tactics (436), and Heavy Scorpion (239).

### Cross-reference findings that changed the repair

The current Byzantine technology-tree evidence reports 57 units, 75 technologies, and 29 buildings, while the compiler remains intentionally partial. It also marks Byzantines as lacking Parthian Tactics, Bloodlines, Blast Furnace, Siege Onager, and Heavy Scorpion. Generic AIRef availability is therefore not equivalent to Byzantine availability.

The repository manifest supplies direct native relationships such as Crossbowman -> 100, Elite Skirmisher -> 98, Pikeman -> 197, Halberdier -> 429, Elite Cataphract -> 361, and Fire Ship -> Warships / Fast Fire Ship -> 246. Those relationships are now first-class compiler data rather than implicit unit links.

The official 185872 update establishes the current Byzantine Varangian access, Shock Infantry classification, combat-triggered gold generation, Gambesons interaction, Cataphract bonus-damage changes, and Logistica target expansion.

Community .per projects reinforce the useful boundary: game facts, research/provider relationships, persistent state, and execution rules are represented explicitly, while the engine remains the final execution authority. Basilisk therefore consumes a verified factual subset instead of trying to manufacture a complete simulator.

### Intentionally still open

- [ ] Extract a genuinely universal GameData baseline separate from civilization overlays. The current snapshot is explicitly marked civilization-scoped as an interim safety boundary.
- [ ] Implement replayable typed patch overlays. `PatchChange` now has CAS/target hooks, but current 185872 data remains a resolved snapshot rather than a baseline-plus-overlay reconstruction.
- [ ] Complete the Byzantine 145-node manifest/technology graph to current 185872 coverage.
- [ ] Populate missing verified research costs, research times, train times, and factual effect fields.
- [ ] Add explicit known-unavailable entity sets so a future universal snapshot can distinguish unavailable from not-yet-ingested.
- [ ] Complete field-level provenance rather than entity-level fallback provenance.
- [ ] Add historical replay fixtures across multiple DE revisions.
- [ ] Add cross-civilization datasets before using the factual layer as a broad strategy authority.

### Acceptance gate

StrategyProfile may consume a factual entity only when that entity is covered by the resolved snapshot. A partial snapshot is valid compiler input for a proven subset; it is not permission to infer that every omitted entity is unavailable.

The next data milestone is therefore not "pretend COMPLETE." It is: build the universal baseline, add civ availability overlays, and make patch replay real.
