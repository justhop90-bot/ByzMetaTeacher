# Forensic research program — ByzMetaTeacher `.per` compiler
Date: 2026-09-28. Read-only; no repo modifications, no commits.

## Repository state (verified 2026-09-28)
- Remote: https://github.com/justhop90-bot/ByzMetaTeacher
- `main` HEAD = `7917269792ff809616f0132fb70a45f2eece2f7b` ("Fix DUC report-surface aggregation").
  Matches the historical SHA in the brief — main has NOT moved.
- PR #86 `feat(compiler): close construction lifecycle observation semantics`: DRAFT,
  58 commits, base `compiler-native-persistent-control-plane`,
  head branch `compiler-construction-lifecycle-final-verify` =
  `731f1935426c47a6dad6ec1f0b22286c70c699f8` (fixture-repair commit).
  Previous construction head `88006ce6637c89f5315b9f243d124028e35f1d9d`
  ("Update construction lifecycle CI evidence index") is the direct parent of `731f193`.
  So: implementation work is IN PR #86, unmerged; `main` does NOT contain it.
- Open PRs: 2 total (per PR page nav). gh CLI unavailable (no auth); PR #86 verified via web.
- Local clone for reading: `C:\Users\justh\AppData\Local\Temp\opencode\ByzMetaTeacher`
  checked out at `7917269` (verified `rev-parse HEAD`).

## Local installation (primary archaeological source)
- Install root (this machine): `C:\Program Files (x86)\Steam\steamapps\common\AoE2DE`
  (the brief's `...\\Age of Empires II DE\\...` path does NOT exist here).
- Executable: `AoE2DE_s.exe` FileVersion/ProductVersion `101.103.54800.0`. steam app `813780`.
- AI root: `resources\_common\ai\` — 8 package dirs + ~17 root `.ai`/`.per` loader pairs.
- `.xs` support: `resources\_common\xs\` (Constants.xs, Effects.xs, x256tech.xs, x9tech.xs)
  plus `ai\*.xs` telemetry shims (BasiliskTelemetry.xs, Belisarius_*).
- Pinned native schema: `docs/reference/inventories/airef-command-schema.json`,
  385 commands, source blob `e2fc2c9b6a6b23f63d0743524dc94252eacfc2af`
  (AIRef commands.js, fetched 2026-04-28), inventory from `joerollman/aoe2-ai-parser`.

## Corpus census (measured, not estimated)
| source | .per | defrules | notes |
|---|---|---|---|
| Promisory/ | 38 | 8107 | richest local idiom source |
| Naga/ | 26 | 7409 | second richest |
| Bright Spark 41/ | 40 | 5440 | |
| Odette_AI 2025/ | 33 | 4207 | |
| Illuminati/ | 15 | 2451 | |
| Belisarius/ | 28 | 530 | Basilisk-family, .xs telemetry |
| AiBuilder/ | 9 | 355 | FE AI Builder remake |
| ByzMetaTeacher-main/ | 1 | 0 | vendored loader `(load "Basilisk\Basilisk")` only |
| ai/ root loaders | ~17 pairs | — | Basilisk, Immortal v0d10f, Rehoboam 1.80j, Shadow DC7, ... |
| campaign/ | 124 (.per+.ai) | — | scenario AI |
| TOTAL ai/ | 206 .per, 21.8 MB | ~28k+ | |

Cross-file pattern hits (all 206 .per): defconst 68542; set-goal 23225;
up-set-target 11898; up-find 11595; escrow 10859; set-strategic-number 10202;
up-jump-rule 6449; disable-self 3351; can-build 2977; can-research 2942;
timer-triggered 2278; up-pending-objects 1987; enable-timer 1782; can-train 1463;
town-size 1455; attack-now 47.

## Compiler architecture verdict (from implementation read)
Two pipelines: Demand-DSL path (`compiler.py:_compile_ir_parts:183-262`, tiny
`demand{require/action/witness/release/invalidate}` grammar) and artifact path
(`compile_package_with_report`, SourceGraph → persistent/SN/recurrent/DUC analyzers).
Goals + construction lifecycle ACTIVE→ISSUED→PENDING→COMPLETE→RELEASED: implemented
end-to-end. SN/timers: analysis+binding infra implemented, DSL lowering open
(no Request construction from DSL; default inventory None raises).
DUC: 124-test analyzer implemented, zero registry adapters → UNSUPPORTED at binder.
Controllers (9) + interactions (15): all EVIDENCE_ONLY. Escrow: feasibility facts +
build singleton only; native escrow ops unlowered. Source graph: implemented except
`load-random` (SOURCE-GRAPH-007). Game data: Byzantine-only factual subset
(CIV_ID=7, patch 185872/2026-09-22). Tests: 56 files, 830 methods, mostly synthetic
EffectiveRule fixtures — analyzer coverage, not DSL emission coverage.

## Artifacts in this directory
A native_command_semantics.csv · B community_per_idiom_catalog.csv ·
C native_state_contracts.json · D community_corpus_manifest.json ·
E compiler_gap_matrix.md · F prompt_readiness_matrix.md · G counterexample_register.md ·
compiler_coverage_baseline.md · community_knowledge_coverage.md · native_unknowns.md ·
compiler_false_assumptions.md · compiler_undercoverage.md · implementation_map.md ·
player_knowledge_matrix.md

Evidence classes used: ENGINE FACT / COMMUNITY PRACTICE / STRATEGY CHOICE /
WORKAROUND / HISTORICAL ARTIFACT / COMPILER POLICY / OPEN-UNKNOWN.
