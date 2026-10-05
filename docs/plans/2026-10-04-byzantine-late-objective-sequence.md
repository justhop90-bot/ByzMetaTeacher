# Byzantine late-game objective sequence implementation plan

Branch: feat/byzantine-late-objective-sequence
Base: 319e062c200e2282291406e6559548f4d7a39fe6

## Scope

Implement a narrow late-game offensive objective controller in `Byzantine.per` only. It layers on the existing Byzantine army readiness, siege-approach, reinforcement, and stale-watchdog lifecycle.

Objective priority is strict and restarts at the top after every completed or lost objective:
1. enemy siege
2. defensive structures
3. military production, with exposed villagers as an economy fallback
4. Town Centers
5. reassess

The controller uses bounded DUC enemy-object searches anchored to the nearest observed enemy Town Center. The selected enemy object becomes the target for a one-shot local army `action-attack-move`. Completion/release is based on a fresh bounded world-state search, never a timer.

## Persistent state

Reserved compiler-owned Goal IDs are 410, 411, 412, 414, 418, and 419 plus timer 8:
- `byzantine-offensive-objective-state`: idle, siege, defense, production, Town Center, executing, witness.
- `byzantine-offensive-objective-class`: none/siege/defense/production/TC.
- `byzantine-offensive-objective-point`: two-goal position span for the current offensive anchor/target.
- `byzantine-offensive-objective-search`: four-goal DUC search-state observation.
- `byzantine-offensive-enemy-player`: selected enemy player number.
- `byzantine-offensive-objective-claim`: objective controller ownership latch.
- `byzantine-offensive-objective-timer`: witness cadence only.

## Search and target order

Siege candidates:
Bombard Cannon, Trebuchet, Mangonel-line, Battering-ram-line, then the siege-weapon class as a bounded fallback.

Defense candidates:
Castle, Keep, Bombard Tower, tower class, then wall class.

Production candidates:
Siege Workshop, Barracks, Archery Range, Stable, Monastery.
If no production target remains in the bounded area, search for an exposed enemy villager and raid that target before advancing to the Town Center class.

Final candidate:
Town Center.

Each class is searched inside a 40-tile bounded radius around the current objective point. Candidate queries are retained in DUC order so the first available query class wins. A selected object is re-targeted by object identity before `action-attack-move`.

## Execution

Before issuing an objective action, build a local actor list from existing military object classes:
cavalry-class, infantry-class, archery-class, siege-weapon-class, plus trebuchet.

Villagers and monks are excluded. No point-move staging is introduced.

The controller issues exactly one `up-target-objects 1 action-attack-move -1 -1` for the selected enemy object. Existing army readiness remains the admission gate. Existing reinforcement owns package loss. The existing stale watchdog is suspended only while the objective controller owns the offensive package and is re-armed on release/recovery.

## Witness/reassessment

After execution, a 20-second timer only advances the controller into a fresh witness search.
- A matching objective still present with `attack-soldier-count > 0` keeps the objective in execution. It does not reissue the attack command.
- A matching objective present with no attacking package (`attack-soldier-count <= 0`) releases the objective claim into the existing reinforcement/recovery owner instead of looping the same attack.
- A missing objective releases the controller and returns it to the siege-first search.
- An objective that moves outside the bounded area is treated as lost for purposes of this pass, forcing fresh reassessment rather than being falsely declared destroyed.
- Castle/fortification threat aborts the objective controller and returns ownership to the existing fortified approach.
- Exhausting the Town Center class clears the objective claim and permits the proven ordinary `attack-now` fallback.

The timer is cadence only. The release decision is the observed attack package/objective state, not timer expiry.

## Verification

Static checks:
- no duplicate `defconst` names
- balanced parentheses
- maximum source line <= 255 characters
- strict source order: siege -> defense -> production -> TC
- objective execution uses object-target `action-attack-move`, not target-point movement

Repository acceptance:
- `python -m unittest LearnerAI.Compiler.tests.test_strategy_camp_controller -v`
- `python -m unittest LearnerAI.Compiler.tests.test_byzantine_defensive_geometry -v`
- `python LearnerAI/Compiler/tests/assert_native_zero.py Byzantine.per --report /tmp/native-reports/byzantine-objective.json`

Then inspect GitHub Actions for the PR. Live AoE2 runtime remains a manual acceptance step because no connected native game harness is available.
