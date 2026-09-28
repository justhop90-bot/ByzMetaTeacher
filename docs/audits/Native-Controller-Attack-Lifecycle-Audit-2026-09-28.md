# Native Controller / Attack Lifecycle Audit

Date: 2026-09-28
Implementation baseline: main, post-attack-lifecycle changes
Scope: typed issue-only `attack-now` lifecycle slice

## Source-to-artifact audit

| Edge | Status | Evidence |
| --- | --- | --- |
| `NativeAttackLifecyclePlan` -> IR export | CONNECTED | `LearnerAI/Compiler/ir/native_attack.py`, `ir/__init__.py` |
| IR -> dedicated binder | CONNECTED | `NativeSemanticBinder.bind_attack_plan()` |
| `attack-now` -> controller ownership | CONNECTED | `default_native_controller_catalog().resolve_surface(COMMAND, "attack-now")` -> `attack-group-control` |
| Native schema -> exact arity/kind | CONNECTED | dedicated attack binder + registry validation |
| Contracted mapping -> executable issue binding | CONNECTED | `attack.execution.issue`, `NativeAttackSemanticBinding` |
| Binder -> emitter | CONNECTED | `registry.validate_attack_plan()` precedes attack-plan lowering |
| Compiler entry points -> emitter | CONNECTED | source/package/demand/file compile APIs carry `attack_plan` |
| Emitter -> staged artifact | CONNECTED | attack rules are emitted into the same final artifact passed to existing staged validation |
| Staged artifact -> native validator | CONNECTED | existing native promotion path; dedicated `assert_attack_native.py` uses pinned parser |
| Equivalent plan -> deterministic bytes | CONNECTED | duplicate compilation is asserted by the acceptance fixture |
| Generic Action promotion -> `attack-now` | FUNCTIONALLY-DISCONNECTED | no `Primitive` adapter is added; generic `bind()` remains fail-closed |
| Evidence-only controller interactions -> emitted prerequisites | FUNCTIONALLY-DISCONNECTED | no exploration/town-size/attack-SN interaction is lowered by the attack emitter |
| Completion witness | UNFINISHED | `COMPLETION_UNOBSERVED`; no native completion signal is claimed |
| Release semantics | UNFINISHED | no release transition or reset is emitted |
| Group membership/admission semantics | UNFED | exact mediated group behavior remains an explicit native unknown |
| Runtime attack-success behavior | UNFED | no runtime simulation or behavioral claim is added |

## Negative-space audit

The executable attack slice does not promote:

- `sn-number-attack-groups`
- `sn-percent-attack-soldiers`
- exploration Strategic Numbers
- town-size/response-distance Strategic Numbers
- DUC search/target operations
- `up-reset-attack-now`
- timer predicates as completion proof
- synthetic `set-goal` completion/release state
- strategy-layer generation

The descriptive controller and interaction catalogs remain evidence-bearing. Their evidence-only status is not weakened to make this tranche executable.

## Artifact gates

Required artifact checks are implemented in:

- `LearnerAI/Compiler/tests/assert_attack_native.py`
- `LearnerAI/Compiler/tests/test_native_attack_lifecycle.py`
- `LearnerAI/Compiler/tests/test_compiler_native_integration.py`
- `.github/workflows/compiler-tests.yml`

The acceptance fixture requires byte-identical duplicate compilation and invokes the pinned `aoe2_ai_lab lint --profile default --json` gate, requiring `finding_count == 0` and `findings == []`.

## Verification status

Static repository audit: complete.

Local runtime test execution is not available in the current execution container because the repository itself is not mounted and outbound GitHub network access is unavailable. Native/compiler execution evidence must therefore come from the repository's CI environment. A temporary pull-request verification probe is used only to execute the existing CI job against the already-implemented main state; the implementation itself remains on `main`.
