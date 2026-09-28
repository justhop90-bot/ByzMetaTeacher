# DUC Native Oracle Artifacts

This directory is the canonical home for black-box DUC engine-oracle artifacts.

## Layout

- `duc-native-oracle.schema.json`: portable JSON Schema Draft 2020-12 for DUC fixture and observation shape.
- `escrow-same-pass-research.schema.json`: portable JSON Schema Draft 2020-12 for the capture-ready DE escrow/research same-pass oracle.
- `fixtures/`: only pinned, reviewable native observations and synthetic semantic examples.
- `candidates/`: capture-ready native fixture candidates that are not evidence and are never eligible for native-contract promotion.
- `candidates/escrow-same-pass-research.native.json`: five-variant, ten-runs-per-variant candidate for `release-escrow -> research`; it remains UNVERIFIED until populated from an actual DE run.
- `README.md`: boundary and maintenance rules.

Do not create parallel schemas under compiler tests, plans, or inventories.

## Boundary

The schema validates structure, types, enums, and conditional target shape.

It deliberately does not attempt to express:
- equality between unrelated document locations;
- arithmetic relationships such as `count == ids.length`;
- semantic assertions about native behavior.

Those belong to the oracle validation layer and fixture assertion runner.

The observation is nested inside its fixture. Therefore the fixture ID is represented once, eliminating a redundant cross-document identity field.

List snapshots store `ids` as the authoritative observation. A separate `count` field is intentionally not stored because the count is derivable from `ids.length`.

## Required assertion states

- `PASS`: native observation proves the assertion.
- `FAIL`: native observation contradicts the assertion.
- `UNVERIFIED`: the fixture ran, but the observation is insufficient to prove the assertion.
- `NOT_APPLICABLE`: the assertion is outside the applicable path for that fixture.

## Candidate boundary

Files under `candidates/` are capture specifications, not observations. They may contain placeholders for engine build, platform, object identity, and observation values.

A candidate becomes a promotable fixture only after:
1. the exact AoE2DE build, patch, AI layer, and runtime platform are recorded;
2. the setup and probe commands are executed against that runtime;
3. the observation fields are populated from the runtime rather than inferred;
4. each relevant assertion is `PASS` or `FAIL`;
5. the populated artifact is moved into `fixtures/` and validated by the oracle assertion runner.

Do not replace `UNVERIFIED` with a guessed engine behavior. Native uncertainty is data.

## Maintenance rules

Keep fixtures small and atomic. Do not bundle multiple disputed semantics into one scenario.

Fixtures of kind `NATIVE_OBSERVATION` must pin the exact engine build and native environment used to produce their observation. They are the only artifacts eligible to support native-contract promotion.

Fixtures of kind `SEMANTIC_EXAMPLE` are synthetic test doubles used to exercise the artifact format and semantic assertion machinery. They must use `engine_scope.build = fixture-test-double` and are never evidence for engine behavior.

A compiler contract may be promoted from oracle evidence only after the corresponding `NATIVE_OBSERVATION` fixture is reproducible and its relevant assertion is `PASS`.

Do not replace `UNVERIFIED` with a guessed engine behavior. Native uncertainty is data.
