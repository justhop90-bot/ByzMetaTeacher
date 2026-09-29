# 08 — Source graph / provenance semantics @ `cd923b5a`

Substrate `ir/source_graph.py:1-10` (events=truth, edges=topology, instances=context, slices=effective projection).
Resolver `source_graph.py:130-184`. Validation `semantic/source_graph_validation.py:119-126`
(policy-gated, canonical ordering, exact-dedup).

## B1 — `#load` (`(load "t")` + `#load "t"`)
- EFFECTIVE SOURCE: spliced slices in lexical depth-first inline order, NOT topological sort (checklist `:14`);
  `_expand_instance` appends slice→recurse→slice (`source_graph:350-520`); slices
  `EffectiveSourceSlice{ordinal,instance,physical_range,text}` (`ir/source_graph:495-532`); consumed by
  `compiler._parse_source_slices` with path+line_offset+column_offset preservation (`compiler:364-375`).
- DIRECTIVE IDENTITY: `SourceAssemblyEventKind.LOAD` (`ir:37-42`); `LoadEventPayload{syntax:PAREN_LOAD|RAW_LOAD,target_text}`
  (`:261-270`); `structural_event_id(source_instance,span,kind,condition_before/after,payload)` (`:736-760`);
  `lexical_ordinal` (`:369-379`); raw strictly `#load "t"` (`_RAW_LOAD_RE :77-79`, malformed→SOURCE-GRAPH-009 `:874-882`);
  paren `(load "t")` (`_parse_load_form :976-991`); strings/comments excluded (`:899-921`, `test_source_graph:270-290`).
- EDGE TYPE / TARGET: `LoadKind.FILE` (paren) vs `RAW_LOAD` (`#load`) (`ir:21-34`; enforced resolver `:363-371` +
  validator `:860-876,1175-1196`); `SourceEdge{source,target:SourceFileId|None,child:SourceInstanceId|None,kind,span,condition,active,event,target_text}` (`:434-492`).
- LINE-COLUMN: `SourceRange{source,start/end_offset,start/end_line,start/end_column}` (`ir:143-181`); `_segment_range`
  (`:541-565`); inconsistency → VAL-095/096 (`validation:452-508`).
- INSTANCE IDENTITY: `structural_instance_id(source,parent,via_edge)` (`ir:715-733`); `SourceInstance{physical,parent,via_edge,ancestry,depth,occurrence,events}` (`:398-431`); physical `SourceFileId{canonical_path,content_sha256}` (`:55-64`, `Path.resolve()+sha256 :89-97`); duplicates = distinct instances, cycles only on active stack (`:260-290,292-324`); `occurrence` counts prior same-source instances.
- FINGERPRINT: dual `assembly_fingerprint` (files+instances+events+edges+slices+symbols) vs `effective_fingerprint`
  (root+slice sha256s) (`ir:600-712`); recompute-checked VAL-070/071; determinism tests (`test_source_graph:328ff` + forging tests).
- CYCLE-DEPTH: active-stack cycle SOURCE-GRAPH-002 (`:302-316`); `MAX_LOAD_DEPTH=10` (`:131`), `parent.depth+1>10` → 003 (`:317-324`); depth-10 valid / 11 reject fixtures (checklist §E `:96-97`).
- DETERMINISTIC MATERIALIZATION (unconditional): containing-dir then search-roots (`_resolve_path :242-258`);
  missing reachable → 001 (`:220-227,471-478`); inactive `#load-if` targets registered as `SourceFile` but NOT expanded (`:393-414`, correction §C `:53-57`).
- BOUNDARY: REPRESENT active+inactive loads with condition contexts; VALIDATE reachability/cycle/depth/identity/order/fingerprints; EMIT via slices→`analyze_effective_rules` (`compiler:605-616,738-749,867-876`); OPEN: engine runtime load timing, package occupancy, scheduler inference (non-goals `:122-129`).

## B2 — `#load-if-defined` / `#load-if-not-defined` / `#else` / `#end-if`
- EFFECTIVE SOURCE: `_mask_inactive_lines` blanks inactive lines preserving offsets (`:1070-1115`); only active loads expand; conditional lines masked to spaces.
- DIRECTIVE IDENTITY: `CONDITIONAL_OPEN/ELSE/END` events + `ConditionalOpenPayload{predicate}` / `ElsePayload{open_event}` / `EndPayload{open,else}` (`ir:330-357`); `ConditionPredicate{symbol,expected:DEFINED|UNDEFINED}` (`:184-194`); `ConditionContext{predicates}` append/pop/complement (`:197-235`); before/after validated (`validation:641-686`); pairing nearest-open (`:772-826`, VAL-104).
- EDGE TYPE: conditional directives create NO edges — `EVENT_EDGE_MISMATCH` if referenced (`:688-701`); `CONDITIONAL_EDGE_FORBIDDEN` VAL-106; `LoadKind.CONDITIONAL_*` legacy compat only ("new authoritative edges never use them", `ir:21-34`).
- LINE-COLUMN: same `SourceRange`; malformed/orphan/duplicate/unterminated → 012/013/014/015/016 (`:645-761`).
- INSTANCE/FINGERPRINT: condition contexts in event/edge fingerprint payloads (`ConditionContext.fingerprint_payload :234-235`, event `:381-395`, edge `:480-492`); symbols in `LoadSymbolEnvironment` fingerprint (`:257-258`).
- CYCLE-DEPTH: `MAX_CONDITIONAL_DEPTH=50` (`:132`); `>50` → 005 (`:602-610`); unresolved symbol → 006 (`:611-621`); validator VAL-040/041/042/102/103.
- MATERIALIZATION: `event.condition_before.evaluate(symbols)` gates expansion (`:358,415`); symbols fully supplied — no inference.
- BOUNDARY: REPRESENT all branches structurally, expand active only; VALIDATE pairing/depth/symbol/exhaustiveness; EMIT active slices only; OPEN: engine conditional timing, undefined-symbol defaults.

## B3 — `load-random` (`load-random …` / `(load-random …)`)
- EFFECTIVE SOURCE: single selected target spliced at directive position; alternatives never simultaneously linear.
- DIRECTIVE IDENTITY: `LOAD_RANDOM` event + `LoadRandomEventPayload{syntax,entries:LoadRandomEntry{target_text,weight?}}` (`ir:294-328`); weights verbatim, `+weight` NOT normalized (checklist REJECT `:20`); entries parsed (`:1014-1067`); payload-preservation test (`test_source_graph_event_ir`).
- EDGE TYPE: `LoadKind.RANDOM` only (resolver `:376,457-505`; validator `:877-889,1197-1208`).
- LINE-COLUMN / INSTANCE / FINGERPRINT: same as B1; selection key `(canonical_posix_path,line,column)` (`LoadRandomSelection.key()`, `ir:291-292`).
- CYCLE-DEPTH: selected target under identical cycle/depth rules.
- DETERMINISTIC MATERIALIZATION (compiler boundary; runtime RNG stays OPEN): default fail-closed SOURCE-GRAPH-007 without explicit `LoadRandomSelection` (`:52-58,147-149,415-433`; `SourceGraphRequest{load_random_selections,allow_load_random} :51-58`); selection must name a declared entry else 007 (`:436-447`); only selected target loaded+expanded (`:448-454`); RANDOM edge records target/child provenance (`:457-505`); contract `docs/plans/2026-09-29-source-graph-load-random-materialization.md:5-11` ("no weighted RNG, engine RNG, probability, or runtime selection inferred"); validator `RANDOM_LOAD_UNMATERIALIZED` VAL-080 + `require_contiguous/fingerprint/reject_random_loads` policy (`validation:95,119-126,1107-1126`).
- BOUNDARY: REPRESENT entries+selection; VALIDATE materialization+payload agreement; EMIT selected slice only; OPEN: runtime random choice, weight semantics, distribution, engine seed.

## B4 — `.xs` boundary
- POLICY: hard reject — entrypoint `.xs` → 017 (`:153-165,186-204`); active `#load/(load)` of `.xs` → 017 (`:378-385`); message "XS source outside compiler boundary; .xs↔.per state bridge not modeled." Tests `test_source_graph:217-240`.
- BOUNDARY: REPRESENT nothing across; VALIDATE rejection with path+line+column; EMIT never includes XS; OPEN: XS compilation, include integrity, XS↔PER bridge (checklist REJECT §21 + non-goals). Inactive `.xs` loads are not expanded — not acceptance.

Downstream still-open (§F `[ ]`): DUC fixture proving child-source producer retains instance identity; cross-pass target-reuse proofs; diagnostic taxonomy — corroborated by DUC checklist `:105,141` (`[ ]` load-file DUC provenance), no new fixture at head.
