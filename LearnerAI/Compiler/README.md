# AoE2DE `.per` Compiler

The compiler is the project's primary product: a deterministic, evidence-backed compiler for community-native Age of Empires II Definitive Edition `.per` practice, currently used to build a Byzantine-focused client.

It converts semantic intent and documented native behavior into native `.per`, while rejecting semantic claims the engine parser cannot prove.

## Read order

For current work:

1. [ `PROJECT_STATE.md` ](PROJECT_STATE.md) — exact accepted state, current verification, and next repair.
2. [ `README.md` ](README.md) — this architecture and interface guide.
3. [ [[BT ]]AGENTS.md` ](../../AGENTS.md) — repository and AI engineering contract.
4. Focused subsystem code and tests.
5. `docs/plans/` and research records only when the current state points to them.

## Compiler boundary

The compiler is not:

- a runtime simulator;
- a universal scheduler or optimizer;
- a tournament-bot framework;
- a replacement for the native `.per` parser;
- a second general-purpose AoE2 language.

The runtime remains the authority for actual DE behavior.

Some source paths and client adapters retain legacy names for compatibility. New architecture documentation should not treat those names as the project identity.

## Compilation pipeline

`(source
  -> AST
  -> semantic demand/lifecycle analysis
  -> capability and admissibility projection
  -> typed semantic program
  -> control/DUC/attack/escrow/SN/Timer contracts
  -> deterministic runtime binding
  -> native .per
  -> pinned aoe2-ai-parser
  -> zero native findings
  -> promoted artifact
  -> DE runtime evidence)`

Runtime probes remain outside the static compilation contract.

## Source language

The intentionally small teaching language remains:

`demand <name> {
    require (<native predicate>)
    action (<native action>)
    witness (<native world-state predicate>)
    release (<native predicate>)
    invalidate (<native invalidation predicate>)   # optional
}`

Native expressions remain visible. The compiler adds typed semantic meaning rather than hiding AoE2 behind a large new language.

## Causal doctrine

Core lifecycle:

`DEMAND
 -> ADMISSIBILITY
 -> CAPABILITY
 -> FEASIBILITY
 -> ACTION
 -> WORLD-STATE WITNESS
 -> RELEASE
 -> RECOVERY
 -> REASSESSMENT`

Operational control layer:

`OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT`

Hard semantic rules:

- `can-*` is admission/permission, not completion;
- action issuance is not completion;
- pending is in-flight protection, not world-state proof;
- timers are cadence/control, not strategic truth;
- observations are only witnesses when a typed completion contract admits them;
- compiler-policy claims are never emitted as invented native conflict classes;
- unknown native/runtime behavior remains OPEN/UNKNOWN.

## Accepted semantic substrate

Current `main` includes:

- demand ownership and emitter-aligned state accesses;
- completion witness, release, invalidation, and cancellation contracts;
- capability/provider/admissibility/feasibility validation;
- deterministic resource/conflict validation;
- construction lifecycle and resource ownership;
- production lifecycle observations for provider readiness, queue capacity, provider availability, birth, queue exit, and pending-object protection;
- research lifecycle and escrow claim semantics;
- Strategic Number semantics and persistent control;
- Timer allocation plus timer-owner/release cleanup analysis;
- DUC SearchSession/TargetSession and typed target identity/reacquisition state;
- attack controller observation and operational semantics;
- typed attack execution lifecycle;
- military composition proof assembly;
- effective source graph resolution and validation;
- deterministic runtime binding and native lowering;
- native zero-findings and cross-platform determinism acceptance.

These are compiler contracts. They do not imply that every runtime interaction they model has already been proven by DE probes.

## Current open frontier

Production/train arbitration is implemented through the existing `ResourceClaim` surface and is no longer the next generic semantic seam.

The live frontier is behavioral synthesis above the existing substrates:

- DUC strategy exposure is now threaded through `StrategyProfile`, `StrategyCompilation`, and both normal/runtime Byzantine compiler entry points using the existing `NativeDucPlan` channel;
- DUC behavioral policy is still needed to select concrete Byzantine discovery/target pipelines and connect them to strategic demands;
- typed `AttackExecution` and its operational bridge are present, but native attack completion, release/reset, group causality, and runtime target liveness remain OPEN;
- remaining escrow/resource arbitration, active Strategic Number evidence, Byzantine factual closure, and broader community strategy packs remain in scope;
- exact DE queue/provider behavior and other runtime interactions remain evidence work, not compiler facts.

## Architecture map

### `compiler.py`

Top-level orchestration and CLI. It coordinates parsing, semantic validation, native validation, runtime binding, and deterministic emission.

### `ast.py` / `parser.py`

Small source-language frontend.

### `ir/`

Typed semantic representation, including demand, capability, game data, strategy, persistent controls, attack, DUC, escrow, and native contracts.

### `semantic/`

Compiler-only reasoning. Validators must reject illegal states without inventing runtime facts.

### `primitives/`

Authoritative native command metadata and semantic primitive registry.

### `runtime_binding.py`

Deterministic symbolic storage binding for Goals, Goal spans, Strategic Numbers, Timers, and persisted manifests.

### `emitter/`

Deterministic native `.per` lowering. Source order is semantic behavior and must remain stable.

### `backends/`

External native validation boundary. The pinned aoe2-ai-parser is the syntax/native-command acceptance authority.

### `clients/`

Explicit downstream strategy/civilization adapters. The generic compiler core stays strategy-neutral.

### `tests/`

Executable semantic and native integration evidence.

## Evidence model

Every executable semantic claim belongs to one of four classes:

- ENGINE FACT
- COMMUNITY PRACTICE
- COMPILER POLICY
- OPEN / UNKNOWN

Community prevalence is precedent, not engine proof.

Compiler policy is allowed when it is explicit and conservatively scoped.

An unresolved engine interaction is not promoted merely because a community script uses it repeatedly.

## Storage and state

The compiler distinguishes:

- semantic state identity from native numeric Goal values;
- Goal spans from independent Goal outputs;
- persistent controls from transient execution facts;
- Strategic Number and Timer storage from strategic truth;
- compiler-owned bindings from runtime-owned state.

Deterministic binding manifests are evidence of the compiler's allocation decision, not proof of native runtime behavior.

## Native validation

Generated `.per` is staged and validated by the pinned native backend.

Acceptance requires zero native findings. Backend failure, rejection, timeout, or non-zero findings prevents promotion.

The repository compiler workflow additionally requires:

- generated fixture reproducibility;
- focused semantic regressions;
- the full compiler test suite;
- 3 OS x 3 Python native-support determinism;
- cross-platform snapshot comparison;
- the aggregate compiler verification gate.

## Current verification baseline

At the current accepted main commit, the compiler workflow reported:

- 1,431 compiler tests passing on the latest verified candidate;
- native zero-findings fixtures passing;
- 9/9 native-support determinism jobs passing;
- cross-platform snapshot comparison passing;
- compiler verification gate passing.

See `PROJECT_STATE.md` for the exact commit and workflow.

## Working rule

When a new player behavior exposes a compiler gap:

1. locate the existing semantic seam;
2. write the smallest typed contract that represents the missing relation;
3. add a focused failing test;
4. implement the minimum behavior;
5. preserve UNKNOWN boundaries;
6. integrate through the existing public compiler surfaces;
7. run the full acceptance gate;
8. update the current-state document.

Do not create a second lifecycle, scheduler, resource model, or public compiler API just to avoid extending an existing one.
