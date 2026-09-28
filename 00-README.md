# Forensic research program — ByzMetaTeacher `.per` compiler
Date: 2026-09-28. Authoritative project-state snapshot; updated after PR #94 merge.

## Repository state (verified 2026-09-28)
- Remote: https://github.com/justhop90-bot/ByzMetaTeacher
- `main` contains the verified code merge `dca0458986d0e50e2ae26889d89f863a3c2ff923` plus the current-state documentation updates recorded after that merge.
- The immediately preceding code merge is PR #94, merge commit `dca0458986d0e50e2ae26889d89f863a3c2ff923`.
- PR #94 adds typed escrow release-plan validation and forwards `escrow_plan` through all six public compiler surfaces into the single emitter path.
- PR #83 and PR #86 were audited and closed as superseded; their stale divergent revisions were not merged.
- Open PRs: none.
- Current main verification run passed 915 compiler tests, generic/native zero-findings acceptance, all native-support determinism jobs, cross-platform snapshot comparison, and the aggregate Compiler verification gate.

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

## Compiler architecture verdict (verified against current main)
The compiler's current execution substrate includes persistent control, construction lifecycle,
Strategic Number allocation/catalog, DUC narrow executable promotion, and attack issue connectivity.
Escrow is currently at the typed-plan/compiler-threading seam: `NativeEscrowReleasePlan` is
validated and forwarded through every public compiler path, but dedicated `release-escrow`
binding/mapping/emission remains open. Timers still lack the final symbolic allocation/emission
slice. Source graph remains executable-safe except for `load-random`; Byzantine data remains
a verified subset rather than the complete 145-node manifest. Current verification covers 915
compiler tests and requires source-to-.per coverage plus the pinned native zero-findings gate.

## Artifacts in this directory
A native_command_semantics.csv · B community_per_idiom_catalog.csv ·
C native_state_contracts.json · D community_corpus_manifest.json ·
E compiler_gap_matrix.md · F prompt_readiness_matrix.md · G counterexample_register.md ·
compiler_coverage_baseline.md · community_knowledge_coverage.md · native_unknowns.md ·
compiler_false_assumptions.md · compiler_undercoverage.md · implementation_map.md ·
player_knowledge_matrix.md

Evidence classes used: ENGINE FACT / COMMUNITY PRACTICE / STRATEGY CHOICE /
WORKAROUND / HISTORICAL ARTIFACT / COMPILER POLICY / OPEN-UNKNOWN.
