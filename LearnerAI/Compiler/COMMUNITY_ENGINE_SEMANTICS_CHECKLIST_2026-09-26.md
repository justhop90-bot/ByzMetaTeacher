# Community Engine Semantics Checklist — 2026-09-26

## Purpose

This is the compiler worklist for the missing layer between the checked-in AIRef/native schema and Basilisk's higher-level Demand/Capability model.

The requirement is not to reproduce every community bot or create a second scripting language. The requirement is to capture the accumulated, engine-specific .per craft that experienced scripters repeatedly encode because the native engine behaves that way.

Evidence classes are intentionally separate:

- ENGINE FACT: AIRef/native documentation or reproducible native behavior.
- COMMUNITY PRACTICE: repeated patterns in established community scripts/tutorials.
- COMPILER POLICY: an explicit semantic contract chosen by this compiler.
- OPEN / UNKNOWN: unresolved; never silently promoted into a compiler fact.

## Gate 0 — preserve the architectural boundary

- [x] Keep native syntax/parameter legality owned by AIRef/native backend.
- [x] Keep Basilisk strategy policy out of generic compiler semantics.
- [x] Do not introduce a scheduler, universal manager, runtime simulator, or second .per language.
- [x] Preserve DEMAND -> CAPABILITY -> FEASIBILITY -> ACTION -> PENDING -> WITNESS -> RELEASE/INVALIDATION -> REASSESSMENT.
- [x] Preserve can-* as admission/feasibility, never completion.
- [x] Preserve world-state witnesses as completion authority.
- [x] Preserve transient resource arbitration as execution state, not strategic ownership.

## Gate 1 — persistent Goals, Strategic Numbers, and Timers

### Goals

- [x] Model Goal storage as engine-backed persistent state across rule passes.
- [x] Distinguish same-rule sequential visibility from later-rule persisted visibility.
- [x] Preserve later-writer overwrite semantics as an explicit engine fact rather than treating a Goal as immutable compiler memory.
- [x] Keep Goal spans/contiguous multi-goal outputs distinct from independent Goal outputs.
- [x] Reserve storage collision-free through package inventory/binding.
- [ ] Add command-specific semantics for all Goal-writing native commands that consume multiple consecutive Goal slots.
- [ ] Add warnings for Goal reuse that changes role from persistent state to scratch/output without an explicit lifetime.

### Strategic Numbers

- [x] Treat SNs as a persistent engine control namespace, not as generic integers.
- [x] Bind SN storage explicitly and collision-safely.
- [x] Record that an SN may change built-in engine behavior.
- [ ] Complete native SN semantic metadata for all checked-in SNs that the compiler exposes.
- [ ] Distinguish native behavior-changing SNs from genuinely unused/custom-safe SNs.
- [ ] Add provenance/version checks when a strategy relies on an SN whose semantics changed across patches.

### Timers

- [x] Treat timers as explicit engine state.
- [x] Keep timer-triggered conditions distinct from strategic truth and world-state completion.
- [x] Preserve explicit enable/rearm/disable behavior.
- [ ] Add timer lifetime/owner analysis beyond the existing storage-order pass.
- [ ] Add diagnostics for timer state that can be left running after its controlling demand is released.
- [ ] Add explicit distinction between timing/cooldown state and durable strategic state.

## Gate 2 — rule/pass ordering and source precedence

- [x] Emit and retain rule_order and within_rule_order.
- [x] Classify same-rule writer -> reader as sequentially visible.
- [x] Classify later-rule writer -> reader as persisted engine state.
- [x] Reject reader-before-first-writer dependencies.
- [x] Preserve source attribution through the ordering analysis.
- [ ] Model repeated pass eligibility as a first-class semantic concept rather than assuming one-shot rule execution.
- [ ] Model disable-self lifetime explicitly.
- [ ] Detect later overwrites of persistent Goal/SN state when earlier consumers can be preempted or starved.
- [ ] Detect unreachable/never-runnable rules caused by earlier persistent state, mutually exclusive guards, or terminal disable-self.
- [ ] Detect rules that are syntactically valid but behaviorally open-loop because no later rule can observe their state transition.
- [x] Track action sequencing inside one emitted rule without inventing a false pass boundary.
- [ ] Track the effective source graph before claiming global rule order once load/load-if-* is supported.

## Gate 3 — asynchronous build/train/research lifecycles

### Common contract

- [x] Separate action issuance from engine-side completion.
- [x] Preserve ISSUED versus PENDING.
- [x] Treat pending as outstanding engine work, not proof of completion.
- [x] Require native feasibility before action issuance.
- [x] Require a world-state witness for completion.
- [x] Preserve strategic intent across ordinary feasibility failure.
- [x] Keep release/invalidation causally downstream of evidence.

### Build

- [x] Encode can-build as feasibility.
- [x] Encode up-pending-objects as an anti-duplication/work-queue guard where applicable.
- [x] Encode building world-state count as completion evidence.
- [ ] Add native building-foundation/status semantics so the compiler can distinguish foundation, pending, active construction, and completed building where the engine exposes it.
- [ ] Add placement-specific witness contracts for DUC/up-build-line/point-building behaviors.
- [ ] Detect a build request that can repeatedly reissue because the pending guard is too narrow.

### Train

- [x] Encode can-train as feasibility.
- [x] Distinguish current, queued, and current+queued target semantics.
- [x] Preserve training intent when the queue/resource/building capability is temporarily unavailable.
- [ ] Add queue-capacity semantics for commands that can fill production queues.
- [ ] Add provider-loss semantics when the production building disappears or becomes unusable.

### Research

- [x] Encode can-research as feasibility.
- [x] Use research-completed as completion witness.
- [x] Prevent timers from substituting for research completion.
- [ ] Model research availability, affordability, queue state, and completion as separate facts throughout the generic IR.
- [ ] Add monotonic capability classification for completed research/age transitions.

## Gate 4 — resource arbitration

- [x] Keep current transient ACTION_EXCLUSION conflict model.
- [x] Keep resource ownership attached to the execution claim rather than moving strategic ownership.
- [x] Require explicit release paths for persistent claims.
- [x] Preserve sn-resource-control as exceptional/global native behavior rather than a universal scheduler abstraction.
- [ ] Add evidence-backed distinction between native resource-control SNs and compiler-local transient claims.
- [ ] Diagnose resource claims that can starve a persistent demand indefinitely.
- [ ] Diagnose conflicting arbitration owners deterministically.
- [ ] Add recovery semantics for resource shortages without treating them as capability loss.
- [ ] Add explicit opportunity-cost versus resource-feasibility distinction at the generic IR boundary.

## Gate 5 — DUC/search/target machinery

- [x] Record DUC as a major native-semantic frontier rather than pretending ordinary facts cover it.
- [x] Record local/remote search limits and performance implications as native facts.
- [ ] Model search-list lifetime and reset semantics.
- [ ] Model filter state, list selection, and retained search state.
- [ ] Track target invalidation when an object leaves/dies/moves/becomes illegal.
- [ ] Distinguish search evidence from durable strategic truth.
- [ ] Add search cardinality metadata and qualitative cost classes.
- [ ] Add diagnostics for stale target use and unreset search state.
- [ ] Add point/target output GoalSpan contracts for all supported DUC point-returning commands.
- [ ] Add path-distance cost metadata and hot-loop diagnostics.
- [ ] Add native fixtures for common search -> target -> action chains.

## Gate 6 — attack machinery

- [x] Record attack-now/attack-groups as stateful engine machinery, not one-shot actions.
- [x] Record timer/cooldown and persistent SN control patterns used by community scripts.
- [ ] Model attack mode as durable engine control state with explicit activation and release.
- [ ] Model attack target/search state separately from strategic demand ownership.
- [ ] Add attack-group lifecycle contracts and release diagnostics.
- [ ] Add target invalidation/reassignment semantics.
- [ ] Add native/community fixtures for timed attack loops, stop conditions, and restart conditions.
- [ ] Add DUC group/target integration only after retained-search semantics are explicit.

## Gate 7 — capability loss and recovery

- [x] Require previous capability truth before declaring capability loss.
- [x] Distinguish provider/capability world-state from ordinary execution feasibility.
- [x] Distinguish capability loss from ordinary feasibility failure, so false can-* never becomes loss.
- [x] Detect only true -> false capability transitions.
- [x] Detect false -> true recovery transitions.
- [x] Preserve original strategic demand identity through loss/recovery.
- [x] Preserve original execution mapping on recovery.
- [x] Keep multiple execution mappings independently recoverable.
- [x] Do not invent an engine Boolean action-failure channel.
- [x] Do not let recovery bypass can-*.
- [x] Prevent recovery from overriding strategic invalidation.
- [x] Keep capability acquisition distinct from demand completion.
- [ ] Extend capability observations beyond the current explicit observation set into generic BUILD/TRAIN/RESEARCH provider capabilities.
- [ ] Classify monotonic capabilities (age/research) separately from recoverable providers (buildings/infrastructure).
- [ ] Add capability-loss fixtures for provider destruction and later recovery.

## Gate 8 — native community craft registry

- [x] Create a machine-readable evidence-backed community engine semantics registry.
- [x] Record evidence class and source for each practice.
- [x] Record compiler action and runtime truth separately.
- [x] Record build/train/research lifecycle contracts.
- [x] Record Goal/SN/Timer semantics.
- [x] Record rule/pass, pending, resource arbitration, recovery, DUC, attack, and load/preprocessor practices.
- [x] Make the registry self-validating for duplicate identities and contradictory lifecycle contracts.
- [ ] Promote registry entries into active diagnostics only where native support is sufficient.
- [ ] Keep evidence-only practices explicitly non-enforcing until parser/IR support exists.
- [ ] Add golden .per fixtures for every promoted community practice.

## Gate 9 — load/preprocessor program graph

- [ ] Parse and resolve load reachability.
- [ ] Parse and resolve load-if-defined and related conditional loading.
- [ ] Preserve physical source locations through the expanded graph.
- [ ] Detect duplicate inclusion and conditional shadowing.
- [ ] Compute effective rule/source order across loaded files.
- [ ] Include loaded storage consumers in Goal/SN/Timer occupancy analysis.
- [ ] Refuse to claim whole-program completeness while the effective source graph is unresolved.

## Gate 10 — performance as behavioral semantics

- [x] Record AIRef command-performance evidence in the compiler's research model.
- [ ] Add qualitative cost classes to DUC/pathing/build-at-point/movement commands.
- [ ] Add repeated-pass cardinality warnings.
- [ ] Add search-list size warnings.
- [ ] Add movement queue/backlog warnings for excessive repeated movement commands.
- [ ] Add a deterministic benchmark fixture set for known expensive primitives.
- [ ] Keep performance warnings separate from native legality findings.

## Gate 11 — evidence governance

- [x] Distinguish ENGINE FACT, COMMUNITY PRACTICE, COMPILER POLICY, and OPEN/UNKNOWN.
- [x] Attach source URLs/provenance to community-practice records.
- [ ] Add patch/version identity to every engine behavior record that can change across DE updates.
- [ ] Add confidence/strength metadata for community practices.
- [ ] Require convergence from more than one community example before promoting a practice to a strong recommendation.
- [ ] Preserve contradictory community observations instead of collapsing them into one false rule.
- [ ] Keep “community usually does this” separate from “the engine requires this.”

## Gate 12 — tests and acceptance

- [x] Unit-test capability transition classification.
- [x] Unit-test community practice registry consistency.
- [ ] Add native zero-findings fixtures for each new promoted semantic contract.
- [ ] Add negative fixtures for pending-as-completion, timing-as-completion, missing can-* feasibility, stale DUC targets, and open-loop attack state.
- [ ] Add source-order fixtures for later overwrite, disable-self, and loaded-file precedence.
- [ ] Add recovery fixtures proving identity preservation across capability loss/recovery.
- [ ] Keep full compiler unittest count and native acceptance fixtures as release gates.
- [ ] Keep the runtime game as the authority for gameplay quality, never as proof that malformed/compiler-incorrect code is acceptable.

## Current implementation tranche

Implemented in this pass:

1. LearnerAI/Compiler/semantic/community_engine.py
   - evidence classes;
   - community-practice registry;
   - Goal/SN/Timer contracts;
   - rule/pass ordering contract;
   - pending/build/train/research contracts;
   - transient resource arbitration contract;
   - DUC/search and attack machinery evidence contracts;
   - capability-loss/recovery transition classifier;
   - load/preprocessor and performance evidence records.

2. LearnerAI/Compiler/ir/strategy.py + LearnerAI/Compiler/ir/strategy_runtime.py
   - explicit EXECUTION_FEASIBILITY versus PROVIDER_WORLD_STATE capability observation kinds;
   - previous capability-observation history;
   - true->false loss detection;
   - false->true recovery detection;
   - strategic reassessment reasons for loss/recovery;
   - original demand identity preserved;
   - strategic invalidation suppresses recovery signaling;
   - deterministic transition fingerprinting.

3. LearnerAI/Compiler/semantic/__init__.py
   - exported engine-semantics contracts.

## What is deliberately not claimed

The compiler now knows the documented/community contracts above, but it is not yet a general .per frontend for all of them.

In particular, DUC, attack machinery, complete Strategic Number semantics, recurrent rule eligibility, disable-self, later-overwrite/preemption analysis, and the load graph remain evidence-backed frontiers until their native syntax/IR support is implemented.

The correct milestone is therefore: community engine semantics are now explicit and typed, with the recovery slice actually enforced; the remaining frontier is native execution coverage, not more abstract lifecycle vocabulary.
