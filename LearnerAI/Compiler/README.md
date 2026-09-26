# LearnerAI Compiler

The compiler is the semantic backplane for the Byzantine player.

It is not the player itself.

Its job is to turn explicit player semantics into auditable .per while rejecting lifecycle defects that native parsing cannot know about.

## Pipeline

    player specification
      -> source parser / AST
      -> semantic lifecycle analysis
      -> validated IR
      -> deterministic .per
      -> native aoe2-ai-parser validation
      -> AoE2DE runtime
      -> runtime evidence

The runtime remains the final authority.

## Current language

The first source language remains deliberately small:

    demand <name> {
        require (<native .per predicate>)
        action (<native .per action>)
        witness (<native .per world-state predicate>)
        release (<native .per predicate>)
    }

Native expressions stay visible. The compiler does not try to invent a second AoE2 engine.

## Semantic responsibilities

The compiler owns:

- demand lifecycle;
- semantic context;
- capability versus demand separation;
- feasibility versus action;
- pending state;
- completion witnesses;
- release;
- future cancellation/obsolescence;
- ownership and dependency diagnostics.

The native backend owns raw .per language legality.

The game owns actual execution.

## Current lifecycle guarantee

An action may move a demand into pending state.

The pending witness may move it to complete.

Release may occur only from complete state.

The action itself is never the witness.

Examples already implemented:

- Castle construction;
- defensive Spearmen;
- Wheelbarrow research.

These are compiler lifecycle examples, not the complete Byzantine player.

## What the compiler must grow into

The next semantic work is driven by the player:

1. demand ownership;
2. capability providers;
3. dependency chains;
4. resource/conflict semantics;
5. cancellation and obsolescence;
6. source-order and first-writer/consumer analysis;
7. dead-end/unfed/blocked/open-loop diagnostics;
8. domain-aware player diagnostics.

Do not add syntax first. Add semantic capability when a real player behavior requires it.

## Native validation

Generated .per is staged and validated by the pinned aoe2-ai-parser backend before promotion when native validation is enabled.

Use Compiler/backends/README.md for the protocol and pin.

## Compiler architecture

compiler.py:
orchestration and CLI.

parser.py:
source syntax to AST.

ast.py:
syntax structures.

primitives/:
small authoritative teaching profile for the current compiler slice.

semantic/:
expression and lifecycle validation.

ir/:
validated semantic representation.

emitter/:
deterministic .per generation.

backends/:
external native validation boundary.

tests/:
semantic and backend regression evidence.

examples/ and generated/:
small lifecycle fixtures only. They are not the full Basilisk controller.

## Verification

Run:

    python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"

The latest checked-in verification record contains 48 passing compiler tests. This is compiler evidence only. It is not gameplay evidence.

## Product boundary

The compiler is successful when it helps us build the player safely.

It is not successful merely because the compiler grows larger.
