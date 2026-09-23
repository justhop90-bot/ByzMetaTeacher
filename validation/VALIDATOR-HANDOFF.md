# Basilisk Validator Handoff

This directory contains two layers of validation. `basilisk-validator.js` is the authoritative front door for Basilisk controller checks. It performs dependency-free static/source-order/hygiene checks, then invokes `repair-lifecycle-replay.js` against the same controller file. The older file remains the detailed lifecycle regression suite rather than being discarded and rewritten for the sake of human architecture worship.

Run from the repository root:

    node validation/basilisk-validator.js

The default controller is `Basilisk/Basilisk.per`. A different controller can be supplied explicitly:

    node validation/basilisk-validator.js path/to/Basilisk.per

The front-door validator now checks balanced parentheses with string-safe structural masking, exact AoE2 logical-operator arity, top-level form and `defrule =>` structure, DE hard limits for rules/elements/line length/timer IDs, duplicate/out-of-range defconsts, typed `c:/g:/s:` operands, named timer resolution, AIRef command-name/type resolution, AIRef point/cost/search-state goal-block safety, AIRef DUC search-list bounds, line/tab hygiene, removal of obsolete terminal retry-budget symbols, canonical lifecycle anchors, engine-action `can-*` contracts, target-aware queued/completed production witnesses, attack delivery contracts, critical-state writer/reader/action coverage, the strengthened pre-final-strategy one-pass rule restriction, source order through strategy/resource/production/attack boundaries, the live Thumb Ring resource-mode gate, and validator handoff wiring. It then requires the full legacy `repair-lifecycle-replay.js` suite to exit successfully. A separate `validation/basilisk-validator-selftest.js` mutation suite exercises the validator against deliberate false-negative cases. A PASS therefore means the controller satisfied both layers. It does not mean a game was played successfully. The game remains the final behavioral debugger, because apparently software still enjoys being tested in the environment where it actually runs.

`repair-lifecycle-replay.js` contains the deeper, controller-specific regression cases accumulated during repair work: persistent demand survives execution failure, claims release, bounded cooldown reopens the same demand, strategic invalidation clears state, capability loss is cleaned up, opening-plan selection remains reversible, RUSH can promote to Castle-Power or recover to BOOM, FLUSH priority is preserved, and downstream executors retain live resource/strategy gates. Do not remove those assertions when adding a new front-door check. Add a direct assertion when a new defect is found, with a stable rule signature rather than a brittle line number.

The lifecycle doctrine being enforced is:

    OBSERVATION -> INTERPRETATION -> STATE -> DEMAND -> PACKAGE
      -> CAPABILITY -> CLAIM -> FEASIBILITY -> ACTION
      -> WORLD-STATE CHANGE -> COMPLETION / INVALIDATION -> REASSESSMENT

The validator deliberately checks source semantics, not just parser cleanliness. It also resolves standard DE unit-line families when validating training witnesses, because units such as Onager and Camel are represented by the engine through their underlying unit lines. In particular, `can-*` predicates are treated as feasibility witnesses, not completion witnesses; persistent demand must survive transient engine/provider failure; strategic invalidation owns cancellation; queued/pending state must not be silently confused with completed state; one-pass-late state is acceptable only when the final executor re-checks the current safety boundary; and source order is a policy dependency whenever first-write or reset-then-recompute behavior is intentional. Rule size is also treated as three distinct concerns: the 32-element DE hard ceiling, the 30-31 element maintenance-risk band, and the separate >150-character single-line rule risk that community tooling flags even when the element count is legal.

When extending the validator, keep it cheap and native to Node's standard library. Run both `node validation/basilisk-validator.js` and `node validation/basilisk-validator-selftest.js` before declaring validator integrity. Prefer exact stable signatures, explicit source-order assertions, small deterministic policy models for transition matrices, and direct lifecycle invariants. Do not build an AST framework, simulation engine, or generic rule parser unless the controller develops a concrete failure that requires one. Keep the checks anchored to actual AoE2 engine constraints and Basilisk lifecycle boundaries. The validator is a guard rail around the .per bot, not a second bot.

Current source baseline: Basilisk/Basilisk.per is at controller content SHA `3355c5bba068137b5d9c46ca114dc9d7185e2091` with 795 parsed rules. Source-level validation of the current controller reports a 239-character maximum line and a 31-element maximum rule size. The front-door validator has also been mutation-tested against deliberate parser, identifier, timer, witness, defconst, and typed-operand defects; those mutations fail with targeted diagnostics. A full end-to-end spawned run of the front door was not executed in this environment, and the connected game machine is unavailable, so this evidence remains validator/replay verification rather than game/runtime PASS.

For the next ChatGPT session: read this file first, then `Basilisk/Lifecycle-Audit-Specification.md`, then run `node validation/basilisk-validator.js` before making lifecycle claims. Treat a failing assertion as a broken wire until the controller source proves otherwise. Do not weaken the validator merely to make a patch pass.

## Current AIRef command-source gate

The repository now contains extracted/inventories/airef-command-inventory.json, generated from the current AIRef master js/commands.js command definitions. It records the exhaustive 385-command vocabulary, each command's AIRef type/version, the source blob SHA, and Basilisk's 88-command usage set. docs/reference/AIREF-COMMAND-SOURCE.md is the human-facing audit companion.

The front-door validator rejects any engine command/fact symbol absent from that snapshot and rejects Fact/Action misuse by rule side. AIRef logical operators are classified as Other and are handled as condition-side syntax. It also checks the AIRef consecutive-goal safety rules for up-get-point, up-get-search-state, up-get-cost-delta, and up-setup-cost-data, plus the 240-local/40-remote DUC search limits.

The repository also carries `extracted/inventories/airef-command-schema.json` with slot metadata for the complete 385-command AIRef catalog. The schema is anchored to the same AIRef `commands.js` blob SHA as the command vocabulary snapshot and is cross-checked against that inventory on every front-door run. Slot validation covers arity, direct parameter families, strict value-list enums, typeOp/compareOp/mathOp syntax, typed operands, and documented numeric ranges. The validator additionally enforces the community-lab retained-search DUC safety checks for unscoped target orders and unsafe `up-set-target-object` use.

The schema was cross-referenced against the bundled `aoe2-ai-parser 0.1.82` laboratory package and its AIRef scraper/parser/linter. The lab is a secondary engineering reference: AIRef remains the language authority; community parser diagnostics supply practical lint categories such as command-family mismatch, typed-operand mismatch, split typed comparison, numeric-range mismatch, and retained-search DUC safety. The lab runtime is not vendored into Basilisk and does not replace game/runtime validation.

## Current strictness upgrades

Three engine-hygiene diagnostics are now explicit and intentionally named after the failures they prevent:

1. **Invalid identifier** means an engine-facing identifier cannot be resolved to a Basilisk `defconst`, the checked-in DE AIRef object/technology/strategic-number registries, or the checked-in value/class registries. The check covers direct `build`, `train`, `research`, `can-*`, `goal`, `set-goal`, `up-compare-goal`, and strategic-number identifier slots. This is specifically aimed at typos such as a misspelled `ri-*`, unit, building, or goal constant. Two explicit current-engine supplements, `siege-tower` and `ri-logistica`, are documented because the checked-in AIRef scrape does not contain them even though Basilisk uses them.
2. **Missing closing parenthesis** is a source-structure error. The validator now reports the opening line of an unclosed `defrule` and the final unmatched-opening count, while the balanced-parenthesis pass still catches premature closing parentheses separately.
3. **Rule too long** means a parsed DE `defrule` exceeds the documented 32-element rule limit. The count is every nested parenthesized command/fact/logical form inside the rule, excluding the outer `defrule` wrapper. Exactly 32 is legal; greater than 32 is a hard failure. The current Basilisk controller has four rules at 31 elements and four more at 30 elements. The validator reports 30-31 as `near-limit` and 32 as `at-limit` without failing them. These are maintenance/semantic hotspots, not automatic engine defects. A separate `complex single-line defrule` check rejects one-line rules above 150 characters because community testing reports unpredictable DE rejection even when the parser accepts them.

The validator also treats 255 characters as the source-line ceiling and keeps the separate line-too-long diagnostic distinct from the 32-element rule limit.


### Existing strictness gates

1. Engine-limit enforcement rejects more than 10,000 rules, more than 32 elements in a DE rule, lines over 255 characters, and numeric timer IDs outside 1..50.
2. Logical operators are checked exactly: `not` takes one operand; `and`, `nand`, `nor`, `or`, `xor`, and `xnor` take exactly two. Nested forms remain mandatory for larger Boolean expressions.
3. Every `build`, `train`, and `research` action must have the matching `can-*` or escrow feasibility predicate in the same rule. Train witnesses must refer to the trained object or its standard engine unit line; build witnesses must refer to the same building.
4. Named timer IDs must resolve to numeric defconsts in 1..50. Typed `c:`, `g:`, and `s:` operands are resolved against the checked-in engine inventories and Basilisk defconsts.
5. Top-level syntax is restricted to `defconst` and `defrule` forms (with preprocessor directives permitted), and every rule must contain exactly one `=>` separator followed by an action form.
6. Strategy-reader phase checking extends to the final strategy writer, and downstream executors must re-check live strategic/resource boundaries. Attack delivery also requires its timer/idle contract and, for Castle-Power, the actual completed Crossbow witness.
7. The validator checks its own handoff plumbing and the legacy validator's default controller path.
8. `validation/basilisk-validator-selftest.js` runs the real front door against temporary mutated controllers covering unknown DUC identifiers, unknown timers, missing rule separators, stray top-level forms, unrelated production witnesses, duplicate/out-of-range defconsts, and invalid `g:/s:` operands. It also includes a positive string-safety case.

The external standards behind these changes are AIRef's documented DE limits, logical-operator syntax, timer range, command vocabulary/type, point/cost/search-state goal allocation rules, DUC search-list bounds, and command parameter typing, plus community examples that pair feasibility commands with engine actions and use queued-aware unit-line counts. The current validator baseline is 795 rules, a 239-character maximum source line, and a 31-element maximum rule size. The AIRef schema covers all 385 commands, while the current Basilisk controller uses 88 of them.