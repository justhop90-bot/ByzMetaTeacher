# Basilisk Validator Handoff

This directory contains two layers of validation. `basilisk-validator.js` is the authoritative front door for Basilisk controller checks. It performs dependency-free static/source-order/hygiene checks, then invokes `repair-lifecycle-replay.js` against the same controller file. The older file remains the detailed lifecycle regression suite rather than being discarded and rewritten for the sake of human architecture worship.

Run from the repository root:

    node validation/basilisk-validator.js

The default controller is `Basilisk/Basilisk.per`. A different controller can be supplied explicitly:

    node validation/basilisk-validator.js path/to/Basilisk.per

The front-door validator now checks balanced parentheses, exact AoE2 logical-operator arity, DE hard limits for rules/elements/line length/timer IDs, line/tab hygiene, removal of obsolete terminal retry-budget symbols, canonical lifecycle anchors, engine-action `can-*` contracts, queued/completed production witnesses, attack delivery contracts, critical-state writer/reader/action coverage, the strengthened pre-final-strategy one-pass rule restriction, source order through strategy/resource/production/attack boundaries, the live Thumb Ring resource-mode gate, and validator handoff wiring. It then requires the full legacy `repair-lifecycle-replay.js` suite to exit successfully. A PASS therefore means the controller satisfied both layers. It does not mean a game was played successfully. The game remains the final behavioral debugger, because apparently software still enjoys being tested in the environment where it actually runs.

`repair-lifecycle-replay.js` contains the deeper, controller-specific regression cases accumulated during repair work: persistent demand survives execution failure, claims release, bounded cooldown reopens the same demand, strategic invalidation clears state, capability loss is cleaned up, opening-plan selection remains reversible, RUSH can promote to Castle-Power or recover to BOOM, FLUSH priority is preserved, and downstream executors retain live resource/strategy gates. Do not remove those assertions when adding a new front-door check. Add a direct assertion when a new defect is found, with a stable rule signature rather than a brittle line number.

The lifecycle doctrine being enforced is:

    OBSERVATION -> INTERPRETATION -> STATE -> DEMAND -> PACKAGE
      -> CAPABILITY -> CLAIM -> FEASIBILITY -> ACTION
      -> WORLD-STATE CHANGE -> COMPLETION / INVALIDATION -> REASSESSMENT

The validator deliberately checks source semantics, not just parser cleanliness. In particular, `can-*` predicates are treated as feasibility witnesses, not completion witnesses; persistent demand must survive transient engine/provider failure; strategic invalidation owns cancellation; queued/pending state must not be silently confused with completed state; one-pass-late state is acceptable only when the final executor re-checks the current safety boundary; and source order is a policy dependency whenever first-write or reset-then-recompute behavior is intentional.

When extending the validator, keep it cheap and native to Node's standard library. Prefer exact stable signatures, explicit source-order assertions, small deterministic policy models for transition matrices, and direct lifecycle invariants. Do not build an AST framework, simulation engine, or generic rule parser unless the controller develops a concrete failure that requires one. Keep the checks anchored to actual AoE2 engine constraints and Basilisk lifecycle boundaries. The validator is a guard rail around the .per bot, not a second bot.

Known handoff baseline from the current repair cycle: the legacy validator returned PASS against the Basilisk controller with 786 parsed rules and controller content SHA `15d7855863ed83dd42a9d2fbcaee55501e3721f4`. That result validates the fetched source under the validator; it is not a substitute for in-game/replay acceptance.

For the next ChatGPT session: read this file first, then `Basilisk/Lifecycle-Audit-Specification.md`, then run `node validation/basilisk-validator.js` before making lifecycle claims. Treat a failing assertion as a broken wire until the controller source proves otherwise. Do not weaken the validator merely to make a patch pass.


## Current strictness upgrades

1. Engine-limit enforcement now rejects more than 10,000 rules, more than 32 elements in a DE rule, lines over 255 characters, and numeric timer IDs outside 1..50. Basilisk had 13 timer constants assigned above 50; those were reassigned to unused slots within the documented DE range before this gate was enabled.
2. Logical operators are now checked exactly: `not` takes one operand; `and`, `nand`, `nor`, `or`, `xor`, and `xnor` take exactly two. Nested forms remain mandatory for larger boolean expressions.
3. Every `build`, `train`, and `research` action must have the matching `can-*` or escrow feasibility predicate in the same rule. Every train action must expose a queued/completed count witness, and every build action must expose a completed/pending building witness.
4. Strategy-reader phase checking now extends to the final strategy writer, not merely the first strategy writer. A one-pass-late strategy reader may propagate state, but it cannot directly issue an engine action before the final strategic posture for that pass is resolved. Attack delivery also requires its timer/idle contract and, for Castle-Power, the actual completed Crossbow witness.
5. The validator checks its own handoff plumbing and the legacy validator's default controller path, preventing a future session from silently running the obsolete `ByzTeacher/ByzMetaTeacher.per` path.

The external standards behind these changes are AIRef's documented DE limits and logical-operator syntax, plus community examples that pair feasibility commands with engine actions and use `unit-type-count-total` for queued-aware training. The relevant sources are AIRef Data Limits, Logical Operator Commands, Intro to Commands, and the AoE2 forum goal-cleanup examples.