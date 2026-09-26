# Compiler Forensic Audit — 2026-09-26

## Scope

Authoritative target: generic AoE2 `.per` compiler. Basilisk/Byzantine strategy is a downstream client and is not part of the generic compiler exit condition.

Repository head at audit start: 159687d39e30bd9204ec2f9e5dad09bac7da54c5. The audit also includes the subsequent generic storage repair commits on `main`. Final verified code head for this pass: 8bec6c7c38d2c42926ed64adcc3659042fcbbb30.

External evidence was cross-checked against the current AIRef command/schema corpus, AIRef data limits, DUC and performance material, UserPatch patch notes, aoe2-ai-parser diagnostics, and public prior-art compiler projects.

## Core conclusion

The compiler foundation is healthy enough to continue, but it is not yet a general `.per` compiler. Its semantic adapter layer currently covers 28 native commands against 385 commands in the checked-in AIRef command schema. The native schema is therefore much broader than the compiler's executable semantic vocabulary.

The most important architectural split is now:

    Generic Compiler
      -> native AoE2 knowledge
      -> semantic `.per` model
      -> storage/package binding
      -> diagnostics
      -> deterministic emitter
      -> native backend

    Reference Bot
      -> generic client of compiler

    Basilisk
      -> separate strategy/gameplay client

Do not move Basilisk StrategyProfile or Byzantine GameData into the generic core merely to increase feature count.

## Evidence classes

- ENGINE FACT: directly documented by AIRef/native backend or reproducibly observed.
- COMMUNITY PRACTICE: repeatedly demonstrated by community scripts, guides, benchmarks, or competitive bots.
- COMPILER POLICY: deliberate deterministic compiler behavior.
- OPEN / UNKNOWN: not established; fail closed when correctness depends on it.

## Forensic matrix

| Area | Current state | Evidence | Status | Generic relevance | Repair |
|---|---|---|---|---|---|
| AST/parser | Small demand DSL; exact source locations now propagate through IR | compiler tests; parser/AST implementation | CONNECTED | P0 | Keep native expressions visible; expand only where semantic need requires |
| Native schema | 385 native commands, 121 parameter families in checked-in inventories | AIRef command/parameter inventories | CONNECTED but narrow semantically | P0 | Add explicit native support-status model; do not pretend 28 semantic adapters equal full compiler coverage |
| Semantic adapters | 28 primitive adapters; analyzer rejects known commands with no adapter | `primitives/registry.py`, `semantic/analyzer.py` | BLOCKED for general `.per` coverage | P0/P1 | Separate native-known/native-typed/semantic-adapted/executable-safe/unsupported states |
| Lifecycle ownership | Typed ownership, writer/consumer analysis, deterministic diagnostics | semantic ownership pass + tests | CONNECTED | P0 | Generalize later to ordinary persistent state |
| Completion/release/invalidation | Typed causal contracts and source-order validation | semantic passes + tests | CONNECTED | P0 | Preserve as generic compiler primitives |
| Action issuance | ISSUED/PENDING distinction implemented; native action return remains unavailable | emitter/analyzer + tests | CONNECTED | P0 | Add generic capability-loss recovery above issuance |
| Resource arbitration | Transient ACTION_EXCLUSION modeled; no scheduler | resource conflict pass | CONNECTED / deliberately narrow | P1 | Generalize only into evidence-backed conflict relations |
| Goal binding | Deterministic GoalSlot/GoalSpan binding with package occupancy | runtime binding + manifests | CONNECTED | P0 | Preserve namespace collision guarantees |
| Lifecycle Goal range | Previous allocator could assign Goal 16000 even though encoded lifecycle values need four higher values | native Goal range + lifecycle encoding | REPAIRED | P0 | Enforce Goal <= 15996 for lifecycle storage |
| Strategic Number binding | Typed inventory-aware binding, WHY_NOT_GOAL justification, deterministic allocation, collision checks, manifest provenance | AIRef SN limits/inventory | CONNECTED / VERIFIED | P0 | Add broader semantic SN usage contracts |
| Timer binding | Added typed TimerSlot allocation, explicit initialization policy, deterministic range/collision checks | AIRef timer range + timer initialization guidance | IMPLEMENTED, pending final CI | P0 | Connect timer allocation to actual lowering when timer semantics are introduced |
| Package binding | Goal package occupancy exists; SN/timer namespace separation now represented | runtime binding | INCOMPLETE | P0 | Expand package inventory to all native storage namespaces |
| Source-order analysis | Lifecycle-specific source order exists; generic state-order analysis does not | emitter order + lifecycle contracts | UNFINISHED | P1 | Model cross-rule read/write visibility and same-pass assumptions |
| Same-pass action sequencing | Multiple actions inside one emitted rule are sequential; current emitter preserves this | emitter output + native rule semantics | CONNECTED | P0 | Never insert a false pass boundary between actions in the same rule |
| DUC | Native schema knows DUC commands, but semantic adapter layer has no real DUC model | AIRef DUC docs + 28-adapter registry | BLOCKED | P1 | Build search/list/group/target lifetime contracts |
| Flare | Engine supports up-find-flare/up-find-player-flare and point Goal spans; live Skirmish probe succeeded | AIRef + user runtime test | COMMUNITY-OBSERVED / ENGINE-SUPPORTED | P1/P2 | Make a minimal compiler fixture, not a Basilisk feature |
| Search-state safety | No generic retained-search evidence model | AIRef + aoe2-ai-parser diagnostics | UNFINISHED | P1 | Add retained list provenance and target-safety diagnostics |
| Performance | No compiler cost model; native research is available | AIRef performance benchmarks | UNFINISHED | P2/P3 | Add qualitative cost classes and cardinality-sensitive warnings |
| GameData/CivProfile | Strong typed factual model but currently Byzantine-heavy | compiler IR + current manifests | FUNCTIONALLY-DISCONNECTED from generic core | P2 client extension | Retain generic data contracts; move civ-specific population downstream |
| StrategyProfile | Large Basilisk-specific strategy layer already exists | `ir/strategy.py` | CLIENT EXTENSION | P2 | Keep behind domain adapter boundary |
| StrategyRuntimeState | Sophisticated live strategic evidence layer exists | `ir/strategy_runtime.py` | CLIENT EXTENSION | P2 | Preserve reusable observation/evidence contracts without importing Basilisk policy |
| Native backend | Pinned parser boundary, staged zero-findings promotion | backend tests/workflow | CONNECTED | P0 | Keep frozen/pinned |
| Diagnostics | Aggregated, deterministic, source-attributed semantic/native findings | diagnostics + tests | CONNECTED | P0 | Extend diagnostic vocabulary as generic coverage grows |
| Community-practice registry | Specification exists; typed registry not implemented | COMMUNITY_PER_PRACTICE_SPEC.md | UNFINISHED | P2 | Build evidence-backed practice records and fixtures |
| Reference bot | No generic reference bot yet | repository structure | UNFINISHED | P2 | Build only after generic compiler seams are stable |

## Critical architectural findings

### 1. Native knowledge is broader than semantic knowledge

AIRef currently supplies a large native vocabulary. The compiler correctly refuses to invent semantic meaning for commands it has not adapted, but the resulting generic coverage is only 28 semantic adapters versus 385 known commands.

This is not a reason to add 357 arbitrary adapters. The compiler needs a support-state model so the distinction is machine-visible:

    native-known
    native-typed
    semantically-adapted
    executable-safe
    unsupported

Unknown semantic meaning must remain explicit.

### 2. Storage is a compiler concern, not Basilisk strategy

Goals, Goal spans, SNs, and Timers form the engine's constrained memory system. AIRef documents Goals 1..16000, SNs 0..511, Timers 1..50, and special restrictions for multi-goal operations. This belongs in generic compiler infrastructure.

The lifecycle allocator now reserves headroom for encoded lifecycle values instead of treating Goal 16000 as an ordinary lifecycle storage location.

### 3. Same-pass ordering must be modeled precisely

An action list inside one `.per` rule is sequential. `up-find-flare` followed by `up-send-flare` inside the same action section is a valid same-pass sequence. A separate rule is a pass boundary and may require a latch or other persistent state.

The compiler must therefore distinguish:

    SAME RULE: sequential action visibility
    NEXT RULE/PASS: state persists only through engine-backed storage

It must not flatten both cases into one generic 'writer before reader' rule.

### 4. DUC is the largest missing native-practice layer

AIRef documents local/remote search, search-state, filters, ranges, sorting, groups, target-point/object control, and related point operations. aoe2-ai-parser already warns about unsafe retained search evidence and unscoped DUC targets.

The compiler currently has almost none of this semantic vocabulary. DUC is therefore a primary P1 compiler frontier.

### 5. Basilisk strategy is valuable prior art but wrong as compiler scope

GameData/CivProfile, StrategyProfile, and StrategyRuntimeState contain reusable concepts such as evidence attribution, typed observations, persistent strategic demand, capability intent, and deterministic reassessment. The Byzantine factual population and posture policies themselves are downstream client policy.

Do not remove useful generic contracts. Do not let Byzantine policy define their interfaces.

## Ordered repair queue

### P0 — generic correctness/reproducibility

1. Native support-status model for all checked-in commands. **Implemented and CI-verified.**
   Files: `primitives/native_schema.py`, `primitives/registry.py`, `semantic/analyzer.py`, diagnostics/tests.
   Goal: make native-known/native-typed/semantic-adapted/executable-safe/unsupported explicit.
   No source-language expansion required.

2. Complete namespace-safe storage binding.
   Files: `runtime_binding.py`, binding tests, runtime binding contract.
   Goal: Goal/GoalSpan/SN/Timer package inventory, provenance, collision detection, deterministic manifests.
   Current generic SN/Timer binding tranche is in progress.

3. Generic package/resource inventory.
   Goal: represent externally occupied Goal/SN/Timer storage explicitly rather than assuming generated-file isolation.

4. Preserve deterministic source file/line/column attribution through every future semantic layer.

### P1 — major `.per` capability

5. Non-lifecycle source-order analysis.
   Model same-rule sequential action flow separately from cross-rule pass boundaries.

6. Capability-loss/recovery contract.
   Preserve persistent demand through temporary capability loss without inventing a scheduler.

7. DUC semantic model.
   Search list, search state, filters, sorting, groups, target safety, point operations, path-distance operations, target invalidation, focus-player semantics.

8. Load/preprocessor package graph.
   Resolve #load and #load-if reachability and connect source/package diagnostics.

### P2 — community/meta

9. Community-practice registry.
10. Golden fixtures for documented idioms.
11. Generic reference-bot contract and initial client.
12. FlareMesh integration fixture.

### P3 — research/performance

13. Evidence-backed command cost taxonomy.
14. DUC cardinality and repetition warnings.
15. Path-distance/sort/fanout hot-path diagnostics.
16. Runtime benchmark harness.

### P4 — experimental

17. Spatial coordination protocols such as FlareMesh.
18. Advanced cooperative goal/SN/flare communication patterns.
19. Tournament-safe XS adapter, only after a separate evidence contract exists.

## Explicitly demoted

These no longer block generic compiler completion:

- full Byzantine 145-node GameData ingestion;
- full Byzantine research-cost/time/effect population;
- Byzantine Castle strategy completion;
- full Basilisk strategy ingestion;
- Byzantine posture tuning;
- Basilisk gameplay repairs.

These remain client work unless they expose a generic compiler primitive.

## External evidence

AIRef:
- https://airef.github.io/commands/commands-index.html
- https://airef.github.io/parameters/parameters-index.html
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/resources/articles/command-performance.html
- https://airef.github.io/resources/articles/logical-operators.html
- https://airef.github.io/resources/articles/leif-duc-tutorial-intro.html
- https://airef.github.io/tables/load-if.html
- https://airef.github.io/tables/up-patch-notes.html
- https://airef.github.io/resources/articles/xs-for-tournaments.html

Other tooling/prior art:
- https://github.com/joerollman/aoe2-ai-parser
- https://github.com/01010100b/AgeScript
- https://github.com/JOTworks/AgeOfPython
- https://github.com/lewisc64/aoe2ai
- https://github.com/teshiba/LibAoe2AISharp

## Acceptance definition

The generic compiler phase is mature when an expert `.per` author can use documented engine primitives without the compiler silently confusing native legality, semantic meaning, compiler policy, and experimental community practice.

The compiler must be able to answer, deterministically:

- Is the native construct legal?
- What storage namespace does it consume?
- Who owns that state?
- Who writes it and who reads it?
- Is the dependency same-rule or cross-pass?
- What proves an action can execute?
- What world evidence proves completion?
- What survives temporary failure?
- Is package storage collision-free?
- Is the pattern known community practice, compiler policy, or open research?
- What exact source location produced the finding?

That is the compiler target. The bot comes after the substrate is honest.
## Verification for this pass

GitHub Actions compiler run on final code head 8bec6c7c38d2c42926ed64adcc3659042fcbbb30:

- Native generated Basilisk fixture: finding_count=0.
- Native strategy vertical-slice fixture: finding_count=0.
- Native strategy-runtime fixture: finding_count=0.
- Native explicit-invalidation fixture: finding_count=0.
- Full compiler unittest suite: Ran 258 tests in 1.264s, OK.

The separate Basilisk Validator workflow is intentionally not part of this generic compiler repair gate. At the time of this record it was still executing independently.

## Native support-state verification

Final compiler head for this slice: 010b0b63a7f4eeb5acc464fbb226dcc072b7014e.

The support model is deterministic and monotonic:

    NATIVE_KNOWN
      -> NATIVE_TYPED
      -> SEMANTICALLY_ADAPTED
      -> EXECUTABLE_SAFE

with `UNSUPPORTED` as the terminal rejection state whenever a command is absent, malformed, lacks a semantic adapter, or has an adapter contract that cannot be proven executable-safe.

Focused tests cover each state, deterministic diagnostic chains, unknown commands, malformed metadata, adapter-contract mismatch, the real checked-in AIRef `current-age` operator placeholder, and compiler rejection of known-but-unadapted native commands.