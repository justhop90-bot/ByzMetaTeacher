import unittest

from Compiler.primitives import default_de_registry
from Compiler.clients.basilisk import (
    ByzantineProfile,
    WaterExecutionPlan,
    WaterExecutionState,
    WaterPosture,
    resolve_effective_civ,
)
from Compiler.ir.strategy import StrategyPosture, build_byzantine_strategy, lower_strategy_profile
from Compiler.ir.strategy_runtime import ReassessmentReason, RuntimeObservationSnapshot, evaluate_strategy_runtime
from Compiler.ir.water import (
    TransportExecutionPhase,
    WaterExecutionState,
    WaterPosture,
    derive_water_posture,
    transition_transport_execution,
)


class WaterTransportExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effective = resolve_effective_civ(ByzantineProfile.for_update_185872())

    def test_transport_state_preserves_intent_and_enters_recovery_when_capability_is_lost(self):
        ready = WaterExecutionState(
            water_map=True,
            transport_required=True,
            transport_capable=True,
            transport_phase=TransportExecutionPhase.READY,
        )
        recovered = transition_transport_execution(
            ready,
            water_map=True,
            transport_required=True,
            transport_capable=False,
        )

        self.assertEqual(recovered.transport_phase, TransportExecutionPhase.RECOVER)
        self.assertTrue(recovered.transport_required)
        self.assertFalse(recovered.transport_capable)


    def test_recovery_holds_until_rebuild_authorization(self):
        ready = WaterExecutionState(
            transport_required=True,
            transport_capable=True,
            transport_phase=TransportExecutionPhase.READY,
        )
        recovered = transition_transport_execution(
            ready,
            water_map=True,
            transport_required=True,
            transport_capable=False,
        )
        self.assertEqual(recovered.transport_phase, TransportExecutionPhase.RECOVER)

        held = transition_transport_execution(
            recovered,
            water_map=True,
            transport_required=True,
            transport_capable=False,
        )
        self.assertEqual(held.transport_phase, TransportExecutionPhase.RECOVER)

        reopened = transition_transport_execution(
            held,
            water_map=True,
            transport_required=True,
            transport_capable=False,
            transport_rebuild_open=True,
        )
        self.assertEqual(reopened.transport_phase, TransportExecutionPhase.PREPARE)

    def test_water_map_and_transport_requirement_are_separate_observations(self):
        profile = build_byzantine_strategy(self.effective)
        plan = profile.water_execution_plan
        self.assertIsNotNone(plan)
        assert plan is not None

        self.assertEqual(plan.water_map_observation, "strategy-water-map")
        self.assertEqual(plan.transport_required_observation, "strategy-transport-required")
        self.assertNotEqual(plan.water_map_observation, plan.transport_required_observation)
        self.assertEqual(
            profile.observation("strategy-water-map").expression,
            "(or (map-type islands) (map-type pacific-islands))",
        )
        self.assertEqual(
            profile.observation("strategy-transport-required").expression,
            "(goal water-transport-objective 1)",
        )

    def test_water_posture_transport_requires_both_map_and_objective(self):
        self.assertEqual(
            derive_water_posture(
                water_map=False,
                transport_required=True,
                dock_exists=True,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.NONE,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=False,
                dock_exists=True,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.FISHING,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=True,
                dock_exists=True,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.TRANSPORT_SUPPORT,
        )

    def test_water_posture_precedence_is_transport_then_naval_then_fishing(self):
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=True,
                dock_exists=True,
                naval_pressure=True,
                warboat_floor_met=True,
            ),
            WaterPosture.TRANSPORT_SUPPORT,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=False,
                dock_exists=True,
                naval_pressure=True,
                warboat_floor_met=False,
            ),
            WaterPosture.NAVAL_DEFENSE,
        )
        self.assertEqual(
            derive_water_posture(
                water_map=True,
                transport_required=False,
                dock_exists=True,
                naval_pressure=True,
                warboat_floor_met=True,
            ),
            WaterPosture.NAVAL_CONTROL,
        )

    def test_unknown_water_evidence_fails_closed(self):
        self.assertEqual(
            derive_water_posture(
                water_map=None,
                transport_required=False,
                dock_exists=False,
                naval_pressure=False,
                warboat_floor_met=False,
            ),
            WaterPosture.UNKNOWN,
        )
        state = transition_transport_execution(
            WaterExecutionState(),
            water_map=True,
            transport_required=True,
            transport_capable=None,
        )
        self.assertEqual(state.transport_phase, TransportExecutionPhase.UNKNOWN)

    def test_runtime_state_marks_transport_loss_as_recovery(self):
        profile = build_byzantine_strategy(self.effective)
        water_map_expression = profile.observation("strategy-water-map").expression
        transport_required_expression = profile.observation("strategy-transport-required").expression
        transport_expression = profile.observation("strategy-own-transport-capable").expression
        rebuild_expression = profile.observation("strategy-transport-rebuild-open").expression

        previous = WaterExecutionState(
            water_map=True,
            transport_required=True,
            transport_capable=True,
            transport_phase=TransportExecutionPhase.READY,
        )
        snapshot = RuntimeObservationSnapshot(
            previous_posture=StrategyPosture.BOOM,
            previous_water_execution_state=previous,
            fact_results=(
                (water_map_expression, True),
                (transport_required_expression, True),
                (transport_expression, False),
                (rebuild_expression, False),
            ),
        )

        runtime = evaluate_strategy_runtime(profile, self.effective, snapshot)

        self.assertIsNotNone(runtime.water_execution_state)
        self.assertEqual(
            runtime.water_execution_state.transport_phase,
            TransportExecutionPhase.RECOVER,
        )
        self.assertIn(
            ReassessmentReason.TRANSPORT_CAPABILITY_LOSS,
            runtime.reassessment_reasons,
        )

    def test_map_type_is_a_typed_native_profile_fact(self):
        registry = default_de_registry()
        map_assessment = registry.assess_support("map-type")
        warboat_assessment = registry.assess_support("warboat-count")

        self.assertEqual(map_assessment.state.value, "executable-safe")
        self.assertEqual(warboat_assessment.state.value, "executable-safe")

    def test_client_exports_typed_water_execution_surface(self):
        self.assertTrue(WaterExecutionPlan)
        self.assertTrue(WaterExecutionState)
        self.assertTrue(WaterPosture)


    def test_transport_demand_is_objective_driven_not_map_driven(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-transport-capability")
        req_text = " ".join(demand.execution.requirements)
        self.assertIn(profile.observation("strategy-water-map").expression, req_text)
        self.assertIn(profile.observation("strategy-transport-required").expression, req_text)
        self.assertIn("(building-type-count-total dock >= 1)", req_text)
        invalidation_refs = {
            evidence.observation_ref
            for evidence in demand.invalidation
            if evidence.observation_ref is not None
        }
        self.assertIn("strategy-transport-capability-lost", invalidation_refs)
        self.assertNotIn("strategy-transport-recovery", invalidation_refs)

    def test_pacific_fishing_bootstrap_activates_continuity_in_dark_age(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rules = {rule.identity: rule for rule in control.rules}
        bootstrap = rules["pacific-fishing-continuity-bootstrap"]
        facts = tuple(fact.source for fact in bootstrap.facts)
        self.assertIn("(map-type pacific-islands)", facts)
        self.assertIn(profile.observation("strategy-dock-exists").expression, facts)
        self.assertIn("(current-age >= dark-age)", facts)
        self.assertIn("(unit-type-count-total fishing-ship < 2)", facts)
        self.assertIn("(goal demand-water-fishing-continuity 0)", facts)
        self.assertIn(
            "(not (or (players-unit-type-count any-enemy galley-line >= 2) "
            "(players-unit-type-count any-enemy fire-galley-line >= 2)))",
            facts,
        )
        self.assertIn(
            "(set-goal demand-water-fishing-continuity 1)",
            tuple(action.source for action in bootstrap.actions),
        )

    def test_islands_fishing_bootstrap_activates_continuity_in_dark_age(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rules = {rule.identity: rule for rule in control.rules}
        bootstrap = rules["islands-fishing-continuity-bootstrap"]
        facts = tuple(fact.source for fact in bootstrap.facts)
        self.assertEqual(facts[0], "(map-type islands)")
        self.assertIn(profile.observation("strategy-dock-exists").expression, facts)
        self.assertIn("(current-age >= dark-age)", facts)
        self.assertIn("(unit-type-count-total fishing-ship < 2)", facts)
        self.assertIn("(goal demand-water-fishing-continuity 0)", facts)
        self.assertNotIn(
            "(not (or (players-unit-type-count any-enemy galley-line >= 2) "
            "(players-unit-type-count any-enemy fire-galley-line >= 2)))",
            facts,
        )
        self.assertIn(
            "(set-goal demand-water-fishing-continuity 1)",
            tuple(action.source for action in bootstrap.actions),
        )

    def test_pacific_transport_load_failure_uses_timer_only_for_reconsideration(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("pacific-transport-load-retry", state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        failure = rules["pacific-transport-lifecycle-load-failure-recover"]
        facts = tuple(fact.source for fact in failure.facts)
        self.assertIn("(goal pacific-transport-lifecycle 1)", facts)
        self.assertIn("(timer-triggered pacific-transport-load-retry)", facts)
        self.assertIn(
            "(up-compare-goal pacific-opening-transport-load-count < 4)",
            facts,
        )
        self.assertIn("(unit-type-count-total transport-ship >= 1)", facts)
        self.assertIn("(up-pending-objects c: 545 == 0)", facts)
        actions = tuple(action.source for action in failure.actions)
        self.assertIn("(set-goal pacific-transport-lifecycle 5)", actions)
        rearm = rules["pacific-transport-lifecycle-rearm-after-loss"]
        rearm_facts = tuple(fact.source for fact in rearm.facts)
        self.assertIn("(goal pacific-opening-transport-objective 1)", rearm_facts)
        self.assertIn("(goal pacific-transport-recovery 0)", rearm_facts)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", rearm_facts)
        rearm_actions = tuple(action.source for action in rearm.actions)
        self.assertIn("(set-goal pacific-transport-lifecycle 1)", rearm_actions)
        self.assertIn("(set-goal pacific-opening-transport-id 0)", actions)
        self.assertIn("(set-goal pacific-opening-transport-load-count 0)", actions)
        self.assertIn("(disable-timer pacific-transport-load-retry)", actions)

        load_witness = rules["pacific-transport-lifecycle-load-witness"]
        witness_facts = tuple(fact.source for fact in load_witness.facts)
        self.assertIn(
            "(up-compare-goal pacific-opening-transport-load-count >= 4)",
            witness_facts,
        )
        self.assertNotIn("(timer-triggered pacific-transport-load-retry)", witness_facts)

    def test_pacific_fishing_continuity_bootstraps_first_boat_without_feudal_escrow(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-fishing-continuity")
        requirements = " ".join(demand.execution.requirements)
        self.assertIn("(current-age >= dark-age)", requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)
        self.assertIn("(wood-amount >= 75)", requirements)
        self.assertIn("(can-train fishing-ship)", requirements)
        self.assertIn("(can-train-with-escrow fishing-ship)", requirements)
        self.assertEqual(demand.target.minimum, 2)

    def test_pacific_fishing_controller_is_typed_and_arbitrates_pressure(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        for expected in (
            "pacific-fishing-controller",
            "sn-maximum-fish-boat-drop-distance",
            "sn-fishing-boat-whaling-percentage",
            "sn-number-boat-explore-groups",
        ):
            self.assertIn(expected, state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        for expected in (
            "pacific-fishing-controller-open",
            "pacific-fishing-controller-enter-naval-defense",
            "pacific-fishing-controller-recover-from-naval-defense",
            "pacific-fishing-controller-dark",
            "pacific-fishing-controller-feudal",
            "pacific-fishing-controller-castle",
        ):
            self.assertIn(expected, rules)

        defense_text = " ".join(action.source for action in rules[
            "pacific-fishing-controller-enter-naval-defense"
        ].actions)
        self.assertIn(
            "(set-strategic-number sn-maximum-fish-boat-drop-distance -2)",
            defense_text,
        )
        self.assertIn(
            "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
            defense_text,
        )

        dark_text = " ".join(action.source for action in rules[
            "pacific-fishing-controller-dark"
        ].actions)
        self.assertIn(
            "(set-strategic-number sn-maximum-fish-boat-drop-distance 30)",
            dark_text,
        )

        feudal_text = " ".join(action.source for action in rules[
            "pacific-fishing-controller-feudal"
        ].actions)
        self.assertIn(
            "(set-strategic-number sn-maximum-fish-boat-drop-distance 48)",
            feudal_text,
        )

        castle_text = " ".join(action.source for action in rules[
            "pacific-fishing-controller-castle"
        ].actions)
        self.assertIn(
            "(set-strategic-number sn-maximum-fish-boat-drop-distance 96)",
            castle_text,
        )

    def test_pacific_harbor_defense_controller_owns_pressure_and_dock_arbitration(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("pacific-harbor-defense", state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        for expected in (
            "pacific-harbor-defense-open",
            "pacific-harbor-defense-close",
            "pacific-harbor-defense-close-no-dock",
            "pacific-harbor-defense-close-nonwater",
        ):
            self.assertIn(expected, rules)

        open_facts = " ".join(fact.source for fact in rules["pacific-harbor-defense-open"].facts)
        self.assertIn("(map-type pacific-islands)", open_facts)
        self.assertIn(profile.observation("strategy-enemy-naval-pressure").expression, open_facts)
        self.assertIn(profile.observation("strategy-dock-exists").expression, open_facts)

    def test_pacific_harbor_defense_gates_transport_and_preserves_escrow_naval_production(self):
        profile = build_byzantine_strategy(self.effective)

        transport = profile.demand("water-transport-capability")
        transport_requirements = " ".join(transport.execution.requirements)
        self.assertIn("(not (goal pacific-harbor-defense 1))", transport_requirements)
        self.assertIn("(can-train-with-escrow transport-ship)", transport_requirements)

        for identity, unit in (
            ("water-naval-defense", "fire-galley"),
            ("water-naval-control", "galley"),
        ):
            demand = profile.demand(identity)
            requirements = " ".join(demand.execution.requirements)
            self.assertIn(
                "(or (not (map-type pacific-islands)) (goal pacific-harbor-defense 1))",
                requirements,
            )
            self.assertIn(f"(can-train-with-escrow {unit})", requirements)

    def test_pacific_harbor_defense_closes_transport_execution_while_pressure_is_active(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rules = {rule.identity: rule for rule in control.rules}
        open_text = " ".join(
            fact.source for fact in rules["transport-objective-open"].facts
        )
        self.assertIn("(not (goal pacific-harbor-defense 1))", open_text)

        close_text = " ".join(
            fact.source for fact in rules["transport-objective-close"].facts
        )
        self.assertIn("(goal pacific-harbor-defense 1)", close_text)

        phase_text = " ".join(
            fact.source for fact in rules["transport-phase-no-longer-required"].facts
        )
        self.assertIn("(goal pacific-harbor-defense 1)", phase_text)

    def test_pacific_transport_escort_is_typed_and_blocks_unescorted_feudal_transport(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("pacific-transport-escort", state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        for expected in (
            "pacific-transport-escort-open",
            "pacific-transport-escort-ready",
            "pacific-transport-escort-rearm-on-loss",
            "pacific-transport-escort-close-on-pressure",
            "pacific-transport-escort-close-nonwater",
        ):
            self.assertIn(expected, rules)

        objective_open = " ".join(
            fact.source for fact in rules["transport-objective-open"].facts
        )
        self.assertIn("(goal pacific-transport-escort 2)", objective_open)

        pacific_transport_open = " ".join(
            fact.source for fact in rules["feudal-resource-island-transport-open"].facts
        )
        self.assertIn("(or (not (map-type pacific-islands)) (goal pacific-transport-escort 2))", pacific_transport_open)

    def test_pacific_transport_escort_uses_existing_fire_galley_escrow_channel(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-pacific-transport-escort")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertIn("(map-type pacific-islands)", requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)
        self.assertIn("(can-train-with-escrow fire-galley)", requirements)
        self.assertIn("(unit-type-count-total fire-galley < 1)", requirements)
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            requirements,
        )

    def test_pacific_transport_recovery_retains_a_post_landing_rebuild_entitlement(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("pacific-transport-recovery", state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        self.assertIn("pacific-transport-recovery-open-on-landed", rules)
        self.assertIn("pacific-transport-recovery-close-nonwater", rules)

    def test_pacific_transport_recovery_demand_uses_dock_pressure_and_escrow(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-pacific-transport-recovery")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertIn("(map-type pacific-islands)", requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            requirements,
        )
        self.assertIn("(can-train-with-escrow transport-ship)", requirements)
        self.assertIn("(unit-type-count-total transport-ship < 1)", requirements)

    def test_pacific_transport_recovery_rearms_lifecycle_without_replaying_landing(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rules = {rule.identity: rule for rule in control.rules}

        rebuild_text = " ".join(
            action.source
            for action in rules["pacific-transport-lifecycle-recover-after-rebuild"].actions
        )
        self.assertIn("(set-goal pacific-transport-lifecycle 0)", rebuild_text)

        recovery_open_text = " ".join(
            action.source
            for action in rules["pacific-transport-recovery-open-on-landed"].actions
        )
        self.assertIn("(set-goal pacific-transport-recovery 1)", recovery_open_text)

        recovery_loss_facts = " ".join(
            fact.source
            for fact in rules["pacific-transport-lifecycle-recover-after-landing-loss"].facts
        )
        self.assertIn("(goal pacific-transport-recovery 1)", recovery_loss_facts)
        self.assertIn("(unit-type-count-total transport-ship < 1)", recovery_loss_facts)

    def test_water_lowering_has_explicit_map_gate_and_recovery_reopen(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rules = {rule.identity: rule for rule in control.rules}
        transport = rules["water-posture-transport"]
        transport_facts = tuple(fact.source for fact in transport.facts)
        self.assertIn(profile.observation("strategy-water-map").expression, transport_facts)
        self.assertIn(profile.observation("strategy-transport-required").expression, transport_facts)
        self.assertIn("transport-phase-reopen", rules)

        prepare = rules["transport-phase-prepare"]
        prepare_text = " ".join(fact.source for fact in prepare.facts)
        self.assertNotIn("(goal transport-phase 3)", prepare_text)

    def test_stock_strategy_exposes_typed_water_execution_plan(self):
        profile = build_byzantine_strategy(self.effective)

        self.assertIsNotNone(profile.water_execution_plan)
        self.assertIn("strategy-water-map", {
            item.identity for item in profile.observations
        })
        self.assertIn("strategy-transport-required", {
            item.identity for item in profile.observations
        })

    def test_water_fishing_expansion_is_bounded_and_excludes_pacific(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-fishing-expansion")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(unit-type-count-total fishing-ship < 4)", requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            requirements,
        )
        self.assertIn("(building-type-count-total dock >= 1)", requirements)

    def test_pacific_opening_transport_objective_is_dark_age_starting_ship_gated(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rule = next(
            item for item in control.rules
            if item.identity == "pacific-opening-transport-open"
        )
        facts = tuple(fact.source for fact in rule.facts)
        self.assertIn("(map-type pacific-islands)", facts)
        self.assertIn("(current-age == dark-age)", facts)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", facts)

    def test_pacific_opening_transport_does_not_depend_on_army_attack_ready(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rule = next(
            item for item in control.rules
            if item.identity == "pacific-opening-transport-open"
        )
        text = " ".join(fact.source for fact in rule.facts)
        self.assertNotIn("byzantine-army-attack-ready", text)

    def test_transport_capability_is_a_feudal_execution_capability(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-transport-capability")
        requirements = tuple(demand.execution.requirements)
        self.assertIn("(current-age >= feudal-age)", requirements)
        self.assertNotIn("(current-age >= dark-age)", requirements)

    def test_naval_escalation_consumes_consolidated_enemy_naval_pressure_observation(self):
        profile = build_byzantine_strategy(self.effective)
        for identity in ("water-naval-defense", "water-naval-control"):
            demand = profile.demand(identity)
            requirements = " ".join(demand.execution.requirements)
            self.assertIn(
                profile.observation("strategy-enemy-naval-pressure").expression,
                requirements,
            )

    def test_water_fishing_continuity_starts_in_dark_age_after_dock(self):
        profile = build_byzantine_strategy(self.effective)
        demand = profile.demand("water-fishing-continuity")
        requirements = tuple(demand.execution.requirements)

        self.assertIn("(current-age >= dark-age)", requirements)
        self.assertNotIn("(current-age >= feudal-age)", requirements)
        self.assertIn("(building-type-count-total dock >= 1)", requirements)

    def test_water_plan_enables_native_boat_exploration_after_first_fishing_ship(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        rule = next(
            item for item in control.rules
            if item.identity == "water-boat-exploration-enable"
        )
        facts = tuple(fact.source for fact in rule.facts)
        actions = tuple(action.source for action in rule.actions)

        self.assertIn(profile.observation("strategy-water-map").expression, facts)
        self.assertIn(profile.observation("strategy-dock-exists").expression, facts)
        self.assertIn("(unit-type-count fishing-ship >= 1)", facts)
        self.assertIn("(set-strategic-number sn-number-boat-explore-groups 1)", actions)
        self.assertIn("(disable-self)", actions)

    def test_checked_in_runtime_contains_dark_age_water_continuity(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        runtime = (root / "Byzantine.per").read_text(encoding="utf-8")

        fishing_start = runtime.index(
            "; Action issuance: water-fishing-continuity | ACTIVE -> ISSUED"
        )
        fishing_end = runtime.index(
            "; Pending diagnostics: water-transport-capability",
            fishing_start,
        )
        fishing_rule = runtime[fishing_start:fishing_end]
        self.assertIn("(current-age >= dark-age)", fishing_rule)
        self.assertNotIn("(current-age >= feudal-age)", fishing_rule)
        self.assertIn("(can-train-with-escrow fishing-ship)", fishing_rule)
        self.assertIn("(defconst sn-number-boat-explore-groups 61)", runtime)
        self.assertIn("(set-strategic-number sn-number-boat-explore-groups 1)", runtime)

    def test_pacific_starting_transport_has_typed_execution_lifecycle(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        for expected in (
            "pacific-transport-lifecycle",
            "pacific-transport-transit-witness",
            "pacific-transport-unload-witness",
            "pacific-opening-transport-point",
            "pacific-opening-transport-id",
            "pacific-opening-transport-load-count",
            "pacific-opening-transport-transit-action",
            "pacific-opening-transport-distance",
            "pacific-opening-transport-unload-action",
            "pacific-opening-transport-unload-count",
        ):
            self.assertIn(expected, state_ids)

        rule_ids = {rule.identity for rule in control.rules}
        for expected in (
            "pacific-transport-lifecycle-open",
            "pacific-transport-lifecycle-load-witness",
            "pacific-transport-lifecycle-transit-witness",
            "pacific-transport-lifecycle-enter-unload",
            "pacific-transport-lifecycle-unload-witness",
            "pacific-transport-lifecycle-landed",
            "pacific-transport-lifecycle-recover-on-loss",
            "pacific-transport-lifecycle-rearm-after-loss",
        ):
            self.assertIn(expected, rule_ids)
        self.assertIn(
            "(up-compare-goal pacific-opening-transport-distance <= 64)",
            " ".join(
                fact.source
                for rule in control.rules
                if rule.identity == "pacific-transport-lifecycle-enter-unload"
                for fact in rule.facts
            ),
        )

    def test_water_plan_lowers_into_persistent_posture_and_transport_state(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)

        self.assertIsNotNone(compilation.control_plan)
        state_ids = {state.identifier for state in compilation.control_plan.states}
        self.assertIn("water-posture", state_ids)
        self.assertIn("transport-phase", state_ids)
        self.assertIn("water-transport-objective", state_ids)
        self.assertIn("water-transport-rebuild", state_ids)
        self.assertIn("pacific-opening-transport-objective", state_ids)

        rule_ids = {rule.identity for rule in compilation.control_plan.rules}
        self.assertIn("transport-phase-recover-on-capability-loss", rule_ids)
        self.assertIn("transport-phase-reopen", rule_ids)
        self.assertIn("transport-rebuild-authorize", rule_ids)
        self.assertIn("pacific-opening-transport-open", rule_ids)
        self.assertIn("pacific-opening-transport-close-at-feudal", rule_ids)
        self.assertIn("pacific-opening-transport-close-on-loss", rule_ids)
        self.assertIn("transport-objective-open", rule_ids)
        self.assertIn("transport-objective-close", rule_ids)
        self.assertIn("transport-phase-ready", rule_ids)
        self.assertIn("water-posture-naval-defense", rule_ids)
        self.assertIn("water-posture-naval-control", rule_ids)

    def test_feudal_resource_island_transport_state_is_feudal_and_fail_closed(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("feudal-resource-island-transport-objective", state_ids)

        open_rule = next(
            rule for rule in control.rules
            if rule.identity == "feudal-resource-island-transport-open"
        )
        open_facts = tuple(fact.source for fact in open_rule.facts)
        self.assertIn("(current-age >= feudal-age)", open_facts)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", open_facts)
        self.assertIn(
            profile.observation("strategy-water-map").expression,
            open_facts,
        )
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            open_facts,
        )
        self.assertNotIn("byzantine-army-attack-ready", " ".join(open_facts))

        close_rules = {
            rule.identity: rule
            for rule in control.rules
            if rule.identity.startswith("feudal-resource-island-transport-close-")
        }
        self.assertEqual(
            set(close_rules),
            {
                "feudal-resource-island-transport-close-nonwater",
                "feudal-resource-island-transport-close-before-feudal",
                "feudal-resource-island-transport-close-on-loss",
                "feudal-resource-island-transport-close-on-naval-pressure",
                "feudal-resource-island-transport-close-on-escort-loss",
            },
        )
        close_text = {
            identity: " ".join(fact.source for fact in rule.facts)
            for identity, rule in close_rules.items()
        }
        self.assertIn("(not (current-age >= feudal-age))", close_text["feudal-resource-island-transport-close-before-feudal"])
        self.assertIn("(not (unit-type-count-total transport-ship >= 1))", close_text["feudal-resource-island-transport-close-on-loss"])
        self.assertIn(
            profile.observation("strategy-enemy-naval-pressure").expression,
            close_text["feudal-resource-island-transport-close-on-naval-pressure"],
        )

    def test_pacific_transport_escort_controller_closes_feudal_transport_when_escort_is_lost(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None
        rules = {rule.identity: rule for rule in control.rules}

        close_text = " ".join(
            fact.source
            for fact in rules["feudal-resource-island-transport-close-on-escort-loss"].facts
        )
        self.assertIn("(map-type pacific-islands)", close_text)
        self.assertIn("(goal pacific-transport-escort 2)", close_text)

        escort_demand = profile.demand("water-pacific-transport-escort")
        self.assertIn(
            "(can-train-with-escrow fire-galley)",
            escort_demand.execution.requirements,
        )

    def test_pacific_convoy_route_falls_back_without_releasing_convoy_intent(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("pacific-convoy-route", state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        for expected in (
            "pacific-convoy-route-rearm-from-fallback",
            "pacific-convoy-route-close-on-pressure",
            "pacific-convoy-route-close-nonwater",
        ):
            self.assertIn(expected, rules)

        escort_loss_actions = tuple(
            action.source
            for action in rules["pacific-convoy-route-close-on-escort-loss"].actions
        )
        dock_loss_actions = tuple(
            action.source
            for action in rules["pacific-convoy-route-close-on-dock-loss"].actions
        )
        self.assertIn(
            "(set-goal pacific-convoy-route 4)",
            escort_loss_actions,
        )
        self.assertIn(
            "(set-goal pacific-convoy-route 4)",
            dock_loss_actions,
        )

        fallback_rearm = " ".join(
            fact.source
            for fact in rules["pacific-convoy-route-rearm-from-fallback"].facts
        )
        self.assertIn("(goal pacific-convoy-route 4)", fallback_rearm)
        self.assertIn("(unit-type-count-total transport-ship >= 1)", fallback_rearm)
        self.assertIn("(goal pacific-transport-escort 2)", fallback_rearm)
        self.assertIn(
            profile.observation("strategy-dock-exists").expression,
            fallback_rearm,
        )
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            fallback_rearm,
        )

    def test_pacific_convoy_route_owns_transport_and_escort_dispatch(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)
        control = compilation.control_plan
        assert control is not None

        state_ids = {state.identifier for state in control.states}
        self.assertIn("pacific-convoy-route", state_ids)

        rules = {rule.identity: rule for rule in control.rules}
        for expected in (
            "pacific-convoy-route-open",
            "pacific-convoy-route-activate",
            "pacific-convoy-route-recover-on-transport-loss",
            "pacific-convoy-route-rearm",
            "pacific-convoy-route-close-on-pressure",
            "pacific-convoy-route-close-on-dock-loss",
            "pacific-convoy-route-close-on-escort-loss",
            "pacific-convoy-route-close-nonwater",
        ):
            self.assertIn(expected, rules)

        open_text = " ".join(fact.source for fact in rules["pacific-convoy-route-open"].facts)
        self.assertIn("(current-age >= feudal-age)", open_text)
        self.assertIn(
            profile.observation("strategy-dock-exists").expression,
            open_text,
        )
        self.assertIn("(unit-type-count-total transport-ship >= 1)", open_text)
        self.assertIn("(goal pacific-transport-escort 2)", open_text)
        self.assertIn(
            f"(not {profile.observation('strategy-enemy-naval-pressure').expression})",
            open_text,
        )

    def test_stock_strategy_has_transport_and_naval_execution_demands(self):
        profile = build_byzantine_strategy(self.effective)
        demand_ids = {item.identity for item in profile.demands}

        self.assertIn("water-transport-capability", demand_ids)
        self.assertIn("water-naval-defense", demand_ids)
        self.assertIn("water-naval-control", demand_ids)


if __name__ == "__main__":
    unittest.main()
