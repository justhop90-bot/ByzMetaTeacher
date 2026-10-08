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
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py:255, 477`
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

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy.ByzantineStrategyControlSliceTests.test_checked_in_runtime_researches_pikeman_in_castle_and_capped_ram_in_imperial`

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

### Task 2: Repair Elite Skirmisher Castle/Imperial production witnesses

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py:1413`
- Test: `LearnerAI/Compiler/tests/test_strategy_opening_economy.py:422` and community strategy tests
- Runtime: `Byzantine.per` Imperial Elite Skirmisher production block around the generated Imperial band section.

**Interfaces:**
- Consumes: `_training_demand()`, `skirmisher-line`, native Elite Skirmisher ID 6, upgrade TechId 98.
- Produces: production requirements that count the actual Skirmisher line correctly after Elite Skirmisher research.

- [ ] **Step 1: Add focused failing assertions**

Require the Imperial Elite Skirmisher floor to use `skirmisher-line` or the concrete Elite Skirmisher unit consistently for both admission and witness. Explicitly reject the current lower-tier/incorrect witness combination `(unit-type-count 6 < 18)` and release witness that resolves to the wrong unit.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy`

Expected: failure on the Imperial Elite Skirmisher requirement/witness mismatch.

- [ ] **Step 3: Implement the minimum behavior**

Make the standing Imperial Elite Skirmisher floor depend on the real post-upgrade unit state while preserving the existing `research-completed 98`/research-status guard. The production gate must be satisfiable once Elite Skirmisher is researched and fewer than the target number of Skirmishers exist.

Do not remove the Byzantine Imperial band posture logic. The repair is only to the unit-state gate and witness.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategy_opening_economy`

Expected: Castle/Imperial Pikeman and Elite Skirmisher production/research assertions pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m unittest LearnerAI.Compiler.tests.test_community_strategy_packs LearnerAI.Compiler.tests.test_byzantine_arabia_endgame_bootstrap`

Expected: Imperial 18-Halb/18-Elite-Skirm/12-Hussar floor and research package remain intact.

- [ ] **Step 6: Commit the passing deliverable**

`fix: make Imperial Elite Skirmisher production witness executable`

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
