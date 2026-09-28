# Native Escrow Release Lowering Audit — 2026-09-28

Verified main: `adec462b420f87bc66c2868908058c0e272baf7c`
Prior implementation commits: `36db86d9d4522d2902a1c234fd5606b136751103` and `63866c6ca2edf9ab3a85ee197f5e31eede824f0b`
Compiler CI: run #2036 / Actions run `36481020162`
Native parser pin: `3dfa2583b7c2ec36b85ccb421ebd0abe9ff276ba`

## Scope

This tranche promotes only the classic DE `release-escrow` Action. It does not promote percentage policy mutation, UP escrow commands, starvation recovery, ownership handoff, or same-pass coupling to a following ordinary action.

## Native and community cross-reference

Repository-native command reference records:

- `docs/reference/engine/commands/release-escrow.md`: Action - Economy; syntax `(release-escrow <Resource>)`; one input `Resource` constant; domain food/wood/stone/gold; mutation transfers the named escrow balance to the normal stockpile and zeros that escrow balance.
- AIRef: `https://airef.github.io/commands/commands-details.html#release-escrow`
- Community corroboration: JackkelDragon AoE2DE_AIBuilder `builder upgrades.per` uses escrow-aware feasibility followed by `release-escrow` before ordinary research/build-upgrade actions.
- Independent corpus corroboration: Andygmb AoE2 AI script corpus contains the same release-before-consume pattern.
- UserPatch escrow-state reference distinguishes escrow-included and escrow-deducted resource views; this tranche deliberately does not lower those additional policy surfaces.

Community evidence establishes executable practice. It is not used as a substitute for native command typing or the still-open DE same-pass proof.

## Implementation chain

| Stage | Module | Status |
|---|---|---|
| Typed IR | `LearnerAI/Compiler/ir/resource_control.py` | CONNECTED |
| Semantic validation | `LearnerAI/Compiler/semantic/resource_control.py` | CONNECTED |
| Public compiler forwarding | `LearnerAI/Compiler/compiler.py` | CONNECTED across six public paths |
| Native binder | `LearnerAI/Compiler/primitives/native_binder.py` | CONNECTED; exact Action/Resource schema |
| Engine mapping | `LearnerAI/Compiler/primitives/engine_semantics.py` | CONNECTED; `escrow.execution.release` |
| Registry promotion | `LearnerAI/Compiler/primitives/registry.py` | CONNECTED; dedicated inventory + resource-domain validation |
| Emission | `LearnerAI/Compiler/emitter/per.py` | CONNECTED; deterministic rule grouping |
| Source fixture | `LearnerAI/Compiler/tests/fixtures/escrow_release.perdsl` | CONNECTED |
| Native acceptance | `LearnerAI/Compiler/tests/assert_escrow_native.py` | CONNECTED; artifact determinism + zero findings |
| Regression coverage | dedicated tests + semantic inventory regression | CONNECTED |

## Deterministic emission

The plan is already required to be ordered by:
`(rule_order, within_rule_order, contract_identity)`.

Emission groups operations by `rule_order`. Within a rule, release actions retain their declared order. The acceptance fixture emits:

```
; Native escrow release rule: 400
(defrule
    (true)
=>
    (release-escrow food)
    (release-escrow gold)
)

; Native escrow release rule: 401
(defrule
    (true)
=>
    (release-escrow wood)
)
```

The acceptance harness compiles the same source and typed plan twice and requires byte-identical output.

## Verification evidence

The final Compiler CI run passed:

- Native escrow release artifact gate: `finding_count=0`, `findings=[]`.
- Escrow artifact SHA-256: `7bfea09bd313323aaaf8bd82972eb51042453adb76256e810f56ab1e9bc9ab27`.
- Compiler regression: **922 tests, OK**.
- Focused persistent-state suites: all passed.
- Native-support determinism: all 9 OS/Python combinations passed.
- Cross-platform snapshot comparison: passed.
- Aggregate Compiler verification gate: passed.

Two implementation defects were found and repaired during audit rather than hidden:
1. The first promotion left `release-escrow` out of `default_de_registry()`'s exact executable inventory, causing fail-closed registry construction. Fixed in `63866c6c...`.
2. The first acceptance harness resolved the fixture from `LearnerAI/tests/fixtures` instead of `LearnerAI/Compiler/tests/fixtures`. Fixed in `5475bf9...`.
A pre-existing exact semantic-mapping inventory test then correctly surfaced the new promoted command and was updated in `adec462b...` to use the dedicated escrow executable inventory.

## Hostile audit

**CONNECTED:** IR → semantic validation → compiler forwarding → dedicated binder → engine mapping → registry admission → deterministic emitter → source fixture → native parser.

**DEAD-END:** none inside the promoted release-only path.

**BLOCKED / OPEN:** same-pass visibility of `release-escrow -> ordinary action`; starvation/emergency release; multi-owner handoff; UP escrow mutation; research in-progress/resource-provider interaction.

**NOT CLAIMED:** the compiler does not infer escrow ownership from the native stockpile, does not treat percentage zero as release, does not synthesize policy reset, and does not claim a completion witness for the native mutation itself.

**Source-order / emission audit:** release operations are explicitly ordered in typed IR; no hidden source-order dependence is introduced. The emitter's existing global artifact/rule/line budgets remain authoritative.

**Retry/open-loop audit:** no retry loop, scheduler, or automatic reassertion was added. `release-escrow` is a one-shot mutation supplied by an already validated plan.

**Promotion-state audit:** `NATIVE_KNOWN -> NATIVE_TYPED -> SEMANTICALLY_ADAPTED -> ENGINE_SEMANTICS_MAPPED -> EXECUTABLE_SAFE` is enforced through dedicated escrow binding. Wrong command, wrong Action kind, wrong arity, wrong parameter name/type/direction, missing mapping, or out-of-domain resource fails closed.

## Result

The release-only escrow lowering slice is **executable-safe and native-verified on main**. The escrow family is not lifecycle-complete; the remaining open items are intentionally preserved as native/runtime research questions rather than smuggled into compiler policy.

The next escrow work should therefore be driven by closure of a specific open engine fact, not by adding more escrow syntax or a resource scheduler.
