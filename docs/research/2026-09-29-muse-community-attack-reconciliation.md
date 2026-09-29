# MUSE + Community Attack/DUC Cross-Reference — 2026-09-29

## Scope
This reconciliation cross-checks the checked-in MUSE forensic package against current compiler main, direct community `.per` sources, current AoE2 modding documentation, and an official World's Edge update note.

Research rule remains strict:
- `[E]` engine/official evidence.
- `[C]` community implementation practice.
- `[I]` compiler-safe inference.
- Community repetition does not promote a native semantic.
- DE runtime claims remain OPEN unless directly proven.

## Cross-reference results

| Finding | MUSE position | Community / official cross-check | Revised compiler disposition |
|---|---|---|---|
| Three non-DUC attack mechanisms | attack-now / attack-groups / town-size attack are distinct mechanisms | AoE forum explicitly documents all three and their different land/naval behavior | `[C][E]` mechanism distinction is reliable; keep mode separation in IR |
| `attack-now` itself | executable issue slice; target/controller semantics open | Community scripts use `(attack-now)` without a preceding DUC target; official update notes discuss behavior of attack-now/attack-groups | `AttackExecution.target` must be optional for `ATTACK_NOW`; do not require DUC target |
| Attack-groups | native controller surface driven by strategic numbers; semantics open in compiler | Community evidence shows `sn-number-attack-groups` starts attack groups; separate attack window control exists | Keep `ATTACK_GROUPS` typed but non-executable in generic compiler |
| Town-size attack | native town-size targeting/controller surface | Community documents `sn-maximum-town-size` as the control surface; Duke changes it for attack | Keep `TOWN_SIZE_ATTACK` typed but non-executable; target is controller-owned |
| Exploratory requirement | MUSE says attack targeting is exploration-mediated but does not claim executable coupling | Community attack examples set at least one explore group; official behavior is consistent with explored-object targeting | Keep exploration→attack relationship evidence-only |
| DUC target acquisition | MUSE has a strong SearchSession/TargetSession model | Community examples chain reset/search/filter/target/get-point operations | `AttackTargetRef` is valid as an optional semantic binding for DUC-targeted execution, not a prerequisite to native attack-now |
| Target invalidation | MUSE models STALE/UNKNOWN and generation/provenance transitions | Community DUC examples mutate search state before target use; no reliable community proof establishes native object liveness after every mutation | Compiler may fail closed on STALE/UNKNOWN for DUC-dependent execution; runtime liveness remains OPEN |
| Attack preparation/regroup | MUSE/Duke research describes preparation and regrouping | Duke `attack.per` explicitly has READY → PREPARING → PULLING-TROOPS → ATTACKING, uses `up-retreat-now`, timers, parity and siege gates | Strong `[C]` lifecycle pattern; useful for client policy, not native engine promotion |
| Attack windows / stop / re-entry | MUSE describes pressure, stop and re-entry | Duke explicitly prolongs attack when military parity is acceptable, stops when inferior, then resets attack state/cooldown | Model as execution-policy observations; do not treat timer/parity as completion |
| Completion | MUSE leaves attack completion open | Community scripts issue attacks, stop/restart them, and measure parity, but no authoritative generic attack-success witness is established | `COMPLETE` still requires explicit objective witness; attack issuance/timer/parity cannot close it |
| Retarget | MUSE separates objective identity from target identity | Community DUC examples establish different targets by rebuilding search state; no generic target-success semantics | Preserve objective across RETARGET; DUC target is replaceable |
| Reinforcement | MUSE ties standing-army recovery to production | Community production idioms use `unit-type-count-total` and `can-train`; production compiler already separates feasibility, pending, queue and birth | Reuse existing production/capability IR; no new attack production subsystem |
| Attack-mode native promotion | MUSE says issue-only is executable-safe | Current native binder only promotes zero-arity `attack-now` | Correctly remains `ATTACK_NOW` only; other modes stay evidence-only |
| Controller interactions | MUSE controller graph is evidence-only | Duke/other community scripts demonstrate interactions, but not exact engine ownership contracts | Do not promote controller edges into native lowering |

## Primary community / official evidence

1. World's Edge Update 61321 documents fixes for AI units attacking through `attack-now` and `attack-groups`, and documents `sn-special-attack-type2` influencing attack-group targeting.
https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-61321/

2. AoE2 forum: Three ways to get the AI to attack documents the three attack mechanisms, explored-object dependency, land/naval differences, and attack-groups behavior.
https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476

3. AoE2 forum tutorial repeats the same three-mechanism distinction and explains town-size targeting.
https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881

4. `tim-kos/the_duke_ai` `the_duke_lib/attack.per` provides direct community source evidence for explicit READY/PREPARING/PULLING-TROOPS/ATTACKING/STOP/TOWN-SIZE-RESETTED state, regrouping via `up-retreat-now`, attack windows, parity gates, siege gates, and re-entry.
https://github.com/tim-kos/the_duke_ai/blob/master/the_duke_lib/attack.per

5. `lewisc64/aoe2ai` demonstrates compact timer-driven attack-now loops and DUC search/target idioms.
https://github.com/lewisc64/aoe2ai

6. AoE2 forum 2026 DUC-targeted attack example demonstrates reset → find → filter → set-target → get-point pipelines.
https://forums.ageofempires.com/t/help-so-you-can-make-the-ai-do-different-points/286382

## Required correction to the existing AttackExecution IR

Prior tranche validation treated `target` as required for ATTACK/PRESS/REINFORCE except town-size attack.

That is too strong.

The corrected rule is:
- `ATTACK_NOW`: DUC target optional. Native controller owns target selection; if a DUC target is supplied, it is semantic context, not proof of native target consumption.
- `ATTACK_GROUPS`: DUC target optional; controller semantics remain evidence-only.
- `TOWN_SIZE_ATTACK`: DUC target optional; native town-size controller owns target selection.
- `DUC_TARGETED`: DUC target required and must be `VALID` under the declared target policy.
- `STALE` and `UNKNOWN` DUC targets may be retained for RETARGET/REASSESS states but cannot authorize a DUC-dependent ATTACK/PRESS action.

## Current evidence boundary

The cross-check does not close attack completion/release, exact attack-controller ownership, attack-group membership semantics, automatic target selection semantics, town-size attack runtime details, DUC object liveness after every mutation, or attack parity as a generic success witness.

## Revised implementation target

The correct next compiler slice is a target-policy bridge, not a second attack controller:
`DUC TargetSession -> AttackTargetRef -> AttackExecution`

The native attack plan remains unchanged:
`ADMISSION_REQUIRED -> ISSUE -> COMPLETION_UNOBSERVED -> REASSESS_REQUIRED`

Only `ATTACK_NOW` remains executable-safe.