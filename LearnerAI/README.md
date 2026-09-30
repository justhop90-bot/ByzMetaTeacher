# LearnerAI

LearnerAI is the strategy, semantic, and compiler workspace for the Byzantine-focused AoE2DE `.per` project.

The active engineering center is `LearnerAI/Compiler/`.

## Current compiler entry point

Read `LearnerAI/Compiler/PROJECT_STATE.md` first, then `LearnerAI/Compiler/README.md`.

The compiler owns semantic contracts that native parsing cannot establish:

- demand ownership;
- capability and admissibility;
- feasibility;
- pending/in-flight state;
- world-state witnesses;
- release and invalidation;
- persistent control semantics;
- native Goal/SN/Timer binding;
- DUC and attack semantic contracts;
- compiler-policy arbitration;
- deterministic native lowering.

The native parser remains the authority for raw `.per` legality.

## Product boundary

The objective is a robust community-native compiler for a Byzantine client.

The project is not a general-purpose scheduler, runtime simulator, tournament bot, or replacement `.per` language.

Runtime DE probing is external evidence acquisition. Static compiler work must not claim probe results that have not been executed.

## Relationship to legacy material

The repository contains historical controller work and compatibility paths. They are preserved as evidence and prior art.

New compiler decisions must be anchored in current `main`, current CI, current evidence records, and the active state document rather than in legacy branch names or dated descriptions.

## Build direction

The player grows vertically from the compiler substrate. The next compiler frontier is the production/train arbitration seam documented in `LearnerAI/Compiler/PROJECT_STATE.md`.

The actual player roadmap remains in `LearnerAI/BUILD_ROADMAP.md`; the compiler state document is authoritative for compiler work.
