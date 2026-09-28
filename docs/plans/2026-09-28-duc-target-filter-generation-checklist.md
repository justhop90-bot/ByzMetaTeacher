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
- [ ] Filter-generation change on a list-derived target => UNKNOWN validity and UNKNOWN proof.
- [ ] Native-ID targets remain untouched because they do not depend on search/filter provenance.
- [ ] Do not claim STALE from filter mutation alone.
- [ ] Existing reset/list invalidation behavior remains unchanged.
- [ ] Existing target-consumer/data-reader diagnostics continue to consume the downgraded state.

## TDD
- [ ] Add local target + filter mutation regression.
- [ ] Add remote target + filter mutation regression.
- [ ] Add native-ID target preservation regression.
- [ ] Add re-establishment-after-filter regression proving CURRENT_PASS_PROOF restoration.
- [ ] Observe focused red phase.
- [ ] Implement one helper in `semantic/duc.py`; no IR changes.
- [ ] Run focused DUC tests.
- [ ] Run full Compiler workflow and native/determinism gate.
- [ ] Update gap matrix after green.

## Explicitly open
Filter mutation alone does not prove that an object died or moved. Actual target liveness remains runtime-dependent.
