# Byzantine Runtime Evidence

Runtime evidence is the authority for gameplay behavior. Compiler tests prove lowering, syntax, determinism, and declared semantic contracts. They do not prove that the live engine chose the intended resource, attack target, path, or battlefield action.

Every captured witness should record the exact `Byzantine.per` SHA-256, repository commit, map, civs, difficulty, population, game time, observed action, and the world-state witness that proves completion. A screenshot is useful evidence, but the trace should state what the screenshot actually proves.

Evidence classes stay separate:

- ENGINE FACT: native engine behavior established by reference documentation or reproducible engine behavior.
- COMMUNITY PRACTICE: recurring scripting practice with provenance.
- COMPILER POLICY: intended ByzMetaTeacher behavior.
- OPEN / UNKNOWN: claim not yet proven in the live engine.

The runtime scenarios under `docs/runtime/scenarios/` are test contracts, not match results. A scenario remains `OPEN` until a live match supplies direct observations. The artifact SHA must be captured at match time.

The first acceptance family is deliberately adversarial: Arena mild Feudal pressure, resource-camp placement and later resource loss, autonomous attack/release, and siege conversion. These are the current high-value boundaries between compiler correctness and gameplay correctness.
