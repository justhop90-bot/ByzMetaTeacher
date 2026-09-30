# Compiler engineering charter

Status: project authority and repository operating contract, 2026-09-30.

## Mission

The project exists to build the generic AoE2DE `.per` compiler defined by the current target architecture, with a Byzantine-focused client.

The lead role owns architecture, sequencing, evidence standards, repository hygiene, integration discipline, and acceptance.

Authority is exercised through code, tests, documentation, Git history, and merge decisions, not through claims.

## Repository as lab

Git is the laboratory.

`main` is the authoritative accepted state. It must remain reproducible and reviewable.

Feature branches are experiments. Each branch should answer one concrete architectural or semantic question.

Pull requests are lab reports. A PR must identify the contract being changed, supporting evidence, exact files/interfaces, regression coverage, remaining OPEN boundaries, and the verification result for the candidate commit.

The commit graph is part of project provenance.

## Mainline policy

No direct edits to `main` are the default operating mode.

Normal path:

`branch -> implementation -> focused verification -> PR -> green compiler CI -> merge -> main verification -> branch retirement`

Use merge commits by default so the accepted history preserves the boundary between an experiment and the integrated compiler line.

## Branch discipline

Preferred current prefixes:

- `compiler/`
- `duc/`
- `attack/`
- `production/`
- `escrow/`
- `game-data/`
- `research/`
- `verification/`
- `git/`

Do not create `v2`, `v3`, `green1`, `final-2`, or equivalent branch variants. Start the next attempt from current `main` and close the superseded PR.

The repository currently contains a large historical branch forest. Those branches are not current compiler state and should be retired as repository administration permits.

## Evidence discipline

Every promoted engine behavior must have an evidence class and provenance.

Recognized classes:

- ENGINE FACT
- COMMUNITY PRACTICE
- COMPILER POLICY
- OPEN / UNKNOWN

When evidence is insufficient, the compiler fails closed or preserves UNKNOWN.

No runtime claim may be inferred from static code merely because a pattern is common in community scripts.

## Runtime probe boundary

Runtime DE probing is external evidence acquisition.

The repository may contain fixture specifications, oracle definitions, expected trace schemas, and research-status transitions.

An unexecuted probe is not compiler fact.

## Documentation authority

Authoritative hierarchy:

1. current code on `main`;
2. green compiler CI for the exact commit;
3. `LearnerAI/Compiler/PROJECT_STATE.md`;
4. current architecture and evidence documents;
5. dated plans, audits, and historical research.

A stale checklist is not a specification.

When a repair changes the current frontier, reconcile the current-state document in the same change window.

## CI authority

`.github/workflows/compiler-tests.yml` defines compiler acceptance.

The legacy validator is retained only as a manual historical/compatibility check. It must not create default-branch compiler noise.

## Definition of done

A compiler repair is done only when:

- the typed contract exists;
- illegal states are rejected;
- implementation is connected to the compiler;
- focused regressions exist;
- generic/client boundaries remain intact;
- native lowering is validated where applicable;
- determinism is preserved;
- evidence status is accurate;
- the exact tested commit is known.

## Design authority

The lead rejects changes that:

- duplicate existing semantic lifecycles;
- create parallel public compiler surfaces without necessity;
- hide native UNKNOWN behavior;
- introduce speculative runtime semantics;
- optimize architecture while leaving the actual community-knowledge gap untouched.

The project optimizes for semantic closure, not architecture theater.
