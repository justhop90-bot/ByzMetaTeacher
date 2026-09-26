# Minimal Basilisk compiler

This compiler is deliberately thin. Requirements, actions, witnesses, and release conditions are native AoE2 `.per` expressions. The compiler owns demand identity, persistent goal initialization, lifecycle release, deterministic goal allocation, and structural validation.

Language:

    demand <name> {
        require (<native .per predicate>)
        require (<native .per predicate>)
        action (<native .per action>)
        witness (<native .per world-state predicate>)
        release (<native .per predicate>)
    }

Every demand needs at least one requirement and exactly one action, witness, and release condition. The compiler rejects missing fields, duplicate fields/demands, malformed names, non-parenthesized expressions, and action separators inside expressions.

Compile from the repository root:

    python LearnerAI/Compiler/compiler.py LearnerAI/Compiler/examples/basics.basilisk LearnerAI/Compiler/generated/Basilisk.per

The generated file contains goal constants, a one-shot demand initialization rule, one action rule per demand, and one witness/release rule per demand.

This is the first compiler slice, not a complete bot generator. Pending state, escrow, source-order analysis, ownership, rule-size checks, capability declarations, and engine primitive schemas belong in later compiler stages. Native `.per` remains visible so generated output can be audited rather than hidden behind invented semantics.
