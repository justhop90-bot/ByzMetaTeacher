# Policy Diagnostic Causal Graph

Date: 2026-10-01

## Scope

This tranche adds the internal causal graph used by the policy-diagnostic validator. It does not introduce source syntax, a scheduler, a second policy language, or new game semantics.

User-facing policy diagnostics remain `POL-*`. Compiler-internal causal-graph invariant failures are `PCG-*`.

## Implementation checklist

- [x] Stable typed `PolicyDiagnosticKey` and semantic subject.
- [x] Typed causal relations: prerequisite, invalidation, contradiction, supersession, derivation.
- [x] Explicit validation phases and diagnostic precedence tables.
- [x] Directional convention: cause -> dependent.
- [x] Canonical storage for symmetric contradiction edges.
- [x] Immutable edge keys and witness metadata.
- [x] Fourteen stable `PCG-*` invariant codes with concrete Python exception subclasses.
- [x] Endpoint, self-edge, duplicate-edge, phase, subject, priority, witness, and cycle validation.
- [x] Suppression records require an actual causal edge.
- [x] Root-cause selection ignores contradiction edges as suppression edges.
- [x] Root selection is deterministic and follows explicit relation/phase/priority ordering.
- [x] Focused regression coverage for all implemented graph invariants.
- [x] Public semantic-package exports added.
- [ ] Wire PolicyRecipe resolution into the graph after a concrete PolicyRecipe IR exists. No such implementation existed on main at tranche start.
- [ ] Add end-to-end compiler report serialization once policy diagnostics themselves consume the graph.

## Cross-reference: existing compiler contracts

The graph follows the repository's existing semantic conventions:

- `LearnerAI/Compiler/diagnostics.py`: stable severity and semantic-diagnostic normalization.
- `LearnerAI/Compiler/semantic/persistent_state.py`: typed diagnostic enums, immutable records, deterministic analysis, and explicit source-order semantics.
- `LearnerAI/Compiler/semantic/operational_semantics.py`: typed validation status and stable diagnostic codes.
- `LearnerAI/Compiler/semantic/community_engine.py`: evidence classes and the rule that community practice does not silently become engine truth.
- `COMMUNITY_PER_PRACTICE_SPEC.md`: community-derived practices remain evidence-backed policy unless native/compiler support is actually established.

## Cross-reference: AoE2 community control semantics

The causal graph intentionally does not promote the following community idioms to engine facts. They are useful policy subjects that must remain provenance-aware.

### Stance, patrol, guard, follow

Community/native references distinguish literal unit relationships from posture:

- AIRef documents native action/stance controls and `sn-enable-patrol-attack`.
- AoE2 community discussion commonly uses Defensive + Patrol for local/mobile defense and Stand Ground for ranged formations.
- Community use of Guard is target-bound protection and Follow is target-bound movement/support.
- The compiler therefore keeps STANCE, RELATIONSHIP, and attack-transit retarget policy separate.

Primary references:

- https://airef.github.io/
- https://airef.github.io/tables/up-patch-notes.html
- https://forums.ageofempires.com/t/defensive-stance-is-useless/169389
- https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476
- https://github.com/SiegeEngineers/WololoKingdoms

The exact behavior of a community recipe remains distinct from an engine guarantee. In particular, literal `action-patrol` and `sn-enable-patrol-attack` are different mechanisms: the former is a native execution relationship; the latter is an attack-transit retargeting control.

## Causal graph invariants

Directed relations form a DAG:

`PREREQUISITE`, `INVALIDATES`, `SUPERSEDES`, `DERIVES`.

`CONTRADICTS` is symmetric semantically and is stored only in canonical endpoint order.

For directed causal edges:

`source.phase <= target.phase`

and the subjects must overlap.

For `SUPERSEDES`:

`source.priority < target.priority`

and both diagnostics must concern the same primary policy field.

For `PREREQUISITE` and `INVALIDATES`, the source must be an error.

Every edge must carry a witness matching the source diagnostic subject.

A suppression is valid only when:

1. the suppressed diagnostic exists;
2. the root diagnostic exists and is the canonical selected root;
3. the referenced causal edge exists;
4. the edge source equals the root;
5. the edge target equals the suppressed diagnostic.

## Failure boundary

`POL-*` means the requested policy is invalid, contradictory, unsupported, or otherwise not executable.

`PCG-*` means the compiler constructed an invalid causal explanation graph.

A `PCG-*` failure is an internal compiler invariant failure and must not be downgraded to a user-policy warning.
