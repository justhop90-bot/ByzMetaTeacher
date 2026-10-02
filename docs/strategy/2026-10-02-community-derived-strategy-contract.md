# Community-Derived Strategic Behavior Contract

## Status

Implementation contract for the missing downstream strategy layer of the AoE2DE .per compiler.

The generic execution substrate is already accepted: demand lifecycle, capability/provider projection, construction, production arbitration, research lifecycle, Strategic Numbers, Timers, DUC state, attack lifecycle, escrow release, deterministic lowering, and native acceptance.

This contract therefore defines only the remaining strategy synthesis.

## Evidence classes

Every strategic rule is classified as:

- ENGINE FACT: native behavior verified from engine/reference evidence.
- COMMUNITY PRACTICE: recurring .per idiom corroborated across independent community sources.
- COMPILER POLICY: deterministic choice made by the compiler from those facts and precedents.
- OPEN / UNKNOWN: runtime behavior not yet proven.

Community practice never becomes engine fact by repetition.

## 1. Economic strategy

Economy answers: what resource constraint currently prevents the chosen position from functioning?

The strategic layer must represent:

- food, wood, gold, and stone protection;
- age-transition financing;
- economic technology maintenance;
- farm and dropsite continuity;
- Town Center expansion;
- temporary military/resource displacement;
- recovery after raids or temporary starvation.

The compiler shall prefer persistent demands with explicit resource floors over hard-coded worker scripts.

Required sequence:

`strategy intent -> protected resource floor -> capability demand -> action -> world witness -> release`

Temporary shortage changes feasibility and arbitration, not the strategic truth of the objective.

## 2. Research strategy

Research is a persistent capability plan, not a timer list.

The standard Byzantine strategy pack shall maintain a small, high-value research set:

- Dark/Feudal economy foundations;
- Castle economy foundations;
- standing military upgrades associated with the active composition;
- Imperial conversion technologies;
- civ-specific strategic upgrades such as Logistics where the factual snapshot proves them.

Each technology demand requires:

- explicit strategic reason;
- age and availability admission;
- escrow-aware affordability where supported;
- research action;
- research-completed witness;
- completion/invalidation semantics;
- resource protection while the technology remains strategically valuable.

Research order is policy. Native queue ordering remains an engine behavior boundary.

## 3. Production strategy

Production exists because a strategic composition or replacement floor requires capacity.

The compiler must synthesize:

- baseline Barracks continuity;
- Feudal ranged/anti-mounted production where observations justify it;
- Castle cavalry/cataphract capacity;
- siege capacity when siege pressure or anti-structure conversion justifies it;
- Monastery capacity when healing/relic play becomes strategic;
- naval capacity from the water posture;
- second/third production capacity only when current-plus-queued demand warrants it.

Production buildings are capability providers, not goals for their own sake.

## 4. Military composition

Military strategy is a set of standing role floors, not a unit list.

The initial Byzantine pack recognizes:

- minimum defensive screen;
- ranged counter role;
- mounted counter role;
- Castle power composition;
- siege response;
- late-game mixed replacement.

Composition arbitration must preserve simultaneous threat classes when they are independent, while suppressing redundant same-class packages.

Attack control consumes composition state. Attack issuance never proves battle success.

## 5. Information and map strategy

Information owns observations.

The compiler consumes:

- current age;
- enemy composition;
- enemy production signals;
- current water assets;
- disconnected-access evidence;
- relic opportunity evidence where proven;
- defensive exposure;
- map-profile evidence.

Map state is a strategic envelope, not a full scheduler.

Unknown map predicates remain OPEN.

The implementation may maintain a valid land strategy without claiming automatic water discovery when the native observation is not proven.

## 6. Fortification

Fortification is justified by exposure and threat.

The strategy layer may maintain demands for:

- wall/gate continuity;
- outpost/watch-tower coverage;
- late defensive Castle/Bombard Tower capability.

Placement-sensitive behavior is not treated as proven merely because a build command exists.

The compiler can prove the need for a defensive capability and lower a safe provider action. Exact location heuristics remain empirical work.

## 7. Siege

Siege is a conversion capability.

Demand sources include:

- enemy ranged mass;
- enemy fortification;
- building-pressure posture;
- late-game composition requirements.

A Siege Workshop is not siege completion.

A produced siege unit is a capability witness, not attack success.

## 8. Monks and relics

Monks are strategic support and information assets.

The compiler shall model:

- Monastery capability;
- monk replacement;
- healing support;
- relic-contest demand when relic opportunity is proven;
- recovery after Monk loss.

Exact relic acquisition and pathing remain OPEN until the native/DUC behavior is independently established.

## 9. Castle and Imperial conversion

Castle is not a terminal state.

After Castle completion the strategy must reassess:

- economy expansion;
- production capacity;
- military composition;
- siege;
- Monks/relics;
- water;
- defensive infrastructure.

Imperial is likewise a conversion state.

Imperial demand shall be persistent when the strategic economy can support it, with explicit resource protection and emergency override policy.

Late game must maintain pressure, replacement, and economic conversion rather than stopping at age advancement.

## 10. Recovery

Recovery preserves strategic identity.

Required recovery classes:

- capability loss;
- production provider loss;
- resource starvation;
- lost military floor;
- lost dock/naval capability;
- failed transport preparation;
- failed infrastructure;
- obsolete strategic objective.

Correct model:

`loss -> reassess -> preserve intent if still valid -> reopen execution`

Incorrect model:

`loss -> delete demand`

Invalidation requires strategic evidence.

## 11. Persistent control

The strategy layer may use:

- Goal state;
- Strategic Number modes;
- Timer cadence;
- action-scoped control;
- restoration/reassertion.

Native same-pass behavior remains evidence-bounded.

No controller may become a hidden universal scheduler.

## 12. Community corpus

The strategy registry shall classify recurring community idioms as:

`DISCOVERED -> CORROBORATED -> SEMANTICIZED -> EXPRESSIBLE -> LOWERABLE -> VERIFIED`

Important recurring families include:

- goal-backed state machines;
- Strategic Number mode switching;
- production parity and counter trains;
- military parity;
- defense toggles;
- resource starvation release;
- persistent research protection;
- map tables;
- water split;
- DUC micro;
- attack cadence/reset;
- recovery/reassertion.

Independent corroboration must consider historical lineage. Copies of the same lineage are not independent evidence.

## 13. Acceptance

A strategy pack is complete when it has:

1. a typed strategic owner;
2. persistent reason;
3. explicit admissibility;
4. capability/provider path;
5. feasibility;
6. action;
7. world-state witness;
8. release/invalidation;
9. recovery;
10. reassessment;
11. deterministic native lowering;
12. focused semantic tests;
13. native zero-findings acceptance;
14. full compiler regression and determinism.

Runtime-only questions remain OPEN and are recorded as such.

## 14. Architectural boundary

No WaterManager, EconomyManager, MilitaryManager, UniversalScheduler, runtime simulator, optimizer, or second .per language is introduced.

All new behavior is lowered through the existing:

`StrategyProfile -> StrategicDemandSpec -> semantic IR -> capability/resource graph -> SN/Timer/DUC/attack/escrow -> native .per`

That is the actual missing layer.
