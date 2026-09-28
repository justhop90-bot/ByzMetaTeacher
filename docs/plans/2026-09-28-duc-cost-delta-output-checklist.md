# DUC Cost-Delta Output-Span Repair Checklist

Date: 2026-09-28
Base: main at 3caeb07b67ec00c5abef31a587ef6a924182942a
Target: promote the already-contracted native `up-get-cost-delta` four-Goal writer into DUC semantic output-span state.

## Gap identification

The next open executable compiler gap after DUC-015 is the DUC cost-output writer surface.

The repository already has:
- AIRef/native schema identity for `up-get-cost-delta` as an Action with one OutputGoalId;
- native validator coverage for four consecutive Goal outputs and a maximum start of 15996;
- a checked-in `NativeGoalSpanContract` named `cost-data-4-goal-span` with width 4 and start range 41..15996;
- `DucGoalOutputSpan` IR with generation, overwrite provenance, path ambiguity, and pass identity;
- existing `_write_goal_output_span()` infrastructure used by other DUC writers.

The missing connection is semantic: `semantic/duc.py` has no `up-get-cost-delta` output-writer branch, so a legal native command is validated structurally but does not enter compiler DUC output state.

## AIRef / community cross-reference

### Native evidence

AIRef documents `up-get-cost-delta` as the command that writes the cost difference for food, wood, stone, and gold into four consecutive Goals. The current repository's DE validator contract permits starts through 15996. The native shape is already represented by `cost-data-4-goal-span`.

Sources:
- https://airef.github.io/commands/commands-details.html#up-get-cost-delta
- https://airef.github.io/tables/up-patch-notes.html
- checked-in `docs/reference/inventories/airef-command-schema.json`
- checked-in `validation/basilisk-validator.js`

### Community practice

Community .per routinely establishes cost-data Goal blocks before adding object/research costs, including The General, Promisory/WololoKingdoms, and other native scripting/compiler projects. `lewisc64/aoe2bots` also lowers `@up-setup-cost-data` through its generated scripting layer.

Relevant examples:
- https://github.com/airef/the-general-ai
- https://github.com/SiegeEngineers/WololoKingdoms
- https://github.com/lewisc64/aoe2bots
- https://github.com/mboop127/AlphaScripter

Community evidence supports that cost-data Goal spans are a normal native workflow. It does not justify inventing resource arithmetic or the runtime delta values.

## Scope boundary

Implement only:
`up-get-cost-delta -> four-Goal output span -> DucGoalOutputSpan provenance/generation`.

Do not implement:
- `up-setup-cost-data`;
- `up-add-object-cost`;
- `up-add-research-cost`;
- `up-reset-cost-data`;
- resource stockpile arithmetic;
- exact runtime cost-delta values;
- a new cost-data state machine.

The compiler should know that four native output Goals are written. It must not pretend to know the values written.

## TDD checklist

### Red

- [x] Add focused test: numeric `up-get-cost-delta 41` creates a width-4 Goal output span.
- [x] Assert the span provenance identifies `up-get-cost-delta`.
- [x] Assert the output span is persisted through `DucSemanticState.goal_output_spans`; effect aggregation was intentionally excluded from this narrow repair.
- [x] Add boundary test: start 15996 succeeds.
- [x] Add rejection test: start 15997 produces deterministic `DUC-017`.
- [x] Run focused DUC tests and capture the red result. Workflow #2117 showed 950 tests with 2 failures and 1 error, all three new cost-delta tests.

### Implementation

- [x] Add a dedicated `up-get-cost-delta` branch in `semantic/duc.py`.
- [x] Resolve `cost-data-4-goal-span` from the shared native contract catalog.
- [x] Validate one OutputGoalId against the native span contract.
- [x] Reuse `_write_goal_output_span()` so overwrite-generation/path provenance behavior is unchanged.
- [x] Keep symbolic OutputGoalId behavior conservative and consistent with existing search-state output handling.
- [x] Do not add a second output-span abstraction.
- [x] Do not add cost-value simulation.

### Green / verification

- [x] Focused DUC tests pass on the final compiler run.
- [x] Full compiler unittest suite passes on the exact final head: 950 tests.
- [x] Native zero-findings acceptance passes.
- [x] All 9 native-support determinism jobs pass.
- [x] Snapshot comparison passes.
- [x] Compiler verification gate passes.

## Documentation closure

After the code is green:
- [x] Update `E-compiler_gap_matrix.md` so DUC Goal-output coverage explicitly includes the cost-delta writer.
- [x] Leave cost-data mutation/arithmetic semantics explicitly open.
- [x] Record exact final SHA and workflow evidence here.

## Acceptance

For:
`(up-get-cost-delta 41)`

the compiler must record a concrete 41..44 native Goal span with writer provenance and deterministic output-span generation, without claiming the four runtime delta values.

For 15996 the span 15996..15999 is valid.

For 15997 the command is rejected because the four-slot writer would exceed the native extended Goal span.



## Final verification record

- Final verified code SHA: `b4c143130b267336412c16a57c97fd3bed536d87`
- Compiler workflow: #2119
- Workflow URL: https://github.com/justhop90-bot/ByzMetaTeacher/actions/runs/36490556399
- Compiler regression: 950 tests passed.
- Native zero-findings acceptance: passed.
- Determinism: 9/9 native-support jobs passed.
- Snapshot comparison: passed.
- Compiler verification gate: passed.
- Remaining open semantics: `up-setup-cost-data`, cost-data mutation commands, and the numeric runtime values written by `up-get-cost-delta` remain deliberately unmodeled.
