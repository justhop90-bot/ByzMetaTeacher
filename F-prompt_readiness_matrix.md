# Prompt readiness matrix 1/19–19/19
Legend: R=research coverage H/M/L; E=evidence; IMPL-readiness READY/NEAR/BLOCKED.
Key: main=7917269; PR86 head=731f193 (unmerged); corpus=local 206per/28k-defrules + AIRef-385.

## 1/19 Baseline integrity + construction lifecycle — R:H E:H IMPL:NEAR
Coverage: PR86 58 commits mapped (parent 88006ce impl, head 731f193 fixture repair);
base compiler-native-persistent-control-plane; construction validators + emitter paths read.
Evidence: PR commit list (web); compiler.py validators; emitter/per.py 191-246;
local can-build 2977 + Duke buildings 88KB + Promisory buildings.per.
Blocking: merge PR86; same-pass goal-visibility proof; foundation/placement runtime evidence.
Contradictions: G-05 (lifecycle dropped from source_order). Fixtures: existing construction
fixtures + candidate fixture-build-with-sn-geometry. Files:
LearnerAI/Compiler/semantic/{action_issuance,completion_witness,release_state,resource_conflicts}.py,
ir/model.py, emitter/per.py, primitives/native_engine_effects.py.

## 2/19 Native semantic coverage matrix — R:H E:H IMPL:READY
Coverage: AIRef-385 schema inventoried; Artifact A (64 commands) maps support states.
Evidence: airef-command-schema.json (blob e2fc2c9b); registry vs binder duplicate gates found.
Blocking: per-SN catalog; DUC adapter authoring. Contradictions: G-12 (fixture-only inflation).
Files: primitives/{native_schema,registry,native_binder,engine_semantics,native_hygiene}.py.

## 3/19 Goal/SN/Timer control plane — R:H E:H IMPL:NEAR
Coverage: storage model + allocator paths read; 0..511/50-slot structure known.
Evidence: runtime_binding.py (GoalSlot/Span, SN/Timer requests+inventories);
ir/recurrent.py timer machine; Corpus: goals 23k, SN 10k, timers ~4k hits.
Blocking: full SN catalog (defaults/version/auto-mutation); DSL allocation path for SN/timers.
Files: runtime_binding.py, semantic/{strategic_number_semantics,persistent_state,pass_scheduler}.py,
ir/{strategic_number,recurrent}.py.

## 4/19 Recurrent execution closure — R:H E:M IMPL:NEAR
Coverage: firing model, jumps, disable-self, starvation/preemption paths read.
Evidence: pass_scheduler.py 116-351; recurrent_execution.py; rule_execution.py
(fires_guaranteed always False); local disable-self 3351 + jumps 6449.
Blocking: hostile fixtures (jump-into-disabled; writer starvation; state convergence proofs).
Files: semantic/{recurrent_execution,pass_scheduler,rule_execution}.py.

## 5/19 General async work (build vs train vs research) — R:H E:M IMPL:NEAR
Coverage: three lifecycles separated; PR86 warns against generalizing foundation/placement/retry.
Evidence: registry ACTION entries; completion-witness catalogs; IDIOM-006 current+queued.
Blocking: queue-state/provider-state/capacity/birth models; totals-as-witness proof (G-04).
Files: primitives/registry.py, semantic/{community_engine,capability_validation}.py, ir/model.py.

## 6/19 Resource/escrow/arbitration — R:H E:M IMPL:BLOCKED on lowering
Coverage: feasibility facts + build singleton mapped; 10.9k-hit demand proven.
Evidence: registry 318/324/330; resource_conflicts.py 1-owner claims; Duke commodity +
Promisory escrow.per; interactions 537-588 EVIDENCE_ONLY.
Blocking: native escrow op lowering; gating formula; starvation/emergency semantics.
Files: semantic/resource_conflicts.py, ir/resource.py, semantic/native_controller*.py.

## 7/19 DUC SearchSession — R:H E:H(structure)/M(semantics) IMPL:BLOCKED on binder
Coverage: lists/cursor/generation/filter/reset/capacity modeled in analyzer.
Evidence: duc.py 486-848/1028-1262; hygiene 741-1050; 124 tests (fixture-only);
local up-find 11.6k. Blocking: zero registry adapters; emission path.
Files: semantic/duc.py, ir/duc.py, primitives/native_hygiene.py.

## 8/19 DUC TargetSession/groups/outputs/costs — R:H E:M IMPL:BLOCKED (same)
Coverage: targets/IDs/groups/spans/mutation in IR + analyzer; liveness rules fail-closed.
Evidence: duc.py 218-378/872-993/1265-1351; oracle schema + candidates.
Blocking: adapters + emission; retained-filter proof; perf measurement (advisory only).
Files: same as 7/19 + docs/reference/oracles/.

## 9/19 Native controller semantics — R:M E:M IMPL:BLOCKED
Coverage: 9-controller catalog + 15 interactions read; all EVIDENCE_ONLY by construction.
Evidence: native_controller.py 313-680; interactions 482-744; corpus SN clusters + TSA + parity.
Blocking: causal/prerequisite/feedback separation; attack lifecycle (G-01); auto-mutation catalog.
Files: semantic/native_controller.py, semantic/native_controller_interactions.py.

## 10/19 Effective source/package graph — R:H E:H IMPL:READY (minus load-random)
Coverage: resolver + validation + fingerprints read; Duke map loads + vendored single-load observed.
Evidence: source_graph.py (depths 10/50); validation module ~1715 lines; 67 tests.
Blocking: load-random materialization; .xs boundary semantics (IDIOM-029).
Files: ir/source_graph.py, semantic/source_graph_validation.py, LearnerAI/Compiler/source_graph.py.

## 11/19 Community idiom knowledge base — R:H E:H IMPL:READY (catalog v1 done)
Coverage: 32-idiom catalog (Artifact B) across all 10 domains with sources.
Evidence: local 28k-defrule census; 6 public repos surveyed; lineage discounts applied.
Blocking: file-level line cites for Promisory/Naga idioms (next pass).
Files: Artifact B; sources in Artifact D.

## 12/19 Practical expressiveness gap — R:H E:H IMPL:NEAR
Coverage: 10-question matrix answered per idiom family (B columns compiler_supported/gap).
Evidence: DSL grammar (5 keywords) vs corpus idioms; lewisc64 lowering precedent.
Blocking: SN/DUC/escrow emission decisions; TSA-arithmetic codegen policy.
Files: compiler.py, parser.py, ast.py, emitter/per.py, ir/*.

## 13/19 Community corpus ingestion — R:H E:M IMPL:NEAR
Coverage: manifest v1 (Artifact D): 9 local + 9 public entries with counts/hashes.
Evidence: measured counts; web survey; lineage notes (Duke→niektb; TSA single-lineage; 392 shared).
Blocking: per-file sha256 + fingerprints; Naga/BrightSpark/Odette lineage.
Files: Artifact D.

## 14/19 Factual game substrate — R:M E:M IMPL:NEAR
Coverage: Byzantine subset mapped (CIV_ID=7, patch 185872); 145-node manifest incomplete.
Evidence: ir/game_data.py + civ_profile.py 252-609; gamedata tests 36.
Blocking: full 145-node manifest; broader civs; patch overlays; native ID provenance.
Files: ir/{game_data,civ_profile}.py.

## 15/19 Strategic knowledge compiler — R:M E:M IMPL:NEAR
Coverage: demand/posture/targets/cost/invalidation model read; policy-vs-semantics split identified.
Evidence: ir/strategy.py 91-231/429-642/696-1097; strategy_runtime.py observation gates.
Blocking: observation primitive coverage (no DUC/attack/escrow); policy separation audit.
Files: ir/{strategy,strategy_runtime,civ_profile}.py, clients/basilisk/.

## 16/19 Whole-player economy/production — R:H E:M IMPL:NEAR
Coverage: opening/transition/farm/dropsite/boom/sustain idioms IDIOM-001..008/024.
Evidence: Promisory + Duke economy files; AiBuilder build-orders; TMB spreadsheet precedent.
Blocking: recovery-pattern file cites (IDIOM-026); provider-loss corpus proof.
Files: Artifact B economy rows; ir/strategy.py land-castle strategy.

## 17/19 Whole-player military/scouting/DUC/adaptation — R:H E:M IMPL:BLOCKED on DUC/attack
Coverage: composition/counters/staging/retreat/TSA/DUC-pipeline idioms cataloged.
Evidence: Duke attack/rush/parity/counter_units/unit_combos; lewisc64 DUC docs; TSA.
Blocking: DUC emission + attack lifecycle (same blockers as 7/8/9).
Files: Artifact B military rows.

## 18/19 Golden corpus + hostile verification — R:H E:M IMPL:NEAR
Coverage: 56 test files/830 methods inventoried; fixture-only vs emission coverage separated.
Evidence: tests/ listing; helpers (reproducibility/determinism/zero asserts); native_backend fixtures.
Blocking: hostile fixtures (G-05 jump/disabled; G-04 totals; DUC widening; load-random).
Files: tests/ (all), tests/fixtures/.

## 19/19 Final closure audit — R:M E:M IMPL:BLOCKED on criteria
Coverage: provisional 56%/42% SUPERSEDED (G-12); artifact-based denominators proposed below.
Evidence: this program's artifacts. Blocking: agreed numeric thresholds per family;
runtime-evidence harness (FLWL gRPC oracle candidate).
Files: compiler_coverage_baseline.md; player_knowledge_matrix.md.
