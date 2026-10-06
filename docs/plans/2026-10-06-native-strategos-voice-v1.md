# Native Strategos Voice v1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compiler-owned, latency-safe Strategos narration layer that emits sparse native chat from existing Byzantine strategic transitions without creating a second decision engine.

**Architecture:** `StrategyProfile.voice_plan` carries a typed `NativeVoicePlan`. Voice rules reuse the existing `GoalSlotRequest` and `TimerRequest` storage/binding infrastructure, and the emitter places the voice block at the end of the artifact so priority arbitration can use native `up-jump-rule` same-pass control. Voice consumes existing strategy/runtime facts only; it never owns demand, attack, recovery, or production decisions.

**Tech Stack:** Python 3, immutable dataclass IR, existing RuntimeBinder/TimerSlot/GoalSlot plumbing, native .per emitter, GitHub Actions/unittest.

## Global Constraints

- `chat-to-player` and `chat-to-allies` are the only voice actions in v1. `chat-local-to-self` remains debug-only.
- Voice rules are transition/state-entry driven. Persistent polling without an edge, reset witness, or bounded rearm is invalid.
- Priority is deterministic. Higher-priority eligible voice wins; same-pass lower-priority voice rules are skipped with native `up-jump-rule`.
- Voice uses one global cooldown timer and one event-owned latch/timer pair per narratable event. The latch is reset only after the source clear/hysteresis witness and the event cooldown timer have both cleared.
- The global cooldown is 12 seconds for ordinary narration and 4 seconds for critical narration. Critical narration bypasses an active ordinary cooldown but still arms the critical cooldown interval afterward.
- Runtime hard budget is 48 messages per match, with an ordinary soft budget at 36. At the soft budget, only CRITICAL/DECISION/RECOVERY events remain eligible. At the hard budget, only CRITICAL events remain eligible.
- v1 deliberately does not implement a rolling 120-second counter. The global cooldown plus hard match ceiling provide the first low-risk runtime throttle; a rolling window would add more mutable state than the initial voice slice requires.
- Voice match count is a Goal-backed counter incremented by `up-modify-goal <goal> g:+ 1`.
- Voice initialization is one-shot and deterministic.
- Generated voice rules are emitted after all ordinary compiler/runtime rules so `up-jump-rule` can skip the remainder of the voice candidate block without depending on unrelated rule positions.
- The Byzantine voice policy contains only evidence-backed messages referring to existing posture, counter, readiness, siege, attack, recovery, reassessment, and endgame state.
- The compiler must remain deterministic and the generated artifact must remain within the existing 10,000-rule, 32-elements/rule, and 255-character/line emitter limits.
- Unknown strategic state does not trigger narration. Voice fails closed.

---

### Task 1: Native voice IR, native chat contracts, and scheduler semantics

**Files:**
- Create: `LearnerAI/Compiler/ir/strategic_voice.py`
- Modify: `LearnerAI/Compiler/ir/__init__.py`
- Modify: `LearnerAI/Compiler/primitives/engine_semantics.py`
- Modify: `LearnerAI/Compiler/primitives/registry.py`
- Modify: `A-native_command_semantics.csv`
- Test: `LearnerAI/Compiler/tests/test_strategic_voice.py`
- Test: `LearnerAI/Compiler/tests/test_native_chat_contract.py`

**Interfaces:**
- Consumes: existing `Expression`, `GoalSlotRequest`, `TimerRequest`, `GoalRole`, `SemanticId`, and native registry/schema.
- Produces: `VoicePriority`, `VoiceAudience`, `VoiceLatchMode`, `NativeVoiceBudget`, `VoiceRule`, `NativeVoicePlan`, `validate_native_voice_plan()`.
- Voice rule storage requests are exposed through `NativeVoicePlan.storage_requests`.

- [ ] **Step 1: Add the focused failing test**

Assert:
- `chat-to-player` is a registered executable Action with arity 2.
- `chat-to-allies` is a registered executable Action with arity 1.
- a one-rule `NativeVoicePlan` validates only if it has a trigger, latch Goal, and message.
- ordinary rules reject invalid cooldowns, empty identifiers, empty messages, and non-deterministic order.
- a persistent trigger without a reset/edge contract raises `VOICE-POLLING-RULE`.
- budget validation rejects soft > hard and hard <= 0.
- event identity/latch identity must be unique.

Run: `python -m unittest LearnerAI.Compiler.tests.test_native_chat_contract LearnerAI.Compiler.tests.test_strategic_voice -v`

Expected red: import/attribute failures because the new IR and chat registry contracts do not yet exist.

- [ ] **Step 2: Implement the minimum behavior**

Create the immutable voice IR. Use `GoalSlotRequest(role=PERSISTENT_STATE)` for event latches and match count/global lock; use `TimerRequest(role=EXECUTION_MEMORY)` for global cooldown and event rearm timers.

Use these concrete defaults:
- soft match budget 36
- hard match budget 48
- ordinary global cooldown 12s
- critical global cooldown 4s

Implement validator rules:
- valid .per identifiers
- unique event identities
- deterministic order
- message non-empty and parser-safe
- only `chat-to-player` / `chat-to-allies`
- trigger and clear semantics required for STATE/REARM_ON_CLEAR
- `EDGE` may omit clear only when the trigger expression is explicitly edge-derived by the caller
- no persistent polling rule without a reset contract
- budget invariants

Register the two chat Actions as contracted engine mappings using current AIRef command/schema evidence. Do not promote `chat-local-to-self`.

- [ ] **Step 3: Verify the focused pass**

Run the identical unittest command.

Expected: all focused voice/chat contract tests pass.

- [ ] **Step 4: Run affected integration check**

Run: `python -m unittest LearnerAI.Compiler.tests.test_native_semantic_binder LearnerAI.Compiler.tests.test_semantic_support_state -v`

Expected: existing primitive/mapping contracts remain green with the two new executable chat mappings.

- [ ] **Step 5: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/strategic_voice.py LearnerAI/Compiler/ir/__init__.py LearnerAI/Compiler/primitives/engine_semantics.py LearnerAI/Compiler/primitives/registry.py A-native_command_semantics.csv LearnerAI/Compiler/tests/test_strategic_voice.py LearnerAI/Compiler/tests/test_native_chat_contract.py
git commit -m "feat: add native strategos voice IR and chat contracts"
```

---

### Task 2: Thread NativeVoicePlan through compilation, binding, and native emission

**Files:**
- Modify: `LearnerAI/Compiler/ir/strategy.py`
- Modify: `LearnerAI/Compiler/ir/program.py`
- Modify: `LearnerAI/Compiler/compiler.py`
- Modify: `LearnerAI/Compiler/clients/basilisk/compiler.py`
- Modify: `LearnerAI/Compiler/emitter/per.py`
- Test: `LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`
- Test: `LearnerAI/Compiler/tests/test_strategic_voice.py`

**Interfaces:**
- Consumes: `StrategyProfile.voice_plan` and `StrategyCompilation.voice_plan`.
- Produces: `CompilerSemanticProgram.voice_plan`, compiler storage bindings, deterministic `; Native Strategos voice plan` emission.

- [ ] **Step 1: Add the focused failing test**

Assert:
- `lower_strategy_profile()` preserves a supplied voice plan.
- `CompilerSemanticProgram` accepts/retains `voice_plan`.
- `compile_strategy_profile()` emits the voice section.
- identical compilation calls produce byte-identical voice output.
- a two-candidate plan emits candidates in priority/order order and a fired candidate uses `up-jump-rule` to skip lower candidates.
- voice state requests bind to GoalSlot/TimerSlot and emitted `defconst` operands are declared.
- ordinary and critical rules use the correct global cooldown duration.

Run: `python -m unittest LearnerAI.Compiler.tests.test_strategic_voice LearnerAI.Compiler.tests.test_strategy_compiler_integration -v`

Expected red: missing voice fields/plumbing and emitter output.

- [ ] **Step 2: Implement the minimum behavior**

Add `voice_plan: NativeVoicePlan | None` to StrategyProfile, StrategyCompilation, and CompilerSemanticProgram.

Extend `_storage_requests()` to include `voice_plan.storage_requests`.

Validate the voice plan at the compiler boundary.

In the emitter:
1. emit voice Goal/Timer symbolic constants through RuntimeBinder bindings;
2. emit one-shot voice initialization;
3. emit timer-expiry/rearm reset rules;
4. emit the global cooldown clear rule;
5. emit voice candidates sorted by `(-priority, order, identity)`;
6. require ordinary candidates to see global lock 0;
7. allow critical candidates to bypass the lock;
8. increment `voice-match-count` with `up-modify-goal ... g:+ 1`;
9. set the event latch and enable its cooldown timer;
10. set the global lock and enable the global cooldown timer;
11. emit `chat-to-player focus-player "..."` or `chat-to-allies "..."`;
12. emit `up-jump-rule <remaining-candidate-count>` as the final action so only the highest-priority eligible voice fires during that pass;
13. apply soft/hard budget guards before the chat action.

Do not use `disable-self` for repeatable strategic events. Rearm is controlled by source clear + event timer expiry.

- [ ] **Step 3: Verify the focused pass**

Run the identical unittest command.

Expected: all voice emission/integration assertions pass.

- [ ] **Step 4: Run affected integration checks**

Run:
`python -m unittest LearnerAI.Compiler.tests.test_strategy_sn_modes LearnerAI.Compiler.tests.test_runtime_semantic_isolation LearnerAI.Compiler.tests.test_compiler_native_integration -v`

Expected: existing deterministic storage/control emission remains green.

- [ ] **Step 5: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/strategy.py LearnerAI/Compiler/ir/program.py LearnerAI/Compiler/compiler.py LearnerAI/Compiler/clients/basilisk/compiler.py LearnerAI/Compiler/emitter/per.py LearnerAI/Compiler/tests/test_strategy_compiler_integration.py LearnerAI/Compiler/tests/test_strategic_voice.py
git commit -m "feat: thread native strategos voice through compiler emission"
```

---

### Task 3: Byzantine voice policy and runtime source/artifact acceptance

**Files:**
- Modify: `LearnerAI/Compiler/ir/community_strategy_packs.py`
- Modify: `LearnerAI/Compiler/ir/strategy.py` only if the default voice plan factory belongs there
- Modify: `LearnerAI/Compiler/clients/basilisk/compiler.py` only if runtime-profile selection needs explicit voice preservation
- Modify: `LearnerAI/Compiler/tests/test_runtime_test_bot.py`
- Create: `LearnerAI/Compiler/tests/test_byzantine_voice_policy.py`

**Interfaces:**
- Consumes: existing Byzantine posture/counter/attack/endgame/recovery facts.
- Produces: `default_byzantine_voice_plan(profile_id)` with approximately 12–14 canonical events.

- [ ] **Step 1: Add the focused failing test**

Assert the default Byzantine plan contains, at minimum:
- posture transition narration
- ranged-pressure narration
- cavalry-pressure narration
- severe counter narration
- army preparation
- army ready
- siege blocker
- attack issued
- attack witness
- attack failure
- gold recovery
- strategic replacement/reassessment
- endgame commitment

Assert every trigger/reset expression references an existing StrategyProfile observation or native state already emitted by the profile. No new strategic fact definitions may be introduced solely for voice.

Run: `python -m unittest LearnerAI.Compiler.tests.test_byzantine_voice_policy -v`

Expected red: no default voice plan exists.

- [ ] **Step 2: Implement the minimum behavior**

Create the Byzantine policy with deterministic priority and concrete messages. Use the existing Strategos lines already established in the design:

- “I see the shape of the fight. I am taking the efficient road.”
- “Their cavalry is no longer incidental. Halberdiers are the answer.”
- “Their ranged line now dictates the field. Elite Skirmishers are the answer.”
- “This threat justifies saturation. I am building the screen.”
- “The force is almost ready. I am finishing the missing piece.”
- “The army is assembled. More preparation would be waste.”
- “The screen is ready. The wall is not. I need siege.”
- “The army is ready. I am going in.”
- “The attack was issued. Now I need proof.”
- “That push opened nothing. I know what was missing.”
- “The gold route has failed. The objective has not.”
- “The old answer solved the old problem. It is no longer the right answer.”
- “The field has changed. So does the plan.”
- “I have spent enough time becoming stronger. Now I will use it.”

Attach the plan to the default Byzantine StrategyProfile. Preserve it through runtime-profile compilation unchanged.

- [ ] **Step 3: Verify the focused pass**

Run the identical policy test.

Expected: policy composition, priorities, source references, and deterministic ordering pass.

- [ ] **Step 4: Run the artifact/runtime checks**

Run:
- `python -m unittest LearnerAI.Compiler.tests.test_runtime_test_bot LearnerAI.Compiler.tests.test_strategy_runtime LearnerAI.Compiler.tests.test_byzantine_voice_policy -v`
- `python -m tools.build_byzantine_bot` (or the repository's existing Byzantine artifact build command if the workflow confirms a different canonical invocation).

Expected:
- `Byzantine.per` contains exactly one `; Native Strategos voice plan` section.
- every named Goal/Timer operand is declared.
- all chat actions are `chat-to-player` or `chat-to-allies`.
- no `chat-local-to-self` occurs in the generated artifact.
- no voice rule exceeds native emitter rule/line limits.
- repeated generation is byte-identical.

- [ ] **Step 5: Commit the passing deliverable**

```bash
git add LearnerAI/Compiler/ir/community_strategy_packs.py LearnerAI/Compiler/tests/test_byzantine_voice_policy.py LearnerAI/Compiler/tests/test_runtime_test_bot.py Byzantine.per
git commit -m "feat: add Byzantine Strategos narration policy"
```

---

### Task 4: Full verification, artifact synchronization, and branch integration gate

**Files:**
- Verify all files changed by Tasks 1–3.
- Modify no strategic behavior unrelated to voice.

**Interfaces:**
- Consumes: complete NativeVoicePlan pipeline and synchronized Byzantine artifact.
- Produces: verified branch commit and PR-ready evidence.

- [ ] **Step 1: Run focused voice suite**

Run:
`python -m unittest LearnerAI.Compiler.tests.test_native_chat_contract LearnerAI.Compiler.tests.test_strategic_voice LearnerAI.Compiler.tests.test_byzantine_voice_policy -v`

Expected: zero failures.

- [ ] **Step 2: Run strategy/compiler regression**

Run the repository compiler test workflow or its local equivalent, including:
- strategy integration
- native semantic binder
- pass scheduler
- timer semantics
- runtime semantic isolation
- deterministic artifact tests

Expected: zero regressions and deterministic output.

- [ ] **Step 3: Validate native findings**

Run the repository's canonical native parser/zero-finding check and confirm zero findings for the generated artifact.

Expected: voice rules are parser-valid and do not introduce native unknowns.

- [ ] **Step 4: Verify artifact synchronization**

Run the canonical Byzantine build/synchronization command. Compare the committed `Byzantine.per` against a second fresh generation.

Expected: byte-identical artifacts.

- [ ] **Step 5: Review runtime risk**

Confirm:
- no polling-only voice rule exists;
- ordinary narration is globally throttled to one event per 12s at most;
- critical narration is globally throttled to one event per 4s at most;
- each event has an independent latch/rearm timer;
- hard 48-message budget is fail-closed;
- voice cannot mutate strategic demand/attack/economy state.

- [ ] **Step 6: Commit verification-only changes**

Only commit source/artifact changes required by failed verification. Do not add unrelated cleanup.

```bash
git status
git diff --check
```

Expected: clean, coherent branch with only the Strategos voice implementation.

## Explicit implementation boundary

The first implementation does **not** add:
- free-form generated prose;
- per-pass self-chat;
- `chat-local-to-self`;
- dynamic numeric prose;
- rolling-window accounting;
- a second strategic planner;
- independent threat thresholds that duplicate the strategic controller.

Those belong outside v1 until runtime evidence shows the sparse transition-driven layer is stable.
