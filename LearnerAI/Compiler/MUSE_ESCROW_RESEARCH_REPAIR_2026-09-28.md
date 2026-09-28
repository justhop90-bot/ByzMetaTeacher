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


## 5B. R3/R4 closure — mutation ordering, ownership, and lifetime

### Mutation ordering

The native escrow state has three distinct mutation classes. They must not be collapsed into one "escrow claim" operation.

1. **Accrual-policy mutation** — `set-escrow-percentage(resource, p)`.
   This changes the percentage of future resource income routed into escrow. It does not, by itself, release the escrow balance already accumulated. Community guidance explicitly uses `release-escrow` and then `set-escrow-percentage ... 0` when both the existing reserve and future accrual policy must be cleared. citeturn169190search0turn449732search44

2. **Balance mutation** — `release-escrow(resource)`.
   This immediately transfers the named resource's escrowed amount back into the normal resource stockpile and sets that escrow amount to zero. The native command index defines it as a state-changing Action, not a Fact. citeturn449732search1

3. **Escrow-consuming action** — ordinary `build/train/research` consumes the normal view; an UP action with `escrow-included` consumes the combined view. UserPatch's explicit example shows the resource view switching from (T-E) to (T) when the escrow state is changed. citeturn834084search0

**Executable ordering invariant ESC-011:** within one emitted rule, escrow mutations are ordered left-to-right and later actions may rely on earlier mutations in that same action sequence. The compiler's safe canonical sequence for ordinary commands is therefore:

`release-escrow(r*) -> set-escrow-percentage(r*, 0) -> ordinary action`

when the intent is both "make the currently escrowed balance spendable" and "stop future accumulation."

There is strong independent community evidence for exactly this sequence. The Duke builder library, AI Script corpora, and AoE2 scripting examples routinely place `release-escrow` immediately before `research`; this is not an accidental formatting convention. citeturn834084search2turn115112search0turn115112search3

**Executable ordering invariant ESC-012:** `set-escrow-percentage(r, 0)` alone is not a release operation. A compiler must never treat percentage-zero as escrow-balance-zero. Existing scripts explicitly perform both operations when they intend both effects. citeturn169190search0turn169190search1

**Executable ordering invariant ESC-013:** a `can-*-with-escrow` Fact must be evaluated before the rule's resource mutations are relied upon unless the compiler has an engine-proven same-rule re-evaluation model. Conditions are matched against the pre-fire state; the mutation sequence is the action-side execution contract. Therefore the canonical research pattern is:

`can-research-with-escrow(T) -> release required escrow -> research(T)`

not a post-release re-check hidden in the same action block.

**Executable ordering invariant ESC-014:** a release occurring in an earlier rule is persistent into later rule passes because escrow is engine-managed player state. A later rule may consume the released normal stockpile subject to the ordinary `can-*` predicate. Rule order therefore creates a real economic dependency and is not merely source-order decoration. The forensic corpus explicitly records that earlier resource actions can leave later rules unable to spend the same resources; there is no proven universal fairness scheduler. citeturn449732search3

### Ownership

The native engine does **not** expose per-demand escrow ownership. Escrow is a per-player, per-resource balance/policy surface. Historical community scripts therefore layer purpose/ownership in ordinary persistent state, for example an `escrow-purpose-goal`, alongside the native escrow balance. citeturn449732search3turn558675search0

This gives the compiler a strict separation:

- **Native owner:** none. The engine owns the actual resource/escrow stockpiles.
- **Semantic owner:** exactly one compiler demand/strategic identity for each active escrow protection contract.
- **Execution claimant:** the action that is authorized to consume that protection.
- **Transient arbitration owner:** optional and distinct from escrow ownership. The existing build-pass arbitration model must not be reused as if it were escrow ownership.

**Executable invariant ESC-015:** one escrow contract must have exactly one semantic owner. Two demands must not independently mutate the same resource's escrow policy or release the same protected balance unless an explicit arbitration/ownership handoff contract exists.

**ESC-016:** ownership is attached to the *purpose of protection*, not to the percentage value. Percentage 0 does not mean "unowned"; it means "stop routing new income into escrow." Existing escrow can still belong to the active protection contract.

**ESC-017:** shared resources are a conflict surface. If demand A protects food/gold for a research package and demand B independently attempts to release or repurpose those same escrow balances, the compiler must diagnose the ownership conflict rather than silently merge the demands.

**ESC-018:** escrow ownership cannot be inferred from resource amount alone. A positive escrow balance proves stored resources exist, not which strategic demand is entitled to consume or release them.

### Lifetime

The lifetime model is therefore two-dimensional:

**Policy lifetime**
`set-escrow-percentage(r,p)` establishes or changes the future-accrual policy for resource (r). The policy remains active until another percentage mutation changes it.

**Balance lifetime**
Escrow balance for (r) exists independently of the percentage policy. It terminates when the engine consumes it through an escrow-included action, or when `release-escrow(r)` transfers it to the normal stockpile. UserPatch also documents the special runtime correction where escrow can temporarily exceed current resource amount and is corrected on the next resource drop, so balance arithmetic itself must remain engine-owned. citeturn834084search0turn449732search0

This yields the following semantic lifetime:

`UNOWNED -> PROTECTED -> CONSUMING/RELEASING -> RELEASED`

with an important side channel:

`PROTECTED --set-percentage(0)--> PROTECTED`

because percentage zero changes the accrual policy but does not release the current balance.

**Executable invariant ESC-019:** protection cannot be cleared by changing the percentage alone.

**ESC-020:** normal completion of the protected action does not automatically prove that all escrow state is released. The compiler needs an explicit release/consumption contract for every resource in the escrow contract.

**ESC-021:** an escrow contract may end by **consumption** or **release**, but those are semantically different terminal paths:
- consumption means the protected resources were actually spent by an escrow-authorized action;
- release means the protection was cancelled/relaxed and the resources became ordinary stockpile again.

**ESC-022:** after terminal release/consumption, the semantic owner must relinquish the contract. Re-entry requires a new explicit acquisition decision, not an implicit continuation of stale ownership.

**ESC-023:** starvation/emergency release is preemption of an active protection contract, not ordinary completion. The protected strategic demand survives unless it is separately invalidated. Reassertion, if desired, occurs on a later admissible pass.

### Canonical research-state machine

For the first executable research slice, the compiler should model:

`UNPROTECTED`
-> **ACQUIRE**: set escrow policy / establish owner
-> `PROTECTED`
-> **ADMISSIBLE**: `can-research-with-escrow`
-> **RELEASE**: release required escrow
-> **ISSUE**: ordinary `research`
-> `PENDING`
-> **COMPLETE**: `research-completed`
-> **RELEASED**: semantic ownership ends.

The critical point is that RELEASE occurs before ISSUE for an ordinary `research` action. The community evidence independently demonstrates this sequence across multiple script families, while UserPatch supplies the underlying resource-view semantics. citeturn115112search0turn115112search1turn115112search47turn834084search0

The compiler must not emit a hidden "release when complete" operation merely because the research demand has completed. The resources were already made spendable before research issuance; any subsequent escrow policy is a separate state decision.

### What is now closed

Closed with strong evidence:
- accrual policy and escrow balance are separate state dimensions;
- percentage zero is not release;
- release-escrow zeroes the named escrow balance;
- community executable practice consistently releases required escrow before ordinary research/build/train commands;
- escrow ownership is not a native engine field and must be compiler-owned semantic state;
- ownership must not be conflated with transient action arbitration;
- a protection contract ends through explicit consumption or release;
- starvation release is preemption/recovery, not successful completion.

Still OPEN:
- whether DE guarantees same-pass visibility of a release to a subsequent ordinary action as a formal engine contract, rather than merely the strongly corroborated community idiom;
- exact cost/provider behavior for each escrow-aware action family beyond the resource-view contract already closed;
- formal native proof for starvation/emergency preemption semantics;
- multi-demand escrow handoff rules.

### Required closure fixture

Before promoting the first executable escrow slice, add a source-to-`.per` fixture that distinguishes all three cases:

1. `set-escrow-percentage 100 -> research` without release: must be rejected or blocked by feasibility semantics.
2. `release-escrow -> research`: must emit in that order.
3. `release-escrow -> set-escrow-percentage 0 -> research`: must emit in that order and prove that the policy reset is distinct from the balance release.

A separate negative fixture must prove that two semantic demands cannot both own and mutate the same resource escrow contract without an explicit handoff.

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
