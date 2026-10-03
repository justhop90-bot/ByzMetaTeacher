# Byzantine Meta Repair Pass v2

Date: 2026-10-03  
Base: `main` at `ab4c5f71760cc57500ae27715047084c56e5ec7c`

This tranche closes the remaining battlefield-level seams identified after the earlier map/opening/economy and multi-production-capacity repairs. It deliberately reuses the bot's existing attack, scouting, counter-package, and recovery owners.

## Cross-reference

The community `lewisc64/aoe2ai` example explicitly enables the documented engine controls `sn-attack-intelligence`, `sn-local-targeting-mode`, and `sn-enable-offensive-priority`, and uses grouped attacks rather than leaving combat behavior entirely to defaults.

Current indexed community material continues to list Naga v0.11 in 2026 AI testing, but it does not expose a reliable current Naga `.per` source in the material available here. This pass therefore treats Naga as a comparison signal for persistent scouting/grouped community practice, not as evidence for undocumented implementation details.

Official AoE2 DE Group Micro behavior likewise supports explicit group combat controls: focus fire, local numerical advantage, target selection, and alternate routing around defensive obstacles are engine-level combat behaviors.

Current Byzantine community guidance separates open Arabia from Arena Fast Castle/boom play and emphasizes flexible counter armies rather than waiting for a universal fixed Castle/Imperial package.

## Exact holes closed

### 1. Engine combat defaults were still untouched

The bot already had an attack lifecycle, attack groups, siege muster, target-point attack-move, and reassessment states, but it left four relevant native controls at engine defaults:

- `sn-attack-intelligence` = 0
- `sn-local-targeting-mode` = 0
- `sn-enable-offensive-priority` = 0
- `sn-zero-priority-distance` = 50

The repair initializes these through the existing Byzantine bootstrap:

- attack intelligence = 1
- local targeting mode = 1
- offensive priority = 1
- zero-priority distance = 255

This is control-plane configuration only. It does not create a second attack subsystem or invent an offensive-priority policy table.

### 2. Castle siege muster had a witness mismatch

Castle muster admission already required the local army group plus the Mangonel group. The holding-loss rule incorrectly compared the army group plus the Trebuchet group against the Castle Mangonel floor. That could invalidate a valid Castle 8-army + 2-Mangonel formation.

The holding-loss witness now checks the same Mangonel group used by admission.

### 3. Imperial attack readiness was over-gated

The previous gate waited for a simultaneous Cataphract floor plus Halberdiers plus a full Trebuchet/Bombard/Ram siege package. That made attack readiness depend on assembling several expensive siege types simultaneously.

The repaired gate requires:

- 12 assembled attack soldiers;
- the existing Halberdier floor;
- mounted posture: existing Cataphract floor;
- balanced/siege posture: any one sufficient siege anchor, using the existing Trebuchet, Bombard Cannon, Battering Ram, or 2-Mangonel paths.

Fortified attacks still use the existing siege-approach controller.

### 4. Counter-package selectors ignored the existing scout focus context

The five executable counter-package selectors were using `any-enemy` counts even though the bot already maintained `sn-focus-player-number` and a persistent scout-selected focus player.

Only the package-selection layer is changed. Its infantry, mounted, ranged, and siege observations now query `focus-player`. The broader map/opening pressure observations remain unchanged, so this is not a wholesale team-game rewrite.

## Non-goals

No new scheduler, DUC system, production system, economy system, or generic combat language is introduced. The existing owners remain authoritative.

## Acceptance

The branch is intended to pass the focused Byzantine tests, checked-in native zero-findings, full compiler regression, cross-platform native-support determinism, and deterministic artifact checks.

Runtime match strength remains a separate playtest question. This repair removes concrete control-plane contradictions and native-default gaps, but it does not substitute compiler acceptance for evidence from actual games.
