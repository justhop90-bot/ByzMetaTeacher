# 06 — GameData factual reconciliation @ `cd923b5a` (FACTUAL_SUBSET, civ-scoped)

Ground truth: `test_game_data.py:403-415,542-558` → modeled 156, unmodeled exactly 3, verified_unavailable 14,
total 173. `require_coverage` fails closed on 527 (`test_gamedata_audit:199-204`). Coverage is civilization-scoped
(`ir/civ_profile:1489-1512`; `ir/game_data:46-60,272-281`).
IR shape: `UnitDef{id,line,providers,base_cost,train_time,upgrades_from/to,validity,provenance,engine_classes,effects}`
(`ir/game_data:320-336`); `TechnologyDef{id,providers,base_cost,research_time,prereqs,unlocks,effects,upgrades,validity,provenance}`
(`:353-367`); `UpgradeRelation(previous,current,research)` (`:264-269`); `ResourceCost{food,wood,gold,stone:int>=0}`
(`:112-121`); enrich fills ONLY unresolved `base_cost/research_time_seconds` on exact TechId+name match, preserves
providers/prereqs/effects (`game_data_dat_snapshot:282-306`); patch must match exactly (`:267-271`); name mismatch
rejects (`:282-286` + `test_game_data:767-796`).

## A1 — UNIT 527 Demolition Ship — CONFLICTING IDENTITY (primary) + INSUFFICIENT AUTHORITATIVE DATA
- MANIFEST IDENTITY: `527 | Demolition Ship | TYPE=UnitUpgrade | USE=Unit | STATUS=ResearchedCompleted | AGE=3 | BUILDING=45 | LINK=1104 | TRIGGER=905` (`docs/reference/BYZANTINES_manifest.txt:111`).
- AUTHORITATIVE EVIDENCE: `UNIT NODE 527 … UNIT:YES|TECH:YES; UNIT:class=22; COSTS:type=1,45;type=3,80; TECH:name='[FTT] Disable Paladin' civ=8 effect=583` (`:555-557`). COSTS bytes identical to raft 1104 but TECH identity is recycled-scenario cruft — idiom/corrupt reuse, NOT engine guarantee.
- IR CAPABILITY: shape exists (`UnitDef` + `UpgradeRelation(1104->527 via 905)` + `ProductionProvider(BuildingId(45))`).
- FIXED-COST TRAP: must NOT copy raft cost `ResourceCost(wood=45,gold=80)` (`game_data_manifest_units:149-160`, raft only) into 527 despite identical DAT COSTS line. That is synthesis.
- SMALLEST GENERAL IR EXTENSION: none for shape. Needed is DATA: authoritative TRIGGER=905 materialization + identity-safe join (conflict-seed pattern `game_data_manifest_technology_conflicts:1-7,38-57`). Do NOT merge by numeric ID through `enrich_game_data_from_dat_snapshot`.
- FORBIDDEN: inventing `UpgradeRelation(1104,527,905)`, `train_time_seconds`, `base_cost`, civ availability.

## A2 — UNIT 528 Heavy Demolition Ship — CONFLICTING IDENTITY (primary) + INSUFFICIENT AUTHORITATIVE DATA
- MANIFEST IDENTITY: `528 | Heavy Demolition Ship | TYPE=UnitUpgrade | USE=Unit | STATUS=ResearchedCompleted | AGE=4 | BUILDING=45 | LINK=527 | TRIGGER=244` (`:112`).
- EVIDENCE: `UNIT NODE 528 … TECH:name='Slinger (make avail)' civ=-1 effect=582 required=(102,…)` (`:558-560`) — same recycled-ID conflict class.
- IR CAPABILITY: chain `527->528 via 244` representable once endpoints+trigger exist; bidirectional-link validator (`game_data:467-484,513-520`) then applies.
- TRAP: same as A1 — identical COSTS line is not a verified 528 cost. Chain-stop precedent already in code (`game_data_manifest_units:1-6`, chains stop before unrepresented trigger techs).
- FORBIDDEN: inventing 528 cost/train-time/`UpgradeRelation(527,528,244)`.

## A3 — TECHNOLOGY 408 Spies/Treason — VARIABLE-NON-SCALAR PROPERTY (primary) + INSUFFICIENT DATA + PATCH-SENSITIVE
- MANIFEST IDENTITY: `408 | Spies/Treason | TYPE=Research | USE=Tech | STATUS=ResearchedCompleted | AGE=4 | BUILDING=82 | LINK=315 | TRIGGER=<MISSING>` (`:140`).
- EVIDENCE: `UNIT NODE 408 … UNIT=NO|TECH=YES; TECH:name='Spy Technology' effect=420 required=(103,…)` (`:678`). No pinned snapshot cost/time joined (seed count 51 excludes 408: `test_game_data:505,524-530`; conflict seeds only 54,909).
- IR CAPABILITY: `TechnologyDef.base_cost:ResourceCost|None` + fixed-int `ResourceCost` only; no variable-cost slot. `CivBonusKind{COST,COST_OVERRIDE,FREE,…}` + `_cost_override/_apply_cost_modifiers` (`civ_profile:666-701`) assume fixed costs.
- FIXED-COST TRAP (explicit): Spies/Treason cost is NOT constant — engine scales it with game state (exact coefficients require engine/DAT authority; deliberately unstated here to avoid synthesis). Assigning ANY `ResourceCost(...)` or filling via `enrich_*` creates a false fact corrupting `cost_of()`/`cost_of_age_advance()` (`civ_profile:227-254`) and fingerprint (`:612-637`). `None` (unresolved) is the only honest state.
- SMALLEST GENERAL IR EXTENSION (no per-tech hack):
  `VariableCost{formula_id:str (e.g. "spies-treason-gold-per-villager"), parameters:tuple[tuple[str,int],...]=(), provenance:tuple[EvidenceRef,...]=()}`;
  change `TechnologyDef.base_cost:ResourceCost|None` → `cost:ResourceCost|VariableCost|None`;
  `CivProfile.cost_of()` raises fail-closed on `VariableCost` (+ later `cost_model` resolver);
  `Validity`+`PatchChange` already version the formula; forbid `COST_OVERRIDE` matching `VariableCost`.
- FORBIDDEN: synthesizing `ResourceCost`, `research_time_seconds`, prerequisites, effects, civ availability, `LINK=315`-as-prereq.

Already modeled at this SHA (plan text listing them as "remaining" is stale — see 09): Fish Trap 199, Carrack 2628, Treadmill Crane 54, Siphons 909 (`game_data_manifest_buildings:40-54`, `game_data_manifest_unit_supplements:32-43`, `game_data_manifest_technology_conflicts:38-57`, `civ_profile:795-888,1190-1222,1355-1393`; proven `test_game_data:350-479`).
Snapshot guardrails hold: boundary `game_data_dat_snapshot:194-319`; 201-record snapshot test `:630-691`; plans "no live DAT values committed" / "do not claim completion of remaining 73 nodes" still in force.
