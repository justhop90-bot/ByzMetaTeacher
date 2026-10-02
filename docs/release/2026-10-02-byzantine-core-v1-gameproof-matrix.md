# Byzantine Core v1 — Game-Proof and Release Matrix

**Branch:** `bot/byzantine-core-v1-final`  
**Profile:** Byzantine Core v1  
**Patch target:** Update 185872  
**Scope:** 1v1 Byzantine community-derived bot with standard land, Arena, Islands, and water/transport support.

## Release contract

The bot is released only when the generated `dist/byzantine/Byzantine.per` is deterministic and passes the existing native zero-findings parser gate. The release manifest records the artifact SHA-256, effective-civ fingerprint, compiler revision, parser revision, demand count, and Strategic Number mode count.

Gameplay acceptance is behavioral. A scenario passes when the compiled policy exposes the expected demand, native condition, action, witness, and recovery path. No scenario is accepted merely because a unit or technology appears somewhere in the artifact.

## Verified artifact run — 2026-10-02

The deployable artifact was built and fully validated on GitHub Actions PR run #3300 (36978087631) from the final Byzantine Core v1 economy-completeness head. The PR is #285; the final code remains on `bot/byzantine-core-v1-final`.

artifact: Byzantine.per
artifact_sha256: 1e7b29160801a92baed79307c311c9bd7e3f0d67b7227a40649f69ecb73f1d96
artifact_bytes: 304874
artifact_lines: 8655
demand_count: 86
strategic_number_mode_count: 22
compiler_revision: 4c6eb8df2023f649be36b6a26cea8125ad1e61e6
native_parser_revision: 3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba
effective_snapshot_fingerprint: 6f69321936d2b4ddc61384f3a71e647f4c188d0f125483d6231b8e0b472e2537

Run #3300 passed the full compiler regression suite (1,493 tests), Byzantine native zero-findings (0 findings), all focused native fixtures, all nine cross-platform native-support determinism jobs, the final cross-platform snapshot comparison, and the compiler verification gate.

The final completeness tranche closes the previously deferred basic economic execution seam: Lumber Camp, Mining Camp, Mill, Farm and Market demands are now emitted through the existing construction lifecycle, using verified native BuildingIds and supported observations. It also adds the minimal Feudal Spearman floor and explicit camp/mill placement Strategic Number policy.

The final artifact contains no `resource-found` executable dependency because the checked-in compiler correctly rejects that command as known-but-unadapted. The bot therefore uses supported `dropsite-min-distance` and existing villager/provider facts instead of smuggling unsupported native semantics into the release.

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
