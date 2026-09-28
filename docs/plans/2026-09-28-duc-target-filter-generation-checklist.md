# DUC Retained-Target Filter-Generation Repair Checklist

## Gap
After DUC-015, the remaining bounded target-lifetime gap is retained object-target provenance across filter-generation changes. The IR already records `source_filter_generation`, but filter mutation currently leaves an old list-derived target fully VALID/PROVEN.

## Community cross-reference
Community AoE2 `.per` scripts commonly rebuild searches after `up-full-reset-search`, `up-filter-*`, and `up-find-*`, then call `up-set-target-object` before consuming the target. AIRef defines `up-set-target-object` as selecting a target from the current search list. Community examples therefore support invalidating stale proof provenance after a filter-generation change, not claiming object death.

Sources:
- https://userpatch.aiscripters.net/reference.html
- https://github.com/lewisc64/aoe2ai
- https://forums.ageofempires.com/t/help-so-you-can-make-the-ai-attack-different-points/286382

## Repair rules
- [x] Filter-generation change on a list-derived target => UNKNOWN validity and UNKNOWN proof.
- [x] Native-ID targets remain untouched because they do not depend on search/filter provenance.
- [x] Do not claim STALE from filter mutation alone.
- [x] Existing reset/list invalidation behavior remains unchanged.
- [x] Existing target-consumer/data-reader diagnostics continue to consume the downgraded state.

## TDD
- [x] Add local target + filter mutation regression.
- [x] Add remote target + filter mutation regression.
- [x] Add native-ID target preservation regression.
- [x] Add re-establishment-after-filter regression proving CURRENT_PASS_PROOF restoration.
- [x] Observe focused red phase.
- [x] Implement one helper in `semantic/duc.py`; no IR changes.
- [x] Run focused DUC tests.
- [x] Run full Compiler workflow and native/determinism gate.
- [x] Update gap matrix after green.

## Explicitly open
Filter mutation alone does not prove that an object died or moved. Actual target liveness remains runtime-dependent.


## Verification record

- Implemented in `LearnerAI/Compiler/semantic/duc.py`.
- Code commits: `77d98f6e5b74724dce6c908d40f0c5ddc9006308` and `b6245f848723d558e3c3fa450e3ba42bcfa27cd9`.
- Compiler workflow: #2121
- Workflow URL: https://github.com/justhop90-bot/ByzMetaTeacher/actions/runs/36491073839
- Exact verified SHA: `b6245f848723d558e3c3fa450e3ba42bcfa27cd9`
- Compiler regression: 954 tests passed.
- Native zero-findings and all nine determinism jobs: passed.
- Snapshot comparison: passed.
- Compiler verification gate: passed.
- Separate repository check `basilisk-validator` remains red on a pre-existing Crossbow role-demand assertion; it is not part of the Compiler workflow gate and did not fail the DUC repair.
