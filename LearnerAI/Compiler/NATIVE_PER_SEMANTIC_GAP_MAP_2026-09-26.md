# Native .per Semantic Gap Map — 2026-09-26

## Purpose

This document maps the gap between the native AoE2 .per engine and the current Basilisk generic compiler substrate.

It is an authority map, not a wish list. Each row answers four questions:

1. What the engine/community actually provides.
2. What the current compiler knows.
3. What remains semantically missing.
4. What architectural component must own the missing behavior.

The compiler must not promote a community idiom into an engine fact merely because the idiom is common.

## Evidence hierarchy

ENGINE FACT: AIRef/native documentation or reproducible engine behavior.

COMMUNITY PRACTICE: repeated established .per usage, guides, community bots, or benchmark work.

COMPILER POLICY: an intentional contract of this compiler.

OPEN / UNKNOWN: unresolved. The compiler must fail closed where correctness depends on it.

Primary native references:
- https://airef.github.io/
- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/resources/articles/intro-to-commands.html
- https://airef.github.io/resources/articles/defconsts-goals-sns-1.html
- https://airef.github.io/resources/articles/enmipho-intro-to-duc.html
- https://airef.github.io/resources/articles/command-performance.html
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/tables/load-if.html
- https://airef.github.io/tables/up-patch-notes.html

Community references:
- https://github.com/niektb/AI
- https://github.com/lewisc64/aoe2ai
- https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476
- https://airef.github.io/resources/articles/enmipho-intro-to-duc.html

## Gap matrix

| Native semantic family | Native/community knowledge | Current compiler coverage | Gap | Required owner |
|---|---|---|---|---|
| Command syntax/parameter typing | Native command and parameter contracts | CONNECTED | Full generic command coverage remains broader than semantic adapters | Native schema / support-state registry |
| Rule recurrence | Facts/actions are repeatedly evaluated as rules; firing depends on current facts and rule state | PARTIAL | No explicit recurrent eligibility model; no complete firing/preemption reasoning | Rule Execution Semantics |
| Rule source order | Emitted rule order matters to first visibility and persistent state interactions | PARTIAL/IMPLEMENTED | Does not yet model later overwrite, starvation, or unreachable rules | Rule Execution Semantics |
| Same-rule sequencing | Commands in one rule execute in emitted sequence | IMPLEMENTED | Need broader command-specific sequencing contracts | Rule Execution Semantics |
| disable-self | A rule can permanently disable itself after firing | EVIDENCE-ONLY | Lifetime and downstream reachability are not modeled | Rule Execution Semantics |
| Goal state | Persistent integer state; many commands read/write Goal operands; some commands write consecutive Goal spans | STRONG STORAGE / PARTIAL SEMANTICS | Command-specific mutation/output behavior and scratch-vs-persistent roles are not fully modeled | Engine State Semantics |
| Strategic Numbers | Persistent engine controls; active/conditional/obsolete SNs differ | PARTIAL | Complete native semantic inventory and patch-aware control contracts missing | Engine Control Semantics |
| Timers | Finite timer namespace with enable/rearm/disable and timer-triggered facts | STORAGE COMPLETE / SEMANTICS PARTIAL | Lifetime, owner, rearm, and cleanup semantics not fully modeled | Engine State Semantics |
| can-* facts | Facts test native execution admissibility; some UP commands are fact/action duals | STRONG for current adapters | Dual fact/action commands and command-specific admission behavior not generalized | Native Command Semantics |
| Action issuance | Actions request engine work; no generic Boolean success channel | STRONG typed lifecycle | Broader native action-specific issuance behavior remains outside adapter set | Action Semantics |
| Pending construction work | Pending objects/foundations can suppress duplicate requests; pending is not completion | PARTIAL/STRONG BUILD | Foundation/progress/cancellation semantics incomplete | Async Work Semantics |
| Pending production work | Pending/queued counts can affect total-count observations | PARTIAL | Queue capacity and queued-vs-training-vs-existing semantics not generalized | Production Async Semantics |
| Research lifecycle | Availability, affordability, feasibility, issuance, completion are distinct | STRONG for current adapters | Queue/cancellation/provider semantics incomplete | Research Async Semantics |
| World-state completion | Building/unit/research state proves completion | STRONG | DUC-specific and progress-state witnesses remain missing | Witness Semantics |
| Resource arbitration | Community scripts use temporary resource controls and protected strategic intent | PARTIAL | Native resource-control SNs and compiler claims not unified | Resource Arbitration |
| Search lists | DUC has local/remote lists with hard capacities and mutable search state | EVIDENCE-ONLY | Search lifetime, reset, filters, targets and provenance absent | DUC State Semantics |
| DUC filters | Filters persist until reset/full-reset and affect later searches | EVIDENCE-ONLY | No retained filter state or stale-filter diagnostics | DUC State Semantics |
| DUC target objects | Lists become target sets; object IDs are transient world references | EVIDENCE-ONLY | No target lifetime/invalidation semantics | DUC Target Semantics |
| DUC Goal outputs | Search-state/point/cost commands write one or more consecutive Goal outputs | STORAGE PARTIAL | Command-specific output-span contracts incomplete | GoalSpan Semantics |
| DUC groups | Groups can replace repeated search/filter work and persist as engine state | EVIDENCE-ONLY | Group identity/lifetime/invalidation absent | DUC Group Semantics |
| Attack machinery | attack-now, attack groups, town-size attack, SN/timer controls form persistent engine behavior | EVIDENCE-ONLY | No attack-mode lifecycle or release model | Attack Engine Semantics |
| Exploration coupling | Attack loops depend on exploration and explored targets | EVIDENCE-ONLY | No generic attack/exploration dependency graph | Attack Engine Semantics |
| Recovery | Community scripts preserve strategic intent through temporary blockage and re-enter through native guards | PARTIAL/IMPLEMENTED capability slice | Provider loss/recovery not generalized | Recovery Semantics |
| Load graph | #load and #load-if-defined change effective source program | EVIDENCE-ONLY | Effective source graph absent | Source Graph / Preprocessor |
| Rule/cardinality cost | Search, pathing, DUC and other commands have measurable pass costs | EVIDENCE-ONLY | No compiler cost model or hot-loop diagnostics | Performance Semantics |
| Evidence provenance | Native/community sources differ in scope and confidence | STRONG in strategy layer | Engine behavior records need patch/version and strength metadata | Evidence Registry |
| Cross-patch behavior | AIRef/UserPatch notes document behavior differences and fixes | PARTIAL | No replayable native semantic snapshots | Native Version Profile |

## Critical semantic boundaries

### Persistent state is not generic memory

Goal, SN, Timer, DUC list, DUC filter, attack mode, and native queue state are different engine mechanisms. The compiler must model the native mechanism first and expose a typed contract above it.

### Feasibility is not capability

can-build, can-train, can-research, and affordability facts describe whether execution is admissible now. Resource shortage, queue blockage, or another failed feasibility condition does not prove capability loss.

Capability loss requires a previously observed capability/provider becoming unavailable.

### Pending is not completion

Construction pending, training queued, and research in progress are outstanding work states. World-state evidence proves completion.

### Source order is not execution order

Source order establishes precedence and visibility. Actual firing depends on facts, disabled state, and prior engine mutations. A rule_order value is never evidence that the rule actually executed.

### DUC is a stateful subsystem

DUC is not a bag of stateless commands. Search lists, filters, targets, groups, Goal outputs, and timers can persist across rules. This is the largest remaining native semantic gap.

## Coverage stages

A native construct should move through:

NATIVE_KNOWN
-> NATIVE_TYPED
-> SEMANTICALLY_ADAPTED
-> ENGINE_SEMANTICS_MAPPED
-> EXECUTABLE_SAFE

ENGINE_SEMANTICS_MAPPED means the compiler knows the native lifetime, state effects, ordering constraints, inputs/outputs, completion/recovery semantics, and evidence needed by the semantic layer.

The existing support-state registry currently stops one conceptual step short of this distinction. That is the central next compiler improvement.

## Acceptance

The gap is closed when an expert .per construct can be traced:

native syntax
-> native command contract
-> engine state effects
-> rule/pass behavior
-> semantic IR
-> storage binding
-> feasibility/action/pending/witness
-> release/recovery
-> deterministic .per
-> native parser zero-findings.

The companion Philosopher's Stone architecture defines the components and gates that implement this chain.
