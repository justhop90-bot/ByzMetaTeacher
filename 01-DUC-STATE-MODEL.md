# 01 — DUC SearchSession / TargetSession state-model dossier @ `cd923b5a`

Ground truth: `LearnerAI/Compiler/ir/duc.py` (610 lines: `DucSearchListState`, `DucSearchIndexState`,
`DucFilterState`, `DucTargetState`, `DucPointRef`, `DucGroupState`, `DucGoalOutputSpan`, `DucSearchOperation`,
`DucResetEffect`, `DucListMutationEffect`); `LearnerAI/Compiler/semantic/duc.py` (4340 lines: abstract
interpreter); `LearnerAI/Compiler/ir/native_duc.py` (emission plan); `primitives/native_hygiene.py`
(~2500 lines: `NativeContractCatalog` + citation catalog); `oracles/duc_native.py` (shape only);
`tests/test_duc_semantics.py`, `test_duc_composite_fixture.py`, `test_duc_oracle_consistency.py`;
`DUC_SEMANTIC_IMPLEMENTATION_CHECKLIST_2026-09-27.md` (slices A–M; D/G explicitly OPEN);
`DUC_RECURRENT_EXECUTION_INTEGRATION_CHECKLIST_2026-09-27.md` (`NEVER_RUNNABLE` suppression);
`MUSE_NEXT_IMPLEMENTATION_CHECKLIST_2026-09-28.md` Tier-1 DUC; `runtime_binding.py` + `RUNTIME_BINDING_CONTRACT.md`
(GoalSlot/GoalSpan: w1 `1..16000`, w2 `41..15998` POINT_PAIR, w4 `41..15996` EXTENDED_4); `docs/plans/2026-09-2*duc*.md`
(18 files); `primitives/engine_semantics.py:187-221,698-721` + `primitives/registry.py:393-614`.

## 1. Per-command static contracts

### `up-find-local` — `EXECUTABLE_SAFE` (search path) + `ENGINE_SEMANTICS_MAPPED` (cursor advisory)
- AUTHORITATIVE SOURCE: `native_hygiene.py:757` contract + `:2287` signature; `semantic/duc.py:87-90,2145-2177`; `ir/duc.py:381-401`. REVISION: `cd923b5a`.
- EXACT SIGNATURE: `(up-find-local <typeOp> <UnitId> <typeOp> <Value)` — 4 predicate operands; final operand is predicate, NOT a result-count budget (`docs/plans/2026-09-27-duc-search-cursor-checklist.md:9,37`).
- INPUTS: retained `DucFilterState` snapshot; `DucSearchIndexState` (offset/generation/query-signature/focus); prior LOCAL `DucListGeneration`.
- OUTPUTS/MUTATIONS: appends new gen (`generation=next_generation`, `capacity=240`); `total=(prev.min, min(240, prev.max+added))`, `last_search=0..available` (`duc.py:656-679`); new `DucSearchOperation` with consumed filter, index/cursor before-after, `result_disposition`, `fact_result`; cursor → `RUNTIME_ADVANCED` (offset None/known=False), or `AT_END`/`BLOCKED_BY_CAPACITY` only if proven (`:681-735`).
- STATE OWNERSHIP: `DucSemanticState.local_list` (`ir/duc.py:494-504`). LIFETIME: retained across rules+passes until `up-reset-search` list flag or `up-full-reset-search` (`:2275-2309,2326-2354`). ORDERING: same-rule order = `within_rule_order`; query-change reset before scan (`:612-649`). PERSISTENCE: yes, cross-rule+cross-pass (`advance_duc_pass` keeps lists/filters, `:4305-4334`).
- CARDINALITY: `0..240` total; `GUARANTEED_EMPTY → 0..0`. VERSION: UP DUC; Fact/Action dual; zero-result-false UP `20130302-150016` (`native_hygiene:2485-2489`); query/filter/focus resets UP `20130305-140519` (`:776-824`).
- KNOWN INTERACTIONS: filters (consumed snapshot, `DUC-012` if ambiguous); search-index; recurrent cost `DUC-015` MEDIUM/240; groups read LOCAL gen; `up-get-search-state`; target establishment reads generation.
- COMMUNITY: lewisc64/aoe2ai chained finds + resets — idiom only, never promoted.
- PROVEN: append-not-replace lineage; scan-frontier cursor; capacity-block + end-of-scan guaranteed-empty. UNKNOWN (OPEN): exact post-search numeric offset; runtime ordering/visibility/success.
- IMPLEMENTATION TARGET: `_apply_duc_search()` + `_search_cardinality()` + `_search_cursor_transition()`; `NativeDucSearchContract("up-find-local","LOCAL",240,...)`. TEST TARGET: chained-search, cursor, capacity, Fact-form, branch-widen tests; composite search seeding.

### `up-find-remote` — `EXECUTABLE_SAFE` (same caveat)
Same as above, REMOTE, `capacity=40` (`native_hygiene:759,2289`; `duc.py:91-95`); remote index carries `focus_player_signature` default `"0"` (`:1160-1180`); focus-player change resets REMOTE only (`:547-609`); recurrent cost FAST/40.

### `up-find-player` — `UNKNOWN` (does NOT exist; only `up-find-flare`/`up-find-player-flare` exist). Do not implement.
### `up-find-status-local/remote`, `up-find-resource` — `SEMANTICALLY_ADAPTED` (same `_apply_duc_search` path; verify per-command Fact nuance before relying).
### `up-set-target-object (SearchSource typeOp Index)`, `SearchSource in {search-local,search-remote}` — `EXECUTABLE_SAFE` (guards) / `EVIDENCE_ONLY`+`OPEN` (failed-Action preservation, post-mutation liveness)
- SOURCE: `native_hygiene:978-989,2309`; `duc.py:2738-2912` Action + `:1428-1514` Fact; `ir/duc.py:276-297`. INPUTS: list + filter generation. OUTPUTS: `DucTargetState{kind=OBJECT, object_refs=[(list_kind,list_generation,list_index,None)], source gens, validity, proof, pass_id}`; Fact path emits `DucTargetFactObservation`, never fabricates (`:1509-1514`).
- ORDERING: requires initialized list (`DUC-005`); proven-empty non-ambiguous → `DUC-014`, no target (`:2788-2818`); OOR index → `DUC-014`, prior target preserved + `DUC-007` (effect OPEN; `failed_action_preserves_previous_target=None`).
- PROOF: `CURRENT_PASS_PROOF` if same pass else `PRESERVED_PROOF`; `UNKNOWN` if path-ambiguous; pass advance → `UNKNOWN/SYNTACTIC_RETENTION` (STALE stays STALE); filter-gen change → `UNKNOWN/UNKNOWN`. TEST: `test_duc_semantics:379-553`.

### `up-set-target-point (Point)` — `NATIVE_TYPED → SEMANTICALLY_ADAPTED` (coordinate values NOT executable-safe)
Writes `point_target: DucPointRef` only (`duc.py:2914-2943`); retained across passes, cleared only by FULL; join keeps iff all paths equal. Point chain fixture OPEN (checklist G) — add fixture before depending.

### `up-set-target-by-id (typeOp Id)` — `SEMANTICALLY_ADAPTED`
`native_hygiene:968-977,2304`; `duc.py:2651-2736`; `c:`+numeric → `native_object_id`, else unresolved symbolic; negative `c:` → `DUC-005`. Output `UNKNOWN/NATIVE_ID_PROOF`, independent of list gens; survives resets/sorts/removes; join keeps iff same ID; FULL reset authoritative. Liveness explicitly UNKNOWN. TEST: `:95-106`.

### `up-target-objects (Option Action Formation Stance)`, `Option in {0,1}` — `SEMANTICALLY_ADAPTED`
`0→LOCAL_SEARCH_RESULTS` (needs init list, no target); `1→SELECTED_OBJECT_ONLY` (needs target; STALE→`DUC-006`, UNKNOWN→`DUC-007` with proof-specific message; records `DucTargetConsumerEffect`). SORT degrades list-index target to UNKNOWN before opt-1 can consume provably. TEST: `:591-619`, composite rule 10.

### `up-target-point (EscrowGoalId Action Formation Stance)` — `SEMANTICALLY_ADAPTED`
`up-target-point` consumes the current local search list and directs those units to the established point target. Its four-argument action form is now promoted through the executable DUC semantic channel; runtime action completion remains OPEN and is witnessed separately from the request.
### `up-clean-search (Source ObjectData Order)` — `SEMANTICALLY_ADAPTED` (STALE-vs-UNKNOWN distinction OPEN, checklist D)
`"-1"→DEDUPE` else `SORT`; SORT keeps cardinality, DEDUPE clears to None; fingerprint rotated; target → `UNKNOWN/UNKNOWN`, `index_stable=False`; cursor NOT reset. Native SORT fact ENGINE-mapped, preservation NOT mapped.
### `up-remove-objects (Source ObjectData cmp Val)` — `SEMANTICALLY_ADAPTED`
Always `REMOVE_MATCHES`. `-1`+static proof selected index removed → STALE; proves only preceding → UNCHANGED; else UNKNOWN. Composite pins both (`-1 > 1`→UNCHANGED; `-1 == 0` idx0→STALE).
### `up-add-object-by-id (Source typeOp Id)` Action-only — `SEMANTICALLY_ADAPTED` (duplicate/presence/position/success OPEN)
Distinct `ADD_OBJECT` kind; cursor+filters preserved; cardinality→None (UNKNOWN); fingerprint→None; list-index target on affected list → UNKNOWN; direct-ID untouched; `c:` non-int/negative → `DUC-017`.
### Bare `up-add-object` does NOT exist. `up-full-reset` as named does NOT exist (native is `up-full-reset-search`).
### Search-index / list-index cursor — reset triggers `ENGINE_SEMANTICS_MAPPED`, advancement `EVIDENCE_ONLY` (deliberately unmodeled numerics)
`DucSearchIndexState{offset,generation,query_signature,focus_player_signature,known,last_reset_reason,cursor_disposition,path_ambiguous}`; dispositions INITIAL/RESET_START/RUNTIME_ADVANCED/AT_END/BLOCKED_BY_CAPACITY/PATH_AMBIGUOUS. Resets: EXPLICIT / QUERY_CHANGE (relevant list) / FILTER_CHANGE (both) / FOCUS_PLAYER_CHANGE (REMOTE). Post-search offset always None/unknown unless AT_END/BLOCKED proven. No numeric offset claim without proof.
### `up-can-search (Source)` Fact-only — `SEMANTICALLY_ADAPTED` (truth beyond exhaustion OPEN)
`DucSearchAvailabilityObservation`, no mutation. `GUARANTEED_FALSE` iff `AT_END∨BLOCKED_BY_CAPACITY`, else `RUNTIME_DEPENDENT` (even uninit). Action use → `DUC-005`.
### `up-full-reset-search ()` — `ENGINE_SEMANTICS_MAPPED`; `up-reset-search (LI LL RI RL)` — `ENGINE_SEMANTICS_MAPPED`; `up-reset-filters ()` — `ENGINE_SEMANTICS_MAPPED`. See transitions T4–T6.
### `up-get-search-state (OutGoal)` — span binding `EXECUTABLE_SAFE`, values beyond conservative cardinality OPEN
Width-4 span `41..15996`; `DucSearchStateObservation` (both cardinalities + cursors + fingerprint + span); `DUC-001` if neither list init; `DUC-017` if span cannot fit; symbolic IDs unresolved; reads lists, writes output, never moves cursor. TEST: `:732-877`.
### Groups: `up-create-group (Goal Goal typeOp GroupId)` / `up-reset-group` / `up-set-group (Source typeOp GroupId)` / `up-group-size` Fact / `up-get-group-size (typeOp GroupId OutGoal)` — group-size w1 binding `EXECUTABLE_SAFE`, membership/flag values OPEN
20 groups `0..19`, cap 40, `_group_cardinality` clipped; `up-set-group` reloads dest list + STALEs same-scope target; groups survive resets/joins with widening. TEST: `:910-1170`.
### `up-get-cost-delta (OutGoal)` w4 — `SEMANTICALLY_ADAPTED` (re-verify binder before SAFE). No cost arithmetic, no setup machine.
### `up-get-point (Point OutGoal)` w2 `41..15998` — `SEMANTICALLY_ADAPTED`. TEST `:123-164` (41/15998 accept, 15999 reject).
### `up-object-data / up-get-object-data / up-object-target-data / up-get-object-target-data` — `SEMANTICALLY_ADAPTED`
`DucTargetDataObservation{relation SELECTED_OBJECT vs SELECTED_OBJECT_TARGET, writes_goal, validity/proof, span?}`; missing→005, STALE→006, UNKNOWN→007; target-of-target always +007 (unmodeled); scalar ObjectData domains NOT modeled (storage/provenance only).

## 2. Transition table

T1 find-local: no gen/filter F → gen N (cap 240), fingerprint chained, card ranges; persists (next=N+1); invalidates none; dependents: filter snapshot pinned, index RUNTIME_ADVANCED, older-gen target proofs relatively stale. UNKNOWN: numeric offset, existence, Fact truth unless proven.
T2 find-remote: same, cap 40 + focus sig.
T3 `up-filter-*` (6 cmds): F → F+1 (predicates+1, fingerprint chained, retained=True); lists kept; BOTH indices FILTER_CHANGED-reset if `resets_search_indices` (distance/exclude/garrison/include/range=True, status=False); list-derived target → UNKNOWN/UNKNOWN; direct-ID exempt. UNKNOWN: whether engine kills live target.
T4 `up-reset-search(a,b,c,d)`: selected lists → None (+next+1 iff present); selected indices EXPLICIT/RESET_START/0; unselected/filter/target untouched except scoped STALE; `rule_reset_lists` suppresses recurrent 008/015 for that kind.
T5 `up-reset-filters`: filters clean (gen+1 unless already clean → idempotent); BOTH indices reset; lists+targets kept.
T6 `up-full-reset-search`: both lists None, filters clean, target+point None, both indices reset; cardinalities 0..0.
T7 valid `up-set-target-object`: (L gen N, filter F) → target OBJECT ref(L,N,i) VALID CURRENT|PRESERVED|UNKNOWN. UNKNOWN: liveness at i.
T8 failed set-target (empty/OOR/uninit): NO new target; prior kept + DUC-007 (+014/005). UNKNOWN: engine preserve/invalidate/replace (candidate `duc-failed-target-action.native.json` UNVERIFIED).
T9 `up-set-target-by-id`: direct-ID UNKNOWN/NATIVE_ID_PROOF; lists/indices/filters untouched. UNKNOWN: liveness/death.
T10 `up-set-target-point`: point_ref set; object target untouched. UNKNOWN: coordinate meaning.
T11 `up-clean-search(L)`: list mutated (SORT keeps card; DEDUPE→None); fingerprint rotated; T→UNKNOWN/UNKNOWN index_stable=False. UNKNOWN: preserved-identity vs retarget-by-index (candidate UNVERIFIED).
T12 `up-remove-objects(L,-1,op,v)`: STALE iff proves selected removed; UNCHANGED iff proves only preceding; else UNKNOWN. UNKNOWN: non-`-1`/dynamic matching.
T13 `up-add-object-by-id`: card→None, fingerprint→None; list-index T(L)→UNKNOWN; direct-ID kept. UNKNOWN: duplicate/presence/position/success.
T14 recurrent find w/o same-rule reset: new gen (accumulation) + DUC-008 + advisory DUC-015; suppressed by same-rule reset or ONE_SHOT. Cost ms/lag advisory only.
T15 pass advance: lists/filters/groups/spans kept (pass+1); object target → UNKNOWN/SYNTACTIC_RETENTION (STALE preserved); focus kept. UNKNOWN: cross-pass survival.
T16 branch join: identical kept; divergent lists → None+variants+ambiguous; filters AMBIGUOUS; targets representative+UNKNOWN (same direct-ID → UNKNOWN/NATIVE_ID_PROOF else stripped); spans widened; `DucBranchMerge` recorded. Path taken fundamentally runtime.
T17 loop back-edge: bounded widen limit 3 + DUC-016, converges. Trip counts OPEN.
T18 NEVER_RUNNABLE rule: NO transition, incoming passes through, jump edge not exported.
T19 SN focus-player write: same value → sig+provenance update; changed → REMOTE FOCUS_PLAYER_CHANGED-reset; dynamic → sig None + reset; LOCAL untouched. Dynamic value + non-SN focus OPEN.
T20 group ops: gen+1 / emptied / dest-list reload (+scoped STALE) / flag set; groups survive resets. Runtime membership/flag values OPEN.

## 3. Canonical structs (no engine simulator)

`SearchSession{list_kind LOCAL|REMOTE; current_generation|None; next_generation (from 1); initialized; capacity 240|440→40 [E]; total_cardinality|None; last_search_cardinality|None; content_fingerprint|None (sha256 chain); generation_variants; path_ambiguous; filter_generation; filter_fingerprint; filter_predicates; filter_path_ambiguous; consumed_filter_snapshot|None; cursor_offset|None (None=runtime-advanced); cursor_generation; cursor_known; query_signature|None; focus_player_signature|None (REMOTE, default "0"); last_reset_reason; cursor_disposition; produced_by; focus_player_provenance}`.
Counters: `next_generation` only on new-gen/clear; `cursor_generation` only on index reset; `filter_generation` only on filter mutation/non-idempotent filter reset.
`TargetSession{kind OBJECT|None (point separate); generation; object_ref(list_kind,list_generation,list_index,native_id); source_list_generation|None; source_filter_generation|None; validity VALID|STALE|UNKNOWN; proof CURRENT_PASS|PRESERVED|NATIVE_ID|SYNTACTIC_RETENTION|UNKNOWN; pass_id; index_stable; liveness RUNTIME_DEPENDENT|WITNESSED_ALIVE|WITNESSED_GONE; provenance; point_ref|None}`.

`validity/proof` describe compiler knowledge about whether the target reference is safely usable and why; `liveness` describes the engine-world object and remains `RUNTIME_DEPENDENT` unless a direct world-state witness is represented. `STALE` therefore never means `WITNESSED_GONE`.
Handoff: copy (kind, gen-or-None-if-ambiguous, index-or-None-if-symbolic, filter gen); proof from pass-equality + ambiguity only. Invalidation: scoped clear→STALE; FULL→absent; filter-gen change (list-derived)→UNKNOWN; SORT/DEDUPE/REMOVE/ADD/`up-set-group`→T11–T13/T20; pass→UNKNOWN (STALE preserved); join divergence→UNKNOWN; failed establishment→keep prior + warn, never invent.

## 4. Static boundary
REPRESENTED: gens/fingerprints/cardinality-ranges; filter snapshots; cursor epoch/query/focus/disposition + ambiguity; object/point/direct-ID targets + proof/pass; groups; Goal spans w1/w2/w4 + overwrite/pass/ambiguity; availability/target-Fact observations; consumer modes; recurrent/branch/loop metadata. VALIDATED (fail-closed): arities; source/option/typeOp/GroupId/index/capacity/Goal/span-fit; Fact-vs-Action admissibility; uninit/proven-empty/capacity guards; reset shapes. EMITTED SAFELY: search-state w4 + group-size w1 via GoalSpan/GoalSlot allocator+emitter (re-verify point w2, cost-delta w4, target-data w1 wiring on `cd923b5a`). MUST REMAIN OPEN: numeric cursor; runtime counts beyond proven-empty/full; existence/ordering/visibility; target liveness after any mutation/reset/filter/pass/failure; failed-Action effect; duplicates; dynamic focus; ObjectData values; cost/point numerics; ms/lag; path taken; trip counts.
