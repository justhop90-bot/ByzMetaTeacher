# Basilisk strategy repair checklist

Baseline before implementation: `50bb74c0331413935e354ee1b4292d2ed544bdec`.

## Implementation checklist

| Item | Decision | Community cross-reference | Status |
|---|---|---|---|
| Castle-Power release when its Castle-age target infrastructure reaches zero | Use `players-building-count target-player == 0`; keep target reacquisition separate | AIRef documents goals as script-controlled integer state; existing community scripts use explicit rule/goal lifecycle transitions. | DONE |
| RUSH participates in standing-army demand creation | Add RUSH to the existing demand-owner set | Community .per practice favors repeated condition/action rules and goal-driven production rather than a second army subsystem. | DONE |
| RUSH participates in standing-army demand clearing | Add RUSH to the existing completion-owner set | Same existing goal lifecycle; no new state variable. | DONE |
| RUSH can train standing Spearmen when demand is live | Add RUSH to existing Spear producer owner set | Community army-training examples use direct goal/condition gates around train actions. | DONE |
| RUSH can train standing Skirmishers when demand is live | Add RUSH to existing Skirm producer owner set | Same direct engine-native pattern. | DONE |
| RUSH Archer production | Leave dedicated RUSH Archer producer unchanged | Community attack/build examples commonly separate posture/trigger from direct unit production. | NO CHANGE NEEDED |
| Generic Feudal RUSH entry threshold | Do not add an extra 3-Archer predicate yet | Simple military-population/attack predicates are normal; tightening entry before closing the downstream lifecycle would treat the symptom. | DEFERRED |
| Feudal `feudal-rush` resource-mode naming | No behavioral change | Current mode is shared by Feudal RUSH/FLUSH and only controls 50F/40W/10G/0S allocation; mismatch is naming, not a separate BOOM economy. | NO CODE CHANGE |
| Dead strategy fallback cleanup | Defer until behavioral repair is runtime-validated | Subtractive cleanup is useful, but not required to close the broken RUSH/Castle wires. | DEFERRED |

## Community references used

- AoE2 AI Scripting Encyclopedia: https://airef.github.io/
- Community attack-now patterns: https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476
- Community custom-AI scripting examples: https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881
- Example public AI script repository: https://github.com/niektb/AI
- Example public AI scripting implementation using timer-gated attack-now and military-population conditions: https://github.com/lewisc64/aoe2ai

The cross-reference conclusion is conservative: the repair stays inside ordinary .per rule/goal/timer/engine-action idioms. No new architecture, telemetry bridge, simulation layer, or duplicated army-state cache was justified.

## Post-implementation audit targets

1. Castle-Power release requires Castle Age exactly, zero target buildings, no town attack, and no aggregate threat.
2. Target reacquisition remains earlier in source order, so a dead target can be replaced before Castle-Power release evaluates.
3. RUSH is recognized by both standing-army demand writer and clearer.
4. RUSH demand is serviceable by the standing Spear and Skirmisher producers.
5. Dedicated RUSH Archer production remains intact.
6. No Castle-Power Crossbow requirement leaks into Feudal RUSH attack authorization.
7. Existing attack gates remain authoritative: target buildings, attack reserve, relative force, counter veto, standing-army completion, attack-cycle idle, retreat clear, and home defense clear.
8. Runtime PASS is not claimed by this static audit. The Windows/game host was unavailable during this repair; runtime replay remains the final validator.

## Known validator limitation

`validation/basilisk-validator.js` still contains previously identified undefined validator function calls. Its overall result must not be treated as a trustworthy PASS/FAIL until those functions are repaired. This checklist therefore records source-level audit results separately from runtime validation.
