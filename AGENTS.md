# AI Engineering Contract

This repository is an AoE2DE `.per` compiler project. The authoritative product is the compiler on `main`; historical controller work and legacy filenames are repository context, not the project target.

## Source of truth

1. Code on `main`.
2. Green `Compiler tests` verification for the exact commit.
3. Current architecture and state documents.
4. Evidence registries and research records.
5. Dated plans, audits, and historical branch artifacts.

A dated plan is history. It does not override current code.

## Git model

`main` is the accepted compiler line.

Every code or semantic change uses:

`branch -> focused implementation -> focused tests -> PR -> full compiler CI -> merge -> main verification`

Do not edit `main` directly.

Use one branch for one semantic question. Preferred prefixes:

- `compiler/` generic compiler semantics
- `duc/` DUC semantics
- `attack/` attack/controller semantics
- `production/` production and queue semantics
- `escrow/` resource-control and escrow semantics
- `game-data/` factual game-data work
- `research/` evidence or runtime-probe preparation
- `verification/` verification-only work
- `git/` repository and engineering-process maintenance

Do not create numbered variants such as `-v2`, `-v3`, `-green1`, or parallel branches for the same repair. When a branch is superseded, its PR is closed and the branch is retired.

Prefer merge commits when merging accepted PRs. The merge commit is provenance: it records the reviewed boundary between the experiment and the accepted compiler line. Do not rewrite merged history.

## Commit discipline

Commits should be small enough to explain and test.

Preferred subjects:

- `feat(compiler): ...`
- `fix(compiler): ...`
- `test(compiler): ...`
- `docs(compiler): ...`
- `docs(governance): ...`
- `chore(repo): ...`

A commit that claims a repair must contain the implementation evidence needed to understand the repair. Do not hide behavior changes inside unrelated formatting or repository cleanup.

## Compiler boundaries

Keep these distinctions intact:

- engine fact vs community precedent vs compiler policy vs OPEN/UNKNOWN;
- admission/permission vs action issuance vs witness;
- pending/in-flight state vs world-state completion;
- timer cadence/control vs strategic truth;
- compiler policy arbitration vs native engine conflict classes;
- semantic compilation vs runtime DE probing.

A missing engine fact stays OPEN. Common community usage is evidence of precedent, not proof of native behavior.

Runtime probes may be prepared by the compiler project, but an unexecuted probe is not compiler fact.

## Documentation discipline

Current state belongs in non-dated current-state documents.

Dated files under `docs/plans/`, audits, and research records are immutable project history unless a change is explicitly a historical correction.

When a repair changes the current frontier, update the current-state/index document in the same PR.

Do not add a new document when an existing canonical document can be reconciled cleanly.

## Compiler naming

New compiler documentation should call this the AoE2DE `.per` compiler or Byzantine compiler project.

Some implementation paths and CI fixture names retain historical legacy names for compatibility. Do not propagate those names into new public architecture unless the compatibility surface itself requires them.

## Acceptance gate

A compiler change is not complete until:

- the typed contract exists;
- illegal states are rejected;
- focused regressions pass;
- the change is connected to the real compiler path;
- native lowering is validated where applicable;
- cross-platform determinism remains green;
- current evidence status is accurate;
- the exact tested commit is known.

The `Compiler tests` workflow is the compiler acceptance authority. Historical validation workflows are not equivalent acceptance gates.

## Repository maintenance

Keep the repository easy for an AI to traverse:

- one obvious entry point for current state;
- one obvious compiler architecture guide;
- one obvious Git operating model;
- tests next to the subsystem they validate;
- historical research preserved but clearly marked as historical;
- no stale current-state claims;
- no parallel public compiler APIs created merely to avoid extending an existing seam.

The desired repository is boring to navigate. The semantic problems are difficult enough without making the file tree a puzzle.
