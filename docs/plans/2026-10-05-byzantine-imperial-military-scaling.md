# Byzantine Imperial Military Scaling Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the agreed Byzantine Imperial military doctrine into a source-backed, persistent, hysteresis-controlled late-game controller that maintains a 18 Halb / 18 Elite Skirmisher / 12 Hussar floor, scales by battlefield posture, preserves the existing gold/siege layer, and emits a native-valid `Byzantine.per`.

**Architecture:** Keep strategic doctrine in the existing Byzantine strategy pack and add one focused typed Imperial military controller for band state, dwell/cooldown policy, and band-specific native control. Production/research remain ordinary StrategyProfile demands and reuse the existing lifecycle, escrow, Goal, Timer, and Strategic Number machinery. Attack/objective controllers continue to own attack execution and world-state witnesses; the military-band controller only selects the production posture.

**Tech Stack:** Python 3.12 / `unittest`, existing StrategyProfile IR, NativeControlPlan/GoalSlot/TimerRequest, existing compiler/emitter, pinned AoE2 AI parser, GitHub Actions `compiler-tests.yml`.

## Global Constraints

- Preserve `DEMAND -> ADMISSIBILITY -> CAPABILITY -> FEASIBILITY -> ACTION -> WORLD-STATE WITNESS -> RELEASE`.
- Preserve `OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT`.
- Timers are cadence/latching state, never world-state truth.
- `can-*` remains permission/feasibility only.
- Standing-floor loss is an emergency military invariant and overrides dwell/cooldown.
- Fortified escalation only overrides normal dwell when the fortified package is actually executable.
- Enemy composition changes band ceilings, not whether the standing army exists.
- Do not introduce a second .per language, scheduler, or simulator.
- Do not claim runtime gameplay correctness from compiler CI; runtime remains a separate user-owned test.
- Current 2026 Byzantine data is authoritative. The September 22, 2026 update added Elite Varangian Guards and increased Cataphract anti-infantry damage, so premium-unit policy remains valuable but does not replace the trash backbone. The current repository data confirms Pikeman 197, Halberdier 429, Elite Skirmisher 98, Hussar 428, and Husbandry 39.
- Do not add Blast Furnace, Bloodlines, Siege Engineers, or other unavailable Byzantine technologies.
- Preserve current premium targets unless a new band policy explicitly supersedes their admission: Cataphract 30, Varangian Guard 24, Ram 8, Trebuchet 8 remain upper replacement/sustain targets.
- Standing Imperial floors are strategic baselines, not enemy-triggered counters: 18 Halberdiers, 18 Elite Skirmishers, 12 Hussars.
- Band targets:
  - Standing floor: 18 / 18 / 12.
  - Open field: 24–30 Halbs / 24–30 Elite Skirms / 16–20 Hussars.
  - Fortified push: 24–28 Halbs / 20–24 Elite Skirms / 10–14 Hussars / 6–10 siege.
  - Gold-starved trash war: 30–36 Halbs / 30–36 Elite Skirms / 18–24 Hussars.
- State-entry resources:
  - Open Field: food 2400, wood 2000, gold 2000.
  - Fortified Push: food 2400, wood 2400, gold 2600, siege >= 2.
  - Trash War: gold <= 800, food >= 2400, wood >= 2200, no executable fortified push.
- State-exit hysteresis:
  - Open Field exits for food < 1800 or wood < 1500 after 30s, gold <= 800 after 30s, or floor loss.
  - Trash exits for gold >= 1800 after 30s and valid Open Field conditions.
  - Fortified exits only after fortified threat is absent for 20s and the minimum 45s dwell is satisfied.
- Minimum dwell:
  - Standing recovery 30s.
  - Open Field 60s.
  - Fortified Push 45s.
  - Trash War 90s.
- Destination guard dwell:
  - Open entry 20s.
  - Fortified entry 15s.
  - Trash entry 30s.
  - Gold recovery 30s.
  - Economic collapse 30s.
- Re-entry cooldowns:
  - Open 30s.
  - Fortified 30s.
  - Trash 45s.
- Precedence:
  1. Floor break.
  2. Executable fortified escalation.
  3. Persistent economic collapse.
  4. Current-state dwell/cooldown hold.
  5. Normal destination priority: Fortified > Trash > Open.
  6. Otherwise hold current state.
- Reason codes: NONE/HOLD 0, FLOOR_BREAK 10, FORTIFIED_ESCALATION 20, ECONOMIC_COLLAPSE 30, GOLD_STARVED 40, GOLD_RECOVERY 50, OPEN_FIELD_ELIGIBLE 60, FORTIFIED_CLEAR 70, OBJECTIVE_LOST 80, HOLD_DWELL 90, HOLD_COOLDOWN 91.
- Boundary semantics:
  - Floor and resource-entry thresholds are inclusive unless explicitly stated otherwise.
  - Open economic exit uses strict less-than.
  - Trash gold entry is <= 800; recovery is >= 1800.
  - Timer/cooldown transition is logically admissible at the exact configured duration, but exact DE pass granularity remains runtime-open.

## Repository Cross-Reference

| Area | Current main evidence | Gap | Repair |
|---|---|---|---|
| Imperial premium sustain | Cataphract 30, Varangian 24, Ram 8, Trebuchet 8 in `community_strategy_packs.py` | No permanent trash backbone | Add Imperial floor + band demands |
| Research pack | Double Bit Axe, Horse Collar, Wheelbarrow, Hand Cart, Bow Saw, Two-Man Saw, Bodkin, Conscription, Chemistry, mining, Heavy Plow, Fletching | Missing Pikeman, Elite Skirmisher, Husbandry, Halberdier, Hussar and late military upgrade ladder | Add typed research demands with line-specific gates |
| Standing military | Castle Knight 2, Cataphract 2, conditional Varangian 2, Monk 2, Bombard 1 | No 18/18/12 Imperial floor | Add persistent Imperial floor demands |
| Production depth | Barracks/range/stable depth driven mainly by Varangian/Cata/Arb/Skirm | Depth observations are not centered on the new trash backbone | Rebase Imperial depth on Halb/ESkirm/Hussar floors while retaining premium replacements |
| Endgame push readiness | Current push gate accepts 4 Cata, 6 Varangian/Arb/Halb plus one siege | Too weak for agreed standing army doctrine | Gate push on Imperial floor package and band state |
| Fortification | Existing `byzantine-fortification-threat` and `byzantine-siege-approach` | No military-band integration | Fortified state becomes a posture input, not an attack owner |
| Endgame controller | Prompt 2–5 lifecycle exists in PR #412; final CI fixture needed world-state provenance | One regression fixture still failed on non-world frontier provenance | Keep the verified code and repair the fixture to use `strategy-enemy-castle` provenance |
| Hysteresis | No Imperial posture controller | No persistent band state/timers | Add four-state native controller with three timers |
| Property testing | No production Imperial resolver seam | Boundary tests had no real target | Test the new resolver directly, then compile/native-check its emitted control |

### Task 1: Freeze the typed Imperial military contract

**Files:**
- Create: `LearnerAI/Compiler/ir/imperial_military.py`
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Modify: `LearnerAI/Compiler/ir/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_imperial_military_contract.py`

**Interfaces:**
- Consumes: existing `StrategyProfile`, `EffectiveCivData`, `EndgamePlan`, native `GoalSlotRequest`, `TimerRequest`.
- Produces: `ImperialMilitaryBand`, `ImperialMilitaryReason`, `ImperialMilitaryPlan`, `ImperialMilitaryInput`, `ImperialMilitaryDecision`, and band constants consumed by the lowerer and strategy pack.

- [ ] **Step 1: Add the focused failing test**

Test:
- enum values are stable;
- exact 18/18/12 floor;
- exact resource thresholds;
- exact dwell/cooldown constants;
- precedence floor > fortified > economic > normal;
- decision reason codes match destination.

Run: `PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_imperial_military_contract -v`

Expected: import/attribute failure because the typed Imperial military module does not yet exist.

- [ ] **Step 2: Implement the minimum typed contract**

Define:
- `ImperialMilitaryBand`: STANDING_FLOOR, OPEN_FIELD, FORTIFIED_PUSH, GOLD_STARVED_TRASH.
- `ImperialMilitaryReason`: 0/10/20/30/40/50/60/70/80/90/91.
- Immutable threshold dataclasses for floor, resources, dwell, cooldown.
- `ImperialMilitaryInput` containing current band, unit counts, resources, siege count, objective/fortification flags, and timer/candidate state.
- `ImperialMilitaryDecision(destination, reason, candidate, timer_action, cooldown_action)`.
- Pure `resolve_imperial_military(input)` with explicit precedence and no timer-as-truth semantics.

- [ ] **Step 3: Verify the focused pass**

Run: `PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_imperial_military_contract -v`

Expected: all focused contract tests pass.

- [ ] **Step 4: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/imperial_military.py LearnerAI/Compiler/ir/strategy.py LearnerAI/Compiler/ir/__init__.py LearnerAI/Compiler/tests/test_imperial_military_contract.py
git commit -m "feat: add Byzantine Imperial military band contract"
```

### Task 2: Lower the persistent band controller

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Test: `LearnerAI/Compiler/tests/test_imperial_military_lowering.py`

**Interfaces:**
- Consumes: `ImperialMilitaryPlan`, StrategyProfile observations, existing native control registry.
- Produces: one merged `NativeControlPlan` containing four persistent band Goal values, candidate/rearm/reason Goal state, one dwell timer, one guard timer, one rearm timer, and deterministic transition rules.

- [ ] **Step 1: Add the focused failing test**

Assert:
- controller states exist;
- all three timers are `TimerRequest` states;
- initialization disables timers;
- floor break transition has no dwell/cooldown guard;
- fortified transition has 15s guard dwell;
- Open has 60s minimum dwell;
- Trash has 90s minimum dwell;
- rearm values are 30/30/45;
- lower-priority simultaneous candidate is discarded;
- timer expiry requires the live guard to remain true.

Run: `PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_imperial_military_lowering -v`

Expected: failure because the lowering function is absent.

- [ ] **Step 2: Implement native lowering**

Add a focused `_byzantine_imperial_military_control_plan(profile)` and merge it into `_strategy_control_plan`.

Rules must:
1. initialize state to STANDING_FLOOR and disable all timers;
2. enter candidate state only after destination guard is true;
3. reset/restart guard timer when candidate changes;
4. re-check the live guard after timer expiry;
5. make floor break immediate;
6. allow executable fortified escalation to bypass normal current-state dwell but not Fortified rearm;
7. enforce current-state minimum dwell for ordinary transitions;
8. arm the destination-specific rearm state on scaling-band exit;
9. never use timer expiry as a battlefield witness;
10. never issue attack or movement actions.

- [ ] **Step 3: Verify focused lowering and native parsing**

Run:
`PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_imperial_military_lowering -v`

Expected: focused tests pass with deterministic rule/state identities.

Then compile the Byzantine profile and run `assert_native_zero.py` on the emitted artifact.

- [ ] **Step 4: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/strategy.py LearnerAI/Compiler/tests/test_imperial_military_lowering.py
git commit -m "feat: lower Byzantine Imperial military band controller"
```

### Task 3: Add the Imperial military economy, upgrade ladder, and production scaling

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py`
- Test: `LearnerAI/Compiler/tests/test_community_strategy_packs.py`
- Test: `LearnerAI/Compiler/tests/test_imperial_military_properties.py`

**Interfaces:**
- Consumes: current Byzantine game-data names and existing `_research_demand`, `_training_demand`, `_endgame_training_demand`, production-depth machinery.
- Produces: standing-floor demands, band-scaled demands, research/upgrade demands, and revised provider-depth observations.

- [ ] **Step 1: Add failing focused tests**

Assert the stock Byzantine profile contains:
- Imperial Halberdier floor 18.
- Imperial Elite Skirmisher floor 18.
- Imperial Hussar floor 12.
- Imperial premium gold floor 12 through Cataphract, while Varangian remains conditional on infantry pressure.
- Imperial standard siege capacity is at least four through the role/siege package.
- Research demands for Pikeman, Elite Skirmisher, Husbandry, Halberdier, Hussar.
- Blacksmith ladder includes Fletching/Bodkin/Bracer for ranged trash, Forging/Iron Casting/Plate Mail for Halbs, and Scale/Chain/Plate Barding for Hussar.
- No Blast Furnace, Bloodlines, or Siege Engineers demand.
- Barracks/range/stable provider depth follows 6/12/18 standing thresholds for Halb/ESkirm/Hussar.
- Open/fortified/trash band demands produce the exact lower/upper targets described above.

- [ ] **Step 2: Observe the expected red state**

Run the focused tests.

Expected: missing demand identities/research rows and existing provider observations fail the new assertions.

- [ ] **Step 3: Implement the minimum policy**

Add:
- research entries gated by age and line participation:
  - Pikeman when spear-line >= 6 in Castle;
  - Elite Skirmisher when skirmisher-line >= 6 in Castle;
  - Husbandry when scout-cavalry-line >= 6 in Castle and stable exists;
  - Halberdier when spear-line >= 8 in Imperial;
  - Hussar in Imperial once scout-cavalry-line is established.
- standing floor demands for 18/18/12.
- premium gold floor target 12 for Cataphract, retaining Varangian conditional target 24.
- band scaling demands:
  - Open: 24/24/16.
  - Fortified: 24/20/10.
  - Trash: 30/30/18.
  - High-bank additions: +6 Halb, +6 ESkirm, +4 Hussar within their applicable states.
- blacksmith demands tied to actual unit presence and existing escrow/resource arbitration.
- revise production replacement observations:
  - barracks: Halberdier < 18 OR Varangian < 12;
  - range: Elite Skirmisher < 18 OR Arbalester < 12;
  - stable: Hussar < 12 OR Cataphract < 12.
- revise production-depth observations so 6/12/18 thresholds follow the new backbone while retaining premium replacements.
- keep existing Cataphract 30, Varangian 24, Ram 8, Trebuchet 8 as upper sustain targets.

- [ ] **Step 4: Verify focused pass**

Run:
`PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_community_strategy_packs LearnerAI.Compiler.tests.test_imperial_military_properties -v`

Expected: all focused strategy assertions pass.

Then compile and inspect the generated profile for duplicate demand identities, invalid tech names, and resource-arbitration conflicts.

- [ ] **Step 5: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/community_strategy_packs.py LearnerAI/Compiler/tests/test_community_strategy_packs.py LearnerAI/Compiler/tests/test_imperial_military_properties.py
git commit -m "feat: add Byzantine Imperial trash backbone and upgrades"
```

### Task 4: Reconcile attack readiness, role/siege floors, hysteresis properties, and endgame regression

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Modify: `LearnerAI/Compiler/ir/role_separation.py`
- Modify: `LearnerAI/Compiler/tests/test_endgame_contract.py`
- Test: `LearnerAI/Compiler/tests/test_imperial_military_properties.py`
- Test: `LearnerAI/Compiler/tests/test_role_separation.py`

**Interfaces:**
- Consumes: the Imperial band controller and existing endgame/role lifecycle.
- Produces: an attack-readiness gate consistent with the standing floor, a standard siege package of 4, fortified siege package of 6, and exhaustive property-style boundary coverage.

- [ ] **Step 1: Add failing tests**

Cover:
- all 18/18/12 floor edges;
- inclusive/exclusive resource edges;
- exact 29/30, 44/45, 59/60, 89/90 timer boundaries;
- exact 29/30/44/45 cooldown boundaries;
- every pairwise and three-way precedence case;
- floor break always wins;
- fortified escalation wins only when its full resource/siege package is executable;
- role siege standard floor 4 and fortified floor 6;
- push admission rejects sub-floor armies even when premium units are abundant.

- [ ] **Step 2: Verify red**

Run the two focused test modules.

Expected: old readiness/siege floors and absent controller behavior fail.

- [ ] **Step 3: Implement minimal reconciliation**

- Update push `military_ready` to require the 18/18/12 standing package.
- Require the applicable band state before normal push admission.
- Keep attack execution ownership unchanged.
- Raise role siege floor standard from 1 to 4 and fortified from 2 to 6.
- Increase the forming-siege selection cap so the role lifecycle can actually satisfy those floors.
- Preserve the existing role ownership boundary: no role-owned attack/move/stop actions.
- Keep objective completion tied to world-state witnesses.
- Keep the corrected PR #412 frontier witness fixture on `strategy-enemy-castle` provenance.

- [ ] **Step 4: Verify focused pass**

Run the focused endgame, role, and Imperial property tests.

Expected: all pass.

- [ ] **Step 5: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/strategy.py LearnerAI/Compiler/ir/role_separation.py LearnerAI/Compiler/tests/test_endgame_contract.py LearnerAI/Compiler/tests/test_imperial_military_properties.py LearnerAI/Compiler/tests/test_role_separation.py
git commit -m "fix: align Byzantine endgame readiness with Imperial army bands"
```

### Task 5: Canonical artifact and acceptance

**Files:**
- Modify: `docs/audits/2026-10-02-byzantine-behavioral-baseline.md`
- Modify: `docs/strategy/2026-10-01-byzantine-strategy-doctrine.md`
- Use: `.github/workflows/compiler-tests.yml`
- Generate: `dist/byzantine/Byzantine.per`

**Interfaces:**
- Consumes: completed Imperial military contract and all prior focused tests.
- Produces: synchronized strategy documentation and deterministic native-valid Byzantine runtime artifact.

- [ ] **Step 1: Add/refresh documentation assertions**

Document the standing 18/18/12 floor, the four posture bands, thresholds, hysteresis, research ladder, provider-depth mapping, and the distinction between standing army and attack group.

- [ ] **Step 2: Run the focused full compiler suite**

Run:
`PYTHONPATH=LearnerAI python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"`

Expected: zero failures/errors.

- [ ] **Step 3: Generate and validate the canonical artifact**

Run:
`PYTHONPATH=LearnerAI python tools/build_byzantine_bot.py`

Then:
`python LearnerAI/Compiler/tests/assert_native_zero.py dist/byzantine/Byzantine.per --report /tmp/native-reports/byzantine-imperial-v1.json`

Expected: deterministic build and zero native findings.

- [ ] **Step 4: Compare generated output for deterministic repeat**

Run the canonical build twice and verify byte equality/hash equality through the existing build regression.

- [ ] **Step 5: Run the authoritative GitHub Actions workflow**

Workflow: `Compiler tests`.

Expected:
- 9 native-support determinism jobs pass;
- snapshot comparison passes;
- canonical Byzantine build passes;
- canonical native zero-findings passes;
- focused military/endgame/role tests pass;
- full compiler regression passes;
- verification gate passes.

- [ ] **Step 6: Merge the coherent tranche into `main`**

Merge only after the fresh workflow for the final head is green. Do not merge PR #413's contract tests independently if they are superseded by the integrated resolver tests. The final `main` artifact must be regenerated from the merged source, then handed to runtime testing.

## Acceptance boundaries

The compiler tranche is complete only when all of the following are true:

1. The actual generated Byzantine strategy contains the 18/18/12 floor.
2. The research ladder contains Pikeman, Elite Skirmisher, Husbandry, Halberdier, and Hussar with the stated gates.
3. The blacksmith ladder does not request unavailable Byzantine technologies.
4. Provider depth responds to the new standing backbone.
5. Attack admission cannot fire with a broken standing floor.
6. Fortified posture owns composition selection only while its executable battlefield/resource guard is true.
7. Gold starvation enters only at <=800 gold and exits only at >=1800 gold after recovery dwell.
8. Timer expiration cannot prove a battlefield transition.
9. Cooldowns prevent immediate re-entry.
10. All pairwise, three-way, and boundary tests pass.
11. Canonical `Byzantine.per` is native-zero-findings and deterministic.
12. Fresh CI is green before merge.
13. Runtime gameplay is handed to the user as a separate test.

## Execution note

The current endgame PR #412 has one known stale provenance fixture; the endgame implementation itself passed all earlier native acceptance and focused tests. The final military tranche should retain that code, fix the fixture, and merge the entire coherent set once the authoritative workflow is green.
