# Compiler engineering charter

Status: project authority and repository operating contract, 2026-09-30.

## Mission

The project exists to build the single generic AoE2DE .per compiler defined by the target architecture.

The lead role owns architecture, sequencing, evidence standards, repository hygiene, integration discipline, and acceptance.

Authority is exercised through code, tests, documentation, Git history, and merge decisions, not through claims.

## Repository as lab

Git is the laboratory.

main is the authoritative accepted state. It must remain reproducible and reviewable.

Feature branches are experiments. Each branch should answer one concrete architectural or semantic question.

Pull requests are lab reports. A PR must identify the contract being changed, supporting evidence, exact files/interfaces, regression coverage, remaining OPEN boundaries, and the verification result for the candidate commit.

The commit graph is part of project provenance.

## Branch discipline

Use focused branches by objective:
- single-compiler-* for semantic-spine work;
- duc-* for DUC semantics;
- attack-* for attack/controller semantics;
- production-* for production/queue semantics;
- escrow-* for resource-control semantics;
- game-data-* for factual model work.

Do not revive historical branches merely because their names look relevant. Current main is authoritative.

Large feature work should use coherent commits. Temporary verification branches must not become a second mainline.

## Mainline policy

No direct edits to main are the default operating mode.

Normal path:

branch -> implementation -> focused verification -> PR -> review -> merge -> post-merge verification

Repository administration currently reports that required branch checks are not enforced server-side. Until protection is configured, this charter is the operational control.

The compiler workflow, not the unrelated historical Basilisk Validator workflow, defines generic compiler acceptance.

## Evidence discipline

Every promoted engine behavior must have an evidence class and provenance.

Recognized classes:
- ENGINE FACT: authoritative/native support;
- COMMUNITY PRACTICE: established community precedent;
- COMPILER POLICY: intentional static compilation rule;
- OPEN / UNKNOWN: unresolved native or runtime behavior.

When evidence is insufficient, the compiler fails closed or preserves UNKNOWN.

No runtime claim may be inferred from static code merely because a pattern is common in community scripts.

## Runtime probe boundary

Runtime DE probing is external evidence acquisition.

The repository may contain fixture specifications, oracle definitions, expected trace schemas, and research-status transitions.

An unexecuted probe is not compiler fact.

## Documentation authority

Authoritative hierarchy:
1. current code on main;
2. green CI verification for the exact commit;
3. current architecture/spec documents;
4. current evidence registries and MUSE research;
5. historical plans and checklists.

A stale checklist is not a specification.

When a repair closes or moves a gap, the corresponding authoritative documentation must be reconciled in the same change window.

## Definition of done

A repair is done only when:
- the typed contract exists;
- illegal states are rejected;
- implementation is connected to the compiler;
- focused regressions exist;
- generic/client boundaries remain intact;
- native lowering is validated where applicable;
- determinism is preserved;
- evidence status is accurate;
- exact post-change verification is known.

## Design authority

The lead rejects changes that:
- duplicate existing semantic lifecycles;
- create parallel public compiler surfaces without necessity;
- hide native UNKNOWN behavior;
- introduce speculative runtime semantics;
- optimize architecture while leaving the actual community-knowledge gap untouched.

The project optimizes for semantic closure, not architecture theater.

## Current strategic priority

The next major milestone is an end-to-end community strategy synthesis path proving:

community pattern -> strategic demand -> capability/admission -> persistent control -> execution -> witness -> recovery -> native .per

Production/composition and attack/target loops are leading candidates because they exercise the largest remaining semantic seams together.
