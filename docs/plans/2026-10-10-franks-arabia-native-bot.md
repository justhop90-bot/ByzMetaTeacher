# Franks Arabia Native Bot — Implementation and Acceptance Record

Date: 2026-10-10

Status: implementation candidate; native parser and DE runtime acceptance are pending.

## Product boundary

The candidate is a standalone native `.per` AI script at the repository root, with a deterministic packaging script and manifest. It does not import or modify the Byzantine profile or checked-in `Byzantine.per`.

This is a deliberate scope decision. The current compiler factual snapshot is Byzantine-scoped, and the generic GameData layer does not yet provide a verified all-civilization baseline. Re-labeling that Byzantine snapshot as Franks would make unit availability and bonuses untrustworthy. This first Franks runtime slice therefore uses explicit native AI aliases and locally defined IDs only where current-patch data has been verified. A typed Franks `CivProfile` can follow once the compiler has an honest shared baseline or a separately verified Franks factual snapshot.

## Civilization and patch evidence

Target patch: AoE2DE update 185872, released 2026-09-22.

- Official patch notes: https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/
- Pinned Franks tech-tree record: https://github.com/SiegeEngineers/aoe2techtree/blob/3bb43b1439eef88dfe7fe892d7f7dc41ac9dd76f/data/trees/FRANKS.json
- Pinned source blob SHA recorded by the fetch: `b957d594e50d1a79b28b48d5123322e4064e0ca7`

Current-patch facts used by this bot:
- Mounted Crossbowman unit ID 2700.
- Heavy Mounted Crossbowman unit ID 2701.
- Throwing Axeman unit ID 281; Elite Throwing Axeman unit ID 531.
- Cranequins technology ID 1452.
- Ordonnance Companies technology ID 1496, Castle Age, reducing Mounted Crossbowman gold cost.
- Bearded Axe and the Cavalry Archer line are not part of this build-185872 strategy.

These identifiers are civ-tree facts, not claims that every native AI alias is recognized by the parser. The native parser acceptance job is the gate for emitted syntax/commands; actual in-game affordability, training, and behavior remain DE runtime questions.

## Full-match strategy contract

| Phase | Strategic intent | Required behaviors |
|---|---|---|
| Dark Age | Establish an efficient food/wood economy | Continuous villager production, population capacity, Mill, lumber camp, no premature stone mining |
| Feudal Age | Reach Castle Age while applying bounded pressure | Stable, up to four Scouts, Blacksmith and Market, refresh lumber/gold dropsites from resource-distance observations |
| Castle Age | Win map control with durable cavalry | Knight production with queue-aware targets, cavalry armor/attack technologies, extra Stables, second TC only after economic thresholds, Castle for Frankish unique-unit and technology access |
| Counter response | Keep the main plan, answer proven enemy compositions | Finite Spearman-line response to enemy cavalry, Throwing Axemen against infantry, Mounted Crossbowmen after Castle Age, bounded Skirmisher and Monk support |
| Imperial Age | Turn army advantage into a base kill | Cavalier/Paladin, Chivalry, Conscription, siege research, Trebuchets and Siege Rams, scalable production and repeated attack cycles |
| Recovery | Prevent a single shortfall from freezing the strategy | Shift gather priorities under food/wood/gold pressure; rebuild missing camps when local resource coverage is inadequate; keep Town Center and military production alive where feasible |

The farm policy does not issue standalone Horse Collar or Heavy Plow research requests because Frankish Mill technologies are free in the target patch. The bot should not spend effort on obsolete Bearded Axe or Cavalry Archer rules.

## Implementation map

- `Franks.per`: canonical native rule source. Source order is intentional; age-up/production ownership and target updates are ordered.
- `tools/build_franks_bot.py`: byte-preserving package to `dist/franks/Franks.per` plus a manifest containing hashes, rule/line counts, target patch, parser pin, and honest runtime status.
- `LearnerAI/Compiler/tests/test_franks_bot_build.py`: package determinism and strategic-contract tests.
- `.github/workflows/compiler-tests.yml`: runs packaging, focused tests, and native zero-findings checks against both the checked-in and packaged bot.

## Acceptance gates

1. Focused build/contract tests pass.
2. Pinned `aoe2-ai-parser` reports zero native findings for both `Franks.per` and `dist/franks/Franks.per`.
3. Full compiler suite and cross-platform determinism remain green.
4. The artifact hash in the generated manifest equals the canonical source hash.
5. A real DE Arabia matrix is run separately; compiler/parse acceptance alone is not runtime acceptance.

## Runtime matrix and diagnosis capture

Run Franks on Arabia, 1v1, standard resources, no treaty, against Moderate first, then Standard and Hard after the basic loop behaves correctly. Record timestamps/observations at 10, 20, 30, and 40 minutes for:
- villager count, idle Town Center, food/wood/gold/stone stock;
- first lumber camp, first Mill, next resource camp at a remote wood/gold/stone patch;
- Feudal/Castle/Imperial completion;
- Scouts, first Knight, cavalry upgrades, first Castle, Throwing Axemen, Mounted Crossbowmen and Ordonnance Companies;
- unit queue vs fielded-unit counts, siege production, attack launches, enemy buildings damaged/destroyed;
- stalls: which demand remains active, which predicate stays false, and whether required building/queue/resource evidence exists.

Do not claim win-rate, build-order timing, or runtime liveness until matches have actually been run. The accepted result for this PR is a deterministic, native-parseable test artifact ready for those runs.
