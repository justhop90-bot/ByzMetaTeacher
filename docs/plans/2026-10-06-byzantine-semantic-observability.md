# Byzantine Semantic Observability Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 1.05 MB Byzantine runtime artifact semantically inspectable by combining effective rules, persistent-state ownership, community/engine evidence, and runtime witness contracts without introducing a second scripting language.

**Architecture:** Reuse the existing SourceGraphResolver, EffectiveRule, FeatureTrace, and StrategyDependencyReport infrastructure. Add an artifact-centric semantic shadow manifest, an evidence ledger with explicit provenance classes, and a runtime-witness schema/scenario layer that references existing rule identities and lifecycle states.

**Tech Stack:** Python 3, immutable dataclasses, existing AoE2 .per parser/source graph, JSON, Markdown, unittest, GitHub Actions/native validator.

## Global Constraints

- `main` is authoritative.
- `Byzantine.per` remains the executable runtime artifact and controlled hybrid overlay.
- Do not introduce a scheduler, runtime simulator, second .per language, or duplicate lifecycle model.
- Preserve DEMAND -> CAPABILITY -> FEASIBILITY -> ACTION -> WORLD-STATE WITNESS -> RELEASE/INVALIDATION -> REASSESSMENT.
- Preserve `can-*` as feasibility/admission, never completion.
- Preserve ENGINE FACT / COMMUNITY PRACTICE / COMPILER POLICY / OPEN or UNKNOWN as distinct evidence classes.
- Runtime game observations remain the authority for gameplay behavior.
- Generated semantic reports must be deterministic and include the exact artifact SHA-256.
- Native acceptance remains a separate gate from semantic/report generation.
- Community sources with common historical lineage do not count as independent corroboration.

---

### Task 1: Build the artifact semantic shadow manifest

**Files:**
- Create: `LearnerAI/Compiler/semantic/semantic_manifest.py`
- Modify: `LearnerAI/Compiler/semantic/__init__.py`
- Test: `LearnerAI/Compiler/tests/test_semantic_manifest.py`

**Interfaces:**
- Consumes: Path to a .per entrypoint; existing SourceGraphResolver and analyze_effective_rules().
- Produces: immutable SemanticRuleRecord, SemanticManifest, build_semantic_manifest(path), and deterministic to_json()/write_json().

- [ ] **Step 1: Add the focused failing test**
Assert that the public builder exists, parses a native-control annotation, extracts Goal reads/writes, records recurrent pass behavior, counts rule elements, and parses the real Byzantine.per Arena pressure rule.

- [ ] **Step 2: Verify red**
Run: `PYTHONPATH=LearnerAI python -m unittest LearnerAI/Compiler/tests/test_semantic_manifest.py`
Expected: failure because Compiler.semantic.build_semantic_manifest does not exist.

- [ ] **Step 3: Implement**
Build from the existing effective source graph. Extract generated semantic comments, preserve source path/line/order, classify annotation kind, index Goal/SN/Timer reads and writes, calculate expression-node element count, and emit deterministic sorted records and shared-state indexes.

- [ ] **Step 4: Verify green**
Run the same focused command. Expected: all manifest tests pass, including parsing the real 1.05 MB artifact.

- [ ] **Step 5: Integration**
Run: `PYTHONPATH=LearnerAI python -m unittest discover -s LearnerAI/Compiler/tests -p 'test_*.py' -k 'SemanticManifest or StrategyDependency or FeatureTrace'`
Expected: zero failures.

- [ ] **Step 6: Commit**
`git add LearnerAI/Compiler/semantic/semantic_manifest.py LearnerAI/Compiler/semantic/__init__.py LearnerAI/Compiler/tests/test_semantic_manifest.py`
`git commit -m 'feat: add deterministic Byzantine semantic shadow'`

### Task 2: Connect shared-state ownership to the semantic shadow

**Files:**
- Modify: `LearnerAI/Compiler/semantic/semantic_manifest.py`
- Test: `LearnerAI/Compiler/tests/test_semantic_manifest.py`
- Existing integration: `LearnerAI/Compiler/semantic/strategy_dependency.py`

**Interfaces:**
- Consumes: manifest rule records plus existing StrategyDependencyReport.
- Produces: deterministic writers_by_state and readers_by_state indexes keyed by Goal, Strategic Number, and Timer identity.

- [ ] **Step 1:** Add fixture rules with two writers and one reader of the same Goal; assert rule order and source locations.
- [ ] **Step 2:** Run the focused manifest test and observe the missing shared-state index failure.
- [ ] **Step 3:** Implement canonical state-access records and deterministic writer/reader indexes. Do not infer causality beyond observed rule order.
- [ ] **Step 4:** Re-run the identical focused command and require zero failures.
- [ ] **Step 5:** Run the SemanticManifest + StrategyDependency integration subset.
- [ ] **Step 6:** Commit the passing deliverable.

### Task 3: Add the community/engine evidence ledger

**Files:**
- Create: `docs/research/2026-10-06-byzantine-community-cross-reference.md`
- Test: `LearnerAI/Compiler/tests/test_idiom_coverage.py` only if the repository evidence-path checker requires a new reference.

**Interfaces:**
- Consumes: the existing community-engine checklist/spec/registry plus cited AIRef and community sources.
- Produces: human-auditable records with evidence class, provenance, scope/version, confidence, and runtime boundary.

- [ ] **Step 1:** Document only supported claims for Goals/SNs/Timers, attack groups, scouting, DUC/search cost, camp-distance SNs, rule/data limits, and structured community tooling.
- [ ] **Step 2:** Validate repository evidence paths with the existing idiom-coverage test.
- [ ] **Step 3:** Commit the evidence ledger separately from policy changes.

### Task 4: Formalize runtime witness contracts and adversarial scenarios

**Files:**
- Create: `docs/reference/runtime-witness.schema.json`
- Create: `docs/runtime/scenarios/arena-mild-pressure-castle.json`
- Create: `docs/runtime/scenarios/resource-camp-placement.json`
- Create: `docs/runtime/scenarios/attack-release-and-siege.json`
- Test: `LearnerAI/Compiler/tests/test_runtime_witness_schema.py`

**Interfaces:**
- Consumes: semantic rule identities, Goal/SN ownership, roadmap claims, and real match checkpoints.
- Produces: machine-readable witness records that separate expected observations from confirmed observations.

- [ ] **Step 1:** Add the failing schema/scenario test.
- [ ] **Step 2:** Verify failure is due to missing witness artifacts.
- [ ] **Step 3:** Implement schema and scenarios without pre-populating runtime results as facts.
- [ ] **Step 4:** Run the focused test and require zero failures.
- [ ] **Step 5:** Commit the witness contract.

### Task 5: Add deterministic semantic-report generation to the release path

**Files:**
- Create or modify: `tools/build_byzantine_semantic_manifest.py` or the existing Byzantine build tool.
- Test: `LearnerAI/Compiler/tests/test_semantic_manifest.py`
- Modify: `.github/workflows/compiler-tests.yml`

**Interfaces:**
- Consumes: checked-in `Byzantine.per`.
- Produces: deterministic semantic manifest with artifact SHA-256 and rule/state indexes; never mutates the .per.

- [ ] **Step 1:** Add a failing test for deterministic double generation.
- [ ] **Step 2:** Observe red, then implement the smallest CLI.
- [ ] **Step 3:** Accept explicit input and optional output, defaulting to stdout.
- [ ] **Step 4:** Compare two output SHA-256 values.
- [ ] **Step 5:** Publish the manifest as a CI artifact.
- [ ] **Step 6:** Commit the release-path integration.

### Task 6: Build the live-runtime evidence loop

**Files:**
- Create: `docs/runtime/README.md`
- Create: runtime traces only after actual matches produce them.

**Interfaces:**
- Consumes: match screenshots/checkpoints, exact bot SHA, exact Byzantine.per SHA, map/civ/difficulty/population metadata, observed actions and witnesses.
- Produces: replayable evidence linked to semantic rule/state identities.

- [ ] **Step 1:** Freeze the evidence-capture contract.
- [ ] **Step 2:** Capture Arena mild-pressure Castle acceptance on current main.
- [ ] **Step 3:** Promote only directly observed facts.
- [ ] **Step 4:** Repeat for resource camps, autonomous attack, siege commitment, and exposed-resource avoidance.
- [ ] **Step 5:** Commit evidence separately from policy repairs.

### Task 7: Add community-corpus convergence and performance diagnostics

**Files:**
- Modify: `LearnerAI/Compiler/semantic/community_engine.py`
- Modify/Test: `LearnerAI/Compiler/tests/test_idiom_coverage.py`

**Interfaces:**
- Consumes: evidence records and source lineage.
- Produces: corroboration strength and qualitative cost metadata without promoting uncertain community patterns to engine facts.

- [ ] Require independent lineage for strong corroboration.
- [ ] Add qualitative cost classes for DUC/pathing/movement/attack loops.
- [ ] Add advisory hot-loop/cardinality diagnostics.
- [ ] Keep performance findings separate from native legality.

### Task 8: Runtime-informed first-broken-edge diagnostics

**Files:**
- Modify: `LearnerAI/Compiler/semantic/strategy_dependency.py`
- Modify: `LearnerAI/Compiler/semantic/semantic_manifest.py`
- Test: new focused runtime-to-feature mapping tests

**Interfaces:**
- Consumes: semantic manifest plus runtime witness records.
- Produces: a deterministic causal diagnosis mapped to OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT.

- [ ] Add the failing runtime-to-feature mapping test.
- [ ] Map observed state to existing FeatureTrace boundaries.
- [ ] Emit the first-broken-edge without inventing unobserved engine facts.
- [ ] Verify an Arena failure and successful Castle witness map deterministically.