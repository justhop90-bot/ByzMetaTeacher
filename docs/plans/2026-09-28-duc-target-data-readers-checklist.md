# DUC Target-Data Reader Slice

Date: 2026-09-28
Base: `main` at `257f1cf984454b3717300a18400090bffddc0d1a`

## Native contract cross-check

- [x] `up-object-data` is a Fact over the selected target object.
- [x] `up-get-object-data` reads the selected target object and writes a Goal.
- [x] `up-object-target-data` is a Fact over the selected object's current target.
- [x] `up-get-object-target-data` reads the selected object's current target and writes a Goal.
- [x] UserPatch records that `up-get-object-data` and `up-get-object-target-data` were explicitly repaired to operate correctly as Facts, so the semantic layer handles both fact and action contexts.
- [x] Native Goal output range is constrained to GoalId 1..16000 and width 1.
- [x] Community `aoe2ai` usage chains `up-set-target-object` into `up-get-object-data` and uses the resulting Goals as downstream geometric/object-data inputs.

## Semantic contract

- [x] Target readers require an established object target.
- [x] STALE targets reject target-data reads with `DUC-006`.
- [x] UNKNOWN list-index/native-ID target lifetime emits `DUC-007` advisory diagnostics rather than being promoted to proof.
- [x] `SELECTED_OBJECT_TARGET` reads expose a separate runtime target-of-target boundary.
- [x] `up-get-object-data` and `up-get-object-target-data` create width-1 Goal output spans with provenance and overwrite generations.
- [x] Goal output state persists across passes through the existing DUC output-span model.
- [x] Fact-context `up-get-*` writes are modeled and visible to DUC output state.
- [x] Native contract evidence is pinned into the shared native catalog.

## Hostile regression coverage

- [x] Missing selected target.
- [x] Current list-index target with Goal output.
- [x] Fact-context object-data reader.
- [x] Fact-context object-target-data reader.
- [x] Stale target after reset.
- [x] Direct native-ID target liveness boundary.
- [x] Direct native-ID target-of-target boundary.
- [x] Target-of-target runtime uncertainty on current-pass target.
- [x] Cross-pass syntactic target retention.
- [x] GoalId out-of-range rejection.
- [x] Goal overwrite provenance.
- [x] Native catalog contract/evidence assertions.
- [x] Native citation catalog hygiene assertions.

## Deliberate remaining boundaries

- [ ] Exact scalar value domain for every ObjectData selector is not modeled. The compiler tracks Goal storage/provenance, not the runtime integer value returned by each ObjectData selector.
- [ ] Runtime liveness of the selected native object remains unverified for direct native-ID targets.
- [ ] Runtime existence/current identity of the selected object's own target remains unverified and is reported as a target-of-target boundary.
- [ ] Exact engine failure/value behavior for missing target objects is not simulated beyond target-state diagnostics and Goal-writer provenance.
- [ ] ObjectData-specific semantic ranges and performance/cardinality costs are not yet encoded.

## Verification

- [x] Observed red focused test: `up-get-object-data` without a target produced no DUC diagnostic.
- [x] Observed green focused target-data suite on the implementation head before final cleanup.
- [x] Native target-data contract and citation assertions passed in the focused runner.
- [x] Full compiler regression suite passed on final cleaned branch head in workflow run `36371712710`.
- [x] Native zero-findings acceptance passed on final cleaned branch head in workflow run `36371712710`.
- [x] All 9 native-support determinism jobs passed on final cleaned branch head in workflow run `36371712710`.
- [x] Aggregate native-support snapshot comparison passed on final cleaned branch head in workflow run `36371712710`.
- [x] Compiler verification gate passed on final cleaned branch head in workflow run `36371712710`.
- [ ] Post-merge `main` verification.

## External evidence

- AIRef command schema in the checked-in command inventory:
  - `up-object-data`
  - `up-get-object-data`
  - `up-object-target-data`
  - `up-get-object-target-data`
- UserPatch patch notes: target-data commands were added for selected-object reads and later fixed to operate correctly as Facts.
- Community `lewisc64/aoe2ai`: repeated `up-set-target-object` -> `up-get-object-data` sequences in production rule generation.
