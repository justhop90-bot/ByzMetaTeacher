# Compiler Project State

Status: authoritative current-state guide for `main`.

Current compiler baseline: the `main` branch is the source of truth for accepted state. The exact commit SHA is the current tip of the repository's default branch.
Latest compiler verification: use the green `Compiler tests` workflow on `main`.

The latest verified compiler candidate reports **1,431 tests, OK**, with native zero-findings acceptance, the compiler verification gate, 9/9 native-support determinism jobs, and cross-platform snapshot comparison.

## What this project is

This is the AoE2DE `.per` compiler and its Byzantine-focused client.

The compiler's purpose is to distill community-native `.per` practice, documented engine semantics, and compiler policy into deterministic, auditable native `.per`.

It is not:

- a tournament bot;
- a runtime simulator;
- a universal scheduler or optimizer;
- a replacement native parser;
- a second general-purpose `.per` language;
- a reconstruction project for any legacy controller.

Legacy names may remain in code paths and fixtures for compatibility. They are not the project definition.

## Current compiler chain

```
source
  -> AST
  -> semantic demand/lifecycle analysis
  -> capability/provider projection
  -> persistent-control / SN / Timer / DUC / attack / escrow semantic contracts
  -> validated typed IR
  -> deterministic runtime binding
  -> native .per emission
  -> pinned aoe2-ai-parser zero-findings acceptance
  -> promoted artifact
```

Runtime execution and DE probing remain outside this static chain.

## Semantic doctrine

The compiler preserves:

```
DEMAND
  -> ADMISSIBILITY
  -> CAPABILITY
  -> FEASIBILITY
  -> ACTION
  -> WORLD-STATE WITNESS
  -> RELEASE
  -> RECOVERY
  -> REASSESSMENT
```

For recurrent/control-heavy community patterns, the operational reading is:

`OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT`

The following distinctions are hard invariants:

- `can-*` is permission/admission, not completion;
- native action issuance is not a witness;
- pending state is in-flight protection, not world proof;
- timers are cadence/control, not strategic truth;
- observations are evidence, not completion unless a typed witness contract says so;
- compiler-policy claims are not native engine conflict classes;
- unresolved native/runtime behavior remains OPEN/UNKNOWN.

## Current accepted layers

The accepted mainline currently includes:

- unified `CompilerSemanticProgram` aggregation;
- typed demand ownership and emitter-aligned state access analysis;
- capability/provider/admissibility/feasibility validation;
- deterministic resource/conflict validation;
- construction lifecycle and resource ownership;
- production lifecycle observations for provider readiness, queue capacity, provider availability, birth, queue exit, and pending-object protection;
- compiler-policy production/train arbitration through the existing ResourceClaim surface;
- research lifecycle and escrow claim semantics;
- typed Strategic Number semantics and persistent-control surfaces;
- typed Timer allocation and owner/release cleanup analysis;
- DUC SearchSession/TargetSession semantics and typed target identity/reacquisition state;
- downstream Byzantine strategy compilation of the existing NativeDucPlan channel;
- attack control observation and operational semantics;
- typed attack execution lifecycle;
- military composition proof assembly;
- source graph resolution and validation;
- deterministic runtime binding and native lowering;
- native zero-findings acceptance and cross-platform determinism.

## Evidence boundary

Evidence is classified as:

- ENGINE FACT;
- COMMUNITY PRACTICE;
- COMPILER POLICY;
- OPEN / UNKNOWN.

The compiler may adopt a static policy when it is explicitly labeled as policy.

It must not upgrade common community usage into an engine fact.

## Current frontier

The major generic execution substrates are largely present. The highest-value remaining compiler work is now behavioral synthesis on top of those substrates: Byzantine DUC discovery/target policy, full attack execution beyond issue-only attack-now, remaining escrow/resource arbitration, active SN evidence closure, Byzantine factual closure, and broad community strategy synthesis.

Production/train arbitration is closed as compiler policy. DUC runtime liveness, retained-filter behavior, group membership, output values, exact target lifetime, and attack completion/release remain OPEN unless independently proven.

## Roadmap

The authoritative remaining-gap roadmap is LearnerAI/Compiler/ROADMAP.md.

The latest MUSE community research synthesis is docs/research/2026-09-30-muse-community-gap-synthesis.md.

The roadmap is intentionally narrower than the historical gap matrix: it excludes already-closed substrate work and separates compiler implementation from runtime evidence acquisition.


The next compiler seam was the production/train arbitration boundary, now
closed as compiler policy (see `semantic/production_arbitration.py` and
`tests/test_production_arbitration.py` plus the
`tests/fixtures/production_arbitration.perdsl` native fixture).

The implemented contract is:

- ordinary `train` demands carry one compiler-policy production claim
  (`action-claim:TRAIN_ARBITRATION`) through the existing `ResourceClaim` /
  arbitration system; no native train conflict class was invented;
- strategy-bound demands normally arbitrate under their strategic identity;
  an explicit `production_arbitration_group` may intentionally group distinct
  strategic demands under one compatible execution-memory contract;
- claim ownership comes from the strategic owner when strategy-bound,
  otherwise the shared unit execution-memory owner (the `build` convention);
  the provider UnitId remains provider identity only;
- `can-train` remains admission/feasibility only;
- `train` remains action issuance only;
- `up-pending-objects` remains duplicate-queue protection;
- `unit-type-count-total` remains observation;
- provider readiness, provider availability, and queue capacity remain distinct;
- SN 264 remains a control input and never enters arbitration;
- exact DE busy/queue interaction, same-pass arbitration, starvation, provider loss, and queue timing remain OPEN pending runtime evidence;
- DUC-targeted training does not inherit ordinary train arbitration.

Runtime probes for this frontier are a separate evidence track. They do not become compiler guarantees merely because their fixture specifications are checked in.

## Where to work

Generic compiler code:

`LearnerAI/Compiler/`

Main orchestration:

`LearnerAI/Compiler/compiler.py`

Typed IR:

`LearnerAI/Compiler/ir/`

Semantic validators and projections:

`LearnerAI/Compiler/semantic/`

Native command primitives:

`LearnerAI/Compiler/primitives/`

Runtime binding:

`LearnerAI/Compiler/runtime_binding.py`

Emission:

`LearnerAI/Compiler/emitter/`

Focused tests:

`LearnerAI/Compiler/tests/`

Compiler architecture and contracts:

`LearnerAI/Compiler/README.md`

Implementation history:

`docs/plans/`

Research/evidence:

`docs/reference/`, `docs/research/`, and the current MUSE records.

## Verification commands

Local compiler regression:

```bash
PYTHONPATH=LearnerAI python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"
```

Native acceptance and cross-platform determinism are authoritative in GitHub Actions. Do not report local-only results as CI evidence.

## Current Git state

- default branch: `main`;
- candidate PR #266 carries the DUC strategy compilation channel on branch `duc-strategy-compilation-channel-2026-10-02` pending merge;
- open PRs on main remain authoritative from GitHub;
- mainline compiler CI: authoritative through the latest green `Compiler tests` workflow on `main`;
- the current-state document deliberately does not embed its own commit SHA or workflow number; GitHub's `main` ref and compiler workflow are the authoritative live pointers;
- the legacy validator no longer runs automatically on pushes or pull requests;
- the repository still contains many historical remote branches; they are not current work;
- merged and superseded branch variants should be retired rather than reused.

## Next repair discipline

The next repair should start from the existing DUC and attack substrates rather than reopening production arbitration:

1. write the failing strategy/behavior test first;
2. reuse existing typed DUC, ResourceClaim, AttackExecution, SN, Timer, escrow, and witness surfaces;
3. add only the smallest compiler-policy projection required by the community behavior;
4. preserve all OPEN/UNKNOWN runtime boundaries;
5. run focused tests, native acceptance, full compiler regression, 9/9 determinism, snapshot comparison, and compiler verification;
6. merge only after the exact candidate commit is green.

That is the state from which new compiler work should begin.
