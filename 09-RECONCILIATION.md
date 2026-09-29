# 09 — Repo reconciliation @ `cd923b5a` (research base vs checklists)

Doc-reconciliation pattern reused from `CONSTRUCTION_LIFECYCLE_CROSSCHECK_2026-09-28.md:1-3,70-94`:
`[x]` verified / `[~]` partial+failure-mode / `[ ]` unfinished-blocked + acceptance-gate + evidence-navigation.
Historical MUSE/docs = evidence, not authority. `STILL OPEN` ≠ failure: several rows are open by design
(runtime belongs to the user).

| Doc row | Status | Evidence |
|---|---|---|
| EFFECTIVE checklist §A–E (file/instance/event/edge/slice identity, resolution, depth 10 / conditional 50, duplicate-vs-cycle, inactive-branch correction, fixture matrix) | NEWLY CLOSED (doc already `[x]`, code+tests present at head) | `ir/source_graph:55-97,398-431,495-532,600-785`; `source_graph:131-132,242-324,393-414,874-882`; `test_source_graph:1-60,217-330`; checklist `:30-110` |
| EFFECTIVE load-random "fail closed unless explicit deterministic policy" §B + REJECT invent-RNG §19 | NEWLY CLOSED (policy implemented); runtime choice remains open | `ir/source_graph:273-328`; `source_graph:52-58,415-454`; `validation:95,119-126,1107-1126`; materialization plan `:5-11` |
| EFFECTIVE §F downstream (child-source DUC producer identity; cross-pass target-reuse proofs; diagnostic taxonomy) | STILL OPEN (`[ ]` at `:116-118`) | Same lines; DUC checklist `:105,141` (`[ ]` load-file DUC provenance) |
| DUC checklist A–C,G–I (typed state, contracts, recurrence, hostile target-by-id) | NEWLY CLOSED (marked `[x]`) | `DUC…:30-83,148-160` + `ir/duc.py` + `semantic/duc.py` presence |
| DUC checklist D (STALE vs UNKNOWN, clean/remove/index, target-lifetime-after-death `:91-93`); F (diagnostics integration `:118-123`); G (14 hostile cases `:130-143`) | STILL OPEN (`[ ]`) | Exact lines; do not infer from partial DUC strength |
| CONSTRUCTION crosscheck (`[~]` phase model disconnected, `[~]` precedence partial, `[ ]` canonical witness / ObjectId typing / transition wiring / same-pass retry / order regression) | STILL OPEN (pattern exemplar) | `CONSTRUCTION…:22-49,71-94,122-227`; cited run #1888 FAILED before construction gates `:210-211` — no closure evidence at `cd923b5a` |
| MUSE_ESCROW same-pass visibility, starvation/handoff, native same-pass/competing-owner fixtures | STILL OPEN by design | `MUSE_ESCROW…:31,49-50,62-63`; historical SHAs + run #2213 `:3-5` are evidence vs old head, not authority for `cd923b5a` |
| NATIVE_CONTROLLER "deliberately not claimed" 7 rows (512-SN, simulation, auto-strategy, attack completion, SearchSession/TargetSession, cost propagation, auto-promotion) | STILL OPEN by design | `NATIVE_CONTROLLER…:67-75`; interactions stay EVIDENCE_ONLY `:63-65` |
| NATIVE_PER_GAP_MAP "Load graph: load-random remains intentionally deterministic-policy blocked" (:70) | STALE DOCUMENTATION (over-broad after selection policy landed) | Replace with: "blocked without explicit `LoadRandomSelection`; materialized+RANDOM-edge with selection; runtime RNG still open" (§B3 evidence) |
| Unit-manifest plan "Remaining: Fish Trap 199; Carrack 2628 blocked by 904; 527/528 blocked by 905/244; 54/408/909 identity conflicts" (`:11-14`) | CLOSED/OBSOLETE | 199/2628/54/909 materialized (`manifest_buildings:40-54`, `manifest_unit_supplements:32-43`, `manifest_technology_conflicts:38-57`; `test_game_data:350-479`); triggers 904/905/244 unmodeled (manifest `:109,111-112`); 408 per file 06 |
| Technology-manifest plan "54,408,909 unmodeled; 16 unit/building nodes remain" (`:12-14`) | OBSOLETE (partial) for 54/909 | Same conflict-seed evidence; 408 + 527/528 remain |
| Game-data civ-profile plan "Full 145-node ingestion / universal baseline / patch overlays / unavailable sets / field provenance" (`:18,79-86`) | NEWLY CLOSED (partial): 145-equivalent now 156 modeled; STILL OPEN: universal baseline, replayable overlays, full costs/effects | `civ_profile:1489-1512` (FACTUAL_SUBSET, civ-scoped) + `test_game_data:403-415,542-558` vs plan `:79-86` |
| DAT snapshot plans "No live DAT values committed" + "do not claim completion of remaining 73 nodes" | STILL OPEN / guardrail holds | Boundary `game_data_dat_snapshot:194-319`; 201-record snapshot test `:630-691`; no 527/528/408 synthesis at head |
| EFFECTIVE acceptance gate ("validate_effective_source_graph() passes … full tests green … native zero … determinism green", `:133-142`) | STALE DOCUMENTATION (pre-selection-policy; head not re-gated here) | Research-only; cites old gate without `LoadRandomSelection` success-path or `cd923b5a` run ID. Needs re-verification, not assumed green. |
| REGRESSED | none proven | Validators remain fail-closed (VAL-080, 001/002/003/005/006/007/009/017) |

Completion gate (final verification, for the engineer): full regression + focused persistent-state suites +
construction + DUC + production lifecycle + research/escrow + strategy runtime + GameData coverage + native
zero-findings per executable fixture + determinism + reproducibility + support-catalog determinism + aggregate gate +
doc/gap-matrix consistency. Reject release when: claimed executable semantic has no evidence; declared-closed gap
still open elsewhere; native fixture stale vs compiler fixture; divergent historical branch mistaken for unmerged work;
runtime OPEN silently promoted to fact.
