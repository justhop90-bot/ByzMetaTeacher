# Byzantine Core v1 Milestone Plan

> For agentic workers: execute the milestones in order. Do not promote a milestone from static compiler evidence alone when the milestone includes a DE behavior claim.

**Goal:** Turn the verified Byzantine strategy compiler path into the first real Byzantine land bot: reproducible artifact, map/opening selection, adaptive economy, Feudal counterplay, Castle conversion, Cataphract/Varangian arbitration, attack/recovery, and a recorded live-DE acceptance matrix.

**Current planning base:** `main` at `d6bf39e74385899e732e96f3474f6d5f87f442c1` when this plan was refined.

## 1. Definition of Core v1

Core v1 is a **land-first Dark -> Feudal -> Castle bot**.

It must demonstrate the following control loop in actual DE play:

```
OBSERVATION
    -> OPENING
    -> ECONOMY
    -> THREAT ARBITRATION
    -> EXECUTION
    -> WORLD-STATE WITNESS
    -> ATTACK / RECOVERY
    -> REASSESSMENT
```

The generated artifact is native `.per`. The compiler remains the only mechanism used to turn strategy policy into the artifact.

Core v1 does **not** claim:
- Imperial strategic completeness;
- full water/naval/transport behavior;
- relic/trade specialization;
- complete DUC tactical micro;
- team-game specialization;
- tournament optimization.

The existing water/transport substrate must not regress, but its full behavioral completion is post-v1.

## 2. Architectural contract

The canonical production path is:

```
ByzantineProfile.for_update_185872()
        |
        v
resolve_effective_civ()
        |
        v
EffectiveCivData
        |
        v
build_byzantine_strategy()
        |
        v
StrategyProfile
        |
        +--> observations
        +--> strategic demands
        +--> posture transitions
        +--> counter packages
        +--> SN modes
        +--> opening selector
        +--> economy controller
        +--> military compositions
        +--> attack plan
        +--> DUC plan
        +--> water plan
        |
        v
resolve_strategy_profile()
        |
        v
lower_strategy_profile()
        |
        v
generic semantic compiler
        |
        v
RuntimeBinder
        |
        v
native emitter
        |
        v
Byzantine.per
```

Important boundary:

**Python runtime evaluation is analysis/test machinery, not the DE bot runtime.**

If a strategic decision is required during an actual match, it must survive lowering into native Goal/SN/rule state. `compile_strategy_runtime_profile()` may be used for deterministic runtime-state tests, but the deployed bot cannot depend on Python being present during the match.

## 3. Global invariants

- `main` remains the compiler source of truth.
- The canonical strategy entry point is `build_byzantine_strategy(effective)`.
- Current patch binding is `ByzantineProfile.for_update_185872()`.
- Reuse existing typed seams before creating new compiler abstractions.
- Preserve `OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT`.
- `can-*` means admission/feasibility only.
- Action issuance is never a completion witness.
- Pending means in-flight protection, not completion.
- Timer means cadence, not strategic truth.
- UNKNOWN stays UNKNOWN until direct runtime evidence promotes it.
- Strategy policy may choose when an action is wanted; native engine facts decide whether it is currently executable.
- A compiler/native pass proves artifact correctness, not game quality.
- No milestone may quietly convert a missing DE test into a static proxy.
- Every DE failure receives an explicit classification.
- No milestone may be marked complete because the artifact "looks plausible."

## 4. Current implementation reality

The repository already contains:

- typed `StrategyProfile`;
- strategic demands and lifecycle binding;
- production arbitration;
- Goal/SN/Timer storage binding;
- Strategic Number arbitration;
- typed counter packages and Python-side runtime arbitration;
- typed MapProfile;
- persistent `opening-plan`;
- persistent `economy-posture`;
- civilian allocation writers for SN 117/120/118/1;
- Castle infrastructure and military demands;
- conditional Varangian Guard demand;
- military composition plans;
- typed attack lifecycle;
- typed DUC channel;
- typed water/transport execution state;
- native parser zero-findings fixtures;
- cross-platform/determinism compiler CI.

The remaining Core v1 gap is behavioral composition of those pieces.

In particular:

1. `MapProfile` is currently policy metadata. `OpeningSelectorPlan` is the executable native selector.
2. Counter arbitration currently has a strong typed/Python representation. Core v1 requires its **decision to affect native demand activation**.
3. Production arbitration protects provider/resource claims. It does **not** by itself decide which strategic objective wins.
4. Varangian Guards are correctly conditioned by infantry pressure, but Core v1 must prove that the broader Castle package does not independently activate them.
5. Attack lifecycle exists, but Core v1 must demonstrate a real attack -> failure -> reassessment loop.
6. Existing water/transport control is a substrate, not a completed naval strategy.

These are the seams the milestones target.

---

# Milestone 0: Reproducible Byzantine bot artifact

**Outcome:** One command creates the canonical Byzantine `.per` plus manifest, twice, with identical bytes and a recorded provenance envelope.

### Compiler surfaces

- `ByzantineProfile.for_update_185872()`
- `resolve_effective_civ()`
- `build_byzantine_strategy()`
- `compile_strategy_profile()`
- `assert_native_zero.py`

### Deliverables

Create:

- `tools/build_byzantine_bot.py`
- `docs/reference/byzantine-core-v1-build.md`
- `LearnerAI/Compiler/tests/test_byzantine_bot_build.py`

Modify:

- `.github/workflows/compiler-tests.yml`

Produce:

- `dist/byzantine/Byzantine.per`
- `dist/byzantine/Byzantine.manifest.json`

Manifest must contain at least:

- profile id;
- civilization;
- patch key;
- effective snapshot fingerprint;
- artifact SHA-256;
- compiler source revision;
- build input identity;
- native parser revision used for acceptance.

### Required behavior

The build command:

1. resolves the current Byzantine factual snapshot;
2. calls only the canonical `build_byzantine_strategy()` entry point;
3. compiles the resulting profile through the normal client/compiler path;
4. writes the artifact and manifest;
5. performs an in-process second compile and asserts byte equality before promotion.

No Steam installation side effect is permitted.

### Static acceptance

- focused build test passes;
- artifact non-empty;
- second compile byte-identical;
- manifest hash matches artifact;
- native parser returns zero findings;
- full compiler verification remains green.

### DE-00

Load the generated artifact into a test DE AI directory.

Acceptance:

- AI loads without script/parser failure;
- villagers are created;
- population management does not immediately deadlock;
- normal opening execution begins;
- no behavior is attributed to "strategy quality" until the artifact is proven loadable.

Failure classification:

- load/parser failure -> BUILD_OR_COMPILER;
- artifact loads but no intended strategic behavior -> POLICY;
- command behavior contradicts an unresolved assumption -> RUNTIME_UNKNOWN.

### Exit gate

Milestone 0 is complete only when the exact artifact used for DE-00 has a recorded SHA-256 and passes the static gate.

---

# Milestone 1: Opening and early economy become a real control loop

**Outcome:** The bot chooses among the supported land openings and the choice materially changes native economic control.

### Scope

Behavioral maps:

- Arabia;
- Arena;
- Standard Land.

Hybrid remains fail-closed unless a verified detector exists.

Islands remains a non-regression compile path for Core v1, not a naval-quality claim.

### Compiler surfaces

- `MapProfile`
- `OpeningSelectorPlan`
- `opening-plan` Goal
- `EconomyControllerPlan`
- `economy-posture` Goal
- SN 117 / 120 / 118 / 1

### Required native opening policy

For Core v1:

```
Arena + no strong early pressure      -> FAST_CASTLE
Land + sustained early pressure       -> COUNTER_FEUDAL
Land + no strong early pressure       -> DEFENSIVE_STANDARD
```

Water opening is outside the live Core v1 behavioral gate.

The selector must not oscillate because of one transient observation. The selected opening is persistent state; reassessment requires an explicit policy transition.

### Required economic policy

At minimum, the selected opening must drive:

- food allocation;
- wood allocation;
- gold allocation;
- builder allocation.

The controller must continue to use the existing SN writers. Do not introduce another villager scheduler.

### Static tests

Create/extend:

- `test_strategy_opening_economy.py`
- `test_byzantine_core_opening_behavior.py`

Assert:

- exact opening precedence;
- persistent Goal selection;
- deterministic economy mode selection;
- no duplicate ownership of SN 117/120/118/1;
- no Varangian activation merely because Byzantines possess the unit.

### DE acceptance

**DE-01: Arabia standard**

No strong early pressure.

Required:

- non-water opening;
- economic allocation changes to the selected posture;
- Feudal transition occurs;
- no unnecessary water investment.

**DE-02: Arena**

No strong early pressure.

Required:

- FAST_CASTLE opening;
- economy shifts to Castle-oriented mode;
- Castle conversion begins after opening prerequisites;
- no permanent Feudal counter posture.

**DE-03: Early infantry pressure**

Controlled scenario with the threshold used by `strategy-opening-pressure`.

Required:

- opening moves to COUNTER_FEUDAL;
- economy shifts away from FAST_CASTLE/BASE;
- defensive production begins;
- after pressure clears, the temporary counter intent releases.

### Exit gate

No promotion if the bot chooses the same opening/economic posture in all three cases.

---

# Milestone 2: Native strategic activation and Feudal threat arbitration

**Outcome:** Enemy pressure does not merely exist as an observed fact. It activates the correct native strategic package and suppresses incompatible packages.

This is the most important refinement to the original Core v1 plan.

### Why it exists

Production arbitration answers:

> Which demands may share an execution/provider claim?

Core v1 also needs to answer:

> Which strategic demand is actually wanted right now?

Those are different questions.

### Compiler surfaces

Reuse:

- `CounterPackage`
- `CounterPackageRuntimeState`
- `arbitrate_counter_packages()`
- `StrategyRuntimeState`
- `StrategicDemandSpec`
- `StrategicBinding`
- production arbitration
- existing Goal control

Add the smallest native activation seam required to carry the decision into emitted `.per`.

Do **not** create a generic scheduler or a second strategy language.

### Native contract

The chosen counter state must become persistent native state.

Conceptually:

```
enemy evidence
      |
      v
counter arbitration
      |
      v
active-counter Goal
      |
      +--> activate correct strategic demands
      +--> suppress incompatible counter package
      +--> preserve independent lifecycle state
```

The exact IR shape may differ, but the contract must remain:

- strategic identities remain distinct;
- lifecycle state remains distinct;
- production arbitration remains distinct;
- counter activation is explicit;
- UNKNOWN never activates a package.

### Counter policy

Core v1 requires:

- mounted Feudal -> spear response;
- ranged Feudal -> skirmisher response;
- mixed pressure -> deterministic arbitration;
- Castle cavalry -> Castle cavalry counter, age/capability gated;
- Castle infantry -> Cataphract/Varangian pathway;
- siege -> siege response;
- threat clears -> temporary package releases.

### Static tests

Create:

- `test_byzantine_core_counters.py`

Assert:

- TRUE -> correct package active;
- FALSE -> package inactive/released;
- UNKNOWN -> package inactive;
- capability loss -> BLOCKED, never COMPLETE;
- competing equal-priority packages resolve deterministically;
- native activation rules are present in generated `.per`;
- production arbitration claims remain collision-safe.

### DE acceptance

**DE-04: Feudal cavalry**

Required:

- spear production begins;
- Feudal economy remains functional;
- no premature premium Castle response.

**DE-05: Feudal ranged**

Required:

- skirmisher production begins;
- economy continues;
- response stops expanding once pressure clears.

**DE-06: Mixed pressure**

Required:

- one deterministic primary package is selected;
- compatible support is allowed;
- duplicate provider/resource claims do not create a production deadlock.

### Exit gate

This milestone is not complete until the selected counter state is visible in the emitted native artifact **and** changes the actual DE production behavior.

---

# Milestone 3: Castle conversion and premium-unit arbitration

**Outcome:** Castle Age becomes a controlled conversion phase rather than a pile of simultaneous production floors.

### Compiler surfaces

- community strategy packs;
- `MilitaryCompositionPlan`;
- production lifecycle;
- opportunity-cost protection;
- Cataphract demand;
- Varangian Guard demand;
- Castle infrastructure demands.

### Required package separation

**Standard Castle package**

- Cataphracts are available;
- Knights are available where policy calls for them;
- Varangian Guard is NOT an unconditional floor.

**Infantry-pressure package**

- Varangian Guard floor may activate;
- Cataphract response remains available;
- production arbitration prevents uncontrolled simultaneous premium expansion.

**Ranged-pressure package**

- ranged counter remains primary;
- Varangian Guard must not activate solely because the civ owns it.

### Static tests

Create:

- `test_byzantine_core_castle_conversion.py`

Assert:

- `castle-standard-package` does not activate the Varangian demand;
- `castle-infantry-package` explicitly references it;
- Varangian demand trigger and invalidation are paired;
- native Varangian IDs remain bound to 2703/2704;
- Castle infrastructure and premium production share existing arbitration without duplicate ownership.

### DE acceptance

**DE-07: Normal Castle conversion**

Required:

- reach Castle;
- establish useful Castle infrastructure;
- begin premium production;
- no immediate Varangian flood.

**DE-08: Castle infantry pressure**

Required:

- infantry package activates;
- Varangians become eligible;
- production reflects the active counter rather than merely the existence of the unit;
- release occurs after pressure clears.

**DE-09: Castle ranged pressure**

Required:

- ranged response remains primary;
- Varangian demand stays inactive unless its own evidence becomes TRUE;
- economy remains capable of Castle continuation.

### Exit gate

A Core v1 build fails this milestone if Varangians behave as an unconditional checkbox in the relevant DE cases.

---

# Milestone 4: Attack execution and recovery

**Outcome:** The Castle military package can produce a real operation, observe its failure, and return to a coherent strategic state.

### Compiler surfaces

- `NativeAttackLifecyclePlan`
- `AttackExecution`
- military composition binding;
- existing DUC target channel;
- recovery/reassessment state.

### Required behavior

```
READY
  -> PREPARE
  -> ASSEMBLE
  -> ATTACK
  -> PRESS / REINFORCE
  -> RETREAT / RETARGET
  -> REASSESS
```

Native attack issuance is never treated as success.

Target loss is not success.

Force destruction is not success.

### Static tests

Create:

- `test_byzantine_core_attack_recovery.py`

Assert:

- Castle compositions bind to an attack objective;
- attack prerequisites are explicit;
- attack issuance is distinct from completion;
- reassessment exists;
- recovery can reopen the strategic objective;
- target-dependent behavior does not bypass DUC proof requirements.

### DE acceptance

**DE-10: First Castle attack**

Required:

- coherent army assembles;
- attack is actually issued;
- economic and production loops continue.

**DE-11: Failed attack**

Required:

- destroyed/failed attack does not strand the bot permanently in ATTACK;
- rebuilding begins;
- reassessment changes or preserves posture according to evidence;
- a subsequent military operation is possible.

**DE-12: Target loss**

Required:

- target loss invalidates stale targeting;
- bot retargets or reassesses;
- no stale target command is emitted from retained compiler state.

### Exit gate

The bot must demonstrate one complete attack/recovery loop in an actual DE match.

---

# Milestone 5: Integrated Core v1 acceptance

**Outcome:** All previous seams operate as one player.

### Static acceptance

Run:

1. focused Byzantine suites;
2. full compiler regression suite;
3. canonical Byzantine artifact build;
4. native zero-findings;
5. artifact byte determinism;
6. binding manifest determinism;
7. cross-platform native-support comparison;
8. final compiler verification gate.

The canonical artifact must contain evidence of:

- opening state;
- economy state;
- active counter machinery;
- Castle conversion;
- premium-unit arbitration;
- attack lifecycle;
- recovery/reassessment bindings.

### DE matrix

| Case | Setup | Required result |
| --- | --- | --- |
| DE-00 | Standard 1v1 load | Bot loads and begins normal play |
| DE-01 | Arabia, low pressure | Standard land opening + working economy |
| DE-02 | Arena, low pressure | Fast-Castle-oriented behavior |
| DE-03 | Early infantry pressure | Counter-Feudal + economic shift |
| DE-04 | Feudal cavalry | Spear response |
| DE-05 | Feudal ranged | Skirmisher response |
| DE-06 | Mixed Feudal pressure | Deterministic counter arbitration |
| DE-07 | Passive Castle conversion | Infrastructure -> premium production |
| DE-08 | Castle infantry pressure | Conditional Varangian/Cataphract response |
| DE-09 | Castle ranged pressure | Ranged response without automatic Varangians |
| DE-10 | Castle attack opportunity | Actual attack operation |
| DE-11 | Failed first attack | Recovery + reassessment |
| DE-12 | Target disappears | Invalidation + retarget/reassess |

### Required evidence record

For every DE case record:

- scenario id;
- map;
- opponent setup;
- artifact SHA-256;
- compiler revision;
- expected behavior;
- observed behavior;
- pass/fail;
- failure classification;
- replay/scenario identifier where available;
- responsible module if failed.

Allowed failure classes:

- `BUILD_OR_COMPILER`
- `POLICY_WRONG`
- `POLICY_MISSING`
- `GAME_DATA_GAP`
- `NATIVE_SEMANTIC_GAP`
- `RUNTIME_UNKNOWN`

### Promotion rule

Core v1 is complete only when:

- all static gates pass;
- all mandatory DE cases have recorded PASS;
- no mandatory case remains UNKNOWN;
- every known weakness is either fixed or explicitly deferred to a named post-v1 milestone.

---

# 5. Test strategy

The project uses three different proofs.

## Proof A: Compiler proof

Answers:

> Did we generate a valid deterministic native AI artifact?

Evidence:

- semantic validators;
- storage binding;
- native zero-findings;
- full regression;
- determinism;
- cross-platform replay.

## Proof B: Policy proof

Answers:

> Does the StrategyProfile encode the intended decision?

Evidence:

- typed profile tests;
- runtime-state tests;
- counter arbitration tests;
- opening/economy tests;
- composition tests.

## Proof C: Game proof

Answers:

> Did the generated bot actually do what the policy intended in DE?

Evidence:

- manual DE scenarios;
- screenshots/replays/observations;
- artifact hash;
- recorded expected vs observed behavior.

Never substitute A for C.

---

# 6. Implementation discipline

Implement each milestone in a red -> implementation -> static green -> native green -> DE cycle.

For every code repair:

1. Add the smallest failing focused test.
2. Implement only the missing policy/compiler seam.
3. Run the focused suite.
4. Compile the canonical Byzantine artifact.
5. Run native zero-findings.
6. Run the full compiler gate.
7. Perform the required DE cases.
8. Record failures by classification.
9. Promote or create the next repair.

Do not add generic infrastructure merely because it might be useful later.

A compiler feature is justified when a required Byzantine behavior cannot be represented safely by the existing typed seams.

A strategy feature is justified when community evidence or a reproducible DE failure demonstrates the need.

---

# 7. Immediate execution order

1. **Milestone 0:** build `Byzantine.per` reproducibly.
2. **First live game:** DE-00.
3. **Milestone 1:** prove opening/economic divergence.
4. **Milestone 2:** make counter arbitration affect native demand activation.
5. **Milestone 3:** prove Castle premium-unit arbitration, especially Varangians.
6. **Milestone 4:** prove attack and recovery.
7. **Milestone 5:** run the complete 13-case matrix.

Do not implement Milestone 2 by expanding the generic compiler into a universal scheduler.

Do not call the stock profile "finished" because its artifact parses.

Do not call the bot "good" because one game looks competent.

The target is narrower and much more useful:

**a deterministic compiler-produced Byzantine bot whose strategic control loop can be observed, tested, and repaired in actual DE games.**

---

# 8. Repository commands

Focused Core v1 tests:

```bash
PYTHONPATH=LearnerAI python -m unittest \
  LearnerAI/Compiler/tests/test_strategy_opening_economy.py \
  LearnerAI/Compiler/tests/test_counter_strategy.py \
  LearnerAI/Compiler/tests/test_production_arbitration.py
```

Full compiler regression:

```bash
PYTHONPATH=LearnerAI python -m unittest discover \
  -s LearnerAI/Compiler/tests -p "test_*.py"
```

Canonical bot build:

```bash
PYTHONPATH=LearnerAI python tools/build_byzantine_bot.py
```

Native acceptance:

```bash
python LearnerAI/Compiler/tests/assert_native_zero.py \
  dist/byzantine/Byzantine.per \
  --report /tmp/native-reports/byzantine-core-v1.json
```

The authoritative compiler/determinism gate remains GitHub Actions.

Live DE acceptance remains a manual/external gate until the project deliberately adds and verifies a real game runner.
