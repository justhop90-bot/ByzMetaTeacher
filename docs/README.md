# Repository guide

This repository is organized around the AoE2DE `.per` compiler. Historical controller material, engine references, and research artifacts remain valuable, but they are not the current product boundary.

## First read

- `README.md` — repository orientation.
- `AGENTS.md` — AI/Git operating contract.
- `LearnerAI/Compiler/PROJECT_STATE.md` — current compiler state.
- `LearnerAI/Compiler/README.md` — compiler architecture.
- `docs/governance/GIT_OPERATING_MODEL.md` — Git and documentation discipline.

## Repository layout

- `LearnerAI/Compiler/` — active compiler implementation, typed IR, semantic validation, native lowering, runtime binding, and tests.
- `docs/governance/` — project authority and operating rules.
- `docs/plans/` — dated implementation plans and execution history.
- `docs/reference/` — engine, AIRef, GameData, and evidence sources.
- `docs/research/` — MUSE and other evidence records.
- `docs/reports/` — verification and audit reports.
- `forensics/` — hostile/native engine research.
- `tools/` — maintenance and evidence tooling.
- `Basilisk/`, `validation/`, and legacy client paths — retained compatibility and archaeology.

The large reference corpus is intentionally separate from the executable compiler.

## Documentation rule

Current state belongs in current-state documents, not dated plan files.

A dated checklist can explain how a repair happened. It cannot override the current compiler state.

## CI rule

`.github/workflows/compiler-tests.yml` is the compiler acceptance workflow.

The legacy validator is manual-only and is not evidence that the compiler is correct or incorrect.
