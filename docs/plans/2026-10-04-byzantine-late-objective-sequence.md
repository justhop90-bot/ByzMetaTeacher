# Byzantine late-game objective sequence implementation plan

Branch: feat/byzantine-late-objective-sequence
Base: 319e062c200e2282291406e6559548f4d7a39fe6

## Scope

Implement a narrow late-game offensive objective controller in `Byzantine.per` only. It will layer on the existing Byzantine army readiness, siege-approach, reinforcement, and stale-watchdog lifecycle.

Objective priority is strict and restarts at the top after every objective:
1. enemy siege
2. defensive structures
3. military production
4. Town Centers
5. reassess

The controller will use bounded DUC enemy-object searches anchored to the nearest enemy Town Center. The selected enemy object becomes the target for a one-shot local army `action-attack-move`. Completion/release will be based on a fresh bounded world-state search, never a timer.

## Persistent state

Reserve unused Goal IDs 410-417:
- `byzantine-offensive-objective-state`: idle/reassess, search phases, executing, witness.
- `byzantine-offensive-objective-class`: none/siege/defense/production/TC.
- `byzantine-offensive-objective-point`: existing two-goal position span for the current anchor/target.
- `byzantine-offensive-objective-search`: DUC search cardinality.
- `byzantine-offensive-objective-claim`: one-shot objective execution claim.
- `byzantine-offensive-enemy-player`: selected enemy player number.
- `byzantine-offensive-objective-stage`: ordered candidate within the current objective class.

## Search and target order

Siege candidates:
Bombard Cannon, Trebuchet, Mangonel-line, Battering-ram-line.

Defense candidates:
Castle, Keep, Bombard Tower, Guard Tower, Watch Tower, Outpost, Wall class.

Production candidates:
Siege Workshop, Barracks, Archery Range, Stable, Monastery.

Final candidate:
Town Center.

Each candidate search is restricted to a bounded radius around the stored offensive anchor/target point. If a candidate exists, the first result is selected, its point is stored, the class/stage is recorded, and the controller enters execution.

## Execution

Before issuing an objective action, build a local actor list from existing military object classes:
cavalry-class, infantry-class, archery-class, siege-weapon-class, plus trebuchet.

Do not include villagers or monks. Do not introduce point-move staging.

Issue exactly one `up-target-objects 1 action-attack-move -1 -1` against the selected enemy object, then release the DUC search claim. Existing army readiness remains the admission gate. Existing reinforcement owns package loss.

Suppress the existing stale attack watchdog only while this DUC objective execution is active; restore its normal cadence when the objective is released. No new tactical scheduler is introduced.

## Witness/reassessment

After execution, fresh bounded searches re-probe the current objective area.
- A surviving matching objective keeps execution active.
- A missing objective releases execution and immediately resets the objective class/stage to the top-level siege search.
- Moving out of the bounded area is treated as loss of the current objective, not as proof of destruction. The controller re-anchors and reassesses from enemy siege again.
- If no objective class is found, clear the claim and return ownership to the existing normal `attack-now` path.

## Verification

Static checks:
- no duplicate Goal IDs
- no undefined new identifiers
- maximum source line remains <= 255 characters
- no logical-arity errors
- objective source order contains the strict siege -> defense -> production -> TC ladder
- execution uses object-target attack-move, not target-point movement

Repository acceptance:
- `python -m unittest LearnerAI.Compiler.tests.test_strategy_camp_controller -v`
- `python -m unittest LearnerAI.Compiler.tests.test_byzantine_defensive_geometry -v`
- `python LearnerAI/Compiler/tests/assert_native_zero.py Byzantine.per --report /tmp/native-reports/byzantine-objective.json`

Then inspect the GitHub Actions acceptance workflow for the branch/PR. Live AoE2 runtime remains a manual test because no connected native game harness is available.
