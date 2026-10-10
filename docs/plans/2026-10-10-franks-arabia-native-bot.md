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

The bot explicitly researches Horse Collar in Feudal, Heavy Plow in Castle, and Crop Rotation in Imperial through the native research lifecycle; all three Frankish Mill technologies are free in the target patch. It avoids wasting effort on obsolete Bearded Axe or Cavalry Archer rules.

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


## Runtime repair tranche 1 — 2026-10-10

This tranche keeps the existing Scouts → Knights → conditional counters → cavalry/siege plan, but repairs control paths that could prevent the planned strategy from reaching the game.

### Changes

- Removed the distance-only failure condition from the first Lumber Camp and first Mill. If the map exposes no forage, a Dark Age Mining Camp on a found gold resource is the fallback second building.
- Delayed Loom from 7 to 18 villagers and only allows it when Feudal Age is not currently researchable, protecting the opening food/TC queue.
- Removed the Market as a hard Castle Age prerequisite. Native `can-research-with-escrow` remains the feasibility authority.
- Added University construction when no Castle has been completed and the Siege Workshop exists, making the University + Workshop Imperial path available without relying on enemy elephant units.
- Held second/third Town Center construction until a Castle is completed to protect stone and wood focus for the Frankish unique-unit/tech path.
- Added conditional Pikeman, Halberdier and Elite Skirmisher research; replaced the unavailable Frankish Siege Ram endpoint with Capped Ram; removed Two-Man Saw, which the current Frankish tech tree marks unavailable.
- Added explicit Heavy Mounted Crossbowman upgrade research using DE TechId 1451, stopped base-unit production when that upgrade is pending, and only trains the heavy unit after completion. Cranequins is gated on the Heavy upgrade being complete.
- Kept the four-unit Mounted Crossbowman baseline from being reset to zero by an unrelated enemy-composition rule; reduced the post-Ordonnance target from 12 to 8 to keep it a support package instead of a second primary army.
- Added `up-reset-attack-now` when the timed attack cycle closes.
- Replaced three overlapping gatherer-percentage emergency overrides with a mutually exclusive food → gold → wood recovery state. Recovery clears at food 400, gold 400, or wood 300 respectively, then returns to age baseline allocation.

### Evidence classes and constraints

- Civilization-specific technology availability was cross-checked against the current Franks technology tree in `SiegeEngineers/aoe2techtree`.
- Native tech IDs for Pikeman (197), Halberdier (429), Elite Skirmisher (98), Capped Ram (96), and Heavy Mounted Crossbowman (1451) were cross-checked against the current DE tech data. Heavy Mounted Crossbowman uses the documented numeric TechId form because its alias is not present in the checked-in AIRef technology inventory.
- Native parser/build acceptance proves the source parses and packaging is reproducible. It does not prove runtime behavior; match execution still needs to validate the intended second-building fallback, actual age-up timings, counters, and repeated attack cycles.
- This is still a hand-authored native `.per` strategy artifact, not a typed compiler-generated Franks profile.

### Runtime acceptance matrix

1. Arabia with standard resources: Feudal without an early Loom stall; first Lumber Camp and Mill; Castle Age without Market gating.
2. Arabia with nonstandard forage availability: second Dark Age building fallback; no Feudal deadlock.
3. Enemy cavalry pressure: Spearman production, Pikeman upgrade in Castle Age, Halberdier in Imperial when still needed.
4. Enemy archer pressure: Skirmisher counter demand and Elite Skirmisher upgrade.
5. Infantry-heavy opponent: Throwing Axemen, Ordonnance Companies, Mounted Crossbowman/Heavy upgrade and Cranequins.
6. Full match with available Castle resources: Castle before second/third TC; Capped Ram research; Trebuchet production; two distinct attack cycles.
7. Castle delayed/unavailable but Siege Workshop exists: University fallback and native Imperial-age eligibility.
8. Resource crisis: only one gatherer recovery mode owns percentages at a time, then age baseline resumes after recovery witnesses.
