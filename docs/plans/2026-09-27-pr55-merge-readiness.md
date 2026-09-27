# PR #55 Merge-Readiness Cross-Reference — 2026-09-27

PR: #55 — `feat(compiler): add path-sensitive recurrent .per execution semantics`

Current branch: `compiler/recurrent-execution-semantics`

## Merge gate

| Gate | Evidence | Status |
|---|---|---|
| Implementation boundary | `LearnerAI/Compiler/semantic/recurrent_execution.py`, `compiler.py`, `rule_diagnostics.py`, `semantic/__init__.py` | IMPLEMENTED |
| Recurrent regression coverage | `LearnerAI/Compiler/tests/test_recurrent_execution.py` | IMPLEMENTED |
| Diagnostic integration | `LearnerAI/Compiler/tests/test_rule_diagnostics.py` | IMPLEMENTED |
| Full compiler suite | CI run `36295625929`: 630/630 | GREEN at pre-CI-fix head |
| Focused semantic suites | CI run `36295625929`: 22 + 25 + 15 passed | GREEN at pre-CI-fix head |
| Native parser / zero-findings gates | CI run `36295625929` | GREEN at pre-CI-fix head |
| Determinism matrix | CI run `36295625929`: all configured jobs + comparison | GREEN at pre-CI-fix head |
| Compiler verification gate | CI run `36295625929` | GREEN at pre-CI-fix head |
| Validator profile contract | `validation/basilisk-validator-profile-selftest.js`; commits `6030dc3`, `903b19e` | CONFIRMED |
| Validator baseline semantics | Commit `6030dc3` explicitly requires `8596a45` to fail on an engine-limit violation | CONFIRMED |
| Validator workflow behavior | `.github/workflows/basilisk-validator.yml` now treats that expected failure as a negative control and checks for `[Rule too long]` | IMPLEMENTED; FRESH CI REQUIRED |
| Documentation | recurrent execution plan, native gap map, research checklist | IMPLEMENTED |
| PR description | Must state implementation boundary, evidence, and validator negative-control disposition | REVISE BEFORE MERGE |
| Review state | PR approval / unresolved threads | REQUIRED |
| Final merge state | final head green, base not behind, required checks green | REQUIRED |

## Cross-reference: implementation

1. `LearnerAI/Compiler/semantic/recurrent_execution.py`
   - bounded path-sensitive abstract interpreter
   - recurrent/one-shot lifetime
   - Goal/SN/Timer state
   - jump semantics
   - conservative unknown guards
   - REX-001 through REX-004 findings

2. `LearnerAI/Compiler/semantic/rule_diagnostics.py`
   - recurrent diagnostic category and codes
   - integration into the existing diagnostic surface

3. `LearnerAI/Compiler/compiler.py`
   - recurrent analysis invoked from source/package/staged-file compilation paths

4. `LearnerAI/Compiler/semantic/__init__.py`
   - public semantic exports

## Cross-reference: tests

1. `LearnerAI/Compiler/tests/test_recurrent_execution.py`
   - persistent starvation
   - successful state establishment
   - disable-self
   - guaranteed recurrent jump preemption
   - one-shot jump recovery

2. `LearnerAI/Compiler/tests/test_rule_diagnostics.py`
   - recurrent findings compile into RuleDiagnostics

3. Existing `pass_scheduler` tests remain the runtime semantic authority for pass execution behavior; this tranche does not replace that scheduler.

## Cross-reference: documentation

1. `docs/plans/2026-09-27-recurrent-execution-semantics.md`
2. `LearnerAI/Compiler/NATIVE_PER_SEMANTIC_GAP_MAP_2026-09-26.md`
3. `LearnerAI/Compiler/RESEARCH_CHECKLIST.md`

These documents must preserve the boundary: bounded static analysis, not a second runtime scheduler or arbitrary world-state simulator.

## Basilisk Validator disposition

The prior validator run `36295625907` was red at `validation/basilisk-validator.js:5153` with:

`[Ranged] Crossbow action boundary must re-check its live role demand`

This was not evidence that PR #55 broke the validator.

The historical validator contract proves that the `8596a45` compatibility profile is a negative control:

- commit `6030dc3` adds a red test explicitly requiring the `8596a45` profile to exit nonzero on a real engine-limit violation and specifically to report `[Rule too long]`;
- commit `903b19e` introduces that compatibility profile;
- commit `d2678dc` changes the workflow to execute the `8596a45` profile as a baseline validator.

The old workflow nevertheless invoked that expected-failing validator command as a normal shell step, so CI correctly reported failure even though the negative control was behaving as designed.

PR #55 now changes the workflow so the baseline command is an explicit negative-control test:

- nonzero exit is required;
- `[Rule too long]` must be present;
- an unexpected failure is rejected;
- an unexpected success is rejected.

The fresh Basilisk Validator workflow must therefore be green after this CI correction. A green result means the negative control passed, not that the historical 8596a45 controller is itself clean under current compiler limits.

## Final merge conditions

- [ ] Fresh compiler workflow green on the final PR head.
- [ ] Fresh Basilisk Validator workflow green on the final PR head.
- [ ] No new compiler or native-validation findings.
- [ ] PR description matches this evidence.
- [ ] Required review approval present.
- [ ] No unresolved review threads.
- [ ] Final head is not behind `main`.
- [ ] Merge only after all required repository checks are green.
