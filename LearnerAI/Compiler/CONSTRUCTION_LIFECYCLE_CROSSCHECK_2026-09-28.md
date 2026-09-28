# Construction Lifecycle Cross-Check and Implementation Checklist — 2026-09-28

Status legend: `[x]` verified; `[~]` partially implemented but not fully connected/verified; `[ ]` unfinished or blocked. Status labels identify the specific failure mode where relevant.

## Evidence cross-check

- [x] AIRef/UserPatch identifies `up-pending-objects` as a comparison Fact over pending build/train work.
- [x] AIRef/UserPatch identifies `up-pending-placement` as a Boolean Fact that is true while native placement is attempting to place the requested building.
- [x] UserPatch later repaired simultaneous-building behavior for `up-pending-placement`; the compiler may therefore use it as a native placement witness for the supported UP/DE contract.
- [x] `up-pending-placement` syntax is exactly `(up-pending-placement <typeOp> <BuildingId>)`; it has no comparison operator or numeric threshold.
- [x] `up-pending-objects` syntax is comparator-based and reports pending construction/production work.
- [x] `building-type-count` is the completed-world-state witness used by the existing compiler.
- [x] Community build rules pair `can-build` with `up-pending-objects` to suppress duplicate build requests.
- [x] Community scripts configure builder counts with `up-assign-builders`; this is persistent native builder policy, not the per-pass build mutex.
- [x] UserPatch documents one successful `build`/`up-build` per AI rule pass; later build commands silently fail.
- [x] UserPatch documents `up-reset-placement` as clearing placement requests that are blocked without a foundation.
- [x] Pending state is not completion and action issuance is not completion.

## Semantic rules to implement

- [x] Preserve generic lifecycle states: `ACTIVE -> ISSUED -> PENDING -> COMPLETE`.
- [~] [FUNCTIONALLY-DISCONNECTED] Add typed construction phase beneath `PENDING`: `NONE`, `PLACEMENT_PENDING`, `FOUNDATION_PENDING`, `COMPLETE`; the IR and pure transition function exist, but the transition model is not the executable lowering source.
- [~] [PARTIAL] Enforce observation precedence: invalidation, COMPLETE, FOUNDATION_PENDING, PLACEMENT_PENDING, retry; the emitter reproduces this order, but the typed transition function is not wired into lowering and same-pass behavior is not yet covered.
- [ ] [UNFINISHED] COMPLETE must be canonically witnessed by `building-type-count` for the requested `BuildingId`; the current implementation accepts the demand's arbitrary `witness` expression.
- [x] FOUNDATION_PENDING witnesses `up-pending-objects`; it is not completion.
- [x] PLACEMENT_PENDING witnesses `up-pending-placement`; it is not completion.
- [~] [OPEN-LOOP] Retry requires completion false, pending-objects zero, and pending-placement false and returns the demand to `ACTIVE`; the subsequent action-issuance rule can observe that new `ACTIVE` state in the same pass, so the later-pass-only retry contract is not yet enforced.
- [x] Retry does not create a new demand identity or retry counter.
- [x] BUILD_PASS_SINGLETON remains a separate transient rule-pass exclusion.
- [~] [PARTIAL] Placement pending suppresses a new build request while the native placement witness remains true, but same-pass retry/reissue behavior is not yet closed.
- [~] [PARTIAL] Construction completion may be observed directly from ISSUED or PENDING; the emitter does so, but canonical construction-witness enforcement is still missing.
- [x] Resource arbitration/escrow ownership is untouched by construction phase observation.

## Compiler implementation

- [x] Add executable native adapter for `up-pending-placement`.
- [x] Add contracted engine-semantic mapping for `up-pending-placement`.
- [~] [FUNCTIONALLY-DISCONNECTED] Add typed construction IR and deterministic transition function; the implementation exists in `ir/construction.py` and `semantic/construction.py`, but executable lowering does not call the transition function.
- [x] Attach construction lifecycle metadata to `build` demands.
- [x] Emit construction-specific observation rules instead of unconditional `ISSUED -> PENDING` for build demands.
- [~] [OPEN-LOOP] Emit retry guards using both pending facts; the guards are present, but same-pass Goal visibility allows retry to fall through into the issuance rule in the same pass.
- [x] Preserve existing generic lifecycle behavior for train/research/non-construction actions.
- [ ] [BLOCKED] Add a native zero-findings fixture covering all construction phase predicates. The fixture exists, but the latest native gate reports 7 `undefined-constant` findings for `c: <BuildingId>` operands such as `castle`.
- [ ] [BLOCKED] Define and validate native `ObjectId` typing/binding for `c: <BuildingId>` operands, including the binding path used by `up-pending-objects` and `up-pending-placement`; do not silence the native validator warnings.
- [ ] [UNFINISHED] Enforce the canonical build-completion witness at semantic analysis time and reject a build demand whose witness is not a `building-type-count` observation for its own target.
- [ ] [FUNCTIONALLY-DISCONNECTED] Wire `transition_construction()` into executable semantic lowering/emission, or explicitly replace it with a single shared transition representation consumed by both.
- [ ] [OPEN-LOOP] Define the intended same-pass retry behavior and enforce the chosen contract. The current rule order permits RETRY to write ACTIVE and a later ACTION ISSUANCE rule to observe ACTIVE in the same pass.
- [ ] [UNFINISHED] Add order-sensitive emitter regression coverage asserting COMPLETE > FOUNDATION_PENDING > PLACEMENT_PENDING > RETRY > ACTION ISSUANCE and explicitly testing same-pass Goal visibility.
- [ ] [x] Keep `up-build`, builder allocation, controlled placement policy, and `up-reset-placement` as the next execution-control surface; do not silently invent them in the phase-observation tranche.

## AIRef and community cross-reference implementation checklist

- [x] `build` remains gated by native feasibility (`can-build`/`up-can-build`) before action issuance; the compiler does not treat the action itself as feasibility.
- [x] `up-pending-objects` is used as the native duplicate-construction/queue-state witness; community scripts use the same comparison pattern.
- [x] `up-pending-placement` is modeled as a Boolean placement-attempt witness with no invented comparator or numeric threshold.
- [x] Completed construction is separated from queue/placement state and witnessed by completed building world state.
- [x] Native `BuildingId` operands for construction Facts are bound from the checked-in engine catalog and emitted numerically, matching the native typed `c:` operand contract.
- [x] Builder assignment remains outside the lifecycle demand state; community `up-assign-builders` usage is treated as execution policy rather than persistent demand ownership.
- [x] The one-success-per-rule-pass `build` constraint is treated as a native pass constraint, not as a persistent construction lock.
- [x] Retry preserves the original demand identity and uses a per-pass execution-memory barrier instead of a retry counter or replacement scheduler.
- [~] Controlled placement (`up-build`, placement data, `up-reset-placement`) remains a separate execution-control surface; it is cross-referenced but intentionally not invented in this observation tranche.
- [~] Community examples often use named `c: castle`/`c: house` operands; the compiler's native gate requires typed binding, so the implementation emits the resolved numeric BuildingId rather than silencing identifier findings.

Evidence basis:
- Checked-in AIRef command schema: `docs/reference/inventories/airef-command-schema.json`.
- Checked-in engine catalog: `docs/reference/engine/catalog/build.md`, `castle.md`, `blacksmith.md`, and related building symbol pages.
- Checked-in AIRef object inventory: `docs/reference/inventories/airef-object-inventory.json`.
- Community `.per` precedent: `Promi/dawn.per`, `LSR.per`, `Castles.per`, and existing repository construction/validator notes.

## Acceptance criteria and verification commands for open construction items

### 1. Native `ObjectId` typing/binding

Status may change from `[ ] [BLOCKED]` to `[x]` only when all of the following are true:
- The semantic/native binding path represents `up-pending-objects` `ObjectId` and `up-pending-placement` `BuildingId` as the correct native object domain, rather than emitting unresolved symbolic names directly into `c:` operands.
- A build target such as `castle` has one deterministic canonical native representation in the emitted `.per`, and the pinned native parser accepts it without `undefined-constant`, operand-domain, or parameter-shape findings.
- The same canonicalization path is used by both construction Facts.
- A negative fixture proves that an unresolved or wrong-domain identifier fails closed during semantic validation.

Local verification:

```text
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"
python LearnerAI/Compiler/tests/assert_native_zero.py /tmp/construction-lifecycle.per --report /tmp/native-reports/construction-lifecycle.json
```

Expected evidence: zero focused-test failures; `finding_count: 0`; `findings: []`; no `undefined-constant` findings.

CI closure evidence:
- `Compiler tests + native zero-findings` is SUCCESS.
- `native-reports/construction-lifecycle.json` exists in the `native-validation-evidence` artifact and contains zero findings.
- `compiler-verification-log` exists and is green.
- `Compare native-support snapshots` is SUCCESS.
- `Compiler verification gate` reports PASSED.

### 2. Canonical build-completion witness enforcement

Status may change from `[ ] [UNFINISHED]` to `[x]` only when semantic analysis rejects any `build B` demand whose completion witness is not the canonical completed-world-state observation for the same `B`.

Required acceptance cases:
- Valid: `action (build castle)` with `witness (building-type-count castle > 0)`.
- Invalid target: `action (build castle)` with `witness (building-type-count town-center > 0)`.
- Invalid witness family: a unit-count or research-status witness.
- Invalid shape: a witness that cannot establish completed presence of the requested building type.
- Emission uses the canonical build witness derived from the build target, not an arbitrary client witness.

Local verification:

```text
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"
```

Expected evidence: explicit accept/reject coverage for all four invalid/valid categories and zero full-suite failures.

CI closure evidence:
- Construction acceptance/rejection cases are present in `compiler-verification-log`.
- Generic train/research lifecycle tests remain green.
- Construction native zero-findings remains zero.
- Verification gate SUCCESS.

### 3. Transition-model wiring

Status may change from `[ ] [FUNCTIONALLY-DISCONNECTED]` to `[x]` only when the typed transition model is the single executable semantic source for construction transitions.

Acceptance criteria:
- `transition_construction()` or a replacement shared transition representation is invoked by the semantic lowering path that produces construction lifecycle rules.
- The emitter no longer independently redefines the construction state machine.
- Changing the canonical transition table/order changes the emitted construction rule plan through the shared path.
- Tests prove parity between semantic transition states and emitted rules for COMPLETE, FOUNDATION_PENDING, PLACEMENT_PENDING, and RETRY.

Local verification:

```text
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "ConstructionTransition"
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"
```

Expected evidence: an integration test that exercises lowering, not merely unit coverage of the pure transition function.

CI closure evidence:
- Construction transition integration tests execute in the normal compiler regression suite.
- Static review shows no duplicated construction transition implementation in the emitter.
- Construction native fixture passes zero-findings.
- Cross-platform native-support determinism remains SUCCESS.
- Verification gate SUCCESS.

### 4. Same-pass retry behavior

Status may change from `[ ] [OPEN-LOOP]` to `[x]` only after the compiler explicitly chooses and enforces one native rule-pass contract.

Preferred closure contract:
- RETRY may restore the demand to `ACTIVE`, but the same pass must not subsequently issue the build again.
- The next legal build issuance occurs only on a later rule pass.
- The implementation uses existing engine-native rule ordering/state behavior, not a new scheduler or synthetic retry counter.

Required acceptance cases:
- PENDING plus no completion plus no pending foundation plus no pending placement causes exactly one transition to ACTIVE.
- The same pass cannot execute `build B` after that retry transition.
- The next pass may execute `build B` when all admission guards are true.
- PLACEMENT_PENDING and FOUNDATION_PENDING never fall through into same-pass reissue.
- Retry preserves demand identity, strategic binding, target, resource-control binding, and witness identity.

Local verification:

```text
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "RuleExecutionSemantics"
```

Expected evidence: an actual same-pass Goal-visibility regression, not merely emitted-string inspection.

CI closure evidence:
- Focused rule-execution suite passes.
- Construction regression logs show explicit same-pass retry coverage.
- The emitted fixture plus execution-model test prove no RETRY -> ACTIVE -> BUILD execution within one simulated pass.
- Native zero-findings remains zero.
- Full verification gate SUCCESS.

### 5. Order-sensitive emitter regression tests

Status may change from `[ ] [UNFINISHED]` to `[x]` only when emitted construction rules have an explicit tested order tied to the chosen same-pass retry contract.

Acceptance criteria:
- Invalidation is emitted before construction observation rules.
- COMPLETE cannot be shadowed by FOUNDATION_PENDING or PLACEMENT_PENDING when the completion witness is true.
- FOUNDATION_PENDING precedes PLACEMENT_PENDING.
- RETRY is ordered consistently with the selected same-pass policy; the test must not assume RETRY-before-ISSUANCE is safe when same-pass Goal writes are visible.
- ACTION ISSUANCE is positioned so unintended same-pass reissue is impossible under the selected policy.
- The test checks exact rule ordering, not merely the presence of comments or substrings.
- No generic `ISSUED -> PENDING` rule exists for a build demand.

Local verification:

```text
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"
python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"
```

Expected evidence: an order-sensitive regression fails when rule order is perturbed and passes only with the selected ordering.

CI closure evidence:
- Order-sensitive construction tests pass in `compiler-verification-log`.
- `assert_generated_fixture_reproducible.py` passes for the checked-in generated fixture.
- Construction native zero-findings reports zero findings.
- All nine native-support determinism jobs and the snapshot comparison pass.
- Final verification gate reports SUCCESS.
## Evidence navigation

- **Latest compiler Actions run:** [Compiler tests #1888](https://github.com/justhop90-bot/ByzMetaTeacher/actions/runs/36391762532) for head `29a164bc554e71e53016aa0027fe1d5dd4f0f293` — **FAILED** at `Verify generic compiler fixture reproducibility`; construction native zero-findings and compiler regression steps were skipped. Workflow definition: [`.github/workflows/compiler-tests.yml`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/.github/workflows/compiler-tests.yml).
- **Native zero-findings result:** not published by #1888. The construction native zero-findings step was skipped because generic `CompilerFixture.per` reproducibility failed first. Expected artifact path remains `native-validation-evidence/native-reports/construction-lifecycle.json`; expected fields remain `finding_count: 0`, `findings: []`.
- **Compiler verification log:** [artifact 10956756270](https://github.com/justhop90-bot/ByzMetaTeacher/actions/runs/36391762532/artifacts/10956756270), expected path `compiler-verification-log/compiler-tests.log`. The artifact is published but empty, so it is not substantive verification evidence.
- **Five implementation checks:**
  - **1. Native ObjectId typing/binding:** [`semantic/native_building_catalog.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/native_building_catalog.py), [`semantic/analyzer.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/analyzer.py), [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py).
  - **2. Canonical build-completion witness:** [`semantic/construction.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/construction.py), [`semantic/analyzer.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/analyzer.py), [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py).
  - **3. Transition-model wiring:** [`ir/construction.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/ir/construction.py), [`semantic/construction.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/construction.py), [`emitter/per.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/emitter/per.py), [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py).
  - **4. Same-pass retry behavior:** [`ir/model.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/ir/model.py), [`semantic/analyzer.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/analyzer.py), [`emitter/per.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/emitter/per.py), [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py), [`tests/test_rule_execution.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_rule_execution.py).
  - **5. Order-sensitive emitter regression:** [`emitter/per.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/emitter/per.py), [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py), [`generated/CompilerFixture.per`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/generated/CompilerFixture.per).
## Compact verification matrix

| Open item | Acceptance criterion | Local verification | Expected compiler evidence | CI job / evidence | Final evidence required | Closure status |
|---|---|---|---|---|---|---|
| Native `ObjectId` typing/binding | `c: <BuildingId>` resolves through one typed native binding path; unresolved/wrong-domain identifiers fail closed; construction facts emit parser-valid operands. | `LearnerAI/Compiler/tests/test_construction_lifecycle.py` via `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"`; native gate: `python LearnerAI/Compiler/tests/assert_native_zero.py /tmp/construction-lifecycle.per --report /tmp/native-reports/construction-lifecycle.json` | Focused construction tests pass; `/tmp/native-reports/construction-lifecycle.json` has `finding_count: 0` and no `undefined-constant` findings. | Job `test` step `Native zero-findings acceptance - construction lifecycle fixture`; artifact `native-validation-evidence/native-reports/construction-lifecycle.json`; log artifact `compiler-verification-log/compiler-tests.log`; gate `verification-gate`. | Test: `LearnerAI/Compiler/tests/test_construction_lifecycle.py`; compiler log: `compiler-verification-log/compiler-tests.log`; CI report: `native-validation-evidence/native-reports/construction-lifecycle.json`. | `[~] IMPLEMENTED; CI UNVERIFIED` pending native zero-findings and final Actions evidence. |
| Canonical build-completion witness | Every `build B` demand completes only from `building-type-count B`; mismatched target, witness family, or witness shape is rejected. | `LearnerAI/Compiler/tests/test_construction_lifecycle.py` via `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"`; full suite via `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"` | Explicit valid/invalid witness tests pass; emitter uses target-derived completion witness; non-construction lifecycle tests remain green. | Job `test`; log artifact `compiler-verification-log/compiler-tests.log`; native construction report `native-validation-evidence/native-reports/construction-lifecycle.json`; gate `verification-gate`. | Test: `LearnerAI/Compiler/tests/test_construction_lifecycle.py`; compiler log: `compiler-verification-log/compiler-tests.log`; CI artifact: `native-validation-evidence/native-reports/construction-lifecycle.json`. | `[~] IMPLEMENTED; CI UNVERIFIED` pending acceptance/rejection and full-suite evidence. |
| Transition-model wiring | The typed construction transition model is the single executable semantic source; emitter does not maintain a second state machine. | `LearnerAI/Compiler/tests/test_construction_lifecycle.py` via `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "ConstructionTransition"` plus `-k "Construction"` | Integration test proves lowering consumes canonical transition data and emitted rules match COMPLETE > FOUNDATION_PENDING > PLACEMENT_PENDING > RETRY. | Job `test`; log artifact `compiler-verification-log/compiler-tests.log`; construction native report `native-validation-evidence/native-reports/construction-lifecycle.json`; determinism jobs `cross-platform-native-support` and `compare-cross-platform-native-support`; gate `verification-gate`. | Test: `LearnerAI/Compiler/tests/test_construction_lifecycle.py`; compiler log: `compiler-verification-log/compiler-tests.log`; CI artifacts: `native-validation-evidence/native-reports/construction-lifecycle.json` and `native-support-replay-*`; gate summary: `Compiler verification gate`. | `[~] IMPLEMENTED; CI UNVERIFIED` pending integration and determinism evidence. |
| Same-pass retry behavior | RETRY restores `ACTIVE` without same-pass `build`; later-pass reissue remains legal; pending foundation/placement never falls through; identity/bindings are preserved. | `LearnerAI/Compiler/tests/test_construction_lifecycle.py` plus `LearnerAI/Compiler/tests/test_rule_execution.py`; run `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"` and `... -k "RuleExecutionSemantics"` | Actual execution-model regression demonstrates no RETRY -> ACTIVE -> BUILD in one pass and successful reissue on a later pass. | Job `test`; focused log artifact `focused-persistent-state-verification-log/focused-persistent-state-tests.log`; full log `compiler-verification-log/compiler-tests.log`; native construction report; gate `verification-gate`. | Tests: `LearnerAI/Compiler/tests/test_construction_lifecycle.py`, `LearnerAI/Compiler/tests/test_rule_execution.py`; logs: `focused-persistent-state-verification-log/focused-persistent-state-tests.log`, `compiler-verification-log/compiler-tests.log`; CI report: `native-validation-evidence/native-reports/construction-lifecycle.json`. | `[~] IMPLEMENTED; CI UNVERIFIED` pending rule-execution evidence. |
| Order-sensitive emitter regression | Exact construction rule order is tested; invalidation precedes observation; COMPLETE > FOUNDATION_PENDING > PLACEMENT_PENDING > RETRY; issuance placement prevents unintended same-pass reissue; no generic build `ISSUED -> PENDING`. | `LearnerAI/Compiler/tests/test_construction_lifecycle.py` via `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py" -k "Construction"`; full suite via `python -m unittest discover -s LearnerAI/Compiler/tests -p "test_*.py"` | Perturbing rule order makes the focused test fail; intended ordering passes; generated fixture remains reproducible. | Job `test`; step `Verify generic compiler fixture reproducibility`; artifact `compiler-verification-log/compiler-tests.log`; native report `native-validation-evidence/native-reports/construction-lifecycle.json`; nine `cross-platform-native-support` artifacts plus `compare-cross-platform-native-support`; gate `verification-gate`. | Test: `LearnerAI/Compiler/tests/test_construction_lifecycle.py`; compiler log: `compiler-verification-log/compiler-tests.log`; CI artifacts: `native-validation-evidence/native-reports/construction-lifecycle.json`, `native-support-replay-*`; reproducibility command output is part of the job log. | `[~] IMPLEMENTED; CI UNVERIFIED` pending regression and fixture reproducibility evidence. |

## Compact artifact index

| Artifact | Direct link / path | Availability/status | Last checked |
|---|---|---|---|
| Latest compiler Actions run #1888 | [GitHub Actions run 1888](https://github.com/justhop90-bot/ByzMetaTeacher/actions/runs/36391762532) | **failed** at generic `CompilerFixture.per` reproducibility; construction/native checks skipped | commit `29a164bc554e71e53016aa0027fe1d5dd4f0f293`, run #1888 (`36391762532`) |
| Native zero-findings report | `native-validation-evidence/native-reports/construction-lifecycle.json` | **not published**; construction native zero-findings step was skipped | run #1888 (`36391762532`) |
| Compiler verification log | [artifact 10956756270](https://github.com/justhop90-bot/ByzMetaTeacher/actions/runs/36391762532/artifacts/10956756270) / `compiler-verification-log/compiler-tests.log` | **published but empty**; no substantive verification evidence | run #1888 (`36391762532`) |
| 1. Native ObjectId binding | [`semantic/native_building_catalog.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/native_building_catalog.py) + [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py) | **published**; not CI-verified because the latest compiler run failed before construction checks | commit `29a164bc554e71e53016aa0027fe1d5dd4f0f293`, run #1888 |
| 2. Canonical build witness | [`semantic/construction.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/construction.py) + [`semantic/analyzer.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/semantic/analyzer.py) | **published**; not CI-verified because the latest compiler run failed before construction checks | commit `29a164bc554e71e53016aa0027fe1d5dd4f0f293`, run #1888 |
| 3. Transition-model wiring | [`ir/construction.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/ir/construction.py) + [`emitter/per.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/emitter/per.py) | **published**; not CI-verified because the latest compiler run failed before construction checks | commit `29a164bc554e71e53016aa0027fe1d5dd4f0f293`, run #1888 |
| 4. Same-pass retry | [`ir/model.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/ir/model.py) + [`emitter/per.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/emitter/per.py) + [`tests/test_rule_execution.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_rule_execution.py) | **published**; not CI-verified because the latest compiler run failed before construction checks | commit `29a164bc554e71e53016aa0027fe1d5dd4f0f293`, run #1888 |
| 5. Order-sensitive emitter regression | [`tests/test_construction_lifecycle.py`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/tests/test_construction_lifecycle.py) + [`generated/CompilerFixture.per`](https://github.com/justhop90-bot/ByzMetaTeacher/blob/compiler-construction-lifecycle-final-verify/LearnerAI/Compiler/generated/CompilerFixture.per) | **published**; not CI-verified because the latest compiler run failed before construction checks | commit `29a164bc554e71e53016aa0027fe1d5dd4f0f293`, run #1888 |
## Explicit non-goals

- [x] Do not model a numeric construction-progress percentage; current documented ObjectData progress values describe training/research, not generic building construction.
- [x] Do not treat builder allocation as a strategic demand.
- [x] Do not reuse BUILD_PASS_SINGLETON as persistent construction ownership.
- [x] Do not infer foundation existence from the build action itself.
- [x] Do not infer completion from timing or from pending-state disappearance alone.

## Validation-order invariant

For build demands, generic completion-witness validation runs before construction-specific witness canonicalization. This preserves the existing WIT-002/WIT-003/WIT-004 diagnostics for timing evidence, non-completion observations, and action coupling. Only a generically valid witness is then canonicalized to completed building presence and attached to the construction lifecycle contract.
