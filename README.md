# ByzMetaTeacher

AoE2DE \`.per\` compiler project.

The accepted product is the compiler on \`main\`, with a Byzantine-focused client and a research/evidence layer for community-native \`.per\` practice.

## Start here

1. [\`AGENTS.md\`](AGENTS.md) — AI engineering and Git operating contract.
2. [\`LearnerAI/Compiler/PROJECT_STATE.md\`](LearnerAI/Compiler/PROJECT_STATE.md) — current accepted compiler state and next frontier.
3. [\`LearnerAI/Compiler/README.md\`](LearnerAI/Compiler/README.md) — compiler architecture and interface map.
4. [\`docs/governance/GIT_OPERATING_MODEL.md\`](docs/governance/GIT_OPERATING_MODEL.md) — branch, PR, merge, and documentation rules.
5. [\`docs/plans/\`](docs/plans/) — dated implementation plans and historical execution records.
6. [\`docs/reference/\`](docs/reference/) — engine, AIRef, GameData, and evidence sources.

## Product boundary

The compiler turns community \`.per\` knowledge and documented native semantics into deterministic, auditable native \`.per\`.

It is not a universal scheduler, runtime simulator, tournament bot, replacement parser, or second general-purpose language.

Runtime DE probing is a separate evidence track. An unexecuted probe is not compiler fact.

## Repository map

- \`LearnerAI/Compiler/\` — active compiler implementation, IR, semantic analysis, lowering, binding, and tests.
- \`docs/\` — governance, architecture, plans, audits, research, references, and validation records.
- \`tools/\` — maintenance and evidence tooling.
- \`forensics/\` — hostile/native research fixtures and analysis.
- \`Basilisk/\`, \`validation/\`, and legacy client paths — historical compatibility material; not the compiler's project definition.

## Git rule

\`main\` is authoritative. Work happens on one focused branch per semantic question, then through a PR and the compiler CI gate. Merge history is retained as provenance.

The compiler acceptance workflow is [\`.github/workflows/compiler-tests.yml\`](.github/workflows/compiler-tests.yml). Historical validator workflows are kept manual and are not compiler acceptance gates.

## Current baseline

The latest accepted compiler state is recorded in [\`LearnerAI/Compiler/PROJECT_STATE.md\`](LearnerAI/Compiler/PROJECT_STATE.md), including the exact \`main\` commit and verification run.

Do not use a dated document as the answer to "what is current?" unless the current-state document explicitly points to it.
