# Native Controller Interaction Semantics Implementation Plan

> For agentic workers: Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

Goal: Add a typed, evidence-governed interaction layer over the merged Native Controller Graph so the compiler can represent controller gating, feedback, automatic state mutation, world-state dependencies, temporal visibility, version scope, and qualitative performance/cardinality effects without changing source syntax or lowering.

Architecture: Keep native_controller.py as the ownership/corpus layer and add semantic/native_controller_interactions.py as the directed interaction layer. Interactions use typed endpoints that can name either a controller or an existing control surface, plus relation kind, lifetime, visibility, mutation ownership, evidence/status, engine-version scope, and optional performance/cardinality metadata. Validation is descriptive and fail-closed: evidence-only relationships remain analyzable but cannot promote to ENGINE_SEMANTICS_MAPPED without native-fact evidence and compatible engine scope.

Tech Stack: Python 3.11-3.13, dataclasses/enums, existing Native Controller Graph, EngineVersionScope, PerformanceClass, unittest, GitHub Actions compiler gate.

## Global Constraints

- Start from canonical main commit 066ab3cd4539d898dd75c718a4997db4e2368f4a.
- Do not change the source language.
- Do not introduce a scheduler, simulator, strategy engine, or generic memory/state abstraction.
- Preserve ENGINE FACT, COMMUNITY PRACTICE, COMPILER POLICY, and OPEN / UNKNOWN evidence classes.
- Community evidence may create EVIDENCE_ONLY interaction records but cannot by itself create executable native semantics.
- Existing Strategic Number arithmetic, source-order, recurrent execution, DUC, and lowering behavior must remain unchanged.
- Feedback relations are explicitly non-acyclic dependency edges and must not be fed into DAG/SCC dependency validation as if they were ordinary prerequisite edges.
- Engine-version scope must be explicit for every seeded interaction.
- Performance metadata is advisory; it must never silently become a blocking semantic rule.
- Existing controller/surface ownership remains authoritative; the interaction layer must cross-check it, not duplicate it as a competing source of truth.

---

### Task 1: Establish the typed interaction contract and hostile validation surface

Files:
- Create: LearnerAI/Compiler/semantic/native_controller_interactions.py
- Test: LearnerAI/Compiler/tests/test_native_controller_interactions.py
- Modify: LearnerAI/Compiler/semantic/__init__.py

Interfaces:
- Produces NativeInteractionEndpointKind, NativeControllerInteractionKind, NativeInteractionLifetime, NativeInteractionVisibility, NativeInteractionMutationOwner, NativeInteractionSupportState.
- Produces immutable NativeInteractionEndpoint, NativeInteractionCardinality, NativeControllerInteraction, and NativeControllerInteractionCatalog.
- Produces NativeControllerInteractionCatalog.validate(controller_catalog, target_engine_families=(AIRefVersionFamily.DE,)).
- Produces NativeControllerInteractionCatalog.resolve(interaction_id), fingerprint(), dependency_edges(), and require_engine_semantics_mapped(interaction_id).
- Produces default_native_controller_interaction_catalog(controller_catalog=None).

- [ ] Step 1: Add the focused failing test

Cover controller gating, surface ownership, automatic mutation, unknown controller/surface endpoints, duplicate identity, self-interaction, contradictory reverse-direction relations, bidirectional feedback, feedback exclusion from dependency edges, evidence-only promotion rejection, mapped interaction evidence requirements, version-scope mismatch, mutation-owner confusion, deterministic ordering/fingerprint, explicit lifetime/visibility, and invalid cardinality ranges.

- [ ] Step 2: Verify the relevant failure

Run: python -m unittest LearnerAI/Compiler/tests/test_native_controller_interactions.py
Expected: import failure for Compiler.semantic.native_controller_interactions caused by the missing production module.

- [ ] Step 3: Implement the minimum contract

Implement endpoint validation, relation compatibility, contradiction rules, feedback non-dependency classification, evidence/status promotion gate, version-scope compatibility, mutation-owner rules, deterministic ordering/fingerprinting, and cardinality validation. Do not seed community interactions yet.

- [ ] Step 4: Verify the focused pass
Run the same focused command and require all interaction contract tests to pass.

- [ ] Step 5: Run affected integration checks
Run: python -m unittest LearnerAI/Compiler/tests/test_native_controller_semantics.py
Run: python -m unittest LearnerAI/Compiler/tests/test_native_engine_effects.py
Run: python -m unittest LearnerAI/Compiler/tests/test_recurrent_execution.py

- [ ] Step 6: Commit the passing deliverable
Commit: feat(compiler): add native controller interaction contract

### Task 2: Seed the first evidence-backed interaction corpus

Files:
- Modify: LearnerAI/Compiler/semantic/native_controller_interactions.py
- Test: LearnerAI/Compiler/tests/test_native_controller_interactions.py
- Modify: LearnerAI/Compiler/semantic/native_controller.py only if evidence requires a new surface/controller identity

Seed the audited relationships: attack gating by exploration, town-size/response controls affecting attack state, civilian allocation/resource protection coupling, escrow to production/research admissibility where justified, DUC search to target availability, documented DUC automatic search-index resets, and advisory DUC performance/cardinality metadata.

Every seeded interaction must retain EVIDENCE_ONLY unless native evidence supports ENGINE_SEMANTICS_MAPPED. Do not infer symmetric causality from co-occurrence in a community script.

- [ ] Step 1: Add failing seeded-corpus assertions
Assert exact interaction IDs, endpoint kinds, relation kinds, mutation owners, visibility/lifetime, engine-version scope, evidence status, and representative performance/cardinality metadata.

- [ ] Step 2: Verify red
Run the focused interaction suite. Expected: seeded interaction lookups fail because the corpus is not yet present.

- [ ] Step 3: Implement the evidence corpus
Add only relationships supported by the cross-referenced evidence. Omit uncertain directions or retain them as evidence-only.

- [ ] Step 4: Verify focused green
Run the focused interaction suite and require all seeded and hostile tests to pass.

- [ ] Step 5: Cross-check existing controller corpus
Run: python -m unittest LearnerAI/Compiler/tests/test_native_controller_semantics.py

- [ ] Step 6: Commit the passing deliverable
Commit: feat(compiler): seed native controller interaction corpus

### Task 3: Attach typed interaction metadata to known Strategic Number bindings

Files:
- Modify: LearnerAI/Compiler/semantic/native_controller_interactions.py
- Modify: LearnerAI/Compiler/semantic/strategic_number_semantics.py
- Test: LearnerAI/Compiler/tests/test_strategic_number_semantics.py
- Modify: LearnerAI/Compiler/semantic/__init__.py

Interfaces:
- Produces NativeControllerInteractionBinding with access_identifier, controller_id, interaction_id, relation, and status.
- Produces bind_strategic_number_interactions(bindings, interaction_catalog=None).
- Extends StrategicNumberSemanticReport with deterministic controller_interactions.

Known SN accesses gain interaction metadata only through existing controller bindings. Unknown SNs remain untouched. Interaction metadata never changes mutation evaluation, comparison evaluation, diagnostics, or emission.

- [ ] Step 1: Add failing integration assertions
Use rules containing sn-number-explore-groups, sn-number-attack-groups, sn-maximum-town-size, and one unmapped SN. Assert known controller bindings, relevant interaction IDs, and absence of fabricated interaction metadata for the unmapped SN.

- [ ] Step 2: Verify red
Run: python -m unittest LearnerAI/Compiler/tests/test_strategic_number_semantics.py

- [ ] Step 3: Implement the minimum hookup
Resolve interaction metadata by controller identity only. Do not re-parse SN semantics or add another source-order pass.

- [ ] Step 4: Verify focused green
Run the same Strategic Number suite.

- [ ] Step 5: Run interaction and recurrent suites
Run: python -m unittest LearnerAI/Compiler/tests/test_native_controller_interactions.py LearnerAI/Compiler/tests/test_recurrent_execution.py

- [ ] Step 6: Commit the passing deliverable
Commit: feat(compiler): bind Strategic Number accesses to controller interactions

### Task 4: Close the documentation boundary and stage the DUC SearchSession tranche

Files:
- Modify: LearnerAI/Compiler/NATIVE_CONTROLLER_SEMANTICS_CHECKLIST_2026-09-28.md
- Modify: LearnerAI/Compiler/NATIVE_PER_SEMANTIC_GAP_MAP_2026-09-26.md
- Modify: LearnerAI/Compiler/README.md
- Modify: LearnerAI/Compiler/COMMUNITY_PER_PRACTICE_SPEC.md
- Create: docs/plans/2026-09-28-duc-search-session-semantics.md

Documentation must distinguish controller ownership, interaction semantics, and executable native mappings. The gap map must record interaction coverage separately from controller corpus coverage.

- [ ] Step 1: Add documentation assertions where existing contract tests already exist. Do not create brittle markdown line-number tests.
- [ ] Step 2: Write the DUC SearchSession implementation plan covering search-index state, retained filters, local/remote list generations, focus-player/query/filter resets, zero-result facts, capacity widening, target establishment and invalidation, same-rule versus later-pass visibility, Goal output spans, recurrent firing gates, cardinality/performance evidence, target-session handoff, and hostile branch/join tests.
- [ ] Step 3: Update the semantic gap/checklist with status INTERACTION SUBSTRATE IMPLEMENTED / INTERACTION CORPUS PARTIAL.
- [ ] Step 4: Run focused suites, full compiler regression, native zero-findings acceptance, and all nine OS/Python determinism jobs through GitHub Actions.
- [ ] Step 5: Reconcile the plan against actual implementation and leave every remaining partial area explicitly marked.
- [ ] Step 6: Commit the passing deliverable
Commit: docs(compiler): close native controller interaction boundary

## Unresolved externally observable decisions

- Whether future interaction records should graduate from raw source URLs to mandatory CitationRecord IDs once the controller corpus becomes a promoted native semantic registry.
- Whether qualitative performance metadata should eventually become warning-level diagnostics or remain advisory.
- Whether controller endpoint version scopes should later be inherited automatically from native contract provenance or remain explicit on each interaction.