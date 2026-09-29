# 06 — GameData factual reconciliation @ `cd923b5a` (FACTUAL_SUBSET, civ-scoped)

Ground truth: current `test_game_data.py` coverage oracle → modeled 159, unmodeled 0, verified_unavailable 14,
total 173. Coverage is civilization-scoped FACTUAL_SUBSET.(`ir/civ_profile:1489-1512`; `ir/game_data:46-60,272-281`).
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

## A3 — TECHNOLOGY 408 Spies/Treason — VARIABLE COST (closed)
- MANIFEST IDENTITY: `408 | Spies/Treason | TYPE=Research | USE=Tech | STATUS=ResearchedCompleted | AGE=4 | BUILDING=82 | LINK=315 | TRIGGER=<MISSING>`.
- IMPLEMENTATION: `TechnologyDef.base_cost` now accepts typed `VariableCost`; the current materialization records formula `spies-treason-gold-per-enemy-civilian` with parameters `minimum_gold=200`, `maximum_gold=30000`, and `gold_per_civilian=200`.
- SAFETY: `EffectiveCivData.cost_of()` rejects `VariableCost` rather than flattening a game-state-dependent cost into a false fixed `ResourceCost`.
- EVIDENCE: the current public reference describes the dynamic gold rule; the compiler preserves it as a typed fact. Runtime evaluation against live enemy-civilian state is deliberately not part of the fixed-cost API.
- TESTS: variable-cost determinism, exact Spies materialization, fixed-cost API rejection, provenance, and manifest-coverage regressions.
- REMAINING: a future runtime cost resolver would require a separate live-state contract. No fixed cost, prerequisite, effect, availability, or LINK=315 semantics are inferred here.

Already modeled at this SHA (plan text listing them as "remaining" is stale — see 09): Fish Trap 199, Carrack 2628, Treadmill Crane 54, Siphons 909 (`game_data_manifest_buildings:40-54`, `game_data_manifest_unit_supplements:32-43`, `game_data_manifest_technology_conflicts:38-57`, `civ_profile:795-888,1190-1222,1355-1393`; proven `test_game_data:350-479`).
Snapshot guardrails hold: boundary `game_data_dat_snapshot:194-319`; 201-record snapshot test `:630-691`; plans "no live DAT values committed" / "do not claim completion of remaining 73 nodes" still in force.
