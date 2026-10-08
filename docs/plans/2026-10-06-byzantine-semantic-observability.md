# Byzantine Semantic Observability Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 1.05 MB Byzantine runtime artifact semantically inspectable by combining effective rules, persistent-state ownership, community/engine evidence, and runtime witness contracts without introducing a second scripting language.

**Architecture:** Reuse the existing SourceGraphResolver, EffectiveRule, FeatureTrace, and StrategyDependencyReport infrastructure. Add an artifact-centric semantic shadow manifest, an evidence ledger with explicit provenance classes, and a runtime-witness schema/scenario layer that references existing rule identities and lifecycle states.

**Tech Stack:** Python 3, immutable dataclasses, existing AoE2 .per parser/source graph, JSON, Markdown, unittest, GitHub Actions/native validator.

## Current implementation status

- [x] Task 1: artifact semantic shadow manifest.
- [x] Task 2: shared Goal/SN/Timer writer/reader ownership indexes.
- [x] Task 3: community/engine evidence ledger with conservative source-family provenance.
- [x] Task 4: runtime witness schema and adversarial scenario contracts.
- [x] Task 5: deterministic semantic-manifest CLI and CI publication.
- [ ] Task 6: live-runtime evidence capture. Infrastructure is implemented; gameplay traces remain OPEN until an actual match supplies observations.
- [x] Task 7: advisory community convergence and operation-cost diagnostics. Cost buckets remain non-blocking and are benchmark-derived.
- [x] Task 8: runtime-specific first-broken-edge assessment. It intentionally remains separate from compiler FeatureTrace so observed gameplay failures are not confused with compiler-stage failures.

Runtime promotion rule: no scenario may be marked CONFIRMED without a captured match record carrying the exact Byzantine.per SHA-256 and direct world-state evidence.

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

Status: COMPLETE on main.

**Files:** `LearnerAI/Compiler/semantic/semantic_manifest.py`, `LearnerAI/Compiler/semantic/__init__.py`, `LearnerAI/Compiler/tests/test_semantic_manifest.py`.

- [x] Focused contract added.
- [x] Effective source graph, annotations, Goal/SN/Timer state accesses, element counts, deterministic serialization, and artifact SHA-256 implemented.
- [x] Focused and full compiler verification passed.
- [x] Merged in commit `809bf110f9ce7c0956b0d233a1eb046f5ca262bf`.

### Task 2: Connect shared-state ownership to the semantic shadow

Status: COMPLETE on main.

The shared-state index was implemented in the semantic shadow itself and pinned against the checked-in artifact.

- [x] Goal/SN/Timer readers and writers indexed deterministically.
- [x] Shared `goal:opening-plan` ownership regression added.
- [x] Existing strategy-dependency/feature-trace machinery remains the causal analysis layer. The manifest does not invent precedence.
- [x] Covered by the full green compiler/native/determinism run merged with Task 1.

### Task 3: Add the community/engine evidence ledger

Status: COMPLETE on main.

**File:** `docs/research/2026-10-06-byzantine-community-cross-reference.md`.

- [x] Evidence classes kept separate.
- [x] Native limits, Goals/SNs/Timers, attack machinery, DUC cost, resource-camp controls, structured .per tooling, provenance lineage, and runtime-open boundaries documented.
- [x] Runtime priority order frozen around Arena Castle, resource camps, research continuity, attack release, siege conversion, and defensive geometry.

### Task 4: Formalize runtime witness contracts and adversarial scenarios

Status: COMPLETE on main.

**Files:** `docs/reference/runtime-witness.schema.json`, `docs/runtime/scenarios/*.json`, `LearnerAI/Compiler/tests/test_runtime_witness_schema.py`, `docs/runtime/README.md`.

- [x] Machine-readable witness schema added.
- [x] Arena, resource-camp, and attack/siege scenarios added as OPEN contracts.
- [x] Scenarios require exact artifact SHA-256 at runtime capture and distinguish expected claims from confirmed observations.
- [x] Compiler verification passed.

### Task 5: Add deterministic semantic-report generation to the release path

Status: COMPLETE on main.

**Files:** `tools/build_byzantine_semantic_manifest.py`, `.github/workflows/compiler-tests.yml`, semantic-manifest tests.

- [x] CLI added with explicit input and optional output.
- [x] CI generates the manifest twice and compares byte-for-byte.
- [x] Manifest includes exact artifact SHA-256.
- [x] Workflow archives semantic-manifest output with native evidence.
- [x] Full native/determinism gate passed.

### Task 6: Build the live-runtime evidence loop

Status: OPEN.

**Files:** `docs/runtime/README.md`, `docs/runtime/scenarios/`, future `docs/runtime/traces/`.

- [ ] Capture an Arena match on current main with exact bot/artifact SHA, pressure checkpoint, Castle admission/issuance, and Castle completion.
- [ ] Capture resource-camp placement and later distinct-gold reacquisition.
- [ ] Capture autonomous attack, release/relaunch, siege conversion, and exposed-resource avoidance.
- [ ] Promote scenario status from OPEN only on direct runtime evidence.

This task cannot be honestly closed by compiler CI. It requires actual DE runtime observations.

### Task 7: Add community-corpus convergence and performance diagnostics

Status: COMPLETE on main.

**Files:** `LearnerAI/Compiler/semantic/community_engine.py`, `LearnerAI/Compiler/semantic/semantic_manifest.py`, focused diagnostics tests.

- [x] Evidence source families classified conservatively.
- [x] Community convergence reports source-family breadth without treating it as engine proof.
- [x] Advisory LOW/MODERATE/HIGH native operation-cost classes added.
- [x] Semantic manifest exposes operation counts and high-cost recurrent rules.
- [x] PR #463 merged as `6ab4561a519e09ce75184af144b0ffc7c83e424b`.
- [x] Post-merge `main` run #4987 is fully green: compiler/native, nine determinism jobs, snapshot comparison, and verification gate.

### Task 8: Runtime-informed first-broken-edge diagnostics

Status: IMPLEMENTATION IN PR #465; verification pending.

**Files:** `LearnerAI/Compiler/semantic/runtime_diagnostics.py`, `LearnerAI/Compiler/tests/test_runtime_diagnostics.py`, semantic exports.

- [x] Rejected runtime claims map only when their rule identities resolve through the semantic manifest to a FeatureTrace carrying an already-broken edge.
- [x] Claims with no broken compiler edge remain `RUNTIME_EDGE_OPEN`; unresolved rule identity remains `UNKNOWN`.
- [x] Focused tests added.
- [ ] Fresh CI run for PR #465 passes.
- [ ] Merge to main.
- [ ] Verify live runtime evidence can consume the mapper.

