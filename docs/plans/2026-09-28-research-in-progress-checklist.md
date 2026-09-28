# Research In-Progress Semantics Implementation Checklist

**Goal:** Promote `up-research-status` into executable native semantics and use it to distinguish research in-progress from completion without inventing timers, schedulers, or escrow ownership.

## Scope

- [ ] Promote `up-research-status` as an executable Fact with exact native arity and provenance.
- [ ] Attach `up-research-status` to the typed research lifecycle as the pending/in-progress observation.
- [ ] Allocate a compiler-owned `research-retry-barrier-*` Goal slot to prevent same-pass reissue after status loss.
- [ ] Emit research-specific `ISSUED/PENDING -> PENDING`, `ISSUED/PENDING -> ACTIVE`, and `ACTIVE -> ISSUED` guards while retaining `research-completed` as the only completion witness.
- [ ] Add focused semantic/lifecycle regression tests.
- [ ] Add a checked-in source-to-.per research acceptance fixture and pinned zero-findings validator.
- [ ] Add the fixture to the Compiler workflow.
- [ ] Run full Compiler verification: native acceptance, persistent-state suites, 935+ regression tests, cross-platform determinism, snapshot comparison, and aggregate gate.

## Evidence boundary

AIRef/UserPatch documents `up-research-status` with `research-unavailable=0`, `research-available=1`, `research-pending=2`, and `research-complete=3`; `>= research-pending` means researching or complete. Community scripts use `can-research` for admission and `up-research-status >= research-pending` to avoid duplicate research while using `research-completed` for completion. citeturn815208search0turn843675search1

The repair does not promote same-pass `release-escrow -> research` visibility, escrow acquisition/ownership, `set-escrow-percentage`, starvation release, or multi-owner handoff. Those remain explicitly open.

## Files

`LearnerAI/Compiler/primitives/registry.py`
`LearnerAI/Compiler/primitives/engine_semantics.py`
`LearnerAI/Compiler/semantic/community_engine.py`
`LearnerAI/Compiler/ir/research.py`
`LearnerAI/Compiler/ir/model.py`
`LearnerAI/Compiler/ir/__init__.py`
`LearnerAI/Compiler/semantic/analyzer.py`
`LearnerAI/Compiler/compiler.py`
`LearnerAI/Compiler/emitter/per.py`
`LearnerAI/Compiler/tests/test_community_engine.py`
`LearnerAI/Compiler/tests/test_compiler.py`
`LearnerAI/Compiler/tests/test_action_issuance.py`
`LearnerAI/Compiler/tests/fixtures/research_in_progress.perdsl`
`LearnerAI/Compiler/tests/assert_research_in_progress_native.py`
`.github/workflows/compiler-tests.yml`

## Verification order

1. Focused red test proving `up-research-status` is currently unsupported.
2. Focused green test for the native mapping.
3. Focused red/green lifecycle tests for the research retry barrier.
4. Native zero-findings source fixture.
5. Full Compiler workflow on the exact `main` SHA.

## Exit condition

This tranche is complete only when the source-to-.per research fixture is native-zero-findings and the full Compiler workflow is green at the same `main` SHA. The implementation must not claim exact provider-busy semantics beyond the promoted research-status fact.