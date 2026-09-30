# Git Operating Model

## Purpose

Git is the compiler laboratory. The repository should make three things obvious without archaeology:

- what is accepted;
- what is being investigated;
- what is historical.

The commit graph is project provenance, not a disposable implementation detail.

## Canonical lines

### `main`

`main` is the only accepted compiler line. It contains the integrated semantic substrate and the latest verified compiler behavior.

A clean compiler baseline means:

- no unmerged repair is required to explain current compiler behavior;
- current-state documentation agrees with the code;
- the compiler workflow for the exact tip is known;
- stale work is not presented as active architecture.

### Feature branches

Feature branches are disposable laboratories. Each branch answers one question and should have one PR.

A branch should be created from the current `main`, not from another feature branch, unless a stacked change is explicitly required and documented.

Branch name format:

`<domain>/<short-semantic-question>`

Examples:

`compiler/production-arbitration`

`duc/target-identity-liveness`

`attack/execution-witness`

`git/repository-operating-model`

Avoid variant suffixes such as `v2`, `v3`, `green1`, and `final-2`. When a design changes, create the next branch from current `main`.

## PR model

A pull request is the reviewable lab report.

Every PR body should answer:

1. What semantic contract changed?
2. Which exact files/interfaces changed?
3. Which evidence supports the behavior?
4. Which states or behaviors remain OPEN?
5. Which focused tests prove the change?
6. Which full verification run proves the candidate commit?

Preferred lifecycle:

`draft -> focused green -> ready -> full CI green -> merge -> verify main -> retire branch`

The repository currently prefers merge commits so the accepted history preserves the reviewed experiment boundary.

## Commit model

Use focused commits with causal messages.

A useful sequence is:

`test -> implementation -> integration/docs -> verification`

Do not create ceremonial commits whose only purpose is to narrate activity.

Do not rewrite accepted history.

## Verification hierarchy

For compiler work:

1. focused unit/regression result;
2. native zero-findings fixture when lowering is involved;
3. compiler regression suite;
4. 3x3 native-support determinism matrix;
5. cross-platform snapshot comparison;
6. Compiler verification gate;
7. post-merge main run.

A red historical workflow does not invalidate a green compiler workflow when the red workflow is an unrelated legacy system. It does indicate repository hygiene debt, and that debt must be made explicit.

## CI authority

### Authoritative

`.github/workflows/compiler-tests.yml`

This workflow is scoped to compiler code and compiler workflow changes. It validates:

- native parser import and pinning;
- generated fixture reproducibility;
- native zero-findings acceptance;
- focused semantic regressions;
- full compiler tests;
- 3 operating systems x 3 Python versions;
- cross-platform native-support snapshot equality;
- the aggregate compiler verification gate.

### Legacy

The historical Basilisk validator is not the compiler acceptance authority. It is retained only as a manually invoked research/compatibility check.

Legacy validation must never create a red default-branch signal for a compiler change.

## Current branch inventory

The repository currently contains a large historical branch forest and no open PRs. That is a provenance problem, not a product problem.

Desired steady state:

- `main`;
- a small number of genuinely active feature branches;
- no merged branch retained indefinitely;
- no superseded branch variants;
- no branch that exists only to preserve an old CI attempt.

Remote branch deletion is a repository-administration operation. It should happen only after the corresponding PR is merged or explicitly abandoned, and only after confirming no active work depends on the ref.

## Documentation routing

Current information belongs in:

- `README.md` for repository orientation;
- `LearnerAI/Compiler/PROJECT_STATE.md` for current compiler state;
- `LearnerAI/Compiler/README.md` for compiler architecture and interfaces;
- `docs/governance/` for operating rules;
- `docs/plans/` for dated implementation plans;
- `docs/reference/` for evidence and factual source material;
- `docs/reports/` for verification or audit reports.

Historical documents remain valuable. They should not masquerade as current state.

## AI traversal rule

The first read should be:

`README.md -> AGENTS.md -> LearnerAI/Compiler/PROJECT_STATE.md -> LearnerAI/Compiler/README.md`

Then inspect the exact subsystem and its focused tests.

This is deliberately a narrow path. An AI should not have to read 800 reference files to discover which commit is authoritative. Humanity has already produced enough paperwork without requiring it to become a rite of passage.

## Repository repair rule

When repository hygiene is the subject of a change:

- preserve code history;
- preserve research evidence;
- isolate legacy systems;
- replace stale current-state claims;
- make the active workflow obvious;
- add automation only when it removes ambiguity rather than creating another ceremony.
