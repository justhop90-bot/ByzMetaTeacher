# LearnerAI Compiler

The compiler is the semantic backplane for the Byzantine player.

It is not the player itself.

Its job is to turn explicit player semantics into auditable .per while rejecting lifecycle defects that native parsing cannot know about.

## Pipeline

    player specification
      -> source parser / AST
      -> semantic lifecycle analysis
      -> typed capability projection + validation
      -> validated IR
      -> runtime binding
      -> deterministic .per
      -> native aoe2-ai-parser validation
      -> AoE2DE runtime
      -> runtime evidence

The capability graph is currently a semantic validation projection of the existing demand IR. It is not yet the source language for strategy composition, and the emitter still lowers the validated demand IR rather than the capability graph.

Demand ownership is currently derived from the semantic demand identity because the small source language has no separate owner declaration. The typed IR is ready for strategy/domain owner identities later; no new source syntax is introduced just to exercise this layer.

The runtime remains the final authority.

## Current language

The first source language remains deliberately small:

    demand <name> {
        require (<native .per predicate>)
        action (<native .per action>)
        witness (<native .per world-state predicate>)
        release (<native .per predicate>)
        invalidate (<native .per invalidation predicate>)   # optional
    }

Native expressions stay visible. The compiler does not try to invent a second AoE2 engine.

Current action-provider contract: an actionable demand must expose at least one native FEASIBILITY predicate in its requirements. The capability validator enforces this before runtime binding or emission. Timing and world observations can remain part of the demand, but they do not replace the engine-native feasibility boundary.

## Semantic responsibilities

The compiler owns:

- demand lifecycle;
- semantic context;
- capability versus demand separation;
- feasibility versus action;
- pending state;
- timing-vs-world-evidence semantics;
- native positional observations where the engine exposes them;
- refusal to invent unsupported builder-count semantics;
- completion witnesses;
- release;
- explicit strategic invalidation and cancellation;
- ownership and dependency diagnostics.

The native backend owns raw .per language legality.

The game owns actual execution.

## Current lifecycle guarantee

An action first moves a demand from active to issued.

A separate pending-admission rule moves issued to pending on the following script pass.

The typed completion-witness contract proves that completion evidence is an explicit world-state observation tied to the demand it establishes. The pending witness moves pending to complete.

The typed release-state contract requires release to be guarded by COMPLETE and transition only to RELEASED. Release is validated independently from completion witnessing.

An optional typed invalidation contract records world-state evidence that the strategic demand is obsolete. Its cancellation contract may transition only ACTIVE, ISSUED, or PENDING to terminal CANCELLED; COMPLETE is never cancelled by this layer. Invalidation is emitted before release and action issuance so a true invalidation preempts execution in the same rule pass.

The action itself is never the witness, and issuance is not completion.

The emitter deliberately writes these three lifecycle rules in reverse transition order:

    RELEASE
    COMPLETE-WITNESS
    ACTIVE-ACTION

AoE2 goal values update immediately, so this source order prevents an already-true witness and release predicate from collapsing the entire lifecycle in one script pass. The intended execution is:

    pass N   : ACTIVE -> ISSUED
    pass N+1 : ISSUED -> PENDING
    pass N+2 : PENDING -> COMPLETE
    pass N+3 : COMPLETE -> RELEASED

The compiler has regression coverage for the rule ordering and the three-pass state sequence.

The action issuance rule requires both the completion witness and release predicate to be false before issuing. This stale-fact barrier prevents a predicate that was already true before the action from being reused as post-action completion or release evidence. An unsatisfied issuance guard leaves the demand ACTIVE and therefore represents issuance failure, not PENDING. The native .per action primitive provides no Boolean return value, so the compiler cannot claim to observe an engine-side rejection after the rule fires; the ISSUED state records that the native action rule fired, while PENDING is a separate lifecycle admission.

Examples already implemented:

- Castle construction;
- defensive Spearmen;
- Wheelbarrow research.

The timing layer now recognizes native `game-time` as interpretation evidence only. A timing-only demand cannot write an action, timing cannot prove completion, and timing alone cannot release a demand.

These are compiler lifecycle examples, not the complete Byzantine player.

## Runtime binding

`RUNTIME_BINDING_CONTRACT.md` defines the typed binding boundary between semantic IR and native storage. It explicitly separates:

- confirmed engine/repository facts;
- Basilisk compiler policy;
- assumptions and unresolved implementation work.

It defines the contracts for:

- scalar GoalSlot;
- native consecutive GoalSpan contracts;
- typed native parameter contracts;
- StrategicNumberSlot and TimerSlot extension points;
- package occupancy and persisted binding extension points;
- deterministic lifecycle Goal binding;
- collision and range diagnostics.

The design deliberately distinguishes a GoalId from the integer value stored in that Goal. In the current lifecycle compiler, active/pending/complete are values of one lifecycle Goal, not three GoalIds.

The lifecycle GoalSlot boundary is implemented. SemanticDemand carries a symbolic storage request; RuntimeBinder resolves it to one native GoalId; the emitter alone converts the resolved slot into the current native lifecycle-value encoding.

## Prior-art-derived storage layer

The compiler now adopts the useful lower-level mechanisms identified in public AoE2 compiler projects without importing their general-purpose language architectures:

- AgeScript's explicit symbolic-memory-to-native lowering discipline;
- AgeOfPython's typed native metadata boundary;
- aoe2ai's explicit volatile Goal lifetime model and reusable Goal/Point storage.

The implemented binding layer distinguishes:

- `GoalSlot`: one scalar GoalId used for semantic lifecycle/state;
- `GoalSpan`: an explicitly contiguous native Goal range with a declared shape;
- `GoalInterval`: the collision unit for package occupancy;
- `VolatileGoalPool`: temporary compiler scratch storage with explicit checkout/release;
- `BindingManifest`: deterministic persisted mapping from symbolic storage requests to native storage.

Goal spans are not inferred from “multiple Goal parameters.” They are admitted only from native contracts derived from the checked-in AIRef command schema. In particular, `up-get-point` and `up-get-search-state` are contiguous spans, while `up-get-threat-data` exposes four independent Goal outputs and is deliberately not collapsed into one span.

Compiler output can optionally carry a binding manifest:

`--binding-manifest <path>`

When native validation is enabled, the .per artifact and manifest are staged together and promoted together only after the pinned native backend accepts the generated .per. This keeps semantic storage assignment reproducible without making the native parser responsible for Basilisk semantics.

## Current semantic position

Implemented and connected to the compile gate:

1. typed demand ownership contract;
2. typed lifecycle state read/write accesses;
3. deterministic first-writer and first-consumer analysis aligned with emitter order;
4. owner mismatch, missing-owner, conflicting-writer, duplicate-writer, consumer-before-writer, and unconsumed-state diagnostics;
5. typed capability/provider/witness graph;
6. provider contract validation;
7. feasibility and admissibility validation;
8. prerequisite dependency closure;
9. deterministic SCC cycle detection;
10. dead-end, unrooted, open-loop, blocked, and disconnected diagnostics;
11. deterministic capability and ownership diagnostics;
12. explicit strategic invalidation/cancellation semantics with deterministic diagnostics;
13. projection of the current demand language into these semantic layers without adding source syntax.

Still required for a full player compiler:

1. richer owner boundaries once strategy/domain owner declarations exist;
2. resource/conflict semantics beyond the current transient action-exclusion layer;
3. explicit action-issuance failure versus pending-state semantics;
4. capability-loss closure and execution-state recovery while preserving strategic demand;
5. broader source-order and same-pass visibility analysis across non-lifecycle state;
6. StrategicNumberSlot and TimerSlot allocation;
7. Castle vertical-slice compilation against actual Basilisk strategy/economy semantics.

The compiler should grow by semantic need, not by accumulating a second programming language.

Resource arbitration is deliberately narrow. The current compiler models only transient action exclusion, such as the existing build-pass singleton. It does not invent persistent global resource reservations or a fairness scheduler.

Do not add syntax first. Add semantic capability when a real player behavior requires it.

## Native schema authority

The checked-in AIRef command schema supplies native command signatures and parameter metadata.
The semantic registry remains deliberately smaller and assigns Basilisk meanings such as
OBSERVATION, FEASIBILITY, ACTION, and WITNESS. A native command without a semantic adapter is
rejected rather than silently treated as understood.

The emitter also enforces the current DE artifact budgets: 10,000 rules, 32 elements per rule,
and 255 characters per line. Build actions are guarded by a shared per-pass claim because the
native engine permits only one successful build/up-build action per AI rule pass.

## Native validation

Generated .per is staged and validated by the pinned aoe2-ai-parser backend before promotion when native validation is enabled.

Use Compiler/backends/README.md for the protocol and pin.

## Compiler architecture

compiler.py:
orchestration and CLI.

parser.py:
source syntax to AST.

ast.py:
syntax structures.

primitives/:
small authoritative teaching profile for the current compiler slice.

semantic/:
expression and lifecycle validation.

ir/:
validated semantic representation.

emitter/:
deterministic .per generation.

backends/:
external native validation boundary.

tests/:
semantic and backend regression evidence.

examples/ and generated/:
small lifecycle fixtures only. They are not the full Basilisk controller.

## Current implementation boundary

Implemented now:
- explicit typed demand ownership contracts;
- explicit typed completion-witness contracts with deterministic witness diagnostics;
- explicit typed action-issuance contract with separate ISSUED and PENDING lifecycle states;
- deterministic issuance diagnostics and issuance-first compile-gate validation;

- typed lifecycle read/write accesses with deterministic emitter-aligned source order;
- typed transient resource claims and conflict contracts;
- deterministic resource/arbitration diagnostics before capability validation;
- deterministic first-writer/first-consumer analysis;
- ownership mismatch, missing-owner, conflicting-writer, duplicate-writer, consumer-before-writer, and unconsumed-state diagnostics;
- compiler-gate integration before capability validation, runtime binding, and emission;
- one symbolic lifecycle GoalSlot request per demand;
- typed GoalId and GoalValue wrappers;
- deterministic GoalSlot and GoalSpan binding with occupied-ID/interval and existing-binding support;
- native parameter/storage contract types;
- deterministic binding manifests and staged promotion;
- typed capability-provider/witness IR;
- provider, witness, admissibility, feasibility, dependency, and lifecycle-closure validation;
- deterministic SCC and dead-end diagnostics;
- regression coverage for ownership, access order, capability validation, lifecycle, binding, and native integration.

Still open:
- package-wide occupancy discovery from an explicit package inventory;
- StrategicNumberSlot and TimerSlot allocators;
- richer owner boundaries once strategy/domain owner declarations exist;
- resource/conflict semantics beyond the build-pass singleton;
- action-issuance versus pending-state distinction;
- broader source-order and same-pass visibility analysis across non-lifecycle state;
- Castle vertical slice compiled against actual Basilisk strategy/economy semantics.

## Verification

Run:

    python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"

The latest checked-in verification record contains the compiler regression suite, timing-semantics tests, and cross-pass lifecycle tests. This is compiler evidence only. It is not gameplay evidence.

## Product boundary

The compiler is successful when it helps us build the player safely.

It is not successful merely because the compiler grows larger.


### Completion witness boundary

Completion is admitted only through a typed `CompletionWitnessContract`. The contract records witness identity, evidence kind, native witness primitive, the demand/capability it establishes, and emitter-aligned source order relative to action issuance. The witness validator rejects timing evidence, non-completion-capable observations, action/witness coupling, identity mismatch, invalid evidence kind, and witness ordering violations before resource/capability validation. This layer validates causal evidence; it does not duplicate the runtime's world-state authority.


### Release-state boundary

A `ReleaseStateContract` explicitly records release identity, world-state evidence, the demand it establishes, `COMPLETE -> RELEASED`, and emitter-aligned source order relative to the completion witness. Release validation rejects timing-only release, action coupling, wrong-demand release, invalid lifecycle transitions, invalid evidence kinds, unknown native primitives, and release rules emitted after their completion-witness rule. The source-language release remains intentionally small; strategic invalidation/cancellation is a separate future contract.


### Invalidation / cancellation boundary

`invalidate` is an optional source statement because existing compiler fixtures remain compatible while strategy sources are migrated to explicit strategic-admissibility evidence. When present, the compiler materializes an `InvalidationContract` and a `CancellationStateContract`. Invalidation rejects timing-only evidence, action coupling, missing world-state evidence, wrong demand identity, unknown native primitives, and invalid source ordering. Cancellation is restricted to `ACTIVE`, `ISSUED`, and `PENDING` and always terminates in `CANCELLED`; completed work remains owned by the release path. Capability-loss recovery that preserves strategic demand remains a separate future contract.

## Factual GameData / CivProfile layer

The compiler now has a typed factual layer beneath strategy:

    NativeEngineProfile
          |
    GameData + CivProfile
          |
    EffectiveCivData
          |
    StrategyProfile
          |
    SemanticDemand / Capability

`LearnerAI/Compiler/ir/game_data.py` owns typed game entities, costs, prerequisites, providers, unit lines, selectors, technology effects, and deterministic structural validation. `civ_profile.py` applies civilization-specific facts and modifiers to produce a deterministic effective snapshot. `native_metadata.py` remains separate so a site-specific native alias such as `ri-logistica` cannot be mistaken for a built-in game symbol.

The current Byzantine fixture is anchored to the repository manifest and Update 185872. It intentionally does not invent unverified current-patch Varangian numeric unit IDs or missing research-cost data. This is a verified factual subset, not yet the complete 145-node Byzantine database.

The StrategyProfile and StrategyRuntimeState layers are implemented. StrategyProfile consumes EffectiveCivData and preserves strategic owner/intent separately from execution state. StrategyRuntimeState binds its evidence to the checked-in native command schema, evaluates a typed runtime snapshot, selects posture deterministically, classifies strategic demands as inactive/active-executable/active-blocked/invalidated/complete, applies opportunity-cost override/release policy, records reassessment causes, and lowers only the selected strategic demands through the existing lifecycle/capability pipeline. Native CI validates both static and runtime strategy fixtures. The remaining compiler gap is whole-player Basilisk strategy ingestion and broader factual coverage, not another lifecycle state machine.
## StrategyProfile / StrategicDemand layer

Implemented:

- typed FLUSH/RUSH/BOOM/CASTLE-POWER postures;
- exact EffectiveCivData patch/fingerprint binding;
- strategic owner distinct from stable demand identity;
- persistent/admissibility/execution/timing evidence classes;
- exact, standing-floor, current+queued, and bounded-package targets;
- opportunity-cost policy with protected floors and emergency posture metadata;
- one-to-many execution-demand mapping with stable local IDs;
- per-execution capability-intent overrides;
- shared factual capability identities for strategy-bound demands;
- generic land Castle strategy constructor with Byzantine wrapper;
- Dark -> Feudal -> Castle strategy fixture through the existing lifecycle/capability compiler;
- native CI validation of the generated strategy `.per`.

Verification: CI run 368 (`36238612808`) reported `finding_count=0` for the generated Basilisk, strategy, and invalidation fixtures and `190 tests, OK`.

### Current strategy boundary

StrategyProfile describes strategic intent and static admissibility, but it does not yet evaluate live strategic observations into changing posture, demand activation, strategic invalidation, opportunity-cost override/release, and reassessment. That is the next compiler layer.

## StrategyRuntimeState / StrategicEvidenceBinding layer

The runtime strategy boundary is now explicit:

    StrategyProfile
      -> StrategicEvidenceBinding
      -> StrategyRuntimeState
      -> selected StrategicDemandSpec
      -> existing SemanticDemand / Capability pipeline
      -> .per

LearnerAI/Compiler/ir/strategy_runtime.py uses the existing expression parser and checked-in AIRef schema. It does not introduce a second AoE2 parser or a second execution lifecycle.

Implemented strategic runtime states are STRATEGIC_INACTIVE, STRATEGIC_ACTIVE_EXECUTABLE, STRATEGIC_ACTIVE_BLOCKED, STRATEGIC_INVALIDATED, and STRATEGIC_COMPLETE.

These are strategic classifications only. ACTIVE/ISSUED/PENDING/COMPLETE/RELEASED/CANCELLED remain the execution lifecycle.

Strategic evidence is bound to typed native observations including current age, resource amounts, building/unit counts, enemy counts, research/capability state, and timing. Persistent strategic evidence rejects action, feasibility-only, and timing-only truth. Unknown native evidence fails closed.

Opportunity-cost runtime state is restricted to protected, overridden, and released. Emergency override requires explicit posture metadata. It is not a scheduler or optimizer.

Runtime evaluation records deterministic reassessment causes and a fingerprint. Native storage is not requested merely because a strategic state exists; the current evaluator requests no runtime Goal storage.

The CI runtime fixture exercises posture-dependent strategy activation, blocked Castle execution, opportunity-cost policy, and the existing lifecycle lowering. The exact final verification is recorded in RESEARCH_CHECKLIST.md.
## GameData factual boundary

GameData is now an explicit factual boundary rather than a strategy database. The checked-in Byzantine 185872 snapshot is intentionally marked `CIVILIZATION` scoped and `FACTUAL_SUBSET`. It carries typed provider edges, upgrade/research relations, age-transition prerequisites, civilization modifiers, factual unit effects, and coverage metadata.

A partial snapshot never means "unavailable to the civilization." StrategyProfile capability intents are admitted only when their referenced factual entity is covered by the resolved snapshot. The runtime engine remains authoritative for actual feasibility and execution.

The full universal game-data baseline, civ availability overlays, and replayable historical patch overlays remain separate open data-layer work. Do not bypass the coverage gate by filling absent entities from generic AIRef records: AIRef native technology IDs establish engine identity and command metadata, not Byzantine civilization availability.
