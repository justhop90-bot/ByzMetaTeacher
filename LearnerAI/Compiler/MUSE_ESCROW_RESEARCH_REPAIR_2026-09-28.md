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


## 5A. R2 closure — exact escrow affordability formula

R2 is now closed for the resource-availability component of the classic escrow-aware command family.

Let, for one resource (r):

- (T_r) = the engine's ordinary resource amount reported by `<resource>-amount`.
- (E_r) = `escrow-amount r`.
- (N_r = T_r - E_r) = the amount available to an escrow-deducted command.
- (C_r(a)) = the amount of resource (r) required by action (a).

The checked-in UserPatch semantics explicitly distinguish two command resource views. An escrow-deducted command sees (T_r - E_r). An escrow-included command sees (T_r). The documented example is (T_mathrm{food}=90), (E_mathrm{food}=50): ordinary training sees 40 food while the with-escrow variant sees 90. urlUserPatch escrow-state semanticshttps://airef.github.io/tables/up-patch-notes.html

Therefore the resource component of the affordability gate is:

[
G^-_r(a) iff T_r - E_r ge C_r(a)
]

for ordinary / escrow-deducted execution, and

[
G^+_r(a) iff T_r ge C_r(a)
]

for with-escrow execution.

Across the four resource types:

[
G^-(a) iff igwedge_{rin{food,wood,stone,gold}} (T_r-E_r ge C_r(a))
]

[
G^+(a) iff igwedge_{rin{food,wood,stone,gold}} (T_r ge C_r(a))
]

The complete native `can-*` fact is:

[
CAN^pm(a) = PRE(a) land G^pm(a)
]

where (PRE(a)) is the command-family-specific non-resource admission set. For example, the documented `can-build-with-escrow` fact still requires civilization availability and tech-tree prerequisites, and explicitly does not establish builder availability or building placement space; the training equivalent also checks housing and a ready, non-busy training building. urlAIRef command indexhttps://airef.github.io/commands/commands-index.html urlCPSB can-train-with-escrow semanticshttps://www.userpatch.aiscripters.net/CPSB.pdf

This closes the affordability ambiguity without claiming that every command family has identical non-resource prerequisites.

### Executable invariants derived from R2

**ESC-001 — Exact resource-view equivalence.** For every supported resource (r), escrow inclusion changes only the resource view used by the native command: included uses (T_r); deducted uses (T_r-E_r). The compiler must not invent a percentage multiplier, reserve deduction, or alternative affordability formula.

**ESC-002 — Component-wise cost admission.** A with-escrow affordability proof is valid only when every non-zero resource component of the action cost satisfies (T_r ge C_r(a)). A normal affordability proof uses (T_r-E_r ge C_r(a)).

**ESC-003 — Non-resource predicates remain native.** Availability, tech prerequisites, housing, provider/building readiness, placement constraints, and other command-specific predicates remain owned by the native `can-*` fact. The compiler must not reconstruct them from static GameData merely to simulate escrow.

**ESC-004 — Feasibility facts are read-only.** `can-*-with-escrow` is a Fact. Evaluating it does not reserve escrow, release escrow, or mutate resource state.

**ESC-005 — Escrow state and action mode must agree.** A `can-*-with-escrow` proof authorizes only an escrow-included execution path. The classic `build`, `train`, and `research` actions are escrow-deducted. Therefore the current compiler cannot safely emit `can-research-with-escrow -> research` while the required resources remain in escrow. The admissible patterns are: release the relevant escrow before the ordinary action, or lower to an explicit UP action whose EscrowState is `escrow-included`. The UserPatch contract defines `escrow-included=0` and `escrow-deducted=1` and shows that the matching UP action observes the corresponding resource view. urlUserPatch EscrowState contracthttps://airef.github.io/tables/up-patch-notes.html

**ESC-006 — Release is total for the named resource.** `release-escrow r` sets that resource's escrow amount to zero and transfers the escrowed amount back into the normal stockpile. It is not a partial claim release. urlAIRef command indexhttps://airef.github.io/commands/commands-index.html

**ESC-007 — Percentage range is closed.** `set-escrow-percentage r p` accepts (0le ple100). This is a controller setting, not the affordability formula itself. urlCPSB set-escrow-percentage semanticshttps://www.userpatch.aiscripters.net/CPSB.pdf

**ESC-008 — Do not assume a synchronous clamp.** The UserPatch note states that if escrow exceeds current resource amount, the runtime corrects that condition on the next resource drop. Consequently the compiler must not impose an artificial invariant (E_rle T_r) at every instantaneous read. The safe compiler contract is the documented resource-view equations above, with native runtime state remaining authoritative. urlUserPatch escrow-state semanticshttps://airef.github.io/tables/up-patch-notes.html

**ESC-009 — No escrow reservation semantics.** Passing `can-*-with-escrow` proves admissibility against the current native resource view; it does not reserve those resources for the demand. Any persistent protection policy is a separate escrow mutation contract.

**ESC-010 — Formula applies before cost transformation.** Civilization discounts, technology-specific costs, and other engine cost effects remain part of native (C_r(a)). The escrow layer only selects the resource view against which the native cost is tested.

### Boundary now closed vs. still open

Closed:
- the exact resource-view equation for escrow-deducted versus escrow-included commands;
- the component-wise affordability inequality;
- the fact that `can-*-with-escrow` retains ordinary non-resource admission predicates;
- the requirement that affordability mode match action consumption mode;
- total named-resource release semantics;
- percentage range.

Still OPEN:
- exact same-pass visibility/order when a rule mutates escrow and then evaluates or consumes it;
- whether the compiler's ordinary `research` action may rely on same-rule `release-escrow` visibility as a formally verified engine contract or must use a later-pass handoff;
- persistent claim ownership/lifetime;
- starvation/emergency override semantics;
- whether the DE implementation introduces any family-specific cost exceptions beyond the documented resource-view rule.

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
