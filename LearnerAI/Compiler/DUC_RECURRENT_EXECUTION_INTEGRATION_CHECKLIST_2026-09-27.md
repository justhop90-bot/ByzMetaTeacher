# DUC / Recurrent Execution Integration Checklist

Date: 2026-09-27

## Finding

The most substantial remaining generic compiler hole exposed by the Naga/community comparison was not missing DUC vocabulary. The compiler already models retained DUC lists, filters, targets, groups, Goal outputs, resets, loop widening, provenance, and target proof states.

The actual gap was semantic isolation between two analyses:

1. `RuleExecutionReport` supplies native source/control-flow reachability.
2. `analyze_recurrent_execution()` already proves that some rules are `NEVER_RUNNABLE`, while conservatively classifying others as `MAY_RUN` or `RUNTIME_DEPENDENT`.
3. `analyze_duc()` previously ignored that firing proof and applied every DUC action on every statically reachable rule.
4. A stateful rule that the recurrent interpreter proves impossible could therefore fabricate a search-list generation, target, group, output, reset, or mutation in the DUC abstract state.
5. Its native jump edge could also incorrectly export a control-flow path that is executable only if the impossible rule fires.

This is a correctness problem, not merely a missing warning. Community .per practice is dominated by guarded recurrent rules and state carried across passes. The DUC state model is only trustworthy when its state transitions are coupled to the engine-facing firing model.

## Community comparison

### Naga

The community AI database records Naga as a Promiskuitiv lineage AI, originally Promi DE AI and rebranded as Naga in 2021, with continued updates through 2025. The database lists support for basing strategy on flank/pocket position and enemy strategy, rebuilding a base, allied assistance, and other stateful strategy features. It explicitly lists DUC military micro as unsupported for Naga, so this compiler tranche must not pretend to reproduce Naga-specific DUC behavior. Source:

https://aoeaidatabase.pythonanywhere.com/ai?name=Naga

The useful architectural lesson is the opposite one: Naga is a long-lived recurrent .per program whose strategic state and rule eligibility matter continuously. The compiler therefore needs to keep semantic state analysis tied to actual rule firing semantics rather than treating source reachability as execution.

### Community DUC practice

AIRef's DUC tutorial describes DUC as persistent search/filter/target state used to select and coordinate units. UserPatch release history documents that filters affect future searches, that search/target operations are stateful, and that DUC commands should not be flooded every pass because they are direct unit-control operations.

Sources:

https://airef.github.io/resources/articles/leif-duc-tutorial-intro.html
https://airef.github.io/tables/up-patch-notes.html
https://userpatch.aiscripters.net/reference.html

The lewisc64/aoe2ai repository contains real community .per chains that guard DUC searches and later consume their persistent Goal/search evidence. This is direct prior art for the exact semantic shape being compiled:

https://github.com/lewisc64/aoe2ai

## Compiler comparison

Current compiler strengths include:

- Effective-source-graph provenance and deterministic rule order.
- Path-sensitive recurrent execution analysis over Goal/SN/Timer state.
- DUC search/list/filter/target/group/output state IR.
- Persistent DUC state across passes with explicit `SYNTACTIC_RETENTION` versus stronger proof states.
- Branch joins and bounded loop widening.
- Native contract provenance and AIRef evidence.
- Shared rule diagnostic aggregation.
- Native zero-findings promotion gate.

The missing edge was:

`recurrent firing proof -> DUC state transition eligibility`

without that edge, the two analyses can disagree about whether a DUC state mutation happened.

## Implementation checklist

### A. Recurrent proof contract
- [x] Reuse the existing `RecurrentExecutionReport` instead of inventing a second firing model.
- [x] Accept an optional recurrent report in `analyze_duc()`.
- [x] Treat `NEVER_RUNNABLE` as a hard execution absence for DUC state effects.
- [x] Keep `MAY_RUN` and `RUNTIME_DEPENDENT` conservative and executable.
- [x] Do not infer stronger firing certainty from source reachability alone.

### B. DUC state transfer
- [x] Suppress DUC searches, filters, targets, groups, outputs, resets, and mutations for rules proven `NEVER_RUNNABLE`.
- [x] Preserve the incoming DUC state when a never-runnable rule is skipped.
- [x] Continue processing later fall-through rules after a never-runnable rule.
- [x] Do not let a never-runnable rule export an `up-jump-rule` edge.

### C. Compiler integration
- [x] Reuse the recurrent report already computed by the artifact compiler.
- [x] Pass that report into `analyze_duc()`.
- [x] Keep DUC analysis after emission, so it reasons over the exact native .per that will be validated.
- [x] Keep the native parser as final authority for syntax/engine acceptance.

### D. Hostile tests
- [x] Impossible stateful guard prevents a DUC search from being invented.
- [x] Impossible stateful guard prevents its jump edge from affecting DUC state.
- [x] Runtime-dependent guard keeps the DUC action live.
- [x] Existing branch/join, target-lifetime, loop-widening, group-output, and reset tests remain covered.
- [ ] Add an artifact-level fixture containing native DUC plus a provably false persistent guard and verify the complete compiler gate rejects/accepts the intended semantic state without native findings.
- [ ] Add a loaded-child-source fixture once the source-graph DUC provenance tranche is implemented.

### E. Diagnostics and provenance
- [x] Existing DUC diagnostics continue to use the shared `RuleDiagnosticReport`.
- [x] Existing source/rule provenance remains the source of DUC findings.
- [ ] Add an explicit informational record for DUC transitions suppressed by proven non-executability if downstream consumers need audit visibility. This is intentionally not a warning: impossible rules are already covered by recurrent diagnostics.

### F. Regression acceptance
- [ ] Focused DUC semantic suite passes.
- [ ] Full compiler regression suite passes.
- [ ] Native zero-findings acceptance fixtures pass unchanged.
- [ ] All native-support determinism jobs pass.
- [ ] Cross-platform aggregate snapshot comparison passes.
- [ ] Merge only after the complete compiler verification gate is green.

## Deliberate scope boundary

This tranche does not attempt to simulate world facts, predict the enemy, or reproduce Naga strategy policy. Unknown world facts remain conservative. The compiler only couples already-established firing evidence to already-established DUC state semantics.

The next distinct DUC gaps remain target object lifetime after world-state disappearance, complete native stale proofs for every list mutator, four-Goal `up-get-search-state` allocation, and AIRef-backed DUC cost diagnostics.
