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
- timing-vs-world-evidence semantics;
- native positional observations where the engine exposes them;
- refusal to invent unsupported builder-count semantics;
- completion witnesses;
- release;
- future cancellation/obsolescence;
- ownership and dependency diagnostics.

The native backend owns raw .per language legality.

The game owns actual execution.

## Current lifecycle guarantee

An action moves a demand from active to pending.

The pending witness moves it to complete.

Release moves it from complete to released.

The action itself is never the witness.

The emitter deliberately writes these three lifecycle rules in reverse transition order:

    RELEASE
    COMPLETE-WITNESS
    ACTIVE-ACTION

AoE2 goal values update immediately, so this source order prevents an already-true witness and release predicate from collapsing the entire lifecycle in one script pass. The intended execution is:

    pass N   : ACTIVE -> PENDING
    pass N+1 : PENDING -> COMPLETE
    pass N+2 : COMPLETE -> RELEASED

The compiler has regression coverage for the rule ordering and the three-pass state sequence.

The action rule also requires both the completion witness and release predicate to be false before entering pending. This stale-fact barrier prevents a predicate that was already true before the action from being reused as post-action completion or release evidence. It does not claim engine timestamps or universal observation freshness; it establishes the strongest causal guard available at the compiler layer.

Examples already implemented:

- Castle construction;
- defensive Spearmen;
- Wheelbarrow research.

The timing layer now recognizes native `game-time` as interpretation evidence only. A timing-only demand cannot write an action, timing cannot prove completion, and timing alone cannot release a demand.

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

The latest checked-in verification record contains the compiler regression suite, timing-semantics tests, and cross-pass lifecycle tests. This is compiler evidence only. It is not gameplay evidence.

## Product boundary

The compiler is successful when it helps us build the player safely.

It is not successful merely because the compiler grows larger.
