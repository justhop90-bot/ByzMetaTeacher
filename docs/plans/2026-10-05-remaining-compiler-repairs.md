# Remaining Compiler Repairs Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining compiler-owned provenance and causal-trace gaps without reopening already-closed compiler substrates or inventing runtime semantics.

**Architecture:** Production FeatureTrace evidence is populated from the actual compiler objects already present at each acceptance boundary. Artifact lineage remains a separate semantic contract: compiler artifact -> runtime assembly -> promotion -> root `Byzantine.per`. Runtime-only uncertainties stay OPEN and are never synthesized as compiler facts.

**Tech Stack:** Python 3.11-3.13, unittest, existing compiler IR/semantic validators, GitHub Actions, JSON Schema Draft 2020-12.

> **Execution status at branch head:** Task 1 FeatureTrace production population implemented; Task 2 report persistence integrated; Task 3 artifact lineage was revised after CI proved the old prefix/suffix overlay model false. The authoritative runtime is a woven `Byzantine.per`; compiler-owned `defrule` bodies must be conserved verbatim inside it. Task 4 canonical builder now uses that conservation contract. Focused artifact-lineage tests have passed 30/30 on the branch. A fresh full CI run is queued for the current head and has not completed, so this tranche is **not yet merge-ready**.

> **Important correction:** the earlier overlay-only assembly design is obsolete. Do not restore it. The root artifact is not ordered as compiler output plus suffix; current evidence showed compiler output and root diverge at the first rule. The compiler therefore owns rule bodies and provenance, while runtime ordering remains with the woven runtime artifact.

## Global Constraints

- Use current `main` as authority. FeatureTrace PR #427 is merged at `beeb391511609223cb6008343e9ab8dc3f3bd1f8`; workflow #4728 passed.
- Do not reopen production/train arbitration, generic DUC substrate, generic attack lifecycle, Goal/GoalSpan allocation, timer allocation, active-SN evidence, or static escrow ownership handoff unless a new defect is exposed by focused tests.
- Do not promote runtime-only facts such as attack acknowledgement, DUC object liveness, queue timing, escrow same-pass timing, or Strategic Number auto-mutation into compiler truth.
- Preserve the evidence boundary: ENGINE FACT, COMMUNITY EVIDENCE, COMPILER POLICY, UNKNOWN.
- FeatureTrace must be populated from actual compiler-stage objects, not reconstructed from emitted text except where emission/artifact evidence is the stage under test.
- Unknown or unavailable evidence remains UNKNOWN/OPEN and fail-closed.
- Artifact SHA-256 values always refer to exact file bytes.
- Canonical root `Byzantine.per` must eventually be byte-identical to the promoted runtime artifact. The builder must fail closed when the declared runtime overlay is missing or collides with compiler-owned identities.
- The current repository does not yet contain a canonical runtime overlay artifact. Therefore the assembly/promotion builder integration may be implemented as a fail-closed pipeline first; overlay extraction is a separate evidence-dependent step and must not be faked.
- Every task has focused tests and an integration verification command. No task is complete on stale CI evidence.

---

### Task 1: Populate FeatureTrace from the real compiler pipeline

**Files:**
- Modify: `LearnerAI/Compiler/semantic/strategy_dependency.py`
- Modify: `LearnerAI/Compiler/compiler.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_dependency.py`
- Test: `LearnerAI/Compiler/tests/test_feature_trace.py`

**Interfaces:**
- Consumes: `SemanticDemand`, `CapabilityGraph`, `BindingResult`, emitted artifact bytes, existing FeatureTrace types.
- Produces: deterministic `tuple[FeatureTrace, ...]` attached to `StrategyDependencyReport`.

- [ ] **Step 1: Add the failing production-trace test**

Add a test that exercises a real analyzed demand and asserts the compiler builds a trace containing, in order:

`SEMANTIC_IR -> SEMANTIC_VALIDATION -> CAPABILITY_GRAPH -> STORAGE_BINDING -> NATIVE_LOWERING -> EMISSION -> ARTIFACT_ANALYSIS`.

For strategic demands carrying `strategic_binding`, include a `STRATEGY_IR` root node and first edge.

The test must assert:
- the feature id is deterministic;
- each satisfied edge points at a real downstream identity;
- the artifact node carries the emitted artifact SHA-256;
- no runtime stages are falsely marked PASS.

- [ ] **Step 2: Verify the expected failure**

Run:
```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_strategy_dependency -v
```

Expected before implementation: the new assertions fail because the compiler currently attaches no production FeatureTrace evidence.

- [ ] **Step 3: Implement the minimum trace builder integration**

Add one helper that consumes actual compiler outputs and creates deterministic traces. Do not add a second dependency graph.

Required mapping:
- `STRATEGY_IR`: only when `SemanticDemand.strategic_binding` exists; identity is the strategic id.
- `SEMANTIC_IR`: every lowered demand, identity is the demand `SemanticId`.
- `SEMANTIC_VALIDATION`: PASS only after the existing semantic validator gate has succeeded.
- `CAPABILITY_GRAPH`: PASS only when the matching capability demand exists.
- `STORAGE_BINDING`: PASS only when the demand lifecycle GoalSlot request resolves through the actual `BindingResult`.
- `NATIVE_LOWERING`: PASS only after `registry.validate_demand_lowering()` has succeeded.
- `EMISSION`: PASS only when the emitted artifact contains the real demand lifecycle marker used by the emitter.
- `ARTIFACT_ANALYSIS`: PASS with the exact artifact SHA-256 after deterministic rule diagnostics have been appended.

If any required relationship is absent, emit a BROKEN edge at that stage rather than skipping the trace. Downstream stages must not be invented.

- [ ] **Step 4: Verify the focused pass**

Run the same focused unittest command. Expected: all FeatureTrace and strategy dependency tests pass.

- [ ] **Step 5: Run the affected compiler integration checks**

Run:
```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_strategy_dependency LearnerAI.Compiler.tests.test_feature_trace -v
```

Expected: zero failures.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/semantic/strategy_dependency.py LearnerAI/Compiler/compiler.py LearnerAI/Compiler/tests/test_strategy_dependency.py LearnerAI/Compiler/tests/test_feature_trace.py
git commit -m "feat: populate Byzantine feature traces from compiler stages"
```

---

### Task 2: Make compiler reports retain the populated first-broken-edge evidence

**Files:**
- Modify: `LearnerAI/Compiler/compiler.py`
- Modify: `LearnerAI/Compiler/semantic/strategy_dependency.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_dependency.py`

**Interfaces:**
- Consumes: Task 1 FeatureTrace tuple, existing `StrategyDependencyReport`.
- Produces: strategy report JSON containing populated `feature_traces` and `first_broken_edge_diagnostics`.

- [ ] **Step 1: Add failing report integration test**

Compile a representative strategy vertical slice through the existing `*_with_report` seam with a strategy report path and assert:
- `feature_traces` is non-empty;
- every trace is deterministic;
- the report artifact SHA equals the trace artifact SHA;
- no runtime trace stage is asserted as PASS.

Add one negative fixture that corrupts the emitted marker in a synthetic artifact and confirms the first broken edge is `EMISSION -> ARTIFACT_ANALYSIS`.

- [ ] **Step 2: Verify the expected failure**

Run:
```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_strategy_dependency -v
```

Expected: report contains no populated production traces before the integration is wired.

- [ ] **Step 3: Implement**

Thread the actual `BindingResult`, emitted artifact bytes, and completed validation state into the Task 1 helper. Attach traces only after `append_persistent_rule_diagnostics()` has produced the final artifact bytes. Then call `with_artifact()` and `with_feature_traces()` on the same report object before writing JSON.

Do not add a separate report format.

- [ ] **Step 4: Verify**

Run the focused strategy dependency tests and the existing Byzantine strategy integration fixture.

Expected:
- report JSON includes `feature_traces`;
- first-broken-edge diagnostics are stable;
- artifact SHA agrees across report and artifact.

- [ ] **Step 5: Commit**

```bash
git add LearnerAI/Compiler/compiler.py LearnerAI/Compiler/semantic/strategy_dependency.py LearnerAI/Compiler/tests/test_strategy_dependency.py
git commit -m "feat: persist compiler feature trace diagnostics"
```

---

### Task 3: Port artifact-lineage contracts onto current main and make assembly fail closed

**Files:**
- Create/restore: `schemas/byzantine/*.schema.json`
- Create/restore: `LearnerAI/Compiler/artifacts/__init__.py`
- Create/restore: `LearnerAI/Compiler/artifacts/lineage.py`
- Create: `tools/assemble_byzantine_runtime.py`
- Create: `tools/promote_byzantine_runtime.py`
- Test: `LearnerAI/Compiler/tests/test_artifact_lineage.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_runtime_assembly.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_runtime_promotion.py`

**Interfaces:**
- Consumes: compiler artifact + compiler manifest + explicitly declared runtime overlay + overlay manifest.
- Produces: runtime artifact/manifest, promotion artifact/manifest, and first-broken-edge lineage diagnostics.

- [ ] **Step 1: Add failing assembly/promotion tests**

Assert:
- missing overlay fails closed;
- compiler/overlay canonical paths are enforced;
- compiler and overlay SHA-256 values are rechecked;
- duplicate compiler/overlay rule identities fail;
- assembly order is exactly compiler then runtime overlay;
- promotion is byte-copy and root bytes equal runtime bytes.

- [ ] **Step 2: Verify red**

Run:
```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_artifact_lineage LearnerAI.Compiler.tests.test_byzantine_runtime_assembly LearnerAI.Compiler.tests.test_byzantine_runtime_promotion -v
```

Expected: assembly and promotion tests fail because the two orchestration tools do not yet exist.

- [ ] **Step 3: Implement**

Reuse the existing semantic verifier from the artifact-lineage tranche. The assembler must:
1. verify compiler manifest/artifact;
2. require the explicit overlay files to exist;
3. verify overlay manifest/artifact;
4. reject identity collisions;
5. assemble deterministically;
6. write runtime manifest.

The promoter must:
1. verify runtime manifest/artifact;
2. compare runtime bytes with the destination bytes before successful promotion;
3. atomically replace the root artifact and promotion manifest;
4. verify the final bytes again.

No fallback that silently copies the compiler artifact when the overlay is absent.

- [ ] **Step 4: Verify focused pass**

Run the three focused artifact test modules. Expected: zero failures.

- [ ] **Step 5: Commit**

```bash
git add schemas/byzantine LearnerAI/Compiler/artifacts tools/assemble_byzantine_runtime.py tools/promote_byzantine_runtime.py LearnerAI/Compiler/tests/test_artifact_lineage.py LearnerAI/Compiler/tests/test_byzantine_runtime_assembly.py LearnerAI/Compiler/tests/test_byzantine_runtime_promotion.py
git commit -m "feat: add fail-closed Byzantine runtime assembly and promotion"
```

---

### Task 4: Make the canonical Byzantine builder consume and verify the artifact lineage

**Files:**
- Modify: `tools/build_byzantine_bot.py`
- Modify: `.github/workflows/compiler-tests.yml`
- Modify: `docs/reference/byzantine-core-v1-build.md`
- Test: `LearnerAI/Compiler/tests/test_byzantine_bot_build.py`

**Interfaces:**
- Consumes: compiler artifact, runtime overlay, assembly/promotion tooling.
- Produces: compiler artifact, runtime artifact, root `Byzantine.per`, three manifests, and lineage verification result.

- [ ] **Step 1: Add failing builder tests**

Assert the builder expects:
- compiler artifact at `dist/byzantine/Byzantine.compiler.per`;
- runtime artifact at `dist/byzantine/Byzantine.runtime.per`;
- promoted root `Byzantine.per`;
- lineage verification after promotion.

Add a test proving the builder fails closed when the declared overlay is absent.

- [ ] **Step 2: Verify red**

Run:
```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_byzantine_bot_build -v
```

Expected: current builder writes the old artifact shape and does not enforce lineage.

- [ ] **Step 3: Implement**

Refactor `tools/build_byzantine_bot.py` into orchestration only:
`compile -> compiler manifest -> assemble -> runtime manifest -> promote -> promotion manifest -> verify lineage`.

Do not retain the old “root Byzantine.per is a separate hand-repaired artifact” contract.

- [ ] **Step 4: Verify**

Run:
```
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_byzantine_bot_build -v
```

Then run the focused artifact-lineage suite.

Expected: the builder itself fails closed until the repository contains the declared runtime overlay. This is an explicit blocker, not a reason to synthesize one.

- [ ] **Step 5: CI integration**

Add the dedicated lineage job from the existing artifact-lineage tranche to current `.github/workflows/compiler-tests.yml`. Make `verification-gate` require it.

- [ ] **Step 6: Commit**

```bash
git add tools/build_byzantine_bot.py .github/workflows/compiler-tests.yml docs/reference/byzantine-core-v1-build.md LearnerAI/Compiler/tests/test_byzantine_bot_build.py
git commit -m "ci: enforce canonical Byzantine artifact lineage"
```

---

## Cross-reference exclusions

The following were checked and are not duplicated in this tranche:

- Active Strategic Number evidence: existing `ActiveSNSeed`/`ActiveSNRecord` implementation and `test_active_sn_evidence.py`.
- Static escrow ownership handoff: existing `EscrowOwnershipHandoff`, validation, and `test_escrow_ownership_handoff.py`.
- Production/train arbitration: roadmap marks compiler policy CLOSED.
- DUC compiler substrate: roadmap marks compiler policy CLOSED.
- Attack lifecycle compiler policy: roadmap marks compiler policy CLOSED.
- Goal/GoalSpan, timer allocation, native parser replacement, generic lifecycle, capability graph, and native binding substrate: already implemented and tested.
- GameData “remaining 4 nodes” text is stale relative to current `test_game_data.py` coverage; current evidence is 159 modeled / 0 unmodeled / 14 verified unavailable. Do not resurrect obsolete blockers.
- Carrack trigger Tech 904, exact DE queue timing, attack acknowledgement, DUC object liveness, escrow same-pass timing, Strategic Number auto-mutation, and similar items remain runtime/evidence boundaries, not compiler repairs.

## Global verification ladder

Focused:
```bash
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_feature_trace LearnerAI.Compiler.tests.test_strategy_dependency -v
PYTHONPATH=LearnerAI python -m unittest LearnerAI.Compiler.tests.test_artifact_lineage LearnerAI.Compiler.tests.test_byzantine_runtime_assembly LearnerAI.Compiler.tests.test_byzantine_runtime_promotion -v
```

Authoritative:
```bash
python LearnerAI/Compiler/tests/assert_native_zero.py Byzantine.per --report /tmp/native-reports/byzantine-promoted.json
PYTHONPATH=LearnerAI python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"
```

CI acceptance additionally requires the existing 3-OS x 3-Python native-support comparison and the dedicated artifact-lineage job.

No CI result is called green unless a fresh run for the exact branch head reports success.
