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