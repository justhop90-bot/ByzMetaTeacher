# Effective Source Graph Implementation Checklist

Date: 2026-09-27

Purpose: make the effective native `.per` source program a deterministic, typed compiler input for recurrent-rule and DUC semantic analysis. This tranche owns load reachability, conditional-load semantics, source ordering, physical source identity, recursive load context, and source provenance. It does not own native backend package legality or `.xs` include integrity.

## Community cross-reference and revised disposition

| Requirement | Community / engine evidence | Initial proposal | Revised disposition |
|---|---|---|---|
| Relative load resolution | Community scripts and tooling treat `load` as a source-file relationship; aoe2-ai-parser reports unresolved load targets as package errors. | Resolve relative to containing source, then search roots. | **KEEP.** Local containing-directory resolution is primary; configured search roots are fallback. |
| Missing reachable load target | aoe2-ai-parser defines `missing-load-target` as an error. | Fail closed. | **KEEP.** Reachable missing loads abort graph construction. cite https://github.com/joerollman/aoe2-ai-parser/blob/main/docs/workflows/validator-diagnostic-codes.md |
| Conditional loading | AIRef documents `#load-if-defined`, `#load-if-not-defined`, `#else`, and `#end-if`; community tooling recognizes these as source-loading syntax. | Evaluate conditions before resolving children. | **KEEP, corrected.** Parse and structurally validate all branches, but resolve/expand only active load edges. This fixes inactive missing-target/cycle false failures. cite https://airef.github.io/tables/load-if.html https://github.com/Jvinniec/aoe2-aiscript/blob/master/syntaxes/customizing_colors.md |
| Source order | Native AI scripting is rule/source-order sensitive; compiler rule execution already consumes effective source order. | Depth-first inline expansion. | **KEEP.** A normal load is expanded at its lexical position, not topologically sorted. |
| Load depth | Compiler/validator evidence documents a nested load depth limit of 10. | Reject >10. | **KEEP.** Depth 10 is valid; depth 11 is rejected. |
| Conditional nesting | Existing compiler diagnostic policy documents a conditional nesting ceiling of 50. | Reject >50. | **KEEP.** Exactly 50 is valid; 51 is rejected. |
| Duplicate load | Community tooling distinguishes duplicate/repeated load targets from cycles. | Preserve repeated instances, detect cycles only on active stack. | **KEEP.** Physical source identity is shared; recursive source instances remain distinct. |
| Cycle detection | A recursive reachable load is structurally invalid. | Active-stack cycle detection. | **KEEP.** Global visited state must not be used as the cycle detector. |
| load-random | Community syntax supports `load-random`; selection is runtime/random behavior rather than ordinary lexical inclusion. Existing compiler policy intentionally avoids compiler-side random selection. | Initially considered expanding all alternatives into a deterministic graph. | **REJECT.** Do not invent RNG or silently treat all alternatives as simultaneously linear. Preserve the typed event payload and fail closed unless an explicit deterministic materialization policy exists. |
| `+weight` load-random form | aoe2-ai-parser documents the `+` form as uncertain/bugged DE/UserPatch behavior. | Treat as ordinary weight. | **REJECT.** Preserve authored syntax; do not normalize uncertain engine behavior into compiler fact. cite https://github.com/joerollman/aoe2-ai-parser/blob/main/docs/workflows/validator-diagnostic-codes.md |
| `.xs` include | aoe2-ai-parser separately validates include reachability. | Put include edges into the same effective `.per` source-order graph. | **REJECT FOR THIS TRANCHE.** `.xs` include integrity remains a package/backend boundary. Do not pollute native `.per` rule ordering with XS inclusion. cite https://github.com/joerollman/aoe2-ai-parser/blob/main/docs/workflows/validator-diagnostic-codes.md |
| Path canonicalization | Cross-platform compiler operation requires stable source identity; repository fingerprints already depend on canonical source identity. | Lexically normalize `.`/`..`, absolute paths, and Windows case. | **KEEP WITH EXISTING REPRESENTATION.** The current `Path.resolve()`-backed `SourceFileId` remains authoritative; tests now prove lexical `.`/`..` normalization. A separate display-path abstraction is deferred because the current IR uses canonical identity as provenance. |
| Symlink semantics | No reliable engine-level evidence establishes symlink meaning inside AI package loading. | Avoid silently adding realpath semantics. | **DEFER.** Existing `Path.resolve()` behavior is retained; no compiler policy is invented without package-level evidence. |
| Determinism | Compiler acceptance already requires repeatable fingerprints/cross-platform determinism. | Stable graph, event, edge, and slice ordering. | **KEEP.** Repeated resolution must produce identical typed graph/fingerprint state. |

## Implementation checklist

### A. Typed graph substrate

- [x] Source-file identity contains canonical path plus SHA-256 content identity.
- [x] Recursive source instances are distinct from physical source-file identity.
- [x] Parent instance and edge provenance are explicit.
- [x] Conditional predicates are preserved as typed contexts.
- [x] Source assembly events have stable identities and lexical ordinals.
- [x] Resolved edges point back to their originating assembly event.
- [x] Effective source slices preserve inline expansion order.
- [x] Assembly and effective fingerprints are separate contracts.

### B. Resolution semantics

- [x] Resolve entrypoint to canonical source.
- [x] Resolve ordinary loads relative to the containing source first.
- [x] Apply configured search roots only after local resolution.
- [x] Detect reachable cycles from the active recursive load stack.
- [x] Enforce maximum nested load depth of 10.
- [x] Evaluate active/inactive conditional branches before expanding children.
- [x] Enforce conditional nesting depth of 50.
- [x] Preserve repeated non-recursive loads as distinct source instances.
- [x] Preserve `load-random` as typed source syntax.
- [x] Fail closed on active `load-random` without an explicit deterministic materialization policy.
- [x] Reject malformed load syntax and malformed conditional directives.

### C. Boundary corrections implemented in this hardening pass

- [x] Inactive `load` directives no longer resolve their child file before active-branch evaluation.
- [x] Inactive missing load targets therefore do not abort compilation.
- [x] Inactive recursive load cycles are not traversed.
- [x] Exact load-depth boundary (depth 10) is explicitly tested.
- [x] Lexical `./` and `sub/../` path normalization is explicitly tested.
- [x] Repeated resolution remains fingerprint-deterministic.

### D. Required graph invariants

- [x] Root instance exists.
- [x] Every active edge resolves to a target source file.
- [x] Every active edge with a child has a corresponding child instance.
- [x] Every child instance points back to its parent and entering edge.
- [x] Source-instance ancestry contains no active cycle.
- [x] Instance identities are unique.
- [x] Event identities are unique and stable.
- [x] Event/edge back-references agree.
- [x] Conditional open/else/end pairing is structurally valid.
- [x] Condition symbols are known to the supplied load-symbol environment.
- [x] Slice ordinals are contiguous.
- [x] Source slices and source ranges remain source-attributed.
- [x] Assembly fingerprint recomputes exactly.
- [x] Effective fingerprint recomputes exactly.

### E. Minimum fixture matrix

- [x] single root without loads
- [x] one direct load
- [x] child load spliced at lexical position
- [x] nested depth-first loads
- [x] duplicate non-recursive load
- [x] recursive cycle
- [x] missing reachable target
- [x] defined conditional branch
- [x] not-defined conditional branch
- [x] unknown conditional symbol
- [x] malformed conditional opener
- [x] unexpected `#else`
- [x] duplicate `#else`
- [x] unexpected `#end-if`
- [x] unterminated conditional
- [x] active load depth 10 boundary
- [x] load depth 11 rejection
- [x] conditional depth 50 boundary
- [x] conditional depth 51 rejection
- [x] inactive missing target
- [x] inactive recursive cycle
- [x] malformed raw load
- [x] malformed parenthesized load
- [x] wrong load arity
- [x] load-shaped text inside a string
- [x] nested `(load ...)` expression that is not a source directive
- [x] `load-random` payload preservation
- [x] `load-random` compiler-policy rejection
- [x] repeated deterministic fingerprint
- [x] lexical path normalization

### F. Downstream contract

- [x] Recurrent rule analysis consumes `EffectiveSourceGraph` rather than rebuilding source reachability.
- [x] DUC analysis receives effective-rule source identity/provenance.
- [ ] Add a DUC-specific fixture proving a producer loaded from a child source retains its source-instance identity through DUC diagnostics.
- [ ] Add complete DUC cross-pass target-reuse proof states.
- [ ] Integrate DUC findings into the shared rule-diagnostic taxonomy.

## Explicit non-goals

This tranche does not:
- choose a runtime `load-random` branch;
- implement XS compilation;
- validate XS include integrity;
- optimize `up-jump-rule` control flow;
- infer engine firing from source order;
- invent a scheduler or runtime source loader;
- turn source graphs into strategy policy.

## Acceptance gate

The tranche is accepted only when:

1. `validate_effective_source_graph()` passes on all valid fixtures.
2. All hostile forged-graph validator tests remain failing closed.
3. Inactive branches are proven not to resolve child files.
4. Load depth 10 passes and depth 11 fails.
5. Repeated resolution produces identical graph/fingerprint output.
6. Full compiler tests remain green.
7. Native zero-findings acceptance remains green.
8. Cross-platform deterministic jobs remain green.

## Community references

- AIRef load-if table: https://airef.github.io/tables/load-if.html
- AIRef command index: https://airef.github.io/commands/commands-index.html
- aoe2-ai-parser diagnostics: https://github.com/joerollman/aoe2-ai-parser/blob/main/docs/workflows/validator-diagnostic-codes.md
- AoE2 AiScript syntax tooling: https://github.com/Jvinniec/aoe2-aiscript
- AoE2 community script tooling: https://github.com/lewisc64/aoe2ai
