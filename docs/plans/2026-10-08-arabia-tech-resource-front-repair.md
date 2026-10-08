# Arabia Tech and Resource-Front Repair Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore reliable Castle/Imperial Pike and Elite Skirmisher research/production and make discovered remote gold/stone fronts reliably receive their next mining camp in the checked-in Byzantine runtime.

**Architecture:** Keep the existing StrategyProfile demand model and lifecycle unchanged. Correct native research symbols at the strategy-to-.per boundary, repair the Elite Skirmisher world-state witness so the upgraded unit is counted correctly, and fix the remote-resource camp indexing so the first newly discovered remote front is actually selected instead of being skipped. Synchronize the compiler source, focused tests, and the affected blocks of `Byzantine.per`.

**Tech Stack:** Python compiler/IR, generated AoE2DE `.per`, unittest, GitHub Actions, native AIRef/UserPatch predicates.

## Global Constraints

- Preserve the current Arabia/Arena baseline and the successful Castle Battering Ram/Siege Ram behavior.
- Do not redesign Byzantine military arbitration or create a second production scheduler.
- Native research-item identifiers must be emitted exactly where the engine expects them.
- Production witnesses must measure the actual upgraded unit state, not a lower-tier unit ID.
- A discovered remote gold/stone resource must be eligible for the first missing camp in the sequence; do not skip the first remote candidate through an off-by-one search index.
- Keep compiler source and checked-in `Byzantine.per` synchronized.
- Preserve fail-closed lifecycle semantics: pending means in-flight, completion is world-state evidence, and a failed placement/research attempt remains retryable.
- Avoid full-file normalization of the ~1.1 MB `Byzantine.per`; update only the affected generated sections.

---

### Task 1: Native Castle research symbols for Pike and Elite Skirmisher

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py:1382` (existing native-tech mapping) and `_research_demand()` at line 255 (existing interface).
- Test: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py:422`
- Runtime: `Byzantine.per` Pike research lifecycle around line 21926; add/synchronize the missing Elite Skirmisher research lifecycle beside the existing Castle research demands.

**Interfaces:**
- Consumes: `_research_demand(..., native_tech_symbol=...)`
- Produces: canonical `ri-pikeman` and `ri-elite-skirmisher` research predicates/actions in lowered output.

- [ ] **Step 1: Add focused failing assertions**

Require the compiled profile to emit:
`(can-research-with-escrow ri-pikeman)`,
`(research ri-pikeman)`,
`(can-research-with-escrow ri-elite-skirmisher)`,
and `(research ri-elite-skirmisher)`.
Reject bare `pikeman` and `elite-skirmisher` research tokens. Also require the checked-in runtime to contain both complete lifecycles.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy.ByzantineStrategyControlSliceTests.test_checked_in_runtime_researches_castle_counter_upgrades_and_capped_ram`

Expected: failure showing Pike is emitted as bare `pikeman` and the Elite Skirmisher runtime lifecycle is absent.

- [ ] **Step 3: Implement the minimum behavior**

Add explicit native mappings in the existing `native_tech_symbol` call-site map:
`research-pikeman -> ri-pikeman`
and
`research-elite-skirmisher -> ri-elite-skirmisher`.

Keep the existing tech IDs as witnesses: Pike 197 and Elite Skirmisher 98. Synchronize `Byzantine.per` so the emitted research actions use those native symbols and the Elite Skirmisher demand has the standard ACTIVE -> ISSUED/PENDING -> COMPLETE -> RELEASE lifecycle.

- [ ] **Step 4: Verify the focused pass**

Run the same focused unittest.

Expected: the research-symbol assertions and checked-in runtime lifecycle assertions pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI.Compiler.tests.test_community_strategy_packs LearnerAI.Compiler.tests.test_strategy_compiler_integration`

Expected: Castle/Imperial research demand identities resolve and compile without native-token errors.

- [ ] **Step 6: Commit the passing deliverable**

`fix: emit native Castle counter research symbols`

---

### Task 2: Verify the existing Elite Skirmisher Imperial production wire unlocks after research

**Files:**
- Verify: `LearnerAI/Compiler/ir/community_strategy_packs.py:1413` (existing `imperial-elite-skirmisher-floor` demand).
- Test: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py:422` plus community strategy tests.
- Runtime: `Byzantine.per:28771` and the surrounding Imperial Elite Skirmisher band-production rules.

**Observed state:**
- The current runtime production rule already has the correct post-upgrade gates: `up-research-status 98 >= 3`, `unit-type-count 6 < 18`, `can-train-with-escrow skirmisher-line`, and `train skirmisher-line`.
- The production is therefore blocked primarily because the Castle Elite Skirmisher research lifecycle is missing from the checked-in runtime.

**Interfaces:**
- Consumes: existing `imperial-elite-skirmisher-floor` demand and TechId 98 research witness.
- Produces: a tested proof that researching Elite Skirmisher unlocks the existing Imperial production path without changing Imperial band arbitration.

- [ ] **Step 1: Add focused assertions**

Require the checked-in Imperial production block to contain the existing research-98 guard, Elite Skirmisher unit-count gate, `can-train-with-escrow skirmisher-line`, and `train skirmisher-line`. Also require the research test from Task 1 so this production block cannot silently remain blocked by missing research.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy`

Expected before Task 1's runtime synchronization: the production block exists, but the full Castle/Imperial research-to-production test fails because Elite Skirmisher research is absent.

- [ ] **Step 3: Implement the minimum behavior**

No new production scheduler or alternate witness is needed. The implementation is the Task 1 research lifecycle plus the existing production wire. Preserve the `up-research-status c: 98 >= 3` gate and `skirmisher-line` training action exactly.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy`

Expected: Castle Pike/Elite Skirmisher research and Imperial Elite Skirmisher production assertions all pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI.Compiler.tests.test_community_strategy_packs LearnerAI.Compiler.tests.test_byzantine_arabia_endgame_bootstrap`

Expected: the persistent 18 Elite Skirmisher floor remains present and connected to the research demand without changing the existing Imperial band strategy.

- [ ] **Step 6: Commit the passing deliverable**

`test: prove Elite Skirmisher research unlocks existing Imperial production`

---

### Task 3: Fix the first remote gold/stone camp index

**Files:**
- Modify: checked-in `Byzantine.per` resource-front lifecycle sections around the gold/stone camp floors; `LearnerAI/Compiler/ir/camp_control.py` remains the placement-radius controller, but the exact floor-indexed search/build rules are currently maintained in the runtime artifact and were introduced by the Castle/resource-front repair commits.
- Tests: `LearnerAI/Compiler/tests/test_byzantine_arabia_artifact.py:37`, `LearnerAI/Compiler/tests/test_strategy_opening_economy.py:456`
- Runtime: `Byzantine.per` gold floors 2-5 around lines 17260-17663 and stone floors 2-5 around lines 17742 onward.

**Observed defect:**
- Floor 2 searches remote resources but requires `remote-count > 1` and selects `search-remote c: 1`.
- That skips the first remote candidate. The first missing camp should consume remote candidate index 0.

**Interfaces:**
- Consumes: `up-find-resource`, `up-get-search-state`, `search-remote`, stored camp point.
- Produces: a camp build rule that uses remote index `floor - 2` and requires remote count `> floor - 2` for floors 2-5.

- [ ] **Step 1: Add focused failing assertions**

Change the artifact contract to require:
floor 2 => `remote-count > 0`, `search-remote c: 0`;
floor 3 => `remote-count > 1`, `search-remote c: 1`;
and so on.

Add the same contract for stone.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI.Compiler.tests.test_byzantine_arabia_artifact LearnerAI.Compiler.tests.test_strategy_opening_economy` 

Expected: failure against the current floor-2 `> 1 / index 1` wiring.

- [ ] **Step 3: Implement the minimum behavior**

Change the generated/lowered resource-front placement rule to select the first remote candidate for floor 2 and advance one candidate per additional camp. Preserve `resource-found`, `can-build mining-camp`, pending-placement barriers, singleton build claim, stored point witness, and retry semantics.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest LearnerAI.Compiler.tests.test_byzantine_arabia_artifact LearnerAI.Compiler.tests.test_strategy_opening_economy`

Expected: all gold/stone indexed-front assertions pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI.Compiler.tests.test_camp_control LearnerAI.Compiler.tests.test_byzantine_defensive_geometry`

Expected: camp placement Strategic Number and spacing behavior remain unchanged.

- [ ] **Step 6: Commit the passing deliverable**

`fix: select first remote resource front for new camps`

---

### Task 4: Canonical artifact synchronization and runtime gate

**Files:**
- Modify: checked-in `Byzantine.per` only in the research/production/camp sections changed above.
- Verify: compiler tests plus native zero-findings/compile workflow.
- Runtime gate: Arabia 1v1, then Arena regression smoke.

- [ ] **Step 1: Regenerate/synchronize affected runtime sections**

Confirm source compiler output and checked-in `Byzantine.per` agree on Pike, Elite Skirmisher, and camp-front predicates.

- [ ] **Step 2: Verify repository-level regression**

Run the focused tests plus the repository's canonical compiler/native validation workflow.

Expected: no parser-invalid rules, no native unresolved research tokens, and no unrelated artifact rewrite.

- [ ] **Step 3: Inspect the diff**

Expected: only the compiler/test/planned-doc changes and the targeted `.per` sections. No line-ending rewrite or multi-thousand-line artifact churn.

- [ ] **Step 4: Merge to main**

Merge the verified PR into `main` with the checked-in `Byzantine.per` synchronized to the compiler.

- [ ] **Step 5: Runtime test**

Copy the new `main` `Byzantine.per` and run Arabia. Verify:
Castle: Pikeman researches and trains; Elite Skirmisher researches and later trains; newly discovered gold and stone fronts receive their next mining camp.
Imperial: Halberdier/Elite Skirmisher/Hussar production continues, with existing Siege Ram behavior preserved.

## Unresolved product decisions

None. The requested runtime behavior and preservation constraints are sufficiently specified by the current compiler doctrine and the observed runtime failures.
