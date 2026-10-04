# Byzantine Role Separation Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Byzantine bot an auditable screen/main/siege/raid/reserve execution partition with world-state witnesses, fortified siege handling, recovery/reformation, and deterministic compiler lowering without adding a second attack scheduler.

**Architecture:** Add a typed `RoleSeparationPlan` to the Byzantine strategy profile. Lower it into compiler-owned native control state plus DUC group rules, using the existing runtime Goal allocator and native DUC contracts. The role controller owns membership and role-state transitions but never owns the attack action; the existing objective controller remains the sole objective actuator. Native group flags are rebuilt only on explicit role-formation/recovery/split epochs, then witnessed with `up-get-group-size`.

**Tech Stack:** Python 3, existing `LearnerAI/Compiler` IR/emitter/runtime binder, AoE2 DE `.per`, checked-in AIRef native schema, GitHub Actions/native validator.

## Global Constraints

- `main` is the current authority and the canonical emitted `Byzantine.per` must remain synchronized with the compiler source.
- Preserve the existing attack lifecycle and exactly four objective `up-target-objects ... action-attack-move` issuers.
- The role controller may classify, group, witness, recover, and release membership, but must not issue attack/move/stop actions.
- Role state is separate from objective state. Objective class/target remains owned by the objective controller.
- Roles are simultaneous: screen, main, siege, reserve may coexist; raid is a detachable split of eligible mobile force.
- Role IDs use native DUC group IDs 5-9 because current `Byzantine.per` has no group operations. Do not use Strategic Number 313 for membership.
- Group membership is rebuilt only on `FORMING`, `RECOVERING`, and explicit `RAID-SPLIT` transitions. Timer ticks never rebuild membership.
- Before setting group flags, searches must be restricted to own ready units and stale/foreign flagged objects must be removed. Converted enemy objects must never receive our group flag.
- Membership witness is group size, not combat success. Combat viability remains established by existing attack-ready/package/overmatch witnesses.
- Timers are cadence only. No role completion or siege success may be inferred from a timer.
- Preserve the existing 75% committed-soldier behavior for fortified approaches, leaving the current 25% reserve policy intact.
- Fortified posture blocks raid formation and requires a live siege floor before breach/assault.
- Existing live-siege revalidation before breach remains authoritative.
- The replay's object-19263 STOP loop is a P0 forensic constraint: role formation must be edge-triggered and must not emit repeated STOP orders.
- The replay's age/production deficits are out of scope for this tranche except where role logic must consume existing attack-ready, fortification, siege, and recovery state.
- Every new native command must be accepted through the checked-in native schema and DUC semantic validator.
- Generated artifacts must remain deterministic, under the 10,000-rule / 32-element-rule / 255-character-line limits, and native-zero-findings clean.

## Cross-reference conclusions

- Replay evidence shows the current bot already produces premium units and siege, but fails to concentrate and control them reliably. Role separation is therefore the correct next layer, not another production package.
- The replay has 25,408 Byzantine AI STOP orders, including 24,720 STOP orders on one object over ~26 minutes. The new role layer must be state/epoch driven, never a repeated command loop.
- Naga's replay contains materially more explicit grouped movement, retreat, and queue-control activity than the Byzantine replay. Community and official AI evidence support group-level coordination, but not a universal role implementation. The compiler must therefore keep the role semantics explicit and conservative.
- Current `Byzantine.per` has no native DUC group membership calls. The compiler already models `up-create-group`, `up-reset-group`, `up-set-group`, `up-get-group-size`, and `up-modify-group-flag`, so role membership can use the established DUC contract rather than introducing new native syntax.
- Fortified siege is already represented by `byzantine-siege-approach` and `byzantine-siege-scale`. This tranche extends those states with role ownership instead of replacing them.

---

### Task 1: Add the typed role-separation IR and strategy contract

**Files:**
- Create: `LearnerAI/Compiler/ir/role_separation.py`
- Modify: `LearnerAI/Compiler/ir/__init__.py`
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py`
- Test: `LearnerAI/Compiler/tests/test_role_separation.py`

**Interfaces:**
- Produces `NativeRoleSeparationPlan`, role/state enums, role specs, and deterministic native rules.
- `StrategyProfile.role_separation_plan` becomes optional and defaults to `None`.
- `build_byzantine_stock_strategy()` attaches the Byzantine role plan; non-Byzantine profiles remain byte-compatible when the field is absent.

- [ ] **Step 1: Add the focused failing test**

Test all of the following through the public strategy builder:
1. Byzantine strategy exposes a non-empty role plan.
2. Role group IDs are exactly 5, 6, 7, 8, 9 for screen/main/siege/raid/reserve.
3. Role plan has exactly one persistent role-state Goal request.
4. Role state values are `IDLE=0`, `FORMING=1`, `COMMITTED=2`, `RAID_SPLIT=3`, `RECOVERING=4`.
5. Role membership selection order is deterministic: screen, siege, main, raid, reserve.
6. Role rules contain no attack action.
7. The raid admission contract requires an exposed economy/production objective and preserves main/screen/siege floors.
8. Fortified admission disables raid formation.
9. Duplicate role identities and duplicate group IDs are rejected.

Run: `python -m unittest LearnerAI/Compiler/tests/test_role_separation.py`

Expected red result: the strategy profile has no `role_separation_plan` field and the role IR module does not exist.

- [ ] **Step 2: Implement the minimum typed model**

Define immutable dataclasses analogous to `NativeDucPlan`:
- `RoleControllerState`
- `RoleKind`
- `RoleMembershipSpec`
- `NativeRoleRule`
- `NativeRoleSeparationPlan`

The plan owns:
- one `GoalSlotRequest` for controller state;
- deterministic role membership metadata;
- deterministic native rule tuples;
- conversion helper to the existing `NativeControlPlan` + `NativeDucPlan` lowering representation.

Role membership semantics:
- Screen: current threat-package cheap counter layer, never siege.
- Main: primary non-screen, non-siege combat backbone.
- Siege: siege-weapon-class units only.
- Raid: mobile units only when exposed economy/production/route-bypass objective is active and all committed floors remain satisfied.
- Reserve: deliberately retained eligible combat capacity after minimum screen/siege/main commitments; not merely an accidental remainder.

Run focused tests again and keep role plan deterministic.

- [ ] **Step 3: Attach the plan to Byzantine strategy**

Add `role_separation_plan` to `StrategyProfile` and `StrategyCompilation`. Attach the default plan from `build_byzantine_stock_strategy()`. Do not attach it to generic land-castle profiles.

- [ ] **Step 4: Verify focused pass**

Run: `python -m unittest LearnerAI/Compiler/tests/test_role_separation.py`

Expected: focused role-contract tests pass.

- [ ] **Step 5: Run strategy regression**

Run: `python -m unittest LearnerAI/Compiler/tests/test_strategy_runtime.py`

Expected: existing runtime strategy tests pass unchanged.

---

### Task 2: Lower and emit native role groups without creating a second scheduler

**Files:**
- Modify: `LearnerAI/Compiler/compiler.py`
- Modify: `LearnerAI/Compiler/emitter/per.py`
- Modify: `LearnerAI/Compiler/runtime_binding.py` only if a new role-state storage hook is required
- Modify: `LearnerAI/Compiler/semantic/native_control.py` only for shared validation helpers if needed
- Modify: `LearnerAI/Compiler/primitives/registry.py` only for a role-plan validation entry point
- Test: `LearnerAI/Compiler/tests/test_role_native_emission.py`

**Interfaces:**
- `compile_semantic_demands(..., role_plan=None)`
- `compile_source(..., role_plan=None)`
- `compile_package(..., role_plan=None)`
- report-producing variants thread the same plan.
- `emit(..., role_plan=None)` validates and emits a deterministic `; Native role separation plan` section.
- `_storage_requests()` includes the role controller Goal request.

- [ ] **Step 1: Add failing emission tests**

Assert:
- role state gets a bound GoalSlot;
- generated output contains deterministic role defconsts;
- role rules are emitted in identity/order sequence;
- emitted role rules contain only facts plus group/state actions;
- no emitted role rule contains `attack-now`, `action-attack-move`, `move`, `stop`, `up-target-objects`, or `up-target-point`;
- equivalent role plans emit byte-identical artifacts;
- invalid group IDs, duplicate identities, missing role state witness, or malformed arity fail closed.

Run: `python -m unittest LearnerAI/Compiler/tests/test_role_native_emission.py`

Expected red: compiler/emitter have no role-plan parameter.

- [ ] **Step 2: Implement binding/threading**

Add the plan to `CompilerSemanticProgram`, the compiler orchestration, storage request collection, and all strategy adapters. Reuse the existing runtime Goal allocator. Do not create a second storage allocator.

- [ ] **Step 3: Implement native validation**

Validate all role rules through the existing native/DUC command contracts. Enforce:
- `up-create-group` exact four-argument signature;
- `up-reset-group` exact group range 0-9;
- `up-get-group-size` exact three-argument signature;
- `up-modify-group-flag` exact three-argument signature;
- group IDs are disjoint within the role plan;
- only own-ready-unit search results may be flagged;
- group-state actions are not objective actions.

- [ ] **Step 4: Implement emission**

Emit, in deterministic order:
1. role-state defconsts;
2. role-state initialization;
3. membership formation rules;
4. role witnesses;
5. raid split/rejoin rules;
6. recovery/reset rules;
7. fortified-siege role rules.

Membership formation is epoch-driven:
- `FORMING` clears stale role groups;
- each role is built once from the current local search;
- successful group formation transitions to `COMMITTED`;
- no formation rule is active once the state is `COMMITTED`.

- [ ] **Step 5: Verify focused pass and determinism**

Run: `python -m unittest LearnerAI/Compiler/tests/test_role_native_emission.py`

Expected: all role emission tests pass and two equivalent compilations produce byte-identical output.

---

### Task 3: Implement role membership witnesses, raid transitions, recovery, and fortified siege

**Files:**
- Modify: `LearnerAI/Compiler/ir/role_separation.py`
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py`
- Test: `LearnerAI/Compiler/tests/test_role_separation.py`
- Test: `LearnerAI/Compiler/tests/test_byzantine_role_artifact.py`

**Role formation rules:**

1. On attack admission and role state `IDLE`, enter `FORMING`.
2. On `FORMING`, reset groups 5-9.
3. Build Screen first from current counter-package units.
4. Build Siege second from siege-class units, bounded by the current siege floor.
5. Build Main from remaining combat units after screen/siege reservation.
6. Build Reserve from the deliberate retained floor before any raid split.
7. Set group flags only after the search has removed non-ready objects and foreign/stale flags.
8. Transition to `COMMITTED` only when required group sizes meet their role floors.
9. If the committed minimum cannot be formed, stay `FORMING`; do not issue attack.

**Role witnesses:**

- Screen witness: `up-get-group-size` >= configured screen floor.
- Main witness: `up-get-group-size` >= main floor derived from existing attack admission.
- Siege witness: `up-get-group-size` >= current standard/fortified siege floor.
- Reserve witness: reserved-group size >= reserve floor when the current package requires a reserve.
- Raid witness: raid group >= raid floor AND main/screen/siege groups still meet committed floors.
- Committed witness: all required role groups meet their floors.
- Recovery witness: attack-ready == 0 OR overmatch-triggered OR siege group below floor OR fortified breach invalidation.
- Group-size witnesses do not prove target destruction or combat victory.

**Raid transition rules:**

- `COMMITTED -> RAID_SPLIT` only when the objective class is production/economy/route-bypass, fortification threat is 0, mobile units exist, and committed main/screen/siege floors survive the split.
- `RAID_SPLIT -> COMMITTED` when the exposed target disappears, the target becomes fortified, mobile floor is lost, or the primary objective changes.
- Raid never gets formed against a siege/fortified objective.
- Raid never steals siege units or the minimum screen.

**Recovery rules:**

- Any loss of `army-attack-ready` immediately leaves committed state.
- Any overmatch trigger forces `RECOVERING`.
- Any siege-floor loss forces `RECOVERING` before fortified breach/assault.
- `RECOVERING` resets all five groups exactly once, preserves the existing 25% reserve policy, and returns to `FORMING` only after recovery admission is satisfied.
- Objective witness remains owned by the objective controller. Positive witness does not invent a role-completion event.

**Fortified siege rules:**

- Existing `byzantine-siege-scale == fortified` remains the admission witness for the enlarged siege package.
- `fortification-threat == 1` blocks raid formation.
- Before breach, revalidate live siege locally and require the Siege group floor.
- Breach retains `sn-percent-attack-soldiers 75`; reserve remains outside the committed attack package.
- Siege group is the only role allowed to satisfy the structure-breaking portion of the fortified package.
- Main and Screen accompany the siege role but are not reassigned as Siege.
- After breach/structure witness, preserve the role state and let the objective controller reassess the next target.
- If live siege disappears or fortified threat clears, return to standard siege scale and reform only when state transitions require it.
- No timer is used as fortified completion evidence.

- [ ] **Step 1: Add red behavioral tests for every transition above.**
- [ ] **Step 2: Run focused tests and verify the failures are behavioral, not setup failures.**
- [ ] **Step 3: Implement minimum rule set.**
- [ ] **Step 4: Verify focused tests pass.**
- [ ] **Step 5: Run existing defensive-geometry and attack lifecycle focused suites.**

Expected: existing objective actuator count remains four; role plan adds no attack action issuer.

---

### Task 4: Synchronize the canonical Byzantine artifact, validate, and update roadmap evidence

**Files:**
- Modify: `Byzantine.per`
- Modify: `docs/plans/2026-10-02-byzantine-expert-opponent-roadmap.md`
- Create: `docs/plans/2026-10-04-byzantine-role-separation.md` (this plan)

- [ ] **Step 1: Produce the artifact through the canonical compiler path.**

The checked-in `Byzantine.per` must contain the emitted role plan and remain byte/determinism reproducible from the canonical Byzantine strategy profile.

- [ ] **Step 2: Run the native/parser gates.**

Run the repository's canonical native validation and focused tests. Required observations:
- zero native findings;
- no invalid identifiers;
- no rule over 32 elements;
- no line over 255 characters;
- role section deterministic;
- objective actuator count unchanged at four;
- no role section attack action.

- [ ] **Step 3: Run cross-platform/compiler regression gates.**

Run the canonical compiler regression, native DUC, persistent-state, military-composition, replay/snapshot, and final verification workflows used by `main`.

- [ ] **Step 4: Update roadmap evidence.**

Mark Phase 4 role separation and fortified siege handling complete only after the emitted artifact and CI evidence are green. Add the role witness/recovery contract to the roadmap text.

- [ ] **Step 5: Runtime acceptance criteria.**

The next runtime replay must demonstrate:
- non-empty screen/main/siege roles on a committed attack;
- siege remains with the main force while raid splits only when eligible;
- raid returns when target disappears or fortification appears;
- fortified attacks retain a reserve and use siege deliberately;
- role formation does not create a repeated STOP loop;
- after objective witness, the army reforms/reassesses rather than remaining permanently bound to a dead target.

## Verification Commands

Focused:
`python -m unittest LearnerAI/Compiler/tests/test_role_separation.py`
`python -m unittest LearnerAI/Compiler/tests/test_role_native_emission.py`
`python -m unittest LearnerAI/Compiler/tests/test_strategy_runtime.py`

Repository acceptance:
Use the existing canonical compiler/native validation commands and the GitHub workflow gates already used by `main`. A prior CI-green state is never reused as proof for this change.

## Completion Criteria

The tranche is complete only when:
- typed role IR exists and is attached only to the Byzantine stock strategy;
- compiler lowering is deterministic;
- native group membership is validated against checked-in DUC contracts;
- role witnesses are explicit and world-state based;
- fortified siege requires live siege capability and never consumes the reserve by implication;
- raid cannot steal committed floors;
- recovery destroys stale role membership exactly once before reforming;
- role rules never issue attack/move/stop actions;
- the canonical `Byzantine.per` contains the role layer;
- native validation is zero-findings;
- focused and repository regressions pass;
- the objective controller still owns the only four precise attack-move issuers.

## Unresolved externally observable decisions

None. The user-authorized implementation chooses the conservative native-group model, 5-9 group IDs, edge-triggered formation, group-size membership witnesses, existing 75% fortified commitment policy, and the existing objective controller as the sole attack actuator.

## Cross-reference addendum applied during implementation

### Replay evidence
The replay makes the role problem concrete: the Byzantine bot produced far more STOP control than the comparison AI and accumulated a pathological repeated-STOP loop on one object. The role layer therefore uses no attack, move, or stop actions and changes membership only at explicit state edges. The replay also showed large premium and siege inventories without reliable concentration or objective completion, so the role layer is an execution partition rather than another production planner.

### Community and engine evidence
Official DE AI work has continued improving formation, pathfinding, and large-group behavior, while community DUC examples use native control-group flags to partition units and re-find them. The compiler already has executable-safe up-create-group, up-reset-group, up-modify-group-flag, up-group-size, and up-get-group-size semantics. The implementation uses up-get-group-size into width-1 Goal outputs followed by up-compare-goal. Strategic Number 313 is intentionally unused.

### Final role membership policy
Screen group 5 is formed from the existing cheap anti-threat layer. Siege group 7 is formed from siege weapons only. Reserve group 9 is formed before Main and contains detachable cavalry/mobile capacity plus monks. Main group 6 is every remaining ready combat unit after Screen, Siege, Reserve, and monks are excluded. Raid group 8 is built only from reserve-eligible cavalry and only for production/Town-Center objective classes with no fortified threat. No role may steal another role's protected floor.

### Witness policy
Formation uses one native group-size snapshot for Screen/Main/Siege/Reserve, then commits only when the required floors pass. Raid gets its own immediate split snapshot and must preserve Screen/Main/Siege floors. Fortified posture has a one-shot latch that refreshes Siege group size on the normal-to-fortified posture edge. Group size is membership evidence, not a combat-success witness. Attack-ready and overmatch remain the authoritative recovery gates.

### Fortified siege policy
Fortified posture requires the enlarged siege floor of two witnessed siege units, retains the existing 75% committed-attack allocation, and blocks raid splitting. Loss of the live siege floor moves role state to RECOVERING and drops attack-ready to zero. The role controller never issues the breach or assault action; the existing siege/objective controller retains those actuators.

### Compiler/runtime synchronization
The compiler strategy profile now carries NativeRoleSeparationPlan, allocates nine Goal slots for role state, memory, and outputs, emits the native group rules deterministically, and gates the two Castle attack-now rules and four precise objective action-attack-move issuers on committed/raid-split role state. Byzantine.per has the same role constants and rule sequence using stable runtime Goal IDs 420-427 and 430. The artifact still has exactly four precise objective attack-move issuers.

### Hard constraints preserved
No second attack scheduler was introduced. No timer is used as role completion evidence. Role formation is not a recurring initializer. Foreign/stale objects are removed from the local search before role flags are rewritten. Recovery clears the five role groups before re-forming. The 25% reserve policy in fortified breach remains owned by the existing siege controller.

### Ownership correction
The role controller does not mutate `byzantine-army-attack-ready`. It raises `byzantine-army-role-recovery-request`. The existing persistent control plane consumes that request, performs `up-reset-attack-now`, clears `army-attack-ready`, and clears the request. This preserves the original state-owner boundary while allowing role formation/fortified/overmatch failure to fail closed.
