# Compiler Project State

Status: authoritative current-state guide for `main`.

Verified main: `6bb30a09faf270f821821610a29d7d2aef3c607f`  
Latest compiler CI: workflow `#2664` on 2026-09-30, green.

The workflow completed the compiler test job, native zero-findings acceptance, compiler verification gate, 9/9 native-support determinism jobs, and cross-platform snapshot comparison. The full compiler regression suite reported **1,212 tests, OK**.

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
- research lifecycle and escrow claim semantics;
- typed Strategic Number semantics and persistent-control surfaces;
- typed Timer allocation and owner/release cleanup analysis;
- DUC SearchSession/TargetSession semantics and typed target identity/reacquisition state;
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

## Current open frontier

The next compiler seam is the production/train arbitration boundary.

The goal is to connect existing production lifecycle semantics to the existing `ResourceClaim` / arbitration system without inventing a native train conflict class.

The intended contract is:

- ordinary `train` demands may carry a compiler-policy production claim;
- claim ownership comes from the semantic/strategic owner, not a provider UnitId;
- `can-train` remains admission/feasibility only;
- `train` remains action issuance only;
- `up-pending-objects` remains duplicate-queue protection;
- `unit-type-count-total` remains observation;
- provider readiness, provider availability, and queue capacity remain distinct;
- SN 264 remains a control input;
- exact DE busy/queue interaction, same-pass arbitration, starvation, provider loss, and queue timing remain OPEN pending runtime evidence;
- DUC-targeted training must not inherit ordinary train arbitration accidentally.

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
- open PRs at the state snapshot: none;
- mainline compiler CI: green at the verified commit;
- the repository still contains many historical remote branches; they are not current work;
- merged and superseded branch variants should be retired rather than reused.

## Next repair discipline

The next repair should:

1. cross-reference the existing production lifecycle and `ResourceClaim` interfaces;
2. write the failing arbitration tests first;
3. implement the smallest policy projection that closes the seam;
4. prove deterministic ownership and conflict behavior;
5. preserve all existing OPEN/UNKNOWN boundaries;
6. run focused tests, native acceptance, full compiler regression, 9/9 determinism, snapshot comparison, and compiler verification;
7. merge to `main` only after the exact candidate commit is green.

That is the state from which new compiler work should begin.
