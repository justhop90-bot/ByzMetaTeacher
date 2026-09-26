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

release is separate from completion, and pending state is separate from both. The compiler now represents the lifecycle with three allocated states:

    goal = demand  active / action may be issued
    goal = pending  action has fired / repeated action is blocked
    goal = complete  world-state witness observed / release may occur
    goal = 0  released

The action rule is the only rule allowed to issue the action, and it immediately moves the demand into its pending state. The witness rule requires that pending state. The release rule requires the completed state. This prevents the common polling-loop failure where an action remains eligible on every pass while its engine-side result is still pending.

For the first examples this means:
- Castle: build castle fires once, then the demand waits for building-type-count castle > 0.
- Spearmen: train spearman fires once, then the demand waits for unit-type-count spearman >= 2.
- Wheelbarrow: research ri-wheelbarrow fires once, then the demand waits for research-completed ri-wheelbarrow.

Pending is a lifecycle state, not a retry counter. Temporary failure to satisfy the action requirements leaves the demand active. Successful action issuance moves it to pending. A pending demand does not become active again until its witness advances it to completion. Each demand also carries structured pending-state diagnostics into the generated output. These diagnostics explicitly identify the active-goal action guard, pending-goal witness guard, complete-goal release guard, and the separation between action, witness, and release. They are compile-time explanations of the generated lifecycle, not runtime state.

This is deliberately stricter than the original prototype, which placed witness and release beside one another in the same rule and therefore did not model either pending execution or the separation between completion and release.


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

The compiler also does not claim that an emitted action succeeded. AoE2 world state remains the runtime authority and the witness remains the completion authority. The pending diagnostics deliberately reinforce this distinction: action issuance moves the lifecycle to pending; only the world-state witness advances it to complete.

## Compile

From the repository root:

    python LearnerAI/Compiler/compiler.py LearnerAI/Compiler/examples/basics.basilisk LearnerAI/Compiler/generated/Basilisk.per

Run tests:

    python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"

Do not edit generated .per by hand. Change the Basilisk source or compiler and regenerate it.
