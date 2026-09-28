# MUSE Escrow / Resource-Control Research Repair — 2026-09-28

Research basis: the checked-in MUSE forensic package and current compiler main after PR #90.
Implementation base: `2e104374bb543d900be8406b7854f465097701cb`.
Research is deliberately separated from executable promotion: unresolved native semantics remain OPEN rather than being converted into compiler policy.

## 1. Why this is the next repair

MUSE identifies escrow/resource control as the largest remaining compiler undercoverage family: 10.9k corpus hits, with the current compiler limited to escrow-aware feasibility facts and the transient build-pass arbitration layer.

Repository evidence:
- `compiler_undercoverage.md`: escrow has 10.9k hits and explicitly identifies escrow operation lowering as justified by the corpus.
- `compiler_coverage_baseline.md`: current state is evidence-only plus build singleton; remaining work is escrow-claim lowering, gating formula, and starvation/override behavior.
- `E-compiler_gap_matrix.md`: corpus evidence is strong, but runtime timing proof, claim/release lowering, gating formula, and starvation/emergency semantics remain incomplete.
- `native_unknowns.md`: exact escrow gating formula and release-vs-admission order remain OPEN.
- `MUSE_NEXT_IMPLEMENTATION_CHECKLIST_2026-09-28.md`: Tier 1 places escrow/resource-control executable lowering before DUC and attack lifecycle work.

## 2. Native facts that are already strong enough to preserve

The repository's checked-in engine references establish ordinary escrow operations and their basic storage semantics:

- `set-escrow-percentage <Resource> <Value>` changes the percentage of a resource routed into escrow.
- `release-escrow <Resource>` moves that resource's escrow stockpile back into the normal stockpile.
- Escrowed resources are not freely consumable by ordinary commands; escrow-aware execution paths explicitly opt into escrow through the native command contract.
- The compiler already has escrow-aware feasibility facts:
  - `can-build-with-escrow`
  - `can-train-with-escrow`
  - `can-research-with-escrow`
- The native controller catalog already identifies `resource-escrow-control`, but intentionally marks its controller/surfaces EVIDENCE_ONLY.

These facts justify typed native contracts. They do not yet justify arbitrary executable resource-control policy.

## 3. Community evidence and confidence split

Strong candidate:
- IDIOM-007: escrow-gated age advance, independently present in Promisory and Duke-style material; uses escrow-aware feasibility plus escrow percentage controls.
- IDIOM-024: escrow-protected research reassertion, useful as a lifecycle/resource interaction fixture.

Secondary candidate:
- IDIOM-026: starvation emergency release. The pattern is useful for recovery testing, but its exact local source evidence must remain attached before promotion.

Do not use as initial executable authority:
- IDIOM-008 commodity/market balancing. The repository itself marks it PARTIAL/NO for compiler support and calls out weak or historical corroboration. It is a research reference, not a native semantic contract.

## 4. Current implementation state after PR #90

PR #90 added typed resource-control IR in `LearnerAI/Compiler/ir/resource_control.py` and validation in `LearnerAI/Compiler/semantic/resource_control.py`.

Those additions currently describe:
- persistent native arbitration;
- escrow admission/reserve/release/consumption;
- transient action-exclusion claims.

The important audit result is that this layer is not yet the executable lowering path. It is not wired into the main compiler pipeline, analyzer, or emitter. That is correct for the current state, because the exact engine gating/release semantics are still OPEN.

Therefore the next repair must not simply turn these dataclasses into emitted `.per` commands. Doing that now would convert research assumptions into fake engine truth.

## 5. Exact research questions that must close before executable promotion

### R1 — Native command typing
Prove exact parameter domains for:
- `set-escrow-percentage`
- `release-escrow`
- `up-modify-escrow`
- `up-release-escrow`

The compiler must distinguish Resource constants from values/amounts and reject wrong-domain operands before emission.

### R2 — Admission formula
Determine exactly what `can-*-with-escrow` means for each supported action family:
- which stockpiles are consulted;
- whether the predicate requires the complete cost in escrow, normal stockpile, or their admissible union;
- whether command-side escrow authorization is separate from affordability;
- whether behavior differs among build/train/research.

Until R2 closes, the compiler must not infer its own affordability/escrow formula.

### R3 — Mutation ordering
Establish the native rule-pass contract for:
1. escrow percentage mutation;
2. escrow-aware feasibility;
3. action issuance;
4. release to normal stockpile.

The acceptance test must prove which mutations are visible later in the same rule and which require a later pass.

### R4 — Ownership and lifetime
Define whether an escrow claim is:
- persistent demand state,
- transient admission state,
- or native resource state with a compiler-owned semantic owner layered above it.

The desired model must not become a scheduler. A claim exists to protect a specific strategic/execution demand and must have a deterministic release or consumption witness.

### R5 — Starvation / emergency override
Treat starvation release as a recovery path, not normal admission. Prove:
- trigger class;
- ownership preemption semantics;
- whether release is immediate;
- whether the protected demand survives;
- whether normal escrow protection can be reasserted on a later pass.

## 6. Proposed first executable slice

Do not begin with commodity balancing.

The first executable slice should be a protected research demand because the repository already has:
- typed research lifecycle;
- `can-research-with-escrow`;
- research completion world-state witnesses;
- release-state semantics;
- community evidence for escrow-protected research.

Required source-to-`.per` slice:
`escrow admission -> native research feasibility -> research issuance -> research completion witness -> escrow release/reassert policy`.

The slice is accepted only when the emitted artifact, not a synthetic semantic fixture, is passed through the native zero-findings gate.

## 7. File-level implementation boundary

Primary modules:
- `LearnerAI/Compiler/primitives/registry.py`: native escrow command adapters and parameter arity.
- `LearnerAI/Compiler/primitives/native_hygiene.py`: escrow storage/parameter contract provenance.
- `LearnerAI/Compiler/primitives/engine_semantics.py`: native escrow state/mutation visibility.
- `LearnerAI/Compiler/semantic/native_controller.py`: promote only proven resource-escrow control surfaces.
- `LearnerAI/Compiler/semantic/resource_conflicts.py`: retain transient arbitration; do not conflate it with escrow ownership.
- `LearnerAI/Compiler/ir/resource_control.py`: bind typed escrow contracts once R1-R5 are closed.
- `LearnerAI/Compiler/semantic/analyzer.py`: bridge explicit escrow intent into typed contracts.
- `LearnerAI/Compiler/emitter/per.py`: emit only contracts whose native semantics are closed.

Verification:
- `test_resource_conflicts.py`
- `test_native_controller_semantics.py`
- `test_native_controller_interactions.py`
- new escrow contract/lifecycle tests
- checked-in `fixture-escrow-age-up`
- later `fixture-research-reassert`
- native zero-findings acceptance and generic fixture reproducibility.

## 8. Promotion gate

No escrow command becomes EXECUTABLE_SAFE merely because the AIRef parser accepts its syntax.

Required progression:

`NATIVE_KNOWN -> NATIVE_TYPED -> SEMANTICALLY_ADAPTED -> ENGINE_SEMANTICS_MAPPED -> EXECUTABLE_SAFE`

Promotion additionally requires:
- source-to-emitted-artifact coverage;
- native zero findings;
- deterministic output;
- same-pass/recurrent execution proof;
- explicit open-unknown handling;
- hostile competing-owner and release/reassertion tests.

## 9. Current status

Escrow is now the active MUSE repair branch.

Closed:
- native command existence and basic syntax for the core escrow controls;
- typed resource-control IR surface;
- separation between transient arbitration and escrow semantics;
- corpus justification for implementation.

Open:
- exact gating formula;
- mutation ordering;
- escrow ownership/lifetime;
- starvation/emergency semantics;
- executable lowering.

The compiler will not promote those unknowns by optimism. Humans have already produced enough software that confidently emitting a wrong financial state machine is no longer an acceptable innovation.
