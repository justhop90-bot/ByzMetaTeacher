# Basilisk Validator Handoff

This directory contains two layers of validation. `basilisk-validator.js` is the authoritative front door for Basilisk controller checks. It performs dependency-free static/source-order/hygiene checks, then invokes `repair-lifecycle-replay.js` against the same controller file. The older file remains the detailed lifecycle regression suite rather than being discarded and rewritten for the sake of human architecture worship.

Run from the repository root:

    node validation/basilisk-validator.js

The default controller is `Basilisk/Basilisk.per`. A different controller can be supplied explicitly:

    node validation/basilisk-validator.js path/to/Basilisk.per

The front-door validator currently checks balanced parentheses, nested binary `and/or` arity, line/tab hygiene, removal of obsolete terminal retry-budget symbols, canonical lifecycle anchors, the pre-strategy one-pass rule restriction, source order from final strategy writer through resource-mode arbitration through production and attack delivery, and the live Thumb Ring resource-mode gate. It then requires the full legacy `repair-lifecycle-replay.js` suite to exit successfully. A PASS therefore means the controller satisfied both layers. It does not mean a game was played successfully. The game remains the final behavioral debugger, because apparently software still enjoys being tested in the environment where it actually runs.

`repair-lifecycle-replay.js` contains the deeper, controller-specific regression cases accumulated during repair work: persistent demand survives execution failure, claims release, bounded cooldown reopens the same demand, strategic invalidation clears state, capability loss is cleaned up, opening-plan selection remains reversible, RUSH can promote to Castle-Power or recover to BOOM, FLUSH priority is preserved, and downstream executors retain live resource/strategy gates. Do not remove those assertions when adding a new front-door check. Add a direct assertion when a new defect is found, with a stable rule signature rather than a brittle line number.

The lifecycle doctrine being enforced is:

    OBSERVATION -> INTERPRETATION -> STATE -> DEMAND -> PACKAGE
      -> CAPABILITY -> CLAIM -> FEASIBILITY -> ACTION
      -> WORLD-STATE CHANGE -> COMPLETION / INVALIDATION -> REASSESSMENT

The validator deliberately checks source semantics, not just parser cleanliness. In particular, `can-*` predicates are treated as feasibility witnesses, not completion witnesses; persistent demand must survive transient engine/provider failure; strategic invalidation owns cancellation; queued/pending state must not be silently confused with completed state; one-pass-late state is acceptable only when the final executor re-checks the current safety boundary; and source order is a policy dependency whenever first-write or reset-then-recompute behavior is intentional.

When extending the validator, keep it cheap and native to Node's standard library. Prefer exact stable signatures, explicit source-order assertions, small deterministic policy models for transition matrices, and direct lifecycle invariants. Do not build an AST framework, simulation engine, or generic rule parser unless the controller develops a concrete failure that requires one. The validator is a guard rail around the .per bot, not a second bot.

Known handoff baseline from the current repair cycle: the legacy validator returned PASS against the Basilisk controller with 786 parsed rules and controller content SHA `15d7855863ed83dd42a9d2fbcaee55501e3721f4`. That result validates the fetched source under the validator; it is not a substitute for in-game/replay acceptance.

For the next ChatGPT session: read this file first, then `Basilisk/Lifecycle-Audit-Specification.md`, then run `node validation/basilisk-validator.js` before making lifecycle claims. Treat a failing assertion as a broken wire until the controller source proves otherwise. Do not weaken the validator merely to make a patch pass.
