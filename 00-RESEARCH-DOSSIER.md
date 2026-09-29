# MUSE static research dossier — AoE2 `.per` compiler (implementation-ready, no runtime)

`CURRENT MAIN SHA=cd923b5a6eb20b8ee61c84eb41bfc0de4800d492` ("fix: add Carrack to Hulk line").
`RESEARCH BASE=cd923b5a` (detached checkout verified at `Temp/opencode/ByzMetaTeacher@cd923b5a`).
Upstream repo: `justhop90-bot/ByzMetaTeacher`. Workspace `AoE2DE/` is the game install, not the repo.
No files in the repo were modified. Static evidence only (repository evidence, AIRef, community `.per`
sources, checked-in engine data, static analysis, deterministic compiler tests, emitted artifacts,
native-parser acceptance). No DE execution was performed; runtime belongs to the user.
Static verification at base: `test_duc_semantics + test_game_data = 172 passed`
(`PYTHONPATH=<root>;<root>/LearnerAI`, pytest from `LearnerAI/`).

## Reading rule (applies to every file in this folder)

- `[E] = engine guarantee` (pinned AIRef / UserPatch / native contract in `primitives/native_hygiene.py` citation catalog).
- `[C] = community idiom` (lewisc64/aoe2ai, Naga/Attila, Duke/AIScript corpora — never a compiler rule).
- `[I] = safe compiler inference` (fail-closed, provenance-carrying, explicitly marked as such).
- Statuses used exactly as ordered: `EXECUTABLE_SAFE / ENGINE_SEMANTICS_MAPPED / SEMANTICALLY_ADAPTED /
  NATIVE_TYPED / NATIVE_KNOWN / EVIDENCE_ONLY / OPEN / UNKNOWN`.
- Anything needing DE execution is `OPEN/UNKNOWN`, never guessed. Community repetition is not engine semantics.
- Every claim cites `file:line@cd923b5a`. Historical MUSE docs are evidence, not authority.

## Per-finding structure (used in files 01–08)

Each construct is documented as:
`NATIVE CONSTRUCT / AUTHORITATIVE SOURCE / SOURCE REVISION-HASH / EXACT SIGNATURE / INPUTS /
OUTPUTS-MUTATIONS / STATE OWNERSHIP / LIFETIME / ORDERING / PERSISTENCE / CARDINALITY-RANGE /
VERSION-PATCH SCOPE / KNOWN INTERACTIONS / COMMUNITY CORROBORATION / WHAT IS PROVEN / WHAT IS UNKNOWN /
COMPILER STATUS / EXACT IMPLEMENTATION TARGET / EXACT TEST TARGET`,
plus transition rows (`STATE A / COMMAND / STATE B / PERSISTENCE / INVALIDATION / DEPENDENT STATE /
UNKNOWN EFFECTS`) and per open problem (`WHAT CAN BE REPRESENTED / VALIDATED / EMITTED SAFELY /
MUST REMAIN OPEN`).

## File map

- `01-DUC-STATE-MODEL.md` — FIRST: SearchSession / TargetSession / list+filter generations / mutations /
  resets / target establishment+provenance+invalidation / Goal output spans / group state+size (transition-oriented).
- `02-DUC-DIAGNOSTICS.md` — SECOND: full `DUC-*` catalogue (stable ID, trigger, severity, proof basis,
  related state/writer/consumer, hard-vs-advisory).
- `03-DUC-PERF-CARDINALITY.md` — THIRD: capacity/performance inventory (advisory only).
- `04-PRODUCTION-RESEARCH-ESCROW.md` — FOURTH: production / research / escrow static semantics with the
  observation/admission/action/pending/completion separation.
- `05-SN-TIMER.md` — FIFTH: Strategic Number + Timer versioned inventory and allocation mechanics.
- `06-GAMEDATA.md` — SIXTH: GameData factual reconciliation (remaining unmodeled Byzantine nodes, IR gaps,
  fixed-cost traps).
- `07-CONTROLLER-ATTACK.md` — SEVENTH: controller + attack static contracts (issue vs admission vs group
  state vs targeting vs completion vs release vs reassessment).
- `08-SOURCE-GRAPH.md` — EIGHTH: `#load` / `#load-if-*` / `load-random` / `.xs` source-graph + provenance semantics.
- `09-RECONCILIATION.md` — TENTH: `NEWLY CLOSED / STILL OPEN / OBSOLETE / REGRESSED / STALE DOCUMENTATION`
  against current `main`.

## Target workflow (unchanged)

`MUSE evidence -> semantic contract -> IR -> validator -> binding -> emitter -> deterministic fixture ->
native parser acceptance -> regression`.
The compiler is complete when every supported construct has that chain while genuine runtime questions
remain explicitly `OPEN`.

## Implementation order (dependency chain)

1. Documentation reconciliation (09) 2. Construction closure 3. DUC SearchSession (01)
4. DUC TargetSession (01) 5. DUC GoalSpan (01) 6. DUC diagnostics + source provenance (02, 08)
7. Production async (04) 8. Capability-loss/recovery (04) 9. Native controller expansion (07)
10. SN/Timer semantics (05) 11. GameData/version profiles (06) 12. Whole-player StrategyRuntime
13. Runtime evidence closures (user-owned DE runs) 14. Final compiler-wide verification.
