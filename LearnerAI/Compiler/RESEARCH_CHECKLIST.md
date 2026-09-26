# Current Compiler Frontier (2026-09-26)

The compiler is a general AoE2 .per engineering platform. Basilisk and Byzantine strategy are downstream clients.

The authoritative current roadmap is `COMPILER_FORENSIC_AUDIT_2026-09-26.md` plus `COMMUNITY_PER_PRACTICE_SPEC.md`.

Priority order:
1. P0: native correctness, support-state visibility, storage/package reproducibility, diagnostics.
2. P1: non-lifecycle state ordering, capability-loss recovery, DUC/search safety, load/preprocessor graph.
3. P2: community-practice registry, golden fixtures, generic reference bot.
4. P3: evidence-backed performance analysis.
5. P4: experimental coordination/spatial patterns.

Important same-pass rule: actions inside one .per rule execute sequentially. A latch or persisted state is required when the dependency crosses rules/passes, not when actions are already in the same action list.

Historical implementation sections below are retained as records. Their old Basilisk-specific exit criteria are no longer the compiler completion definition.

---
# LearnerAI Compiler Research Checklist

This checklist keeps compiler work subordinate to the actual Byzantine player.

## Already established

### Native .per ecosystem

The community already provides a capable native parser/linter. The pinned aoe2-ai-parser backend is the native authority.

Do not build a replacement native parser, native formatter, native command inventory, native logical-arity checker, native rule-length checker, or package graph validator unless a specific teaching need cannot be handled at the boundary.

### LearnerAI contribution

The semantic contribution is different:

    persistent intent
      -> demand
      -> capability
      -> feasibility
      -> action
      -> pending
      -> world-state witness
      -> release / invalidation
      -> reassess

## Deep cross-check and implementation record (2026-09-26)

This pass was explicitly adversarial: the compiler contracts were checked against the live
Basilisk controller, the checked-in AIRef command schema, current AIRef engine limits,
native/community .per examples, and the CI test runner.

### Evidence established

- AIRef documents 10,000 rules, 32 DE elements per rule, and 255 characters per source line. Nested logical operators count as rule elements and have exact operand counts. citeturn347585search1turn347585search0
- Community .per examples use explicit goals, pending-object facts, can-build/can-* feasibility checks, and direct build actions rather than an opaque manager layer. citeturn347585search2turn347585search4turn347585search5
- The checked-in repository AIRef schema is the compiler's native command-signature authority; semantic adapters remain a smaller Basilisk-owned layer.
- The current Basilisk package already owns a large numeric Goal namespace, so a compiler-local base Goal guess is not a package-level contract.
- The native runtime therefore remains responsible for raw .per legality, while the compiler adds typed semantics that native parsing cannot infer.

### Implemented in this pass

- [x] recursive logical-operator arity validation;
- [x] explicit single-native-command action roots;
- [x] native command arity sourced from the checked-in AIRef schema;
- [x] explicit rejection of native commands without a Basilisk semantic adapter;
- [x] stable reservation of existing runtime bindings;
- [x] duplicate existing-binding detection;
- [x] persistent binding-manifest data model with deterministic JSON round trip;
- [x] compiler-side rule, element, and line-length budgets;
- [x] one-shot initialization chunking under the 32-element DE limit;
- [x] per-pass build arbitration for the native one-build-per-pass constraint;
- [x] regression tests for each hardening edge;
- [x] CI-driven repair of serializer, nested-arity, and initialization lifecycle defects found during implementation.

### GitHub prior-art cross-check (2026-09-26)

The public prior art was compared directly against the current Basilisk compiler:

- `01010100b/AgeScript`: adopt the typed Compilation -> Assembly -> Script separation, explicit intermediate instructions, Goal-backed memory discipline, deterministic lowering, and hard rule-budget enforcement. Do not copy its general-purpose programming language model.
- `JOTworks/AgeOfPython`: adopt AIRef-derived native metadata, explicit parameter typing, compiler-owned Goal memory allocation, and strong separation between source variables and native storage. Do not copy its Python-like frontend or opaque memory conventions.
- `lewisc64/aoe2ai`: adopt named Goal allocation, explicit volatile Goal/Point lifetimes, staged persistent state as a semantic concept, and rule-budget-aware lowering. Do not add its generalized strategy DSL constructs until Basilisk semantics require them.
- `mboop127/AlphaScripter`: retain structured .per representation and game-facing validation ideas as reference only; its genetic optimization model is outside the Basilisk compiler boundary.
- `teshiba/LibAoe2AISharp`: treat programmatic command construction as precedent for typed native wrappers, but keep AIRef as the command authority.

Adoption rule: steal proven storage, IR, lowering, and validation mechanisms; do not steal architecture that turns Basilisk into a generic programming language or universal strategy scheduler.

### Prior-art reuse tranche implemented / in progress

- [x] prior-art decisions recorded in `docs/plans/2026-09-26-basilisk-prior-art-reuse.md`;
- [ ] explicit GoalSpan request/allocation and interval occupancy;
- [ ] deterministic volatile Goal scratch pool;
- [ ] optional end-to-end binding-manifest artifact;
- [x] native GoalSpan storage contracts derived from the checked-in AIRef command schema;
- [x] native storage contract catalog explicitly distinguishes contiguous Goal spans from multiple independent Goal outputs;
- [x] typed capability-provider/dependency semantics implemented and connected to the compile gate;
- [x] current demand language projected into the capability graph without adding source syntax.

### Still required before full-player compilation

- [x] command-specific GoalSpan allocation from native storage contracts;
- [ ] StrategicNumberSlot and TimerSlot allocation;
- [x] explicit Goal occupancy ranges/intervals consumed by the binder when supplied as package inventory;
- [x] automatic binding-manifest write-back as an end-to-end compiler artifact;
- [x] typed capability-provider graph plus provider-contract and admissibility validation passes;
- [x] compiler pipeline projects current SemanticDemand IR into the capability graph before binding/emission;
- [x] demand ownership and lifecycle first-writer/first-consumer analysis is integrated before capability projection;
- [x] actionable projected providers require a native FEASIBILITY predicate while preserving observation/timing semantics;
- [x] demand ownership and writer/consumer contracts;
- [x] prerequisite dependency graph, deterministic SCC cycle detection, and dead-end diagnostics;
- [x] resource/conflict semantics for the current transient action-exclusion arbitration layer;
- [x] first-writer/first-consumer analysis for lifecycle state with emitter-aligned source order;
- [ ] action-issuance failure versus pending-state distinction;
- [ ] Castle vertical slice compiled against actual Basilisk semantics.

## Implemented compiler foundation

- [x] semantic primitive profile;
- [x] lifecycle validation;
- [x] repeated-action prevention;
- [x] pending-state diagnostics;
- [x] negative lifecycle tests;
- [x] native backend subprocess boundary;
- [x] pinned backend identity;
- [x] protocol validation;
- [x] staged artifact validation;
- [x] deterministic diagnostics;
- [x] combined semantic/native report;
- [x] compiler/native integration tests.

## Next compiler work, ordered by player need

### 1. Freeze native tooling

- [ ] reproducible backend installation;
- [ ] manifest verification;
- [ ] archive/source checksum;
- [ ] golden protocol contract;
- [ ] no automatic backend upgrades.

### 2. Demand ownership

Implemented for the current lifecycle demand layer:

- [x] typed DemandOwnership contract attached to SemanticDemand;
- [x] typed StateAccess records for lifecycle reads and writes;
- [x] deterministic first-writer/first-consumer boundaries aligned with emitter rule order;
- [x] missing owner diagnostics;
- [x] lifecycle ownership/state mismatch diagnostics;
- [x] conflicting writer-owner diagnostics;
- [x] duplicate writer-phase diagnostics;
- [x] consumer-before-writer diagnostics;
- [x] unconsumed lifecycle-state diagnostics;
- [x] compiler-gate integration before capability validation and emission.

Current source semantics intentionally derive the owner from the demand identity. A separate Strategy/Construction/Economy owner declaration remains future semantic work and does not justify new source syntax yet.

### 3. Capability providers

Add semantic representation for:

- construction providers;
- production providers;
- research providers;
- economic capability;
- military capability.

The compiler must be able to answer:

What can satisfy this demand?

### 4. Player dependency chains

Model the chain needed for the first vertical slice:

    Castle intent
      -> Castle demand
      -> prerequisite capability
      -> resource protection
      -> construction feasibility
      -> action
      -> Castle witness
      -> Castle economy
      -> production expansion
      -> reassessment

The goal is not a universal planner.

The goal is semantic visibility of the actual player chain.

### 5. Recovery and invalidation

Add diagnostics for:

- temporary failure that incorrectly destroys intent;
- stale demand after strategic invalidation;
- capability loss with unreleased execution state;
- failed action without re-openable demand;
- recovery that cannot return to the original strategic path.

### 6. Resource and conflict semantics

Teach the compiler enough to identify when:

- two demands legitimately compete;
- a claim is required;
- a global resource lock is unjustified;
- a resource owner never releases;
- a lower-priority execution path can starve a strategic demand.

Do not turn this into a universal scheduler.

### 7. Source-order analysis

Where Basilisk-style rule order is deliberate, the compiler should eventually identify:

- first writer;
- first consumer;
- reset-then-recompute chains;
- same-pass visibility assumptions;
- later overwrites;
- unreachable or preempted rules.

### 8. Timing and map-conditioned evidence

The player now has concrete Arabia timing windows and reactions. Compiler responsibility is deliberately limited to semantic guardrails:

- timing primitives are typed as interpretation evidence;
- timing-only action demands are rejected;
- timing cannot prove completion;
- timing-only release is rejected.

Numeric Arabia thresholds remain Strategy tuning data. Do not hard-code the map profile into the compiler.

For positional tower/wall semantics, only engine-native observations should be admitted. Builder count is currently an execution/runtime concern; do not fabricate a compiler primitive for it until a sourced native fact exists.

### 9. Domain-aware teaching diagnostics

Diagnostics should use the player vocabulary:

DEMAND;
CAPABILITY;
FEASIBILITY;
ACTION;
PENDING;
WITNESS;
RELEASE;
INVALIDATION;
REASSESSMENT.

## Deliberately do not build

- replacement native parser;
- generic Python-like language;
- runtime simulator;
- universal scheduler;
- universal manager;
- whole-game optimizer.

## Current verification

The checked-in compiler verification record contains the lifecycle suite plus timing and positional-semantics regression tests.

No GitHub Actions result is being treated as proof for the latest adapter work. Local test results remain local evidence.

## Exit condition for the compiler phase

The compiler phase is not complete when every planned primitive is documented.

It is complete when the compiler can safely express and diagnose the semantic chain required for the Dark -> Feudal -> Castle Byzantine vertical slice.

### Prior-art reuse tranche verification (2026-09-26)

The first reuse tranche is now implemented and CI-verified:

- [x] typed GoalSpan requests with explicit shape, width, contract ID, and native start bounds;
- [x] interval-based collision detection for scalar GoalIds versus contiguous Goal spans;
- [x] deterministic volatile Goal scratch-pool checkout/release with explicit lifetime;
- [x] versioned deterministic binding manifest output;
- [x] staged manifest promotion tied to the native .per validation result;
- [x] AIRef-derived span contracts for contiguous point-pair and four-goal outputs;
- [x] explicit rejection of treating independent multi-Goal outputs such as threat-data fields as one span;
- [x] current compiler fixture remains unchanged in semantic behavior;
- [x] native backend validation and full compiler unittest suite pass on the implementation head.

The remaining compiler work is semantic, not storage plumbing: explicit demand ownership and writer/consumer contracts, richer resource/conflict relations, issuance-failure semantics, source-order analysis, and the Castle vertical slice. The typed capability/provider graph is now integrated as a compile-time validation projection of the current demand language.


### Demand ownership implementation record (2026-09-26)

- [x] SemanticDemand carries explicit DemandOwnership.
- [x] Lifecycle access provenance is typed as StateAccess with read/write kind, lifecycle phase, owner, demand, and deterministic source order.
- [x] analyze_demand_ownership() reports deterministic OWN-* diagnostics.
- [x] The first writer is the initialization rule for the current lifecycle state; the first consumer is the first lifecycle reader in emitter order, currently the RELEASE rule.
- [x] Multiple writers by one owner are legal only across distinct lifecycle phases; duplicate writers in the same phase are rejected.
- [x] Writers from different owners are rejected as conflicting persistent writers.
- [x] The compiler gate executes ownership validation before capability validation, runtime binding, and emission.


### Final demand ownership verification (2026-09-26)

Compiler CI run 207 (36234240102) verified the authoritative demand-ownership tree through the repository workflow:

- native generated Basilisk fixture: finding_count=0, failed=false;
- full compiler unittest suite: 132 tests, OK;
- ownership regression fixtures and compile-gate integration executed in the same suite.


### Resource/conflict implementation record (2026-09-26)

- [x] Add typed ResourceClaim, ConflictContract, ResourceClaimId, ResourceKind, and ResourceScope IR.
- [x] Attach typed resource claims to capability providers while preserving compatibility with existing action conflict metadata.
- [x] Materialize the existing build-pass singleton as a transient ACTION_EXCLUSION claim owned by the executing provider.
- [x] Diagnose arbitration without a conflict class, conflict class without an arbitration owner, multiple arbitration owners, duplicate claims, incompatible conflict-group arbitrators, and invalid classes.
- [x] Validate conflict groups deterministically before capability-provider validation, binding, and emission.
- [x] Lock bridge materialization, exact diagnostics, deterministic ordering, and public compile-gate integration with focused fixtures.
- [x] Compiler CI run 230 verified the final resource-conflict tree: native finding_count=0 and 140 tests passed.

The model deliberately stops at transient action exclusion. Persistent resource reservations and scheduler/fairness semantics remain outside Basilisk's compiler boundary.


### Action-issuance implementation record (2026-09-26)

- [x] Add typed `ActionIssuance`, `ActionIssuancePhase`, and `ActionIssuanceFailure` IR.
- [x] Add explicit `ISSUED` lifecycle state between ACTIVE and PENDING.
- [x] Emit `ACTIVE -> ISSUED` only from the native action rule and `ISSUED -> PENDING` as a separate ordered admission rule.
- [x] Preserve issuance failure as `RETAIN_ACTIVE` when issuance guards do not fire; do not invent an engine-side failure fact.
- [x] Validate native feasibility recursively through nested logical requirement expressions.
- [x] Add deterministic `ISS-*` diagnostics and compile-gate precedence before resource/capability validation.
- [x] Update lifecycle/ownership regressions and generated Basilisk fixture for the four-stage lifecycle.
- [x] Compiler CI run 275 verified the final tree: native `finding_count=0`; full compiler suite `145 tests, OK`.

Runtime limitation remains explicit: the native action command does not provide a Boolean issuance-return channel. `ISSUED` therefore means the action rule fired; it is not a claim that the game reports successful world-side execution. PENDING remains a separate compiler lifecycle state admitted on the following pass.


### Completion-witness implementation record (2026-09-26)

- [x] Add typed `CompletionWitnessContract` and `WitnessEvidenceKind.WORLD_STATE` to semantic IR.
- [x] Attach explicit witness contracts to `SemanticDemand` without adding source syntax.
- [x] Add deterministic `WIT-*` diagnostics for missing contract, timing evidence, non-completion-capable observation, action coupling, identity mismatch, order violation, invalid evidence kind, and invalid native primitive.
- [x] Validate atomic and logical witness expressions recursively.
- [x] Connect witness validation before action issuance, resource/conflict, capability validation, binding, and emission.
- [x] Project the typed witness expression into the capability graph without bypassing the contract.
- [x] Add focused typed-IR, causal-order, timing, action-coupling, non-completion-observation, identity-mismatch, deterministic-validator, and valid-witness regression fixtures.
- [x] Compiler CI run 298 verified the final witness tree: native `finding_count=0`; full compiler suite `151 tests, OK`.


### Release-state implementation record (2026-09-26)

- [x] Add typed `ReleaseStateContract` and `ReleaseEvidenceKind.WORLD_STATE` to semantic IR.
- [x] Attach release contracts to `SemanticDemand` without adding source syntax.
- [x] Validate `COMPLETE -> RELEASED` explicitly and reject premature/invalid lifecycle exits.
- [x] Add deterministic `REL-*` diagnostics for missing contract, timing evidence, missing world-state evidence, action coupling, identity mismatch, invalid from/to state, ordering, evidence kind, and native primitive.
- [x] Preserve emitter ordering: RELEASE rule precedes COMPLETION-WITNESS rule but is guarded by COMPLETE.
- [x] Migrate legacy release diagnostics to the typed release validator and add focused release-state regression fixtures.
- [x] Compiler CI run 319 verified the final release-state tree: native `finding_count=0`; full compiler suite `158 tests, OK`.


### Explicit invalidation and cancellation implementation record (2026-09-26)

- [x] Add optional `invalidate` source field without breaking existing lifecycle fixtures.
- [x] Add typed `InvalidationContract` and `CancellationStateContract` to semantic IR.
- [x] Add terminal `CANCELLED` lifecycle encoding without changing existing non-invalidating Goal values.
- [x] Validate world-state invalidation evidence separately from completion/release evidence.
- [x] Reject timing-only invalidation, action-coupled invalidation, missing world-state evidence, wrong demand identity, invalid native primitive, and source-order violations.
- [x] Restrict cancellation to `ACTIVE`, `ISSUED`, and `PENDING`; reject cancellation of `COMPLETE`.
- [x] Emit invalidation before release/witness/pending/action lifecycle rules so a true invalidation preempts same-pass execution.
- [x] Add deterministic multi-diagnostic regression coverage.
- [x] CI run 345: native `Basilisk.per` `finding_count=0`; generated invalidation fixture `finding_count=0`; compiler suite `165 tests, OK`.
- [x] Temporary verification PRs were closed unmerged; implementation remains on `main`.


### GameData / CivProfile implementation record (2026-09-26)

- [x] Add immutable PatchId, Validity, EvidenceRef, and typed PatchChange.
- [x] Add typed BuildingId, UnitId, TechId, CivId, UnitLineId, Resource, and Age.
- [x] Add deterministic ResourceCost arithmetic and explicit engine-rounding policy for civilization cost modifiers.
- [x] Add typed building, unit, technology, provider, unit-line, prerequisite, selector, and technology-effect IR.
- [x] Validate duplicate entities, provider references, upgrade links, unit-line references, and technology unlock references.
- [x] Add typed CivProfile, availability hooks, civilization bonuses, and civilization-specific interactions.
- [x] Add deterministic EffectiveCivData resolution and snapshot fingerprinting.
- [x] Populate a verified Byzantine factual subset from docs/reference/BYZANTINES_manifest.txt.
- [x] Encode Byzantine cost modifiers and other factual civilization modifiers separately from base GameData.
- [x] Encode Update 185872 Byzantine patch facts: Varangian access, Cataphract bonus changes, and Logistica interaction expansion.
- [x] Add a separate native metadata profile with explicit local-alias semantics for ri-logistica and ri-elite-varangian-guard.
- [x] TDD red/green evidence recorded through CI runs 349/350/351/352; final native-data tree: 173 compiler tests passed, native fixtures clean.
- [x] Cross-reference against AIRef, The Duke, Niek/Atilla, AgeScript, and AgeOfPython without importing their architectures.

#### Remaining data work

- [ ] Ingest the full Byzantine 145-node manifest into typed GameData.
- [ ] Populate every verified research cost/research time and effect instead of leaving unresolved values where the source does not establish them.
- [x] Verify and promote current-patch Varangian Guard unit numeric IDs from the authoritative Basilisk/Basilisk.per controller definitions.
- [ ] Expand NativeEngineProfile from the two known site-specific aliases to the complete checked-in AIRef command/parameter inventory.
- [ ] Add historical snapshot fixtures proving patch overlay replay across multiple DE revisions.
- [ ] Add cross-civilization data fixtures before strategy semantics begin consuming the data layer broadly.

### Cross-reference outcome

AIRef supports the native type boundary and the separation of command/parameter semantics from game facts.

The Duke and Niek/Atilla support first-class age, provider, research, resource, production, and strategic-state relationships in community-native .per, while keeping those concerns expressed as ordinary facts/goals/rules rather than a universal manager.

AgeScript and AgeOfPython support typed metadata, source-to-native lowering, and compiler-owned storage discipline. Their general-purpose language designs remain out of scope.

The compiler should therefore borrow the community's proven factual boundaries and execution idioms, then place Basilisk strategy above them rather than inside them.

### Next compiler layer

The next missing semantic layer is not another lifecycle primitive.

It is StrategyProfile -> StrategicDemand -> CapabilityIntent:

- [ ] typed strategic postures;
- [ ] persistent strategic-demand specifications;
- [ ] target/floor semantics distinct from execution witnesses;
- [ ] opportunity-cost policy attached to strategic ownership;
- [ ] strategic admissibility/invalidation evidence;
- [ ] deterministic lowering into the existing SemanticDemand/capability pipeline;
- [ ] first Dark -> Feudal -> Castle Byzantine vertical slice.
### StrategyProfile / StrategicDemand implementation record (2026-09-26)

- [x] Typed FLUSH/RUSH/BOOM/CASTLE-POWER postures.
- [x] StrategyProfile bound to exact EffectiveCivData patch and fingerprint.
- [x] Strategic owner separate from stable demand identity.
- [x] Persistent strategic evidence distinct from execution feasibility and timing evidence.
- [x] Exact, standing-floor, current+queued, and bounded-package targets.
- [x] Opportunity-cost policy with protected floors and emergency-posture metadata.
- [x] One strategic demand can lower to multiple execution demands.
- [x] Per-execution capability-intent overrides.
- [x] Multiple strategic demands can share a factual capability identity without collapsing their strategic identities.
- [x] Generic land Castle strategy constructor plus Byzantine wrapper.
- [x] Dark -> Feudal -> Castle vertical slice through the existing lifecycle/capability pipeline.
- [x] Native CI validates the generated strategy `.per`.
- [x] Final implementation head verified by CI run 368 (`36238612808`): three native fixtures clean; `190 tests, OK`.

### GameData / CivProfile harsh-audit repairs

- [x] Imperial Age discount modeled as an age-advance cost override.
- [x] Byzantine building HP modeled as an age-scoped building modifier.
- [x] Spearman/Pikeman/Halberdier and Camel Rider discounts remain civilization modifiers over unit-line facts.
- [x] Fire Ship current attack-speed bonus is separated from generic unit facts; Dromon remains represented as a factual unit/provider entry and is not assigned an unverified extra civilization modifier.
- [x] Current team Monk healing modifier represented as a team-scoped civ bonus.
- [x] Town Watch and Town Patrol free facts represented separately from ordinary technology costs.
- [x] Logistica cost and Greek Fire effects represented in the current verified subset.
- [x] Verified production relationships made explicit for the current subset.
- [x] Unverified static age-up building prerequisites removed rather than encoded as false facts; native `can-research-with-escrow` remains the runtime authority.
- [x] Unit-line membership references are now structurally validated.

### Current compiler boundary

The compiler now describes static strategy intent, evaluates typed runtime strategic evidence, and lowers selected strategic demands into the existing execution semantics. The remaining gap is broader whole-player Basilisk strategy ingestion and complete factual coverage; another execution lifecycle is not required.

### Data-layer open work

- [ ] Complete 145-node Byzantine manifest ingestion.
- [ ] Complete verified research cost/time/effect ingestion.
- [x] Promote current-patch Varangian Guard numeric IDs from the authoritative controller evidence.
- [ ] Expand NativeEngineProfile to the complete checked-in AIRef command/parameter inventory.
- [ ] Implement replayable historical patch overlays rather than explicit snapshot matching.
- [ ] Add broader factual cross-civilization datasets.
### StrategyRuntimeState / StrategicEvidenceBinding implementation record (2026-09-26)

- [x] Add StrategicObservationType and native observation contracts without creating a second expression parser.
- [x] Bind StrategicEvidence expressions through the existing parser and checked-in AIRef command schema.
- [x] Reject action, timing-only, and unsupported native evidence from persistent strategic truth.
- [x] Fail closed on unresolved native identifiers and wrong native parameter families.
- [x] Add immutable RuntimeObservationSnapshot and deterministic StrategyRuntimeState.
- [x] Separate strategic runtime classifications from the execution lifecycle.
- [x] Deterministically select posture from typed evidence and transition priority.
- [x] Reject incompatible equal-priority posture transitions.
- [x] Keep persistent strategic intent when execution feasibility is false.
- [x] Distinguish strategic invalidation from execution failure.
- [x] Apply protected/overridden/released opportunity-cost runtime state using existing OpportunityCostPolicy.
- [x] Record explicit reassessment causes and deterministic fingerprints.
- [x] Avoid allocating runtime Goals for reconstructible strategic state.
- [x] Lower runtime-selected strategic demands through the existing lifecycle/capability/resource/runtime-binding compiler pipeline.
- [x] Add native CI fixture for strategy runtime evaluation/lowering.
- [x] Final CI run 382 (36239760165) verified four native fixtures with finding_count=0 and the full compiler suite with 218 tests, OK.

### Hard-audit findings repaired before runtime sign-off

- [x] Fixed incomplete Byzantine unit-line membership.
- [x] Fixed missing Fire Ship and Archer upgrade links required by bidirectional upgrade validation.
- [x] Fixed missing Castle Petard provider line.
- [x] Fixed fake Logistica interaction target by replacing the unresolved class token with the exact Cataphract/Varangian unit set.
- [x] Anchored current Varangian unit/tech IDs to authoritative controller evidence.
- [x] Fixed a circular import introduced by the runtime evidence layer.
- [x] Fixed the runtime domain import to reference EffectiveCivData from civ_profile.
- [x] Fixed stale/incorrect GameData audit tests that were unreachable after unittest.main().
- [x] Added affordability facts to strategic observation binding.
- [x] Added direct observation access on StrategicEvidenceBinding.
- [x] Promoted Castle strategic invalidation into StrategicDemandSpec.invalidation while retaining execution invalidation at the existing lifecycle boundary.

### Remaining compiler work after StrategyRuntimeState

- [ ] Complete Byzantine 145-node factual ingestion.
- [ ] Complete verified research costs/times/effects.
- [ ] Expand native metadata to the complete checked-in AIRef command/parameter inventory where strategy semantics require it.
- [ ] Add replayable historical patch overlays.
- [ ] Add broader cross-civilization factual fixtures.
- [ ] Replace the toy strategy fixture with compilation of actual Basilisk strategic modules without moving gameplay policy into GameData.