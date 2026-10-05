# Byzantine Behavioral Baseline - 2026-10-02

## Exact artifact
Repository: justhop90-bot/ByzMetaTeacher
Branch: main
Reviewed commit before roadmap write: bf63a4dac56434a0c939b7f0663e7ed1ec6af463
Byzantine.per blob before roadmap write: 858e65dbbfdbb0fe3edd779bc23db82a68835e42

Source measurements:
- 16,125 lines
- 569,632 characters
- 1,172 defrules
- 782 defconst definitions
- 0 tabs
- maximum source-line length: 226 characters
- balanced parentheses
- 0 unterminated rules

The documentation-only roadmap commit does not alter Byzantine.per.

## Native grammar findings
Four real logical-arity defects exist in the reviewed Byzantine.per:
1. Line 2522: 16-operand or in Scout loss recovery.
2. Line 4778: 3-operand or in Imperial farm arbitration.
3. Line 4783: 3-operand and inside the same farm rule.
4. Line 5760: 3-operand or in siege-approach gating.

One rule exceeds the DE 32-element ceiling:
- rule beginning line 4759: 34 elements.

Four rules are exactly at 32 elements:
- line 5656
- line 6181
- line 6238
- line 6274

Three rules are at 30 elements:
- line 4198
- line 9075
- line 9312

No missing closing parenthesis exists in the reviewed Git artifact. A game error reported as missing-parenthesis near line 2525 must therefore be tied to this exact artifact before being treated as a source defect.

## Command-role baseline
A direct check against the repository's checked-in AIRef command inventory found:
- 0 unknown command heads
- 0 Fact/Action role mismatches

DUC arity must be interpreted through the project's own current Fact/Action contracts. The project documents up-find-local and up-find-remote as Fact/Action primitives with four native predicate operands, so raw counts from an older inventory snapshot are not sufficient evidence of a defect.

## Strategic inventory baseline
The current bot already contains substantial systems for:
- age progression
- Castle and Imperial commitment
- scouting and enemy-production intelligence
- military composition
- siege
- walls and fortification
- farms, dropsites, and markets
- water and transport
- late-game surplus spending
- bounded gatherer deltas
- recovery states

Therefore the next strategic work should target arbitration quality and subsystem interaction before adding new vocabulary.

## Observed game signal
Recent play reached Imperial, built a coherent army, used a generally standard late-game plan, and defeated the easy AI. The major observed weakness was persistent late-game resource banking of roughly 8k wood, 8k gold, and 4-5k food.

This points to a spending-controller failure rather than a basic age-up or military-composition failure.

## Existing spending structure
Current late-game minimum targets include:
- Cataphract: 18
- Varangian Guard: 14
- Arbalester: 14
- Halberdier: 18
- Ram: 4
- Trebuchet: 4
- Bombard Cannon: 4

Current surplus thresholds include:
- gold > 4500
- wood > 5000
- food > 5000

The current mechanism therefore behaves primarily as a fixed-floor/reassertion system. It does not yet constitute a continuous demand engine that remains hungry after all minimum packages are satisfied.

## Naga/community reference signal
Community discussion around Naga emphasized:
- scouting enemy production early enough to predict composition
- attacking exposed economy
- avoiding waste under towers and fortified walls
- using siege instead of sacrificing ordinary units into fortifications
- preserving and repositioning army elements under defensive fire
- hit-and-run and raid behavior
- adapting to enemy commitments rather than executing an unchanging army script

Community testing also reports weaknesses in some water/transport behaviors, so Naga is a behavioral reference set with known counterexamples, not an authority to copy.

## Petersen process reference
Sandy Petersen's documented AoE design work emphasizes explicit rule-based AI, strong faction identity, playtesting, rapid iteration, and balancing from observed games. This roadmap therefore treats empirical game behavior as the final debugging surface rather than assuming source complexity equals intelligence.

## Phase-0 conclusion
Do not begin strategic tuning from intuition. First resolve or isolate the known grammar defects, preserve this behavioral baseline, and then redesign the late-game spending controller around measurable bank pressure and current strategic objective.

The first strategic hypothesis to test after grammar hardening is:
persistent late-game surplus is caused by fixed spending floors becoming satisfied while no higher-level objective continually creates new spend demand.


## 2026-10-05 Imperial military tranche reconciliation

The late-game audit has now been cross-reconciled against the executable Byzantine strategy source.

The standing Imperial military floor is:
- 18 Halberdiers
- 18 Elite Skirmishers
- 12 Hussars

The floor is persistent and does not require exact enemy-counter confirmation. Enemy composition changes the scaling ceiling, not the existence of the army.

The four persistent Imperial postures are:
- STANDING_FLOOR: restore 18/18/12 and the floor-recovery bank.
- OPEN_FIELD: 24/24/16, scaling to 30/30/20 on a high bank; mounted pressure can raise Halberdiers to 30/36 and ranged pressure can raise Elite Skirmishers to 30/36.
- FORTIFIED_PUSH: 24/20/12 with a live siege package; high-bank scaling reaches 28/24/14 and requires the fortified battlefield/resource witness.
- GOLD_STARVED_TRASH: 30/30/18, scaling to 36/36/24 when food/wood support sustained trash replacement.

The state controller is hysteresis-latched. Standing recovery requires 30 seconds. Open, fortified, and trash minimum dwells are 60/45/90 seconds. Entry guard dwells are 20/15/30 seconds, fortified-clear and gold-recovery use 20/30 seconds, and re-entry cooldowns are 30/30/45 seconds. Floor loss is an immediate override. Fortified escalation only overrides normal dwell when the full fortified resource/siege package is executable.

The Imperial upgrade contract now includes the Castle and Imperial Spear/Skirmisher/Cavalry ladder, Husbandry, relevant blacksmith armor/attack upgrades, Bracer, Halberdier, and Hussar. The policy explicitly does not request unavailable Byzantine technologies such as Blast Furnace, Bloodlines, or Siege Engineers.

The older fixed floors in this document remain useful as historical observations of the pre-tranche artifact. The executable source is now the authority for the active 2026-10-05 Imperial military contract.
