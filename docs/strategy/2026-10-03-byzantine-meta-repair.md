# Byzantine Meta Strategy Repair

Date: 2026-10-03  
Target: Byzantine Stock v1, AoE2DE Update 185872  
Repository: `justhop90-bot/ByzMetaTeacher`  
Status: implementation branch, runtime and compiler wiring under verification

## 1. Objective

Convert the existing Byzantine strategy substrate from an overcommitted Fast Castle trajectory into a map- and threat-conditioned Byzantine policy while preserving one owner per strategic responsibility.

The target causal path is:

`MAP / SCOUTING / THREAT`
→ `OPENING`
→ `ECONOMIC POSTURE`
→ `RESOURCE PROTECTION`
→ `CAPABILITY / PRODUCTION`
→ `MILITARY COMPOSITION`
→ `ATTACK / DUC`
→ `WITNESS / RECOVERY`
→ `REASSESSMENT`

The repair does not introduce a new scheduler, research controller, economy controller, army builder, or attack subsystem.

## 2. Strategic policy

Open land defaults to a defensive Byzantine trajectory unless actual pressure justifies Counter-Feudal and sufficient safety evidence justifies Fast Castle.

Arena remains Fast Castle by default. After Castle Age, an Arena Fast Castle position with low pressure enters the existing Castle-conversion path using the new Fast Imperial economic posture.

The strategic families are therefore:

- DEFENSIVE_STANDARD
- COUNTER_FEUDAL
- FAST_CASTLE
- WATER_ECONOMY
- WATER_CONTROL

Fast Imperial is intentionally represented as a Castle-conversion economy mode rather than another opening writer. This avoids duplicate ownership of `opening-plan`.

BOOM remains an existing persistent posture. Castle completion no longer forcibly overrides BOOM; BOOM can continue into Castle when its economic conditions remain valid.

## 3. Economic technology arbitration

Double-Bit Axe, Horse Collar, Wheelbarrow, and Gold Mining are Feudal opportunities rather than unconditional Castle-only purchases.

Execution remains under the existing research demand lifecycle and `can-research-with-escrow` feasibility contract.

Feudal opportunity windows use explicit protected floors:

| Technology | Food floor | Gold floor |
|---|---:|---:|
| Wheelbarrow | 1000 | 250 |
| Double-Bit Axe | 900 | 250 |
| Horse Collar | 900 | 250 |
| Gold Mining | 900 | 250 |

The floor exists in both strategic opportunity-cost metadata and executable native guards. This keeps the compiler policy and generated `.per` behavior aligned.

The policy is deliberately not equivalent to "research every Feudal technology immediately." The Castle bank, military floor, and emergency posture remain higher-order constraints.

## 4. Military arbitration

The existing demand identities remain authoritative.

The standard Castle package no longer unconditionally consumes `castle-cataphract-floor`. Cataphract demand is owned by the existing infantry-pressure package.

Varangian Guard demand remains conditional on the existing infantry-pressure package. The checked-in runtime had a mounted-pressure guard on the Varangian issuance path; that wire is corrected to the existing infantry-pressure package.

No new Cataphract, Camel, Varangian, Skirmisher, or Spearman demand subsystem is introduced.

## 5. Attack wiring

The existing Castle attack-group SN path is extended to BOOM as well as CASTLE-POWER. No second attack controller is introduced.

The typed Byzantine attack lifecycle is corrected so:

- infantry pressure + Cataphract floor → Cataphract attack preparation;
- siege pressure + Knight floor → mobile Knight attack preparation;
- Cataphract completion is witnessed by infantry-pressure clearance;
- Knight completion is witnessed by siege-pressure clearance.

Native attack completion remains an open runtime boundary unless independently proven.

The checked-in runtime artifact had an additional composition gate that required four Cataphracts, four Skirmishers, two Mangonels, and one Monk before any Castle attack could become attack-ready. That gate is replaced by an assembled-backbone contract: at least eight attack soldiers plus a valid Castle backbone, with Cataphracts when infantry pressure is real, Knights otherwise, or the existing Skirmisher floor. Fortified assaults continue through the existing siege-approach state instead of making siege and Monks a universal attack prerequisite.

## 6. Ownership and non-duplication

| Responsibility | Single owner |
|---|---|
| Map policy | `MapProfile` |
| Opening decision | `OpeningSelectorPlan` / `opening-plan` |
| Strategic posture | `StrategyPosture` / `strategy-posture` |
| Civilian economy | `EconomyControllerPlan` / `economy-posture` |
| Resource opportunity cost | `OpportunityCostPolicy` |
| Research lifecycle | existing `StrategicDemandSpec` research lifecycle |
| Military composition | existing composition / counter packages |
| Production capacity | existing production arbitration |
| Attack lifecycle | existing `AttackExecution` / native attack plan |
| DUC target discovery | existing `NativeDucPlan` |
| Water | existing `WaterExecutionPlan` |
| Resource camps | existing Byzantine camp controller |
| Recovery | existing invalidation/reassessment contracts |

## 7. Runtime invariants

1. `opening-plan` has one writer.
2. Civilian allocation SNs remain owned by one economy controller.
3. Fast Imperial uses economy posture 9 because checked-in runtime already reserves posture 8 for food recovery.
4. Feudal economic technology demand does not remove the Castle resource bank.
5. Premium Castle units require a strategic package rather than merely Castle Age.
6. BOOM and CASTLE-POWER share the existing attack-group control surface.
7. Timers remain cadence controls, never completion witnesses.
8. Native attack completion remains UNKNOWN until engine evidence exists.
9. Every persistent demand retains explicit release/invalidation behavior.
10. No second research, economy, scheduler, attack, or DUC subsystem is introduced.

## 8. Verification

Required acceptance:

- focused Byzantine strategy tests;
- focused Byzantine playtest tests against checked-in `Byzantine.per`;
- native zero-findings for checked-in `Byzantine.per`;
- freshly compiled strategy zero-findings;
- full compiler regression suite;
- cross-platform native-support determinism;
- deterministic artifact output.

Runtime game verification remains separate from compiler acceptance. A compiler pass establishes representation correctness, not strategic game strength.
