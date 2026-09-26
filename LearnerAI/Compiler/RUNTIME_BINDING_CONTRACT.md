
# Runtime Binding Contract

## Status

This document defines the runtime-binding contract for the LearnerAI compiler. The lifecycle GoalSlot portion is implemented; the broader storage families remain explicitly scoped extension points.

Evidence is classified explicitly:

- **CONFIRMED**: directly supported by the checked-in repository or current AIRef/native documentation.
- **POLICY**: an intentional Basilisk compiler rule chosen to make generated state deterministic and auditable. A policy is not an engine fact.
- **ASSUMPTION / OPEN**: not yet established by the repository or native runtime and therefore must not be treated as an implementation guarantee.

The compiler must preserve that distinction in code comments, diagnostics, tests, and future documentation.

## 1. Current compiler fact pattern

### CONFIRMED

The semantic IR now contains one symbolic lifecycle GoalSlotRequest in each SemanticDemand. It contains no resolved GoalId, pending GoalId, or complete GoalId.

The analyzer no longer computes `base_goal + (offset * 3)`. The `base_goal` compiler option is now binding configuration.

The emitter receives a resolved BindingResult and performs the current native lifecycle-value encoding:

    GoalId = G
    ACTIVE = 1
    PENDING = G + 1
    COMPLETE = G + 2
    RELEASED = 0

These are lifecycle values associated with one Goal storage location, not separate GoalIds.

### IMPLEMENTED

- GoalId and GoalValue are distinct native-layer types.
- SemanticDemand uses typed symbolic storage requests.
- RuntimeBinder is the sole resolver for lifecycle GoalIds.
- Existing bindings can be reused.
- Occupied GoalIds are respected.
- Allocation order is deterministic.
- GoalId bounds are checked.
- Native parameter/storage contract types exist without being confused with semantic primitive roles.

### OPEN

Full GoalSpan/SN/Timer allocation and package-wide occupancy discovery remain unimplemented.
The checked-in AIRef command schema is now the native signature source, and the binding layer
now provides a deterministic JSON manifest model with stable reservation of existing assignments.
Automatic end-to-end manifest write-back remains open.

## 2. Engine resource model

### CONFIRMED

Current AIRef documents:

- GoalId range: `1..16000`.
- Strategic-number range: `0..511`.
- Timer range: `1..50`.
- DE rule limit: 10,000 rules.
- DE rule-element limit: 32.
- DUC local search list: 240.
- DUC remote search list: 40.
- source-line limit: 255 characters.

AIRef also documents special extended-goal restrictions:

- Goals `1..40` cannot be used as the starting goal for point/cost/search/guard operations that automatically modify consecutive goals.
- Four-goal extended operations accept starts in `41..508`.
- Point operations need two consecutive goals, so their upper safe start differs from four-goal operations.
- The original UserPatch guidance warns against point starts `511..512` and four-goal starts `509..512`.

AIRef's Strategic Number index documents 512 SNs, `0..511`, and recommends starting custom use at SN 510 and working downward because SN 511 has DE bugs and previously unused SNs may become active in later DE versions.

UserPatch documentation also states that goal/timer storage must be explicitly initialized rather than relying on engine defaults.

### POLICY

Basilisk will maintain separate storage pools for:

- scalar GoalSlot;
- two-goal GoalSpan;
- four-goal GoalSpan;
- StrategicNumberSlot;
- TimerSlot.

The compiler will not infer a GoalSpan merely because a native command has multiple Goal arguments.

### OPEN

Exact native contracts for every multi-output command must be sourced from the checked-in AIRef inventory before those commands are admitted to compiler lowering.

## 3. Typed binding API

The binding API is deliberately compile-time only.

### Storage kinds

    class StorageKind(str, Enum):
        GOAL_SLOT = "GoalSlot"
        GOAL_SPAN = "GoalSpan"
        STRATEGIC_NUMBER = "StrategicNumberSlot"
        TIMER = "TimerSlot"

    class GoalSpanKind(str, Enum):
        POINT_PAIR = "POINT_PAIR"
        EXTENDED_4 = "EXTENDED_4"

    class GoalRole(str, Enum):
        LIFECYCLE_STATE = "LIFECYCLE_STATE"
        PERSISTENT_STATE = "PERSISTENT_STATE"
        DERIVED_SCALAR = "DERIVED_SCALAR"
        NATIVE_OUTPUT = "NATIVE_OUTPUT"
        EXECUTION_MEMORY = "EXECUTION_MEMORY"

    @dataclass(frozen=True)
    class GoalSlot:
        goal_id: int
        role: GoalRole
        provenance_id: str

    @dataclass(frozen=True)
    class GoalSpan:
        start_goal_id: int
        width: int
        kind: GoalSpanKind
        provenance_id: str

    @dataclass(frozen=True)
    class StrategicNumberSlot:
        sn_id: int
        provenance_id: str

    @dataclass(frozen=True)
    class TimerSlot:
        timer_id: int
        provenance_id: str

These are resolved bindings. They are not semantic identities.

## 4. Storage requests

Semantic IR must request storage without supplying the final numeric ID.

    @dataclass(frozen=True)
    class StorageRequest:
        request_id: str
        semantic_id: str
        owner_id: str
        source_unit: str

        storage_kind: StorageKind
        goal_role: GoalRole | None = None
        span_kind: GoalSpanKind | None = None

        native_contract_id: str | None = None
        purpose: str = ""

        origin_mode: str = "SOURCE_OWNED"
        derivation_id: str | None = None

        stability_key: str = ""

### API invariant

A StorageRequest MUST NOT contain:

- `goal_id`;
- `sn_id`;
- `timer_id`;
- an arbitrary numeric slot.

The request describes what storage is needed. The binder chooses where.

## 5. Native contract API

Storage allocation cannot safely operate without native command contracts.

The compiler therefore needs a small metadata interface, not a second parser.

    @dataclass(frozen=True)
    class NativeStorageContract:
        contract_id: str
        command: str
        parameter_index: int

        storage_kind: StorageKind
        width: int
        span_kind: GoalSpanKind | None

        consecutive: bool

        start_min: int | None
        start_max: int | None

        initialization: str

The contract is referenced by lowering.

Example:

    up-get-point
        storage_kind = GOAL_SPAN
        width = 2
        span_kind = POINT_PAIR
        consecutive = true

    up-get-search-state
        storage_kind = GOAL_SPAN
        width = 4
        span_kind = EXTENDED_4
        consecutive = true
        start_min = 41
        start_max = 508

    up-get-threat-data
        storage_kind = GOAL_SLOT
        width = 4
        span_kind = null
        consecutive = false

The last distinction is intentional. Four Goal outputs do not imply a four-goal span.

### CONFIRMED

AIRef describes `up-get-search-state` as four consecutive extended goals, `up-get-point` as an extended goal pair, and `up-get-threat-data` as four separate output goals for elapsed time, player, source, and target.

### POLICY

The compiler refuses a native lowering unless the required storage contract exists.

### OPEN

The exact contract metadata should be generated/checked against the repository's pinned AIRef schema rather than hand-maintained indefinitely.

## 6. GoalId policy

### CONFIRMED

The engine accepts GoalIds `1..16000`.

### POLICY

Basilisk reserves ranges to separate scalar storage from extended storage:

    1..40
        external/legacy-sensitive; never allocated for compiler GoalSpan.

    41..508
        default compiler GoalSpan arena.

    509..512
        never used as four-goal span starts.

    513..16000
        default compiler scalar GoalSlot arena.

This is a compiler policy, not an engine claim.

The policy deliberately leaves the four-goal span range compact and keeps scalar GoalSlots outside it, eliminating scalar/span aliasing by construction.

### Point-specific policy

Point spans have a different native upper boundary.

The compiler MUST use the contract's `start_min/start_max`, rather than assuming all spans have the `41..508` range.

A point-pair binding may therefore use a start above 508 only if the native contract explicitly permits it and the package policy permits it.

The compiler must not reduce all GoalSpan types to one generic range.

## 7. GoalSpan allocation

Allocation is interval allocation, not scalar allocation.

    @dataclass(frozen=True)
    class GoalInterval:
        start: int
        end: int

    def interval(span: GoalSpan) -> GoalInterval:
        return GoalInterval(
            span.start_goal_id,
            span.start_goal_id + span.width - 1,
        )

Required checks:

1. start lies inside the native contract range;
2. end <= 16000;
3. span does not overlap another span;
4. span does not overlap an externally reserved GoalSlot;
5. span width exactly matches the native contract;
6. the command's contract actually requires consecutive storage.

No automatic widening is allowed.

## 8. Scalar GoalSlot allocation

### POLICY

Scalar compiler state is allocated from the `513..16000` pool by default.

Persistent/lifecycle state is allocated deterministically from the low side.

Compiler scratch/native-output state is allocated deterministically from the high side.

Example:

    persistent:
        513, 514, 515, ...

    scratch:
        16000, 15999, 15998, ...

This is a packing policy only. It is not an engine distinction.

### CONFIRMED

A scalar GoalId is legal anywhere in the engine GoalId range if the native command accepts a GoalId.

### OPEN

Whether an eventual full Basilisk package should reserve additional scalar ranges for historical/community conventions must be determined from the actual package inventory rather than guessed.

## 9. StrategicNumberSlot policy

### CONFIRMED

SNs are `0..511`.

AIRef recommends custom use beginning at SN 510 and descending, while checking the active SN index because future DE releases can consume previously unused numbers.

### POLICY

A compiler request for a StrategicNumberSlot must contain an explicit justification:

    WHY_NOT_GOAL

The binder rejects custom SN requests without it.

Allocation:

    candidate = highest inventory-approved inactive SN <= 510
    walk downward

SN 511 is excluded from automatic allocation.

### Required request

    @dataclass(frozen=True)
    class StrategicNumberRequest:
        request_id: str
        semantic_id: str
        owner_id: str
        purpose: str

        why_not_goal: str
        native_contract_id: str | None
        stability_key: str

The binder must record the active/inactive status from the exact inventory snapshot used during allocation.

### OPEN

The repository currently does not have a general compiler SN-allocation implementation. This design does not claim that one exists.

## 10. TimerSlot policy

### CONFIRMED

Timers are `1..50`.

### POLICY

Timer allocation is exclusive by default.

A TimerSlot may represent only temporal control state such as:

- cooldown;
- backoff;
- retry delay;
- interval gate;
- bounded reassessment delay.

A timer is not semantic truth and cannot be used as a completion witness.

Timers are initialized explicitly before first semantic use.

### OPEN

Compiler lifetime analysis is not currently strong enough to prove safe timer reuse. Therefore reuse should not be implemented in the first allocator.

## 11. Provenance contract

Every binding must carry immutable provenance.

    @dataclass(frozen=True)
    class BindingProvenance:
        provenance_id: str

        request_id: str
        semantic_id: str
        owner_id: str
        source_unit: str

        origin_mode: str
        derivation_id: str | None

        storage_kind: StorageKind
        goal_role: GoalRole | None
        span_kind: GoalSpanKind | None

        allocated_ids: tuple[int, ...]

        native_contract_id: str | None

        purpose: str
        initialization_policy: str

        engine_inventory_sha: str
        package_inventory_sha: str
        allocator_version: str

        stability_key: str

Minimum provenance questions:

    Who owns this storage?
    Why does it exist?
    Which semantic value requested it?
    Is it source-owned, derived, or engine-observed?
    Which native operation consumes it?
    Which exact engine inventory justified it?
    Which package snapshot was checked?
    Why is this storage type appropriate?
    Which numeric IDs were assigned?

If those questions cannot be answered, binding fails.

## 12. Package occupancy

### CONFIRMED

The current compiler emits an independent .per artifact and validates it through a staged native backend.

### POLICY

Runtime binding must eventually operate against package-wide occupancy rather than a single compiler invocation.

The binding context therefore accepts:

    @dataclass(frozen=True)
    class PackageResourceInventory:
        occupied_goal_ids: frozenset[int]
        occupied_goal_intervals: tuple[GoalInterval, ...]

        occupied_sn_ids: frozenset[int]
        occupied_timer_ids: frozenset[int]

        package_snapshot_sha: str

The allocator may never overwrite occupied external storage.

### OPEN

The repository does not currently expose a complete package-wide resource manifest for arbitrary externally-authored .per.

Therefore the first implementation must use an explicit imported occupancy manifest or a deliberately limited compiler-owned namespace. It must NOT pretend that a single-file scan is package-wide truth.

## 13. Binding API

The public compiler API should be:

    class RuntimeBinder(Protocol):
        def bind(
            self,
            requests: tuple[StorageRequest, ...],
            context: "BindingContext",
        ) -> "BindingResult":
            ...

with:

    @dataclass(frozen=True)
    class BindingContext:
        engine_inventory_sha: str
        package_inventory: PackageResourceInventory
        native_contracts: tuple[NativeStorageContract, ...]
        existing_bindings: tuple["BindingRecord", ...]
        allocator_version: str

and:

    @dataclass(frozen=True)
    class BindingRecord:
        request_id: str
        binding: GoalSlot | GoalSpan | StrategicNumberSlot | TimerSlot
        provenance: BindingProvenance

and:

    @dataclass(frozen=True)
    class BindingResult:
        records: tuple[BindingRecord, ...]
        diagnostics: tuple["BindingDiagnostic", ...]
        manifest_sha: str

Binding is transactional:

    collect requests
      -> validate all requests
      -> allocate in deterministic order
      -> validate collisions
      -> produce manifest
      -> commit result

No partially allocated state escapes the binder.

## 14. Determinism

Allocation order must be stable.

Sort requests by:

1. storage kind;
2. span kind;
3. semantic owner;
4. semantic ID;
5. stability key.

Existing bindings are reused before allocating new resources.

A source edit must not renumber unrelated bindings merely because a new demand appeared earlier in the source.

### POLICY

Binding manifests are persistent artifacts and are part of reproducibility. The v1 in-memory
BindingManifest already has deterministic JSON serialization, duplicate-request rejection, and
duplicate-GoalId rejection.

### OPEN

The final on-disk location and automatic write-back step remain implementation work. The compiler
must still receive a package occupancy inventory before generated storage can safely coexist with
the full Basilisk controller.

## 15. Diagnostics

The binder must expose semantic diagnostics such as:

    RUNTIME-BINDING-MISSING-PROVENANCE
    RUNTIME-BINDING-CONTRACT-MISSING
    RUNTIME-BINDING-CONTRACT-MISMATCH
    RUNTIME-BINDING-GOAL-RANGE
    RUNTIME-BINDING-GOAL-SPAN-RANGE
    RUNTIME-BINDING-GOAL-SPAN-OVERLAP
    RUNTIME-BINDING-GOAL-COLLISION
    RUNTIME-BINDING-SN-ACTIVE
    RUNTIME-BINDING-SN-INVENTORY-MISSING
    RUNTIME-BINDING-SN-JUSTIFICATION-MISSING
    RUNTIME-BINDING-TIMER-RANGE
    RUNTIME-BINDING-TIMER-COLLISION
    RUNTIME-BINDING-PACKAGE-COLLISION
    RUNTIME-BINDING-RAW-NATIVE-ID
    RUNTIME-BINDING-INITIALIZATION-MISSING

These are compiler diagnostics.

The pinned `aoe2-ai-parser` remains the final authority for actual .per syntax and native legality.

## 16. Integration with the current IR

### IMPLEMENTED MIGRATION

The compiler now uses:

    DemandNode
      -> semantic validation
      -> SemanticDemand + LifecycleStorage + GoalSlotRequest
      -> RuntimeBinder
      -> BindingResult + GoalSlot
      -> LifecycleEncoding
      -> deterministic .per

The first migration deliberately preserves the existing lifecycle behavior while removing native storage identity from semantic analysis.

The remaining sections below describe the future storage families and full binding contract; they are not claims that those allocators already exist.

The first migration should change only the storage typing.

Current:

    class SemanticDemand:
        name: str
        goal: int
        ...
        pending_goal: int
        completed_goal: int

Target:

    class SemanticDemand:
        name: str
        lifecycle_storage: "StorageRequestRef"
        lifecycle_values: "LifecycleStateValues"
        ...

with:

    @dataclass(frozen=True)
    class LifecycleStateValues:
        released: int
        active: int
        pending: int
        complete: int

This preserves the current three-transition lifecycle while making the storage/value boundary explicit.

The first migration should retain the existing lifecycle values to isolate the binding refactor from behavioral changes.

Only afterward should lifecycle-value normalization be considered.

## 17. Binding rules for the current compiler slice

Castle, defensive Spearmen, and Wheelbarrow currently need:

    one GoalSlot each
    four lifecycle values each

They do NOT need:

    three GoalSlots each
    GoalSpan
    StrategicNumberSlot
    TimerSlot

That distinction is a required regression test.

## 18. Required tests

### Goal/value typing

- one lifecycle demand produces one GoalSlot request;
- pending/complete values do not produce separate storage requests;
- changing the GoalId does not change lifecycle values;
- changing lifecycle values does not change GoalId ownership.

### GoalSpan

- point command requires POINT_PAIR;
- four-goal extended command requires EXTENDED_4;
- four separate output GoalIds do not become a GoalSpan;
- invalid span width fails;
- overlap fails;
- native contract mismatch fails.

### Ranges

- GoalId 1 and 16000 accepted for scalar storage if package policy permits;
- GoalId 0 and 16001 rejected;
- extended start below native minimum rejected;
- four-goal start above 508 rejected;
- point start uses its own contract range rather than the four-goal range;
- 509..512 are not four-goal starts.

### Strategic numbers

- 511 rejected;
- active SN rejected;
- inactive inventory-approved SN accepted;
- missing inventory rejected;
- missing WHY_NOT_GOAL rejected.

### Timers

- 1 and 50 accepted;
- 0 and 51 rejected;
- duplicate ownership rejected;
- implicit reuse rejected.

### Provenance

Every binding must have complete provenance and the exact inventory hashes.

### Determinism

Same requests + same inventories + same allocator version produce the same manifest.

### Package collision

External occupied IDs block compiler allocation.

### Native backend

The generated artifact must still pass the pinned native backend.

## 19. Evidence boundary

The compiler design must label claims exactly as follows.

### CONFIRMED

Directly documented or directly observed:

- AIRef GoalId range;
- special extended Goal restrictions;
- SN range and current SN guidance;
- timer range;
- current `SemanticDemand` integer fields;
- current analyzer allocation;
- current emitter behavior;
- current native backend boundary.

### POLICY

Deliberate Basilisk choices:

- scalar pool `513..16000`;
- default four-goal span pool `41..508`;
- exclusive TimerSlot ownership;
- WHY_NOT_GOAL for custom SNs;
- persistent binding manifests;
- deterministic allocation order;
- no automatic resource recycling in v1.

### ASSUMPTION / OPEN

Must be proven before implementation depends on it:

- complete package-wide external resource inventory;
- final generated native-storage contract coverage;
- exact lifetime semantics needed for timer/Goal reuse;
- final binding manifest location/versioning policy;
- whether the compiler will be allowed to consume pre-existing numeric bindings from the larger Basilisk controller.

## 20. Non-goals

The binder is not:

- a general scheduler;
- a gameplay manager;
- a runtime allocator;
- a second native parser;
- a universal optimizer;
- a replacement for AIRef;
- a semantic owner of Strategy state;
- a mechanism for inventing new strategic state.

Its job is deliberately narrow:

    semantic storage request
        -> native resource binding
        -> provenance
        -> deterministic lowering

Nothing more.

## 21. Implementation gate

Do not implement the allocator until these are available:

1. typed storage requests in IR;
2. native storage contracts sourced from the checked-in command schema;
3. package occupancy policy;
4. provenance model;
5. deterministic manifest contract;
6. regression tests separating GoalId from GoalValue.

The first implementation should be rejected if it still accepts arbitrary integer GoalIds from semantic analysis.

That would merely move the same bug into a nicer-looking module.
