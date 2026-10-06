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
        self.assertIn(profile.observation("strategy-transport-required").expression, req_text)
        self.assertIn("(building-type-count-total dock >= 1)", req_text)
        self.assertNotIn(profile.observation("strategy-water-map").expression, req_text)

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

    def test_water_plan_lowers_into_persistent_posture_and_transport_state(self):
        profile = build_byzantine_strategy(self.effective)
        compilation = lower_strategy_profile(profile, self.effective)

        self.assertIsNotNone(compilation.control_plan)
        state_ids = {state.identifier for state in compilation.control_plan.states}
        self.assertIn("water-posture", state_ids)
        self.assertIn("transport-phase", state_ids)
        self.assertIn("water-transport-objective", state_ids)
        self.assertIn("water-transport-rebuild", state_ids)

        rule_ids = {rule.identity for rule in compilation.control_plan.rules}
        self.assertIn("transport-phase-recover-on-capability-loss", rule_ids)
        self.assertIn("transport-phase-ready", rule_ids)
        self.assertIn("water-posture-naval-defense", rule_ids)
        self.assertIn("water-posture-naval-control", rule_ids)

    def test_stock_strategy_has_transport_and_naval_execution_demands(self):
        profile = build_byzantine_strategy(self.effective)
        demand_ids = {item.identity for item in profile.demands}

        self.assertIn("water-transport-capability", demand_ids)
        self.assertIn("water-naval-defense", demand_ids)
        self.assertIn("water-naval-control", demand_ids)


if __name__ == "__main__":
    unittest.main()
