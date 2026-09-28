# Native Engine-State / Control-Effect Tranche — 2026-09-27

## Purpose

Close the compiler's current engine-semantic hole at the correct architectural seam.

The repository already has a native command schema, a primitive-level semantic support ladder, a community-engine evidence registry, persistent-state analysis, recurrent execution analysis, and a pass scheduler. The remaining defect is duplication: the compiler's Goal, Strategic Number, Timer, and rule-control semantics are partly implemented, but the native effect identity is maintained independently by several analyzers and is not represented by the same support-state gate used by the semantic primitive layer.

This tranche makes native engine-state/control effects an explicit, evidence-backed catalog and promotes those commands to `ENGINE_SEMANTICS_MAPPED` without pretending that they are ordinary demand primitives.

## External evidence reviewed

- AIRef data limits: https://airef.github.io/resources/articles/data-limits.html
  - Goals, Strategic Numbers, Timers, and rule/cardinality limits are native storage constraints rather than compiler policy.
- AIRef command reference: https://airef.github.io/resources/articles/intro-to-commands.html
  - Native command kinds, typed parameters, operator prefixes, and command syntax.
- AIRef Strategic Number index: https://airef.github.io/strategic-numbers/sn-index.html
  - Strategic Numbers form a persistent native control surface with patch/civ-specific behavior.
- AIRef scripting example material: https://airef.github.io/resources/articles/swgb-scripting.html
  - Recurrent timer, Goal, Strategic Number, and disable-self patterns.
- aoe2ai: https://github.com/lewisc64/aoe2ai
  - Current community authoring system translates recurrent/high-level intent into large sets of native Strategic Number, Timer, Goal, DUC, and attack operations.
- aoe2-ai-parser:
  https://github.com/joerollman/aoe2-ai-parser
  - Native syntax/package validation is broad and should remain delegated to the native backend; semantic support is a different layer.
- AlphaScripter: https://github.com/mboop127/AlphaScripter
  - Runtime/evolutionary evaluation exists elsewhere; it does not replace static engine-state semantics.

## Corrected diagnosis

The largest architectural hole is no longer the absence of a semantic-contract type. That seam already exists.

The current gap is that the contract is only executable-facing for the existing primitive adapter island, while engine-state commands used by the rule machine are separately hard-coded in `persistent_state.py`, `recurrent_execution.py`, and `pass_scheduler.py`.

The target layering is:

```
native schema
    -> native engine-effect catalog
    -> semantic analyzer / recurrent scheduler
    -> capability/lifecycle semantics
    -> deterministic emitter
    -> native parser validation
```

The catalog describes engine facts. It does not become strategy policy, a second expression language, or a runtime simulator.

## Implemented checklist

### A. Engine-state/control inventory

- [x] Explicit Goal state effects.
- [x] Explicit Strategic Number state effects.
- [x] Explicit Timer state effects.
- [x] Explicit `disable-self` rule-control semantics.
- [x] Explicit `up-jump-rule` control-transfer semantics.
- [x] Explicit support for native `Fact/Action` command kinds.
- [x] Explicit typed-prefix dependency metadata for native Goal/SN operands.
- [x] Evidence source on every catalog contract.
- [x] Schema compatibility validation for every catalog contract.

Covered native commands:

```
set-goal
goal
up-compare-goal
up-modify-goal

set-strategic-number
strategic-number
up-compare-sn
up-modify-sn

enable-timer
disable-timer
timer-triggered
up-set-timer
up-timer-status

disable-self
up-jump-rule
```

### B. Support-state enforcement

- [x] Preserve the existing primitive path:
  `NATIVE_KNOWN -> NATIVE_TYPED -> SEMANTICALLY_ADAPTED -> ENGINE_SEMANTICS_MAPPED -> EXECUTABLE_SAFE`.
- [x] Promote mapped non-primitive engine-state/control commands to `ENGINE_SEMANTICS_MAPPED` while preserving `EXECUTABLE_SAFE` for commands that already have complete primitive adapters.
- [x] Keep those commands distinct from `EXECUTABLE_SAFE` primitive bindings.
- [x] Keep unknown native commands fail-closed.
- [x] Do not promote a mapped command whose checked-in native schema kind disagrees with its contract.
- [x] Accept native `Fact/Action` commands as structurally typed when the native schema declares them that way.

### C. Analyzer integration

- [x] Remove the second persistent-state command inventory from `semantic/persistent_state.py`.
- [x] Derive Goal/SN/Timer state accesses from the native engine-effect catalog.
- [x] Derive typed Goal/SN operand dependency recognition from the catalog.
- [x] Preserve existing source-order, cross-rule persistence, overwrite, starvation, and open-loop diagnostics.
- [x] Add Goal mutation dependency coverage for `up-modify-goal`.
- [x] Add Goal comparison dependency coverage for `up-compare-goal`.

### D. Hostile regression coverage

- [x] Exact control-plane inventory is asserted.
- [x] Catalog inventory must exist in the native schema.
- [x] Goal read/write contracts are asserted.
- [x] Strategic Number write/read/typed-operand contracts are asserted.
- [x] Timer write/read contracts are asserted.
- [x] Rule-control persistence and same-pass behavior are asserted.
- [x] Evidence provenance is asserted.
- [x] Non-primitive mapped control-plane commands report `ENGINE_SEMANTICS_MAPPED`; pre-existing primitive-backed commands retain `EXECUTABLE_SAFE`.
- [x] Dual `Fact/Action` commands do not receive false primitive-safe bindings.
- [x] Existing primitive-level executable mappings remain unchanged.
- [x] `up-modify-goal` contributes both a Goal writer and a prefixed Goal/SN operand reader.
- [x] `up-compare-goal` contributes the correct persistent Goal dependency.

## Verification gates

- [x] Run the full compiler unit suite on the branch: 735 tests, 0 failures, GitHub Actions run 1706.
- [x] Run the native zero-findings fixtures: generic, strategy/runtime, strategic-number, and invalidation fixtures all returned 0 findings.
- [x] Run the deterministic support-state/inventory gate: all 9 OS/Python replay jobs and the aggregate comparison passed.
- [x] Inspect changed-file diff: the change is confined to generic compiler primitives/semantic analysis/tests plus this plan; no client-specific implementation was added.
- [x] Review the resulting Actions run logs: compiler verification gate passed on merge ref 7f189b6eb06c476a455d73e0a0e8d4fe90d212c3, testing branch head c360e85f6d31df02400d7f247a76fa3be3537919.

## Intentionally not in this tranche

These are the next engine-semantic families, but they should not be collapsed into this control-plane change:

- [ ] DUC retained search/filter/target state and post-search cursor semantics.
- [ ] DUC Goal output spans and object-data writers.
- [ ] DUC performance/cardinality cost model.
- [ ] Attack-group and attack-target lifecycle.
- [ ] Production queue admission and queue saturation semantics.
- [ ] Provider availability and generic capability-loss/recovery bindings.
- [ ] Effective load/preprocessor package semantics beyond the current source-graph core.
- [ ] Complete patch-version semantic overlays for Strategic Numbers.
- [ ] Broader native command semantic coverage.

## Acceptance definition

This tranche is complete only when a native Goal/SN/Timer/control command can be traced without a bespoke analyzer-owned command list:

```
AIRef/native schema identity
    -> NativeEngineEffectContract
    -> support-state assessment
    -> persistent/recurrent semantic consumer
    -> existing IR/runtime semantics
    -> deterministic .per
    -> native parser validation
```

The DUC and attack families remain explicitly unsupported until they receive equivalent state/effect contracts. Evidence-only knowledge must not leak into executable support.
