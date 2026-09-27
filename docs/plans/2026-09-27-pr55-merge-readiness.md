# Recurrent Execution Merge Readiness — Current Compiler State

Date: 2026-09-27

This record supersedes the stale PR #55 merge narrative. The recurrent execution implementation has been ported onto the current compiler head rather than carrying the old branch history forward.

## Scope

Implemented:
- bounded path-sensitive recurrent execution analysis;
- recurrent versus one-shot lifetime through existing rule-pass behavior and `disable-self`;
- exact literal Goal/SN/Timer state effects;
- conservative unknown-guard handling;
- native `up-jump-rule` control-transfer modeling;
- deterministic REX-001 through REX-004 diagnostics;
- integration into the shared RuleDiagnostic surface;
- compiler wiring for source, package, and staged-file report paths;
- focused recurrent regression coverage;
- current project documentation updates.

Explicitly excluded:
- runtime simulation;
- arbitrary world-state proof;
- generic scheduler construction;
- DUC semantics;
- strategy policy.

## Port audit

The stale PR branch was 54 commits behind current `main` and therefore was not merged directly.

The implementation was re-applied from its merge-base patch onto the current compiler state after the Effective Source Graph repair. Only compiler/recurrent files and their documentation were ported.

The old Basilisk Validator workflow/self-test edits were deliberately excluded from this compiler tranche.

## Required verification

- [ ] Fresh Compiler Tests workflow green on the final ported head.
- [ ] Native zero-findings acceptance green.
- [ ] All nine OS/Python determinism jobs green.
- [ ] Cross-platform snapshot comparison green.
- [ ] Compiler verification gate green.
- [ ] Current main contains the merged Effective Source Graph repair before recurrent execution is merged.

## Known semantic boundary

The recurrent analyzer is conservative. A runtime-dependent predicate must not be promoted into an engine fact. State-space exhaustion is reported as runtime-dependent rather than as a proof of non-runnability.
