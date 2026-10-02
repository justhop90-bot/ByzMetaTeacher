# Varangian Guard, MapProfile, Opening, and Economic Controller Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Update 185872 Byzantine Varangian strategic gap and add typed map-conditioned opening and economic control policy through the existing StrategyProfile and NativeControlPlan seams.

**Architecture:** Keep GameData factual and patch-pinned. Add three policy-only IR modules: MapProfile describes supported environmental categories, OpeningSelector persists a deterministic opening interpretation, and EconomyController selects documented civilian-allocation Strategic Number modes. Lower all controller behavior into the existing native Goal/SN persistent-control plane; no new scheduler, lifecycle, or .per language is introduced.

**Tech Stack:** Python 3.11+, immutable dataclasses/enums, existing StrategyProfile/StrategicDemandSpec, NativeControlPlan/Rule/State, runtime binding, semantic analyzer, unittest, pinned aoe2-ai-parser CI.

## Global Constraints

- Update 185872 remains the authoritative Byzantine patch.
- Varangian Guard is conditional strategy, not an unconditional Castle floor.
- Strategy evidence remains separate from factual GameData evidence.
- Map detection uses native `map-type` observations; MapProfile is policy metadata.
- Opening selection is durable once selected and uses deterministic precedence.
- Economy control writes only the existing documented civilian-allocation SNs 117, 120, 118, and 1.
- Opening/economy controls must not replace construction, production, escrow, DUC, attack, or water lifecycles.
- No runtime semantics are inferred beyond existing native command mappings.
- Existing StrategyProfile constructors remain source-compatible by making new fields optional.
- Acceptance continues to rely on the repository native zero-findings, full unittest, and cross-platform determinism workflow.

---

### Task 1: Add the Varangian Guard strategic package

**Files:** Modify `LearnerAI/Compiler/ir/community_strategy_packs.py`; Test `LearnerAI/Compiler/tests/test_community_strategy_packs.py`

**Interfaces:** Consumes existing `EffectiveCivData`, `StrategicDemandSpec`, `StrategicMilitaryComposition`, and `community_strategy_observations()`. Produces `strategy-enemy-infantry-pressure`, `strategy-enemy-infantry-pressure-cleared`, `castle-varangian-guard-floor`, and a conditional Castle infantry composition.

- [ ] Add failing tests for the new observations, demand, verified Varangian line/provider, and separate infantry package. Assert the existing standard Castle package remains free of an unconditional Varangian floor.
- [ ] Run `python -m unittest LearnerAI/Compiler/tests/test_community_strategy_packs.py` and observe the expected missing-feature failure.
- [ ] Implement the minimum policy using `_provider_for_line(effective, "varangian-guard-line")`, escrow-aware admission, unit-count witness, pressure-clear invalidation, and a separate `castle-infantry-package`.
- [ ] Re-run the focused test and then `python -m unittest LearnerAI/Compiler/tests/test_strategy_runtime.py LearnerAI/Compiler/tests/test_strategy_compiler_integration.py`.

### Task 2: Establish typed MapProfile and durable opening selection

**Files:** Create `LearnerAI/Compiler/ir/map_profile.py`; Create `LearnerAI/Compiler/ir/opening.py`; Modify `LearnerAI/Compiler/ir/strategy.py`; Modify `LearnerAI/Compiler/ir/community_strategy_packs.py`; Modify `LearnerAI/Compiler/clients/basilisk/__init__.py`; Test `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`

**Interfaces:** Produces `MapKind`, `MapProfile`, `OpeningFamily`, and `OpeningSelectorPlan`, plus a persistent `opening-plan` Goal lowering through `NativeControlPlan`.

- [ ] Add failing tests asserting five typed map categories and opening precedence: islands+naval pressure -> WATER_CONTROL; islands -> WATER_ECONOMY; arena -> FAST_CASTLE; land pressure -> COUNTER_FEUDAL; otherwise DEFENSIVE_STANDARD.
- [ ] Run `python -m unittest LearnerAI/Compiler/tests/test_strategy_opening_economy.py` and observe the expected missing-field/import failure.
- [ ] Implement policy-only map/opening types, optional StrategyProfile fields, deterministic Goal selection with `(goal opening-plan 0)` guards, and public exports.
- [ ] Re-run the focused test and `python -m unittest LearnerAI/Compiler/tests/test_community_strategy_packs.py LearnerAI/Compiler/tests/test_strategy_goal_state.py`.

### Task 3: Establish the economic controller

**Files:** Create `LearnerAI/Compiler/ir/economic_control.py`; Modify `LearnerAI/Compiler/ir/strategy.py`; Modify `LearnerAI/Compiler/ir/community_strategy_packs.py`; Modify `LearnerAI/Compiler/clients/basilisk/__init__.py`; Test `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`

**Interfaces:** Produces `EconomyMode`, `EconomyControllerPlan`, persistent `economy-posture`, and guarded writes to SN 117/120/118/1.

- [ ] Add failing tests asserting deterministic modes for base, Fast Castle, counter-Feudal, water economy, water control, Castle conversion, and Imperial conversion. Assert only SN 117/120/118/1 are written and none overlap existing strategy SN writers.
- [ ] Run the focused test and observe the expected missing-controller failure.
- [ ] Implement the controller through the existing persistent control plane. Use policy inputs: base 50/30/20 builders 5; Fast Castle 55/15/30 builders 3; counter-Feudal 42/38/20 builders 8; water economy 40/40/20 builders 5; water control 38/42/20 builders 8; Castle conversion 45/25/30 builders 7; Imperial conversion 40/25/35 builders 7. Treat these as policy values, not engine facts.
- [ ] Re-run the focused test and `python -m unittest LearnerAI/Compiler/tests/test_strategy_sn_modes.py LearnerAI/Compiler/tests/test_native_control_plane.py`.

### Task 4: Wire acceptance and audit

**Files:** Modify `LearnerAI/Compiler/ir/__init__.py`; Modify `.github/workflows/compiler-tests.yml`; Modify `LearnerAI/Compiler/tests/test_strategy_opening_economy.py`

**Interfaces:** Public exports plus focused native zero-findings acceptance for the stock Byzantine artifact.

- [ ] Add the focused native fixture/command and public exports.
- [ ] Run focused tests and the stock strategy native validator through Actions.
- [ ] Run the full compiler workflow and the cross-platform native-support replay matrix.
- [ ] Report current commit status only from fresh verification. Do not reuse the older stale audit result.

## Open verification facts

- Update 185872 GameData supports Varangian IDs 2703/2704 and the verified Varangian unit line.
- Exact live-game usefulness of the Varangian floor and selected civilian-allocation percentages remains a runtime strategy question.
- The current main tip `381f045f6c7a2cbc06dd6493a59f9ff0c7ae3438` was not green when this work began.