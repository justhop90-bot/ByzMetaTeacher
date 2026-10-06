# Byzantine Community and Engine Cross-Reference

Status: evidence ledger for semantic observability. This document records evidence; it does not promote community habits to engine facts.

## Evidence classes

- ENGINE FACT: supported by AIRef/native documentation or reproducible engine behavior in this repository.
- COMMUNITY PRACTICE: recurring pattern in independent established scripts, tutorials, or tools.
- COMPILER POLICY: explicit ByzMetaTeacher design choice.
- OPEN / UNKNOWN: not established. Runtime behavior stays unproven until witnessed.

## 1. Native scale limits

**Class:** ENGINE FACT

AIRef documents a maximum of 10,000 AI rules in DE, a 32-element per-rule ceiling, 255 characters per source line, 50 timers, DUC local/remote list limits of 240/40 objects, and a script-pass lag warning around 20 ms. These are not abstract style preferences. They are hard constraints or runtime performance boundaries that should appear in semantic reports.

Source: https://airef.github.io/resources/articles/data-limits.html

**ByzMetaTeacher consequence:** the semantic shadow reports rule count, maximum rule element count, and over-limit rules. Future performance diagnostics should also count hot-loop/search/movement constructs rather than only checking legality.

## 2. Goals, Strategic Numbers, and Timers are state, not comments

**Class:** ENGINE FACT + COMPILER POLICY

AIRef documents Goals and Strategic Numbers as numeric engine-backed state, and the compiler already models persistence, same-pass visibility, later-pass visibility, and timer cadence separately. Strategic Numbers can alter native automatic behavior, so their ownership and version sensitivity must remain explicit.

Sources:
- https://airef.github.io/resources/articles/defconsts-goals-sns-1.html
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/resources/articles/data-limits.html

**ByzMetaTeacher consequence:** a shared Goal/SN writer is a control arbitration surface. The semantic shadow must expose writers and readers so the existing StrategyDependency/FeatureTrace machinery can diagnose overlapping controllers instead of making the human reconstruct them from raw rules.

## 3. Attack control is a persistent controller

**Class:** COMMUNITY PRACTICE grounded in documented native commands

Community guides describe attack-now, attack-groups, and Town Size Attack as distinct non-DUC attack mechanisms. The documented examples use Strategic Numbers and Timers to control cadence, and the guides explicitly state that these attack systems require explored/scouted enemy objects.

Sources:
- https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881
- https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476

**ByzMetaTeacher consequence:** an emitted `(attack-now)` is only ACTION. It is not a battle-success witness. Runtime traces must separately record attack demand, attack control state, target visibility, issuance, attack-soldier witness, expiry/reset, and reassessment.

## 4. DUC and movement cost are behavioral concerns

**Class:** ENGINE FACT + COMMUNITY PRACTICE

AIRef publishes command-performance benchmarks and warns that repeated path-distance/movement work can be materially more expensive than ordinary facts, while DUC search operations have bounded search-list sizes. The compiler already treats DUC and attack as explicit semantic frontiers.

Source: https://airef.github.io/resources/articles/command-performance.html

**ByzMetaTeacher consequence:** future semantic reports should expose search cardinality, repeated-pass use, path-distance usage, movement queue patterns, and attack-loop frequency as advisory behavioral diagnostics, separate from native legality findings.

## 5. Resource dropsite and camp control are native control surfaces

**Class:** ENGINE FACT

AIRef's Strategic Number index contains native controls for camp placement distances including `sn-lumber-camp-max-distance` and `sn-mining-camp-max-distance`. These controls are materially relevant to the recurring ByzMetaTeacher runtime defect where villagers reach a resource frontier without issuing or choosing an appropriate dropsite.

Source: https://airef.github.io/strategic-numbers/sn-index.html

**ByzMetaTeacher consequence:** resource-camp behavior should be analyzed as a controller/latch system with resource-front observations, placement parameters, builder capability, action issuance, building-complete witness, and release. It should not be reduced to a worker-count threshold.

## 6. Structured .per tooling is already a community norm

**Class:** COMMUNITY PRACTICE

The community contains structured tooling around `.per`: `lewisc64/aoe2ai` provides a higher-level language that compiles to AoE2 AI syntax; `ks07/aoe2-ai-fmt` provides formatting/syntax tooling; `Jvinniec/aoe2-aiscript` provides editor tooltips, completion, and syntax highlighting. These projects do not define our compiler semantics, but they establish that preserving a machine-readable representation beside executable `.per` is practical and familiar.

Sources:
- https://github.com/lewisc64/aoe2ai
- https://github.com/ks07/aoe2-ai-fmt
- https://github.com/Jvinniec/aoe2-aiscript

## 7. Historical corpus must preserve lineage

**Class:** COMMUNITY EVIDENCE

AIRef states that its community archive contains scripts going back over twenty years and credits earlier UserPatch documentation and many long-term scripters. That is valuable prior evidence, but copied scripts are not independent confirmations. A convergence registry must track source lineage before assigning strong corroboration.

Source: https://airef.github.io/

**ByzMetaTeacher consequence:** the promotion path remains DISCOVERED -> CORROBORATED -> SEMANTICIZED -> EXPRESSIBLE -> LOWERABLE -> VERIFIED. Historical descendants of one script family count as one lineage unless an independent engine investigation or separate lineage corroborates the behavior.

## 8. What the community cannot prove for us

**Class:** OPEN / UNKNOWN

Community practice does not prove the exact battlefield outcome of an attack, the exact usefulness of a placement heuristic on every map seed, target liveness after arbitrary DUC mutations, queue timing under every provider state, or the gameplay quality of the Byzantine policy.

Those remain runtime questions. The semantic artifact may record the claim and its expected witness, but only an actual match can promote the observation to CONFIRMED.

## 9. Immediate Byzantine research priorities

1. Arena mild-pressure Castle trajectory: prove the repaired arbitration edge in a live match.
2. Resource-camp controller: prove nearby gold/wood dropsite issuance and later distinct gold reacquisition.
3. Research continuity: prove DBA/Horse Collar admission occurs promptly after the intended age transition without starving Castle.
4. Military release: prove the first autonomous attack launches, gathers an actual group, expires/reset correctly, and can relaunch.
5. Siege conversion: prove BBC/trebuchet/siege demands become battlefield actions rather than merely production state.
6. Defensive geometry: prove villagers do not repeatedly take exposed resource paths when a safe alternative is available.

These priorities are deliberately runtime-first. The compiler can describe a state machine perfectly and still lose because a villager decided that walking underneath an enemy Castle was a reasonable career move.

## 10. Repository boundary

This ledger supplements, rather than replaces, the existing `COMMUNITY_ENGINE_SEMANTICS_CHECKLIST_2026-09-26.md`, `COMMUNITY_PER_PRACTICE_SPEC.md`, `docs/research/2026-10-02-community-strategy-synthesis-registry.md`, and `docs/strategy/2026-10-02-community-derived-strategy-contract.md`.