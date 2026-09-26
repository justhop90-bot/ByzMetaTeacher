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

## Engine-state semantics

The primitive profile now distinguishes capability, pending, queued/under-construction, and completed evidence.

up-pending-objects is an observation of pending work. building-type-count-total and unit-type-count-total include existing plus queued/under-construction objects. Those facts are valid execution inputs but are not completion witnesses.

Completion witnesses must use evidence that proves the requested world state. The compiler therefore rejects pending and total-count primitives as completion witnesses instead of allowing a demand to declare its own action still being queued as success.

The capability profile also includes can-build-with-escrow, can-train-with-escrow, and can-research-with-escrow. These remain feasibility predicates: escrow-aware feasibility authorizes an action but does not prove that the action succeeded.

## Expression validation

The semantic analyzer parses parenthesized native .per expressions enough to identify their root primitive, validate primitive argument counts, and validate logical operator arity.

AoE2 logical operators are not arbitrary variadic functions. and, or, nand, nor, xor, and xnor are binary and not is unary. More operands require nesting. This follows the documented AIRef command behavior.

The compiler currently permits nested logical expressions but keeps ordinary primitive arguments atomic. It rejects rule separators, unknown primitives, invalid contexts, and incorrect argument counts.

## Native validation

The compiler now has a native validation boundary after deterministic .per emission:

    source -> AST -> semantic IR -> .per -> native backend adapter -> normalized diagnostics

The adapter invokes the pinned aoe2-ai-parser release through subprocess rather than importing its code. Its backend identity is locked by version, source commit, and Python major/minor.

The adapter validates the machine-readable JSON protocol strictly. Native findings retain their backend diagnostic codes and confidence/severity. Source columns are normalized from the backend's zero-based spans to LearnerAI's one-based columns.

Backend failures are never reported as script rejection. Timeout, executable failure, version mismatch, and malformed JSON all mean that native validation evidence is unavailable or invalid.

See backends/README.md for the complete protocol, process isolation rules, research findings, and fixture matrix.

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

## Native validation

The compiler can stage its generated .per and ask the pinned native backend to validate it before promotion:

    python LearnerAI/Compiler/compiler.py ^
        LearnerAI/Compiler/examples/basics.basilisk ^
        LearnerAI/Compiler/generated/Basilisk.per ^
        --validate-native ^
        --native-backend-root tools/native-backends/aoe2-ai-parser

Use --native-json for the normalized machine-readable validation result.

Without --validate-native, compilation retains the original direct-write behavior. With native validation enabled, a rejected artifact or unavailable backend does not replace an existing output file.

Exit status with native validation is:

    0 = VALIDATED
    1 = REJECTED
    2 = backend/process/validation infrastructure failure

See backends/README.md and RESEARCH_CHECKLIST.md for the adapter contract and remaining research work.

## Compile

From the repository root:

    python LearnerAI/Compiler/compiler.py LearnerAI/Compiler/examples/basics.basilisk LearnerAI/Compiler/generated/Basilisk.per

Run tests:

    python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"

Do not edit generated .per by hand. Change the Basilisk source or compiler and regenerate it.
