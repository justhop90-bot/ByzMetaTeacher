# Basilisk compiler

The compiler is now split into a real translation pipeline:

    Basilisk source
        -> parser / AST
        -> primitive + lifecycle semantic analysis
        -> validated semantic IR
        -> deterministic .per emitter
        -> AoE2DE

The current language remains intentionally small:

    demand <name> {
        require (<native .per predicate>)
        require (<native .per predicate>)
        action (<native .per action>)
        witness (<native .per world-state predicate>)
        release (<native .per predicate>)
    }

The source language does not pretend to replace AoE2's rule language. Native .per expressions remain visible, which makes generated output auditable and prevents the compiler from inventing a second game engine.

## Semantic contract

require describes conditions under which the demand is admissible and executable. The first primitive profile distinguishes observation, admissibility, feasibility, and resource-arbitration facts.

action must resolve to an AoE2 action primitive. A fact such as can-build cannot be emitted as an action.

witness is completion evidence. It describes a world-state condition that proves the requested action produced the intended state. An action firing is not proof of completion.

release is separate from completion. The compiler currently represents this distinction with an intermediate demand goal:

    goal = 1  persistent demand / action phase
    goal = 2  witnessed completion / release phase
    goal = 0  released demand

Therefore a release condition cannot clear the demand merely because it is true while the action is still pending. The witness must first advance the demand into the release phase.

This is deliberately stricter than the original prototype, which placed witness and release beside one another in the same rule and therefore did not model their lifecycle relationship.

## Primitive registry

primitives/registry.py is the authoritative profile for the commands understood by this compiler slice. Unknown primitives are rejected. Primitive metadata records:

- AoE2 kind: fact or action
- semantic role
- argument count
- supported version profile

The registry is intentionally incomplete. That is a feature at this stage: silently passing unknown commands would make the compiler appear smarter than it is.

## Expression validation

The semantic analyzer parses parenthesized native .per expressions enough to identify their root primitive, validate primitive argument counts, and validate logical operator arity.

AoE2 logical operators are not arbitrary variadic functions. and, or, nand, nor, xor, and xnor are binary and not is unary. More operands require nesting. This follows the documented AIRef command behavior.

The compiler currently permits nested logical expressions but keeps ordinary primitive arguments atomic. It rejects rule separators, unknown primitives, invalid contexts, and incorrect argument counts.

## Current architecture

    compiler.py
        orchestration / CLI

    parser.py
        source syntax -> AST

    ast.py
        syntax data structures

    primitives/
        authoritative primitive profile

    semantic/
        expression parsing and lifecycle/context validation

    ir/
        validated semantic representation

    emitter/
        deterministic .per generation

## What is deliberately not implemented yet

Pending construction/training/research state, escrow policy, ownership, goal-range manifests, source-order analysis, generated rule-size accounting, compiler-wide dependency graphs, cancellation/obsolescence syntax, and higher-level economy/production/military declarations remain later stages.

The compiler also does not claim that an emitted action succeeded. AoE2 world state remains the runtime authority and the witness remains the completion authority.

## Compile

From the repository root:

    python LearnerAI/Compiler/compiler.py LearnerAI/Compiler/examples/basics.basilisk LearnerAI/Compiler/generated/Basilisk.per

Run tests:

    python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"

Do not edit generated .per by hand. Change the Basilisk source or compiler and regenerate it.
