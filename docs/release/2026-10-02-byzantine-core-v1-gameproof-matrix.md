# Byzantine Core v1 — Game-Proof and Release Matrix

**Branch:** `bot/byzantine-core-v1`  
**Profile:** Byzantine Core v1  
**Patch target:** Update 185872  
**Scope:** 1v1 Byzantine community-derived bot with standard land, Arena, Islands, and water/transport support.

## Release contract

The bot is released only when the generated `dist/byzantine/Byzantine.per` is deterministic and passes the existing native zero-findings parser gate. The release manifest records the artifact SHA-256, effective-civ fingerprint, compiler revision, parser revision, demand count, and Strategic Number mode count.

Gameplay acceptance is behavioral. A scenario passes when the compiled policy exposes the expected demand, native condition, action, witness, and recovery path. No scenario is accepted merely because a unit or technology appears somewhere in the artifact.

## Scenario matrix

| Scenario | Required policy evidence | Release signal |
|---|---|---|
| Standard open land | Dark villager ladder, Loom, Feudal counters, Castle transition | staged economy + conditional counter branches |
| Early mounted pressure | Spearman package, production provider, mounted-pressure guard | Spear response without universal Feudal mass |
| Early ranged pressure | Archery Range, Skirmisher package, Fletching/Bodkin sequencing | bounded ranged counter |
| Heavy infantry pressure | Varangian/Cataphract response, later Hand Cannoneer branch | infantry-specific conversion |
| Arena | 2TC demand, Monastery/Monk branch, Cataphract/Logistica path | Arena-only expansion and premium branch |
| Open Castle defense | 1TC path, siege response, reactive premium units | no unconditional second TC |
| Fast Imperial | 40-villager Imperial conversion, Imperial economy | age transition followed by production conversion |
| Imperial mounted war | Halberdier, Heavy Camel and relevant research | sustained mounted-threat package |
| Imperial ranged war | Elite Skirmisher and research | sustained ranged-threat package |
| Imperial infantry war | Chemistry + Hand Cannoneer | sustained infantry conversion |
| Cataphract conversion | Logistica + Elite Cataphract sequencing | premium cavalry conversion |
| Islands | Dock, fishing, transport, naval-defense/control demands | complete water branch |
| Transport loss | existing water recovery state + reusable transport demand | capability loss reopens transport need |
| Resource starvation | preserved age/production intent with escrow-aware feasibility | temporary shortage delays rather than kills demand |
| Prolonged late game | villager backbone, Conscription, active composition demand | continuing production rather than one-time unlocks |

## Native and deterministic gate

The release build must satisfy all of the following:

- generic compiler fixture reproducibility;
- Byzantine artifact byte determinism across two builds;
- native zero-findings for `dist/byzantine/Byzantine.per`;
- cross-platform native-support snapshot agreement;
- full compiler regression suite;
- Byzantine bot-focused tests;
- no unsupported native primitive introduced by bot policy.

## Known open runtime boundaries

The compiler does not simulate economy income, queue-exit timing, exact same-pass native visibility, or battlefield success. Those remain runtime/open questions. The bot therefore uses observable engine facts for admission and completion and never promotes timers, retries, or resource balance into proof of world-state success.

## Release artifacts

Expected output:

```text
dist/byzantine/Byzantine.per
dist/byzantine/manifest.json
```

The manifest is authoritative for the build identity. The generated `.per` remains the deployable artifact.
