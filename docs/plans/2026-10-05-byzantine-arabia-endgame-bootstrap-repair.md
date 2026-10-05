# Byzantine Arabia Endgame Bootstrap Repair Implementation Plan

> For agentic workers: Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

Goal: Make the canonical Byzantine Arabia/standard-land path self-bootstrapping and capable of reaching its existing endgame attack controller without weakening witness ownership or creating a second lifecycle model.

Architecture: Repair the existing demand and control graph at its broken edges. Add small persistent Castle seed demands, add the missing ram upgrade demands, replace the exact-trash attack admission snapshot with a mature-force package, and reconnect the already-declared attack-readiness/siege-approach states to the existing objective/role/group lifecycle.

Tech Stack: Python compiler IR and native-control lowering, generated .per, unittest regressions, pinned native AoE2 AI parser, GitHub Actions compiler acceptance.

## Global Constraints

- Canonical entry point remains build_byzantine_strategy() -> build_byzantine_stock_strategy().
- Arabia remains DEFENSIVE_STANDARD when there is no early enemy pressure; Fast Castle remains an opening decision, not an endgame fork.
- Do not create a second attack lifecycle.
- Do not use timers as truth or attack issuance as proof.
- Preserve live world-state witnesses and frontier verification.
- Persistent 18 Halberdier / 18 Elite Skirmisher / 12 Hussar demands remain production policy; they are no longer the exact admission prerequisite for every endgame push.
- Unknown native runtime semantics remain fail-closed.
- Rams remain part of the existing ram-line; no new unit-line abstraction is introduced.

---

### Task 1: Bootstrap the research prerequisites

Files:
- Modify: LearnerAI/Compiler/ir/community_strategy_packs.py around line 1245
- Test: LearnerAI/Compiler/tests/test_byzantine_arabia_endgame_bootstrap.py

Interfaces:
- Consumes existing _training_demand(), spearman-line, skirmisher-line, and scout-cavalry-line.
- Produces persistent Castle seed demands that satisfy the existing six-unit research gates.

- [x] Add the focused regression for six-unit seed demands.
- [x] Implement the three small persistent Castle seed demands.
- [ ] Run the focused unittest and confirm the identities resolve through the real strategy builder.

Expected behavior: once Castle is reached, the bot can bootstrap the existing Pikeman, Elite Skirmisher, Husbandry, and later Halberdier/Hussar research paths even without enemy pressure.

### Task 2: Connect Imperial ram conversion

Files:
- Modify: LearnerAI/Compiler/ir/community_strategy_packs.py around lines 484 and 1327
- Test: LearnerAI/Compiler/tests/test_byzantine_arabia_endgame_bootstrap.py

Interfaces:
- Consumes existing _research_demand() and verified ram-line technology data.
- Produces persistent research-capped-ram and research-siege-ram demands.

- [x] Add the focused regression for both research demands.
- [x] Add Capped Ram and Siege Ram to the existing Imperial military research pack.
- [x] Add ram-line seed-count gates of 2 and 4.
- [ ] Run the focused unittest against the repaired branch.

Expected behavior: an Imperial Byzantine player with existing Rams can turn a large food/wood bank into the existing ram upgrade chain without a manual click.

### Task 3: Repair endgame admission and readiness wires

Files:
- Modify: LearnerAI/Compiler/ir/strategy.py around lines 2922-3300
- Test: LearnerAI/Compiler/tests/test_byzantine_arabia_endgame_bootstrap.py

Interfaces:
- Consumes existing Imperial band, attack package, siege observations, objective lifecycle, role lifecycle, and endgame witnesses.
- Produces byzantine-army-attack-ready=1 and byzantine-siege-approach=normal only when the mature package is witnessed.

- [x] Add regression coverage for ram siege admission, mature-force admission, readiness writers, and recovery behavior.
- [x] Replace exact 18/18/12 attack admission with the mature-force package.
- [x] Count ram-line as qualifying siege.
- [x] Add writers for attack-ready and normal siege approach.
- [x] Replace exact-floor recovery rules with army-package/siege-package recovery.
- [ ] Run the focused unittest and inspect the emitted control section for stale exact-floor rules.

Expected behavior: a strong, actually witnessed Imperial army can enter the existing objective/role/group lifecycle without waiting for an artificial simultaneous 18/18/12 snapshot.

### Task 4: Canonical artifact and acceptance

Files:
- Modify: Byzantine.per and Byzantine.manifest.json through the canonical builder.
- Test: full LearnerAI/Compiler/tests suite.
- Acceptance: .github/workflows/compiler-tests.yml.

Interfaces:
- Consumes the repaired canonical stock strategy.
- Produces deterministic Byzantine.per and native-zero evidence.

- [ ] Run focused regression: PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_byzantine_arabia_endgame_bootstrap -v
- [ ] Run canonical build: PYTHONPATH=LearnerAI python tools/build_byzantine_bot.py
- [ ] Run native zero findings on dist/byzantine/Byzantine.per.
- [ ] Run full unittest discovery.
- [ ] Verify the checked-in artifact and manifest match the repaired source.
- [ ] Require authoritative Compiler CI success before merging to main.

## Verification status

Source changes and focused regressions are implemented on the isolated branch. Completion remains gated on fresh test/build/native-zero/CI evidence.